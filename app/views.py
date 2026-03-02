"""
app/views.py
Core views: Dashboard, Attendance, Students, Import, Absentees, Student Portal.
"""
from datetime import datetime

from django.utils import timezone
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required

from accounts.decorators import role_required
from accounts.models import User
from departments.models import Department
from teachers.models import TeacherAssignment
from .models import Absence, AttendanceSession, Student
from .forms import UploadFileForm, StudentEditForm, StudentPasswordChangeForm
from .services import get_attendance_stats, import_students_from_file, mark_attendance_for_date

from django.http import HttpResponseRedirect

from .utils import is_working_day
import holidays
from django.conf import settings


def index(request):
    if request.user.is_authenticated:
        if request.user.is_student:
            return redirect('student_dashboard')
        elif request.user.is_teacher:
            return redirect('teacher_dashboard')
        return redirect('dashboard')
    return render(request, 'attendance/index.html')


# ──────────────────────────────────────────────
# Admin Dashboard
# ──────────────────────────────────────────────
@role_required(['ADMIN'])
def dashboard(request):
    """Admin dashboard: system-wide attendance statistics and quick actions."""
    today = timezone.now().date()

    # System-wide stats
    all_students = Student.objects.filter(is_active=True)
    stats = get_attendance_stats(all_students, today)

    # Department & teacher counts
    total_departments = Department.objects.filter(is_active=True).count()
    total_teachers = User.objects.filter(role='TEACHER', is_active=True).count()

    # Department-wise stats
    departments = Department.objects.filter(is_active=True).annotate(
        students_count=Count('students', filter=Q(students__is_active=True), distinct=True),
        teachers_count=Count('teacher_assignments', distinct=True),
    )

    # Today's absentees
    recent_absentees = (
        Absence.objects.filter(date=today, student__is_active=True)
        .select_related('student', 'student__department')
        .order_by('student__department__name', 'student__roll_number')
    )

    context = {
        'today': today,
        'total_students': stats['total'],
        'total_present_today': stats['present'],
        'total_absent_today': stats['absent'],
        'attendance_percent': stats['percentage'],
        'total_departments': total_departments,
        'total_teachers': total_teachers,
        'departments': departments,
        'recent_absentees': recent_absentees,
    }
    return render(request, 'attendance/dashboard.html', context)


# ──────────────────────────────────────────────
# Student Dashboard (Student Login Portal)
# ──────────────────────────────────────────────
@role_required(['STUDENT'])
def student_dashboard(request):
    """
    Student self-service portal.
    Shows their own attendance percentage, present/absent day counts,
    and a history of absence records.
    """
    user = request.user

    # Find the student record linked to this user
    try:
        student = Student.objects.select_related('department').get(user=user)
    except Student.DoesNotExist:
        messages.error(request, "No student record is linked to your account. Please contact the administrator.")
        return render(request, 'attendance/student_dashboard.html', {'student': None})

    # Calculate attendance stats for this student
    today = timezone.now().date()
    total_absences = Absence.objects.filter(student=student).count()

    # Count total school days (distinct dates with any absence record in the system)
    # A simpler approach: count from the student's creation date to today
    from datetime import timedelta
    start_date = student.created_at.date() if student.created_at else today
    total_possible_days = max((today - start_date).days, 1)  # At least 1

    # Actually, let's count distinct dates where attendance was marked for student's department
    total_marked_days = (
        Absence.objects.filter(student__department=student.department)
        .values('date').distinct().count()
    )
    # If no attendance has been marked yet, use 1 to avoid division by zero
    if total_marked_days == 0:
        total_marked_days = 1

    days_present = total_marked_days - total_absences
    if days_present < 0:
        days_present = 0

    attendance_percent = round((days_present / total_marked_days) * 100, 1)

    # Absence history
    absence_history = (
        Absence.objects.filter(student=student)
        .order_by('-date')
        .select_related('marked_by')
    )

    context = {
        'student': student,
        'today': today,
        'total_marked_days': total_marked_days,
        'total_absences': total_absences,
        'days_present': days_present,
        'attendance_percent': attendance_percent,
        'absence_history': absence_history,
    }
    return render(request, 'attendance/student_dashboard.html', context)


