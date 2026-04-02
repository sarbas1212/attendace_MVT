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
from .forms import UploadFileForm, StudentEditForm, StudentPasswordChangeForm,StudentPhotoForm
from .services import get_attendance_stats, import_students_from_file, mark_attendance_for_date

from django.http import HttpResponseRedirect

from .utils import is_working_day
import holidays
from django.conf import settings

from django.views.generic import UpdateView

from django.http import JsonResponse

from django.urls import path, include, reverse


def index(request):
    if request.user.is_authenticated:
        if request.user.is_student:
            return redirect('student_dashboard')
        elif request.user.is_teacher:
            return redirect('teacher_dashboard')
        return redirect('dashboard')
    return render(request, 'attendance/app/index.html')


@role_required(['ADMIN'])
def dashboard(request):
    today = timezone.now().date()
    org = request.user.organization

    all_students = Student.objects.filter(is_active=True, organization=org)
    stats = get_attendance_stats(all_students, today)

    total_departments = Department.objects.filter(is_active=True, organization=org).count()
    total_teachers = User.objects.filter(role='TEACHER', is_active=True, organization=org).count()

    departments = Department.objects.filter(is_active=True, organization=org).annotate(
        students_count=Count('students', filter=Q(students__is_active=True), distinct=True),
        teachers_count=Count('teacher_assignments', distinct=True),
    )

    recent_absentees = (
        Absence.objects.filter(
            date=today,
            student__is_active=True,
            organization=org
        )
        .select_related('student', 'student__department')
        .order_by('student__department__name', 'student__roll_number')
    )

    if request.GET.get("subscribed") == "1":
        messages.success(request, "Subscription activated successfully.")

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
    return render(request, 'attendance/app/dashboard.html', context)


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
    return render(request, 'attendance/app/student_dashboard.html', context)

@role_required(['ADMIN', 'TEACHER'])
def import_students(request):
    """
    Import students from an Excel/CSV file.
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
                # Add organization check for security
                department = get_object_or_404(Department, id=department_id, organization=request.user.organization)

            # Pass organization to service function
            organization = request.user.organization
            result = import_students_from_file(file, department, organization)

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

            # Redirect to the specific department's student list
            return redirect('students_list', dept_id=department.id)
    else:
        # IMPORTANT: Initialize form for GET requests (page load)
        form = UploadFileForm()

    # FIX: Filter departments by organization for security
    departments = Department.objects.filter(
        is_active=True,
        organization=request.user.organization
    )

    return render(request, 'attendance/app/import.html', {
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
    """
    today = timezone.now().date()
    organization = request.user.organization  # <-- Get organization early

    # 1. BUILD STUDENT QUERYSET (Role-based)
    if request.user.is_teacher:
        teacher_dept_ids = TeacherAssignment.objects.filter(
            teacher=request.user
        ).values_list('department_id', flat=True)
        students = Student.objects.filter(
            department_id__in=teacher_dept_ids, 
            is_active=True,
            organization=organization  # <-- Filter by org
        ).select_related('department')
    else:
        students = Student.objects.filter(
            is_active=True,
            organization=organization
        ).select_related('department')

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
        if selected_date > today:
            selected_date = today
    else:
        selected_date = today

    # 3. REAL-TIME CALENDAR CHECK
    is_workday, reason = is_working_day(selected_date)

    # 4. HANDLE POST (Attendance Submission)
    if request.method == "POST":
        if not is_workday:
            messages.error(request, f"Access Denied: Attendance cannot be recorded for a {reason}.")
            return redirect(f"{request.path}?date={selected_date.strftime('%Y-%m-%d')}")

        absent_ids = set()
        for student in students:
            status = request.POST.get(f"status_{student.id}")
            if status == "absent":
                absent_ids.add(student.id)

        # A. Save Absences - WITH ORGANIZATION
        mark_attendance_for_date(
            students, 
            absent_ids, 
            selected_date, 
            marked_by=request.user,
            organization=organization  # <-- FIXED
        )

        # B. CREATE ATTENDANCE SESSION
        if request.user.is_teacher:
            my_depts = TeacherAssignment.objects.filter(teacher=request.user).values_list('department_id', flat=True)
            for d_id in my_depts:
                AttendanceSession.objects.update_or_create(
                    date=selected_date, 
                    department_id=d_id,
                    organization=organization,  # <-- ADD THIS TOO
                    defaults={'marked_by': request.user}
                )
        else:
            if dept_filter:
                AttendanceSession.objects.update_or_create(
                    date=selected_date, 
                    department_id=dept_filter,
                    organization=organization,  # <-- ADD THIS TOO
                    defaults={'marked_by': request.user}
                )
            else:
                affected_depts = students.values_list('department_id', flat=True).distinct()
                for d_id in affected_depts:
                    AttendanceSession.objects.update_or_create(
                        date=selected_date, 
                        department_id=d_id,
                        organization=organization,  # <-- ADD THIS TOO
                        defaults={'marked_by': request.user}
                    )

        messages.success(request, f"Attendance saved for {selected_date.strftime('%d %b %Y')}")
        return redirect(f"{request.path}?date={selected_date.strftime('%Y-%m-%d')}")

    # 5. PREPARE CONTEXT DATA
    absent_ids = set(
        Absence.objects.filter(
            date=selected_date, 
            student__in=students,
            organization=organization  # <-- ADD THIS
        ).values_list('student_id', flat=True)
    )

    session_exists = AttendanceSession.objects.filter(
        date=selected_date, 
        department_id__in=students.values_list('department_id', flat=True),
        organization=organization  # <-- ADD THIS
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
        'departments': Department.objects.filter(is_active=True, organization=organization),
        'selected_department': dept_filter,
    }
    return render(request, 'attendance/app/attendance_list.html', context)

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
    return render(request, 'attendance/app/absentees.html', context)

