from datetime import date, datetime
from django.contrib import messages

from django.utils import timezone
from django.http import JsonResponse
import pandas as pd
from django.shortcuts import render, redirect

from accounts.models import User
from .models import Absence, Student
from teachers.models import Teachers
from departments.models import Department
from .forms import UploadFileForm
from teachers.forms import AssignTeacherForm,TeacherCreationForm
from departments.forms import DepartmentForm
from django.db.models import Count
from django.db.models import Q

from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator

# from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import logout
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required

from accounts.decorators import role_required
# views.py




# class CustomLoginView(LoginView):
#     template_name = 'attendance/login.html'
#     redirect_authenticated_user = True

#     def get_success_url(self):
#         user = self.request.user
#         if user.role == 'STUDENT':
#             return reverse_lazy('my_attendance')
#         elif user.role == 'TEACHER':
#             return reverse_lazy('teacher_dashboard')
#         else:
#             return reverse_lazy('dashboard')  # Admin

# class CustomLogoutView(LogoutView):
#     next_page = reverse_lazy('login')

@role_required(['ADMIN', 'TEACHER'])
def import_students(request):

    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        department_id = request.POST.get('department')
        department = Department.objects.get(id=department_id)

        if form.is_valid():
            file = request.FILES['file']

            try:
                if file.name.endswith('.csv'):
                    df = pd.read_csv(file)
                elif file.name.endswith('.xlsx'):
                    df = pd.read_excel(file, engine='openpyxl')
                else:
                    raise Exception("Unsupported file format")
            except Exception as e:
                return render(request, 'attendance/import.html', {'form': form, 'error': str(e)})

            required_columns = ['Student Name', 'Roll Number', 'Course Name']
            if not all(col in df.columns for col in required_columns):
                return render(request, 'attendance/import.html', {'form': form, 'error': 'Required columns missing.'})

            for _, row in df.iterrows():
                Student.objects.update_or_create(
                    roll_number=row['Roll Number'],
                    defaults={
                        'student_name': row['Student Name'],
                        'course_name': row['Course Name'],
                        'department': department
                    }
                )

            messages.success(request, "✅ Students Imported Successfully!")
            return redirect('attendance_list')

    else:
        form = UploadFileForm()

    departments = Department.objects.all()
    return render(request, 'attendance/import.html', {'form': form, 'departments': departments})

@role_required(['ADMIN', 'TEACHER'])
def attendance_list(request):
    today = timezone.now().date()

    # Filter students based on teacher's department
    if request.user.role == 'TEACHER':
        teacher_departments = Teachers.objects.filter(teacher=request.user).values_list('department', flat=True)
        students = Student.objects.filter(department__in=teacher_departments).order_by('id')
    else:
        students = Student.objects.all().order_by('id')

    # Handle selected date
    selected_date_str = request.GET.get('date')
    if selected_date_str:
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
        if selected_date > today:
            selected_date = today
    else:
        selected_date = today

    if request.method == "POST":
        date_str = request.POST.get("date")
        if date_str:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if selected_date > today:
                selected_date = today

        for student in students:
            status = request.POST.get(f"status_{student.id}")
            if status == "absent":
                Absence.objects.get_or_create(student=student, date=selected_date)
            else:
                Absence.objects.filter(student=student, date=selected_date).delete()

        messages.success(request, "✅ Attendance Marked Successfully!")
        return redirect(f"{request.path}?date={selected_date.strftime('%Y-%m-%d')}")

    absent_ids = Absence.objects.filter(date=selected_date, student__in=students).values_list('student_id', flat=True)

    return render(request, 'attendance/attendance_list.html', {
        'students': students,
        'absent_ids': absent_ids,
        'selected_date': selected_date,
        'today': today
    })

@role_required(['ADMIN', 'TEACHER'])
def absentees_list(request):

    selected_date = request.POST.get("date")

    if selected_date:
        selected_date = date.fromisoformat(selected_date)
    else:
        selected_date = timezone.now().date()

    absentees = Absence.objects.filter(date=selected_date)

    return render(request, 'attendance/absentees.html', {
        'absentees': absentees,
        'selected_date': selected_date
    })



def mark_attendance(request):
    if request.method == "POST":
        student_id = request.POST.get("student_id")
        action = request.POST.get("action")

        if not student_id:
            return JsonResponse({"error": "No student ID"}, status=400)

        student = Student.objects.get(id=int(student_id))

        if action == "absent":
            Absence.objects.create(student=student)

        return JsonResponse({"status": "success"})
    



@role_required(['ADMIN'])
def dashboard(request):
    role = request.user.role

    if role == 'STUDENT':
        return redirect('my_attendance')

    if role == 'TEACHER':
        return redirect('teacher_dashboard')

    # Admin Dashboard
    today = timezone.now().date()

    # Attendance stats
    total_students = Student.objects.count()
    total_absent_today = Absence.objects.filter(date=today).count()
    total_present_today = total_students - total_absent_today
    attendance_percent = round((total_present_today / total_students) * 100, 2) if total_students else 0

    # Department & Teacher stats
    total_departments = Department.objects.count()
    total_teachers = Teachers.objects.count()  # correctly counting assigned teachers

    # Department-wise student and teacher counts
    departments = Department.objects.annotate(
        students_count=Count('students'),           # students linked to this department
        teachers_count=Count('teachers')   # teachers assigned via TeacherDepartment
    )

    # Recent absentees with department info
    recent_absentees = Absence.objects.filter(date=today).select_related('student', 'student__department')

    # Optional: course stats (still useful)
    course_stats = Student.objects.values('course_name').annotate(count=Count('id')).order_by('course_name')

    context = {
        'today': today,
        'total_students': total_students,
        'total_present_today': total_present_today,
        'total_absent_today': total_absent_today,
        'attendance_percent': attendance_percent,
        'total_departments': total_departments,
        'total_teachers': total_teachers,
        'departments': departments,
        'recent_absentees': recent_absentees,
        'course_stats': course_stats,
    }

    return render(request, 'attendance/dashboard.html', context)