# ──────────────────────────────────────────────
# Import Students from Excel/CSV
# ──────────────────────────────────────────────
@role_required(['ADMIN', 'TEACHER'])
def import_students(request):
    """
    Import students from an Excel/CSV file.
    - Teachers can only import into their assigned department.
    - Admins can choose any department.
    """
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']

            # Determine department
            if request.user.is_teacher:
                assignment = TeacherAssignment.objects.filter(teacher=request.user).first()
                if not assignment:
                    messages.error(request, "No department assigned to you. Contact the administrator.")
                    return redirect('import_students')
                department = assignment.department
            else:
                department_id = request.POST.get('department')
                if not department_id:
                    messages.error(request, "Please select a department.")
                    return redirect('import_students')
                department = get_object_or_404(Department, id=department_id)

            # Use service function for import
            result = import_students_from_file(file, department)

            if result['errors']:
                for error in result['errors']:
                    messages.warning(request, error)

            if result['created'] or result['updated']:
                messages.success(
                    request,
                    f"Import complete: {result['created']} created, {result['updated']} updated."
                )
            elif not result['errors']:
                messages.info(request, "No students were imported.")

            return redirect('students_list')
    else:
        form = UploadFileForm()

    departments = Department.objects.filter(is_active=True)
    return render(request, 'attendance/import.html', {
        'form': form,
        'departments': departments,
    })


# ──────────────────────────────────────────────
# Attendance Marking
# ──────────────────────────────────────────────
@role_required(['ADMIN', 'TEACHER'])
def attendance_list(request):
    """
    Mark / view attendance for a given date.
    Enforces 'Working Day' rules and creates 'Attendance Sessions'.
    """
    today = timezone.now().date()

    # 1. BUILD STUDENT QUERYSET (Role-based)
    if request.user.is_teacher:
        teacher_dept_ids = TeacherAssignment.objects.filter(
            teacher=request.user
        ).values_list('department_id', flat=True)
        students = Student.objects.filter(
            department_id__in=teacher_dept_ids, is_active=True
        ).select_related('department')
    else:
        students = Student.objects.filter(is_active=True).select_related('department')

    # Department filter (Admin only)
    dept_filter = request.GET.get('department')
    if dept_filter:
        students = students.filter(department_id=dept_filter)

    students = students.order_by('department__name', 'roll_number')

    # 2. HANDLE DATE SELECTION
    selected_date_str = request.GET.get('date') or request.POST.get('date')
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
        except ValueError:
            selected_date = today
        # Prevent marking future attendance
        if selected_date > today:
            selected_date = today
    else:
        selected_date = today

    # 3. REAL-TIME CALENDAR CHECK
    is_workday, reason = is_working_day(selected_date)

    # 4. HANDLE POST (Attendance Submission)
    if request.method == "POST":
        # Block marking if it's a Sunday/Holiday
        if not is_workday:
            messages.error(request, f"Access Denied: Attendance cannot be recorded for a {reason}.")
            return redirect(f"{request.path}?date={selected_date.strftime('%Y-%m-%d')}")

        absent_ids = set()
        for student in students:
            status = request.POST.get(f"status_{student.id}")
            if status == "absent":
                absent_ids.add(student.id)

        # A. Save Absences
        mark_attendance_for_date(students, absent_ids, selected_date, marked_by=request.user)

        # B. CREATE ERP ATTENDANCE SESSION
        # This record is what the system uses to calculate "Total Working Days"
        if request.user.is_teacher:
            # Teacher marks for all their assigned departments
            my_depts = TeacherAssignment.objects.filter(teacher=request.user).values_list('department_id', flat=True)
            for d_id in my_depts:
                AttendanceSession.objects.update_or_create(
                    date=selected_date, 
                    department_id=d_id,
                    defaults={'marked_by': request.user}
                )
        else:
            # Admin marks for a specific department if filter is active
            if dept_filter:
                AttendanceSession.objects.update_or_create(
                    date=selected_date, 
                    department_id=dept_filter,
                    defaults={'marked_by': request.user}
                )
            else:
                # If admin marks 'All Students', find every dept in the current student list
                affected_depts = students.values_list('department_id', flat=True).distinct()
                for d_id in affected_depts:
                    AttendanceSession.objects.update_or_create(
                        date=selected_date, 
                        department_id=d_id,
                        defaults={'marked_by': request.user}
                    )

        messages.success(request, f"Attendance officially finalized for {selected_date.strftime('%d %b %Y')}")
        return redirect(f"{request.path}?date={selected_date.strftime('%Y-%m-%d')}")

    # 5. PREPARE CONTEXT DATA
    absent_ids = set(
        Absence.objects.filter(
            date=selected_date, student__in=students
        ).values_list('student_id', flat=True)
    )

    # Check if an official session exists for the departments currently being viewed
    session_exists = AttendanceSession.objects.filter(
        date=selected_date, 
        department_id__in=students.values_list('department_id', flat=True)
    ).exists()

    context = {
        'students': students,
        'absent_ids': absent_ids,
        'selected_date': selected_date,
        'today': today,
        'is_workday': is_workday,
        'holiday_reason': reason if not is_workday else None,
        'session_exists': session_exists,
        'stats': get_attendance_stats(students, selected_date),
        'departments': Department.objects.filter(is_active=True),
        'selected_department': dept_filter,
    }
    return render(request, 'attendance/attendance_list.html', context)