# ──────────────────────────────────────────────
# Department Selection for Students
# ──────────────────────────────────────────────
@role_required(['ADMIN', 'TEACHER'])
def select_department(request):
    """Show departments to select for viewing students."""
    organization = request.user.organization

    # Teachers: only assigned departments
    if request.user.is_teacher:
        teacher_dept_ids = TeacherAssignment.objects.filter(
            teacher=request.user,
            organization=organization
        ).values_list('department_id', flat=True)

        departments = Department.objects.filter(
            id__in=teacher_dept_ids,
            organization=organization,
            is_active=True
        )
    else:
        # Admin: all departments in their org
        departments = Department.objects.filter(
            organization=organization,
            is_active=True
        )

    # IMPORTANT: Department -> Student related name is "students"
    departments = departments.annotate(
        student_count=Count(
            'students',
            filter=Q(students__is_active=True, students__organization=organization)
        )
    ).order_by('name')

    total_students = Student.objects.filter(
        organization=organization,
        is_active=True
    ).count()

    return render(request, 'attendance/app/select_department.html', {
        'departments': departments,
        'total_students': total_students,
    })

# ──────────────────────────────────────────────
# Students List (Department-specific)
# ──────────────────────────────────────────────
@role_required(['ADMIN', 'TEACHER'])
def students_list(request, dept_id=None):
    """List students for a specific department."""
    organization = request.user.organization
    query = request.GET.get('q', '')
    
    # Get the department
    if dept_id:
        department = get_object_or_404(
            Department, 
            pk=dept_id, 
            organization=organization,
            is_active=True
        )
    else:
        # Redirect to department selection if no dept_id
        return redirect('select_department')
    
    # Teachers can only view their assigned departments
    if request.user.is_teacher:
        teacher_dept_ids = TeacherAssignment.objects.filter(
            teacher=request.user,
            organization=organization
        ).values_list('department_id', flat=True)
        
        if department.id not in teacher_dept_ids:
            messages.error(request, "You don't have access to this department.")
            return redirect('select_department')
    
    # Get students in this department
    students = Student.objects.filter(
        department=department,
        organization=organization,
        is_active=True
    ).order_by('roll_number')
    
    # Search
    if query:
        students = students.filter(
            Q(student_name__icontains=query) |
            Q(roll_number__icontains=query)
        )
    
    # Pagination
    paginator = Paginator(students, 25)  # More per page since compact
    page_obj = paginator.get_page(request.GET.get('page'))
    
    return render(request, 'attendance/app/students_list.html', {
        'page_obj': page_obj,
        'department': department,
        'search_query': query,
        'total_count': paginator.count,
    })


# ──────────────────────────────────────────────
# Student Detail (AJAX/Modal)
# ──────────────────────────────────────────────
@role_required(['ADMIN', 'TEACHER'])
def student_detail(request, pk):
    """Get student details."""
    organization = request.user.organization
    student = get_object_or_404(Student, pk=pk, organization=organization, is_active=True)
    
    # Check teacher permission
    if request.user.is_teacher:
        teacher_dept_ids = TeacherAssignment.objects.filter(
            teacher=request.user,
            organization=organization
        ).values_list('department_id', flat=True)
        
        if student.department_id not in teacher_dept_ids:
            messages.error(request, "You don't have access to this student.")
            return redirect('select_department')
    
    # Get attendance stats
    total_absences = Absence.objects.filter(student=student).count()
    
    # Check if AJAX request (for modal) or regular request (for full page)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'attendance/app/student_detail_modal.html', {
            'student': student,
            'total_absences': total_absences,
        })
    
    return render(request, 'attendance/app/student_detail.html', {
        'student': student,
        'total_absences': total_absences,
    })