# @role_required(['ADMIN'])
# def assign_teacher_department(request):
#     if request.method == 'POST':
#         form = AssignTeacherForm(request.POST)
#         if form.is_valid():
#             form.save()
#             messages.success(request, "✅ Teacher assigned successfully!")
#             return redirect('list_teachers')
#     else:
#         form = AssignTeacherForm()

#     return render(request, 'attendance/assign_teacher_department.html', {'form': form})



# @role_required(['TEACHER'])
# def teacher_dashboard(request):
#     teacher = request.user
#     today = timezone.now().date()

#     # Get departments assigned to this teacher
#     assigned_departments = TeacherDepartment.objects.filter(teacher=teacher)
#     departments = [td.department for td in assigned_departments]

#     # Filter students by teacher's departments only
#     students = Student.objects.filter(department__in=departments)

#     # Total students in teacher's departments
#     total_students = students.count()

#     # Today's absences
#     absences_today = Absence.objects.filter(date=today, student__in=students)
#     total_absent_today = absences_today.count()

#     # Total present today
#     total_present_today = total_students - total_absent_today

#     # Attendance percentage
#     attendance_percent = round((total_present_today / total_students) * 100, 2) if total_students else 0

#     # Course distribution within teacher's departments
#     course_stats = students.values('course_name').annotate(count=Count('id'))

#     # Recent absentees today
#     recent_absentees = absences_today.select_related('student')

#     # Check if teacher is class teacher for each department
#     class_teacher_departments = assigned_departments.filter(is_class_teacher=True)

#     context = {
#         'today': today,
#         'total_students': total_students,
#         'total_present_today': total_present_today,
#         'total_absent_today': total_absent_today,
#         'attendance_percent': attendance_percent,
#         'course_stats': course_stats,
#         'recent_absentees': recent_absentees,
#         'departments': departments,
#         'class_teacher_departments': class_teacher_departments,
#     }

#     return render(request, 'attendance/teacher_dashboard.html', context)



# ----------------------
# Department Views
# ----------------------
# @role_required(['ADMIN'])
# def add_department(request):
#     if request.method == 'POST':
#         form = DepartmentForm(request.POST)
#         if form.is_valid():
#             form.save()
#             messages.success(request, "✅ Department added successfully!")
#             return redirect('list_departments')
#     else:
#         form = DepartmentForm()
#     return render(request, 'attendance/add_department.html', {'form': form})

# @role_required(['ADMIN'])
# def list_departments(request):
#     departments = Department.objects.all()
#     return render(request, 'attendance/list_departments.html', {'departments': departments})




# # ----------------------
# # Teacher Views
# # ----------------------
# @role_required(['ADMIN'])
# def add_teacher(request):
#     if request.method == 'POST':
#         form = TeacherCreationForm(request.POST)
#         if form.is_valid():
#             form.save()  # Saves User + TeacherDepartment
#             messages.success(request, "✅ Teacher added successfully!")
#             return redirect('list_teachers')
#     else:
#         form = TeacherCreationForm()
#     return render(request, 'attendance/add_teacher.html', {'form': form})

# @role_required(['ADMIN'])
# def list_teachers(request):
#     # List teachers along with assigned department
#     teachers = TeacherDepartment.objects.select_related('teacher', 'department').all()
#     return render(request, 'attendance/list_teachers.html', {'teachers': teachers})




def students_list(request):
    query = request.GET.get('q')
    course_filter = request.GET.get('course')

    students = Student.objects.all().order_by('id')

    # 🔎 Search
    if query:
        students = students.filter(
            Q(student_name__icontains=query) |
            Q(roll_number__icontains=query)
        )

    # 🎓 Course Filter
    if course_filter:
        students = students.filter(course_name=course_filter)

    # 📚 Get distinct courses
    courses = Student.objects.values_list(
        'course_name',
        flat=True
    ).distinct()

    # 📄 Pagination (10 per page)
    paginator = Paginator(students, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'courses': courses,
        'selected_course': course_filter,
        'search_query': query
    }

    return render(request, 'attendance/students_list.html', context)




def edit_attendance(request):
    today = timezone.now().date()

    students = Student.objects.all().order_by('id')
    absentees = Absence.objects.filter(date=today)

    absent_student_ids = absentees.values_list('student_id', flat=True)

    if request.method == "POST":
        student_id = request.POST.get("student_id")
        action = request.POST.get("action")

        student = Student.objects.get(id=student_id)

        if action == "mark_absent":
            Absence.objects.get_or_create(
                student=student,
                date=today
            )

        elif action == "mark_present":
            Absence.objects.filter(
                student=student,
                date=today
            ).delete()

        return redirect('edit_attendance')

    context = {
        'students': students,
        'absent_student_ids': absent_student_ids,
        'today': today
    }

    return render(request, 'attendance/edit_attendance.html', context)




def edit_student(request, pk):
    student = get_object_or_404(Student, pk=pk)

    if request.method == "POST":
        student.student_name = request.POST.get("student_name")
        student.roll_number = request.POST.get("roll_number")
        student.course_name = request.POST.get("course_name")
        student.save()
        return redirect('students_list')

    return render(request, 'attendance/edit_student.html', {'student': student})


def delete_student(request, pk):
    student = get_object_or_404(Student, pk=pk)
    student.delete()
    return redirect('students_list')