# ──────────────────────────────────────────────
# Absentees List (with Print support)
# ──────────────────────────────────────────────
@role_required(['ADMIN', 'TEACHER'])
def absentees_list(request):
    """
    View absentees for a specific date (GET-based filter for bookmarkable URLs).
    Includes print-ready layout.
    """
    today = timezone.now().date()
    selected_date_str = request.GET.get('date')

    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
        except ValueError:
            selected_date = today
    else:
        selected_date = today

    # Department filter
    dept_filter = request.GET.get('department')
    absentees = Absence.objects.filter(
        date=selected_date, student__is_active=True
    ).select_related(
        'student', 'student__department', 'marked_by'
    )

    if dept_filter:
        absentees = absentees.filter(student__department_id=dept_filter)

    # For teachers, scope to their departments
    if request.user.is_teacher:
        teacher_dept_ids = TeacherAssignment.objects.filter(
            teacher=request.user
        ).values_list('department_id', flat=True)
        absentees = absentees.filter(student__department_id__in=teacher_dept_ids)

    departments = Department.objects.filter(is_active=True)

    context = {
        'absentees': absentees,
        'selected_date': selected_date,
        'today': today,
        'departments': departments,
        'selected_department': dept_filter,
        'total_absent': absentees.count(),
    }
    return render(request, 'attendance/absentees.html', context)


