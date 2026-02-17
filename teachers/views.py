from django.utils import timezone
from  django.db.models import Count
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from app.models import Absence, Student
from accounts.models import User
from .forms import AssignTeacherForm, TeacherCreationForm, Teachers
from .models import Teachers

# Create your views here.

@role_required(['ADMIN'])
def assign_teacher_department(request):
    if request.method == 'POST':
        form = AssignTeacherForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Teacher assigned successfully!")
            return redirect('list_teachers')
    else:
        form = AssignTeacherForm()

    return render(request, 'attendance/assign_teacher_department.html', {'form': form})



@role_required(['TEACHER'])
def teacher_dashboard(request):
    teacher = request.user
    today = timezone.now().date()

    # Get departments assigned to this teacher
    assigned_departments = Teachers.objects.filter(teacher=teacher)
    departments = [td.department for td in assigned_departments]

    # Filter students by teacher's departments only
    students = Student.objects.filter(department__in=departments)

    # Total students in teacher's departments
    total_students = students.count()

    # Today's absences
    absences_today = Absence.objects.filter(date=today, student__in=students)
    total_absent_today = absences_today.count()

    # Total present today
    total_present_today = total_students - total_absent_today

    # Attendance percentage
    attendance_percent = round((total_present_today / total_students) * 100, 2) if total_students else 0

    # Course distribution within teacher's departments
    department_stats = students.values('department__name').annotate(count=Count('id'))


    # Recent absentees today
    recent_absentees = absences_today.select_related('student')

    # Check if teacher is class teacher for each department
    class_teacher_departments = assigned_departments.filter(is_class_teacher=True)

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

    return render(request, 'attendance/teacher_dashboard.html', context)

# ----------------------
# Teacher Views
# ----------------------
@role_required(['ADMIN'])
def add_teacher(request):
    if request.method == 'POST':
        form = TeacherCreationForm(request.POST)
        if form.is_valid():
            form.save()  # Saves User + optionally Teachers (department)
            messages.success(request, "✅ Teacher added successfully!")
            return redirect('list_teachers')
    else:
        form = TeacherCreationForm()
    return render(request, 'attendance/add_teacher.html', {'form': form})

@role_required(['ADMIN'])
def list_teachers(request):
    teachers = User.objects.filter(role='TEACHER')
    
    for teacher in teachers:
        # Get the teacher's record (Teachers table)
        td = Teachers.objects.filter(teacher=teacher).first()
        teacher.department_name = td.department.name if td and td.department else "—"
        teacher.teachers_record = td  # So we can access subject in template
    
    context = {
        'teachers': teachers,
    }
    return render(request, 'attendance/list_teachers.html', context)



# ------------------------
# Edit Teacher
# ------------------------
@role_required(['ADMIN'])
def edit_teacher(request, pk):
    teacher_user = get_object_or_404(User, pk=pk, role='TEACHER')
    
    # Try to get existing Teachers record (department + subject)
    try:
        teacher_record = Teachers.objects.get(teacher=teacher_user)
    except Teachers.DoesNotExist:
        teacher_record = None

    if request.method == 'POST':
        # Update User fields
        form = TeacherCreationForm(request.POST, instance=teacher_user)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(user.password)  # Update password if needed
            user.save()

            # Update or create Teachers record
            department = form.cleaned_data.get('department')
            subject = form.cleaned_data.get('subject')

            if teacher_record:
                teacher_record.department = department
                teacher_record.subject = subject
                teacher_record.save()
            elif department or subject:
                Teachers.objects.create(
                    teacher=user,
                    department=department,
                    subject=subject
                )

            messages.success(request, "✅ Teacher updated successfully!")
            return redirect('list_teachers')
    else:
        initial_data = {
            'department': teacher_record.department if teacher_record else None,
            'subject': teacher_record.subject if teacher_record else ''
        }
        form = TeacherCreationForm(instance=teacher_user, initial=initial_data)

    return render(request, 'attendance/add_teacher.html', {'form': form, 'edit_mode': True})

# ------------------------
# Delete Teacher
# ------------------------
@role_required(['ADMIN'])
def delete_teacher(request, pk):
    teacher_user = get_object_or_404(User, pk=pk, role='TEACHER')
    
    if request.method == 'POST':
        # Delete associated Teachers record if exists
        Teachers.objects.filter(teacher=teacher_user).delete()
        teacher_user.delete()
        messages.success(request, "❌ Teacher deleted successfully!")
        return redirect('list_teachers')

    # Optional: confirmation page
    return render(request, 'attendance/delete_teacher_confirm.html', {'teacher': teacher_user})