# ──────────────────────────────────────────────
# Student Edit
# ──────────────────────────────────────────────
@role_required(['ADMIN', 'TEACHER'])
def edit_student(request, pk):
    """Edit a student's details via ModelForm."""
    organization = request.user.organization
    student = get_object_or_404(Student, pk=pk, organization=organization)
    
    # Check teacher permission
    if request.user.is_teacher:
        teacher_dept_ids = TeacherAssignment.objects.filter(
            teacher=request.user,
            organization=organization
        ).values_list('department_id', flat=True)
        
        if student.department_id not in teacher_dept_ids:
            messages.error(request, "You don't have permission to edit this student.")
            return redirect('select_department')

    # Prepare Cancel URL
    cancel_url = reverse('students_list', kwargs={'dept_id': student.department_id})

    if request.method == "POST":
        form = StudentEditForm(request.POST, instance=student)
        if form.is_valid():
            student = form.save()
            from .services import sync_student_user
            sync_student_user(student, organization)
            
            messages.success(request, f"Student {student.student_name} updated successfully!")
            return redirect('students_list', dept_id=student.department_id)
    else:
        form = StudentEditForm(instance=student)

    return render(request, 'attendance/app/edit_student.html', {
        'form': form,
        'student': student,
        'cancel_url': cancel_url,
    })


# ──────────────────────────────────────────────
# Upload Student Photo
# ──────────────────────────────────────────────
@role_required(['ADMIN', 'TEACHER'])
def upload_student_photo(request, pk):
    organization = request.user.organization
    student = get_object_or_404(Student, pk=pk, organization=organization)

    # Check teacher permission
    if request.user.is_teacher:
        teacher_dept_ids = TeacherAssignment.objects.filter(
            teacher=request.user,
            organization=organization
        ).values_list('department_id', flat=True)

        if student.department_id not in teacher_dept_ids:
            messages.error(request, "You don't have permission to upload photo for this student.")
            return redirect('select_department')

    # IMPORTANT: Calculate Cancel URL
    cancel_url = reverse('students_list', kwargs={'dept_id': student.department_id})

    if request.method == 'POST':
        form = StudentPhotoForm(request.POST, request.FILES, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, f"Photo uploaded for {student.student_name}!")
            return redirect('students_list', dept_id=student.department_id)
        else:
            print(f"Form errors: {form.errors}")
            messages.error(request, f"Error: {form.errors}")
    else:
        form = StudentPhotoForm(instance=student)

    return render(request, 'attendance/app/upload_photo.html', {
        'form': form,
        'student': student,
        'cancel_url': cancel_url,  # <-- PASS THIS TO TEMPLATE
    })

# ──────────────────────────────────────────────
# Reset Student Password
# ──────────────────────────────────────────────
@role_required(['ADMIN', 'TEACHER'])
def reset_student_password(request, pk):
    """Reset a student's password back to the default format."""
    organization = request.user.organization
    student = get_object_or_404(Student, pk=pk, organization=organization)
    
    # Check teacher permission
    if request.user.is_teacher:
        teacher_dept_ids = TeacherAssignment.objects.filter(
            teacher=request.user,
            organization=organization
        ).values_list('department_id', flat=True)
        
        if student.department_id not in teacher_dept_ids:
            messages.error(request, "You do not have permission to reset this student's password.")
            return redirect('select_department')

    first_name = student.student_name.split()[0] if student.student_name else "student"
    default_pwd = f"{first_name.lower()}@{student.date_of_birth.year}" if student.date_of_birth else None

    if request.method == 'POST':
        if not student.date_of_birth:
            messages.error(request, f"Cannot reset password for {student.student_name} because Date of Birth is missing.")
        else:
            from .services import sync_student_user
            sync_student_user(student, organization, password_raw=default_pwd)
            messages.success(request, f"Password for {student.student_name} reset to: {default_pwd}")
            
        return redirect('students_list', dept_id=student.department_id)

    # Prepare Cancel URL
    cancel_url = reverse('students_list', kwargs={'dept_id': student.department_id})

    return render(request, 'attendance/app/reset_password_confirm.html', {
        'student': student,
        'default_pwd': default_pwd,
        'cancel_url': cancel_url,
    })