# ──────────────────────────────────────────────
# Students List
# ──────────────────────────────────────────────
@role_required(['ADMIN', 'TEACHER'])
def students_list(request):
    """List students with search, department filter, and pagination."""
    query = request.GET.get('q', '')
    dept_filter = request.GET.get('department', '')

    students = Student.objects.filter(is_active=True).select_related('department')

    # Teachers see only their department's students
    if request.user.is_teacher:
        teacher_dept_ids = TeacherAssignment.objects.filter(
            teacher=request.user
        ).values_list('department_id', flat=True)
        students = students.filter(department_id__in=teacher_dept_ids)

    # Search
    if query:
        students = students.filter(
            Q(student_name__icontains=query) |
            Q(roll_number__icontains=query)
        )

    # Department filter
    if dept_filter:
        students = students.filter(department_id=dept_filter)

    students = students.order_by('department__name', 'roll_number')

    # Pagination
    paginator = Paginator(students, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    departments = Department.objects.filter(is_active=True)

    context = {
        'page_obj': page_obj,
        'departments': departments,
        'selected_department': dept_filter,
        'search_query': query,
        'total_count': paginator.count,
    }
    return render(request, 'attendance/students_list.html', context)


# ──────────────────────────────────────────────
# Student Edit / Delete
# ──────────────────────────────────────────────
@role_required(['ADMIN', 'TEACHER'])
def edit_student(request, pk):
    """Edit a student's details via ModelForm."""
    student = get_object_or_404(Student, pk=pk)

    if request.method == "POST":
        form = StudentEditForm(request.POST, instance=student)
        if form.is_valid():
            student = form.save()
            # Ensure User account is synced
            from .services import sync_student_user
            sync_student_user(student)
            
            messages.success(request, f"Student {student.student_name} updated successfully!")
            return redirect('students_list')
    else:
        form = StudentEditForm(instance=student)

    return render(request, 'attendance/edit_student.html', {
        'form': form,
        'student': student,
    })


@role_required(['ADMIN', 'TEACHER'])
def reset_student_password(request, pk):
    """Reset a student's password back to the default format: firstname@YearofBirth (POST-only)."""
    student = get_object_or_404(Student, pk=pk)
    
    # Teachers can only reset passwords for students in their department
    if request.user.is_teacher:
        teacher_dept_ids = TeacherAssignment.objects.filter(teacher=request.user).values_list('department_id', flat=True)
        if student.department_id not in teacher_dept_ids:
            messages.error(request, "You do not have permission to reset this student's password.")
            return redirect('students_list')

    first_name = student.student_name.split()[0] if student.student_name else "student"
    default_pwd = f"{first_name.lower()}@{student.date_of_birth.year}" if student.date_of_birth else None

    if request.method == 'POST':
        if not student.date_of_birth:
            messages.error(request, f"Cannot reset password for {student.student_name} because Date of Birth is missing.")
        else:
            from .services import sync_student_user
            sync_student_user(student, password_raw=default_pwd)
            messages.success(request, f"Password for {student.student_name} reset to: {default_pwd}")
            
        return redirect('students_list')

    return render(request, 'attendance/reset_password_confirm.html', {
        'student': student,
        'default_pwd': default_pwd,
    })


@role_required(['ADMIN', 'TEACHER'])
def change_student_password(request, pk):
    """Manually set a student's password."""
    student = get_object_or_404(Student, pk=pk)
    
    # Teachers can only change passwords for students in their department
    if request.user.is_teacher:
        teacher_dept_ids = TeacherAssignment.objects.filter(teacher=request.user).values_list('department_id', flat=True)
        if student.department_id not in teacher_dept_ids:
            messages.error(request, "You do not have permission to change this student's password.")
            return redirect('students_list')

    if request.method == 'POST':
        form = StudentPasswordChangeForm(request.POST)
        if form.is_valid():
            from .services import sync_student_user
            new_pwd = form.cleaned_data['new_password']
            sync_student_user(student, password_raw=new_pwd)
            messages.success(request, f"Password for {student.student_name} updated successfully!")
            return redirect('students_list')
    else:
        form = StudentPasswordChangeForm()

    return render(request, 'attendance/change_student_password.html', {
        'form': form,
        'student': student,
    })


@role_required(['ADMIN'])
def delete_student(request, pk):
    """Soft-delete a student (POST-only)."""
    student = get_object_or_404(Student, pk=pk)

    if request.method == 'POST':
        student.is_active = False
        student.save()
        messages.success(request, "Student removed successfully!")
        return redirect('students_list')

    return render(request, 'attendance/delete_confirm.html', {
        'object': student,
        'object_type': 'Student',
        'cancel_url': 'students_list',
    })




@role_required(['ADMIN', 'TEACHER'])
def calendar_view(request):
    """View to display the institution calendar with holidays."""
    country_code = getattr(settings, 'ERP_REGION', 'IN')
    # Fetch holidays for current and next year
    current_year = timezone.now().year
    country_holidays = holidays.CountryHoliday(country_code, years=[current_year, current_year + 1])

    # Format holidays for FullCalendar JS
    calendar_events = []
    for date, name in country_holidays.items():
        calendar_events.append({
            'title': name,
            'start': date.isoformat(),
            'className': 'bg-danger-subtle text-danger border-danger'
        })

    return render(request, 'attendance/calendar.html', {
        'events': calendar_events
    })