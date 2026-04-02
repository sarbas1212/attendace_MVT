"""
teachers/views.py
CRUD views for teacher management and the teacher dashboard.
"""
from django.utils import timezone
from django.db.models import Count
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from accounts.models import User
from app.models import Absence, Student
from .forms import AssignTeacherForm, TeacherCreationForm
from .models import TeacherAssignment

from django.core.mail import send_mail
from django.conf import settings

# ──────────────────────────────────────────────
# Teacher Dashboard
# ──────────────────────────────────────────────
@role_required(['TEACHER'])
def teacher_dashboard(request):
    """Dashboard scoped to the logged-in teacher's assigned departments."""
    teacher = request.user
    organization = teacher.organization # Get org
    today = timezone.now().date()

    # Departments this teacher is assigned to (Filter by org)
    assignments = TeacherAssignment.objects.filter(
        teacher=teacher, 
        organization=organization
    ).select_related('department')
    departments = [a.department for a in assignments]

    # Students in those departments (Filter by org)
    students = Student.objects.filter(
        department__in=departments, 
        organization=organization,
        is_active=True
    )
    total_students = students.count()

    # Today's absence stats
    absences_today = Absence.objects.filter(date=today, student__in=students, organization=organization)
    total_absent_today = absences_today.count()
    total_present_today = total_students - total_absent_today
    attendance_percent = (
        round((total_present_today / total_students) * 100, 1) if total_students else 0
    )

    # Department-wise student counts
    department_stats = (
        students.values('department__name')
        .annotate(count=Count('id'))
        .order_by('department__name')
    )

    # Recent absentees today
    recent_absentees = absences_today.select_related('student', 'student__department')

    # Class teacher status
    class_teacher_departments = assignments.filter(is_class_teacher=True)

    context = {
        'today': today,
        'total_students': total_students,
        'total_present_today': total_present_today,
        'total_absent_today': total_absent_today,
        'attendance_percent': attendance_percent,
        'department_stats': department_stats,
        'recent_absentees': recent_absentees,
        'departments': departments,
        'class_teacher_departments': class_teacher_departments,
    }
    return render(request, 'attendance/teacher/teacher_dashboard.html', context)


# ──────────────────────────────────────────────
# Teacher CRUD (Admin Only)
# ──────────────────────────────────────────────
@role_required(['ADMIN'])
def add_teacher(request):
    organization = request.user.organization
    
    if request.method == 'POST':
        # PASS organization to form to filter dropdowns
        form = TeacherCreationForm(request.POST, organization=organization)
        if form.is_valid():
            teacher_user, temp_password = form.save(organization=organization)
            
            # Send Email
            subject = "Your Attendance System Account"
            message = (
                f"Hello {teacher_user.first_name},\n\n"
                f"Your teacher account has been created.\n\n"
                f"Login Details:\n"
                f"Username: {teacher_user.username}\n"
                f"Temporary Password: {temp_password}\n\n"
                f"Please login and change your password immediately.\n"
                f"Login URL: {request.build_absolute_uri('/accounts/login/')}\n\n"
                f"Thank you."
            )
            
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [teacher_user.email],
                    fail_silently=False,
                )
                messages.success(request, f"Teacher created and credentials emailed to {teacher_user.email}")
            except Exception as e:
                messages.warning(request, f"Teacher created, but email failed to send. Temp Password: {temp_password}")
                
            return redirect('list_teachers')
    else:
        form = TeacherCreationForm(organization=organization)

    return render(request, 'attendance/teacher/add_teacher.html', {'form': form, 'title': 'Add Teacher'})

@role_required(['ADMIN'])
def edit_teacher(request, pk):
    """Edit an existing teacher's profile and department assignment."""
    organization = request.user.organization
    
    # SECURITY: Only get teachers from THIS organization
    teacher_user = get_object_or_404(User, pk=pk, role='TEACHER', organization=organization)
    assignment = TeacherAssignment.objects.filter(teacher=teacher_user, organization=organization).first()

    if request.method == 'POST':
        # PASS organization to form
        form = TeacherCreationForm(request.POST, instance=teacher_user, organization=organization)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.organization = organization
            user.save()

            department = form.cleaned_data.get('department')
            subject = form.cleaned_data.get('subject') or 'General'

            if department:
                if assignment:
                    assignment.department = department
                    assignment.subject = subject
                    assignment.save()
                else:
                    TeacherAssignment.objects.create(
                        teacher=user,
                        department=department,
                        subject=subject,
                        organization=organization,
                    )
            elif assignment:
                assignment.delete()

            messages.success(request, "Teacher updated successfully!")
            return redirect('list_teachers')
    else:
        initial = {
            'department': assignment.department if assignment else None,
            'subject': assignment.subject if assignment else '',
        }
        form = TeacherCreationForm(instance=teacher_user, initial=initial, organization=organization)

    return render(request, 'attendance/teacher/add_teacher.html', {
        'form': form,
        'title': 'Edit Teacher',
        'edit_mode': True,
    })

@role_required(['ADMIN'])
def delete_teacher(request, pk):
    """Delete a teacher user and their assignments (POST-only)."""
    organization = request.user.organization
    
    # SECURITY: Only get teachers from THIS organization
    teacher_user = get_object_or_404(User, pk=pk, role='TEACHER', organization=organization)

    if request.method == 'POST':
        TeacherAssignment.objects.filter(teacher=teacher_user, organization=organization).delete()
        teacher_user.delete()
        messages.success(request, "Teacher deleted successfully!")
        return redirect('list_teachers')

    return render(request, 'attendance/app/delete_confirm.html', {
        'object': teacher_user,
        'object_type': 'Teacher',
        'cancel_url': 'list_teachers',
    })

@role_required(['ADMIN'])
def list_teachers(request):
    """List all teacher users with their department assignments."""
    organization = request.user.organization
    
    # SECURITY: Only list teachers from THIS organization
    teachers = User.objects.filter(role='TEACHER', organization=organization).order_by('username')

    for teacher in teachers:
        assignment = TeacherAssignment.objects.filter(teacher=teacher, organization=organization).first()
        teacher.department_name = assignment.department.name if assignment else "—"
        teacher.subject_name = assignment.subject if assignment else "—"
        teacher.is_class_teacher_flag = assignment.is_class_teacher if assignment else False

    return render(request, 'attendance/teacher/list_teachers.html', {'teachers': teachers})

# ──────────────────────────────────────────────
# Assign Teacher to Department
# ──────────────────────────────────────────────
@role_required(['ADMIN'])
def assign_teacher_department(request):
    """Assign a teacher to a department (or mark as class teacher)."""
    organization = request.user.organization
    
    if request.method == 'POST':
        # PASS organization to form
        form = AssignTeacherForm(request.POST, organization=organization)
        if form.is_valid():
            form.save(organization=organization)
            messages.success(request, "Teacher assigned successfully!")
            return redirect('list_teachers')
    else:
        form = AssignTeacherForm(organization=organization)

    return render(request, 'attendance/teacher/assign_teacher_department.html', {
        'form': form,
    })