# ──────────────────────────────────────────────
# Change Student Password
# ──────────────────────────────────────────────
@role_required(['ADMIN', 'TEACHER'])
def change_student_password(request, pk):
    """Manually set a student's password."""
    organization = request.user.organization
    student = get_object_or_404(Student, pk=pk, organization=organization)
    
    # Check teacher permission
    if request.user.is_teacher:
        teacher_dept_ids = TeacherAssignment.objects.filter(
            teacher=request.user,
            organization=organization
        ).values_list('department_id', flat=True)
        
        if student.department_id not in teacher_dept_ids:
            messages.error(request, "You do not have permission to change this student's password.")
            return redirect('select_department')

    # Prepare Cancel URL
    cancel_url = reverse('students_list', kwargs={'dept_id': student.department_id})

    if request.method == 'POST':
        form = StudentPasswordChangeForm(request.POST)
        if form.is_valid():
            from .services import sync_student_user
            new_pwd = form.cleaned_data['new_password']
            sync_student_user(student, organization, password_raw=new_pwd)
            messages.success(request, f"Password for {student.student_name} updated successfully!")
            return redirect('students_list', dept_id=student.department_id)
    else:
        form = StudentPasswordChangeForm()

    return render(request, 'attendance/app/change_student_password.html', {
        'form': form,
        'student': student,
        'cancel_url': cancel_url,
    })


# ──────────────────────────────────────────────
# Delete Student
# ──────────────────────────────────────────────
@role_required(['ADMIN'])
def delete_student(request, pk):
    """Soft-delete a student (POST-only)."""
    organization = request.user.organization
    student = get_object_or_404(Student, pk=pk, organization=organization)
    dept_id = student.department_id

    if request.method == 'POST':
        student.is_active = False
        student.save()
        messages.success(request, "Student removed successfully!")
        return redirect('students_list', dept_id=dept_id)

    # FIX: Calculate full URL for Cancel button
    cancel_url = reverse('students_list', kwargs={'dept_id': dept_id})

    return render(request, 'attendance/app/delete_confirm.html', {
        'object': student,
        'object_type': 'Student',
        'cancel_url': cancel_url,
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

    return render(request, 'attendance/app/calendar.html', {
        'events': calendar_events
    })



# app/views.py

from django.http import JsonResponse

@role_required(['ADMIN'])
def test_s3_config(request):
    """Debug view to test S3 configuration."""
    from django.conf import settings
    from app.models import Student
    
    # Get a student with photo
    student_with_photo = Student.objects.filter(
        profile_photo__isnull=False
    ).exclude(profile_photo='').first()
    
    data = {
        'AWS_STORAGE_BUCKET_NAME': settings.AWS_STORAGE_BUCKET_NAME,
        'AWS_S3_REGION_NAME': settings.AWS_S3_REGION_NAME,
        'AWS_S3_CUSTOM_DOMAIN': getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', 'Not set'),
        'DEFAULT_FILE_STORAGE': settings.DEFAULT_FILE_STORAGE,
        'MEDIA_URL': settings.MEDIA_URL,
    }
    
    if student_with_photo:
        data['sample_student'] = student_with_photo.student_name
        data['photo_field_value'] = str(student_with_photo.profile_photo)
        try:
            data['photo_url'] = student_with_photo.profile_photo.url
        except Exception as e:
            data['photo_url_error'] = str(e)
    else:
        data['note'] = 'No students with photos found'
    
    return JsonResponse(data, json_dumps_params={'indent': 2})



from django.http import HttpResponse

@role_required(['ADMIN'])
def debug_student_photos(request):
    """Debug view to check student photos."""
    from app.models import Student
    
    html = "<h1>Student Photos Debug</h1><table border='1' cellpadding='10'>"
    html += "<tr><th>ID</th><th>Name</th><th>Photo Field</th><th>Photo URL</th><th>Preview</th></tr>"
    
    for student in Student.objects.all()[:10]:
        photo_field = str(student.profile_photo) if student.profile_photo else "None"
        try:
            photo_url = student.profile_photo.url if student.profile_photo else "None"
        except Exception as e:
            photo_url = f"Error: {e}"
        
        preview = ""
        if student.profile_photo:
            try:
                preview = f'<img src="{student.profile_photo.url}" width="50" height="50" style="object-fit: cover; border-radius: 50%;">'
            except:
                preview = "Error loading"
        
        html += f"<tr><td>{student.pk}</td><td>{student.student_name}</td><td>{photo_field}</td><td style='word-break: break-all; max-width: 300px;'>{photo_url}</td><td>{preview}</td></tr>"
    
    html += "</table>"
    return HttpResponse(html)