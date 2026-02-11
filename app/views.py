from django.utils import timezone
from django.http import JsonResponse
import pandas as pd
from django.shortcuts import render, redirect
from .models import Absence, Student
from .forms import UploadFileForm
from django.db.models import Count
from django.db.models import Q

from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
# views.py

def import_students(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['file']
            df = pd.read_excel(excel_file)

            required_columns = ['Student Name', 'Roll Number', 'Course Name']

            if not all(col in df.columns for col in required_columns):
                return render(request, 'attendance/import.html', {
                    'form': form,
                    'error': "Invalid Excel format!"
                })

            for _, row in df.iterrows():
                Student.objects.update_or_create(
                    roll_number=row['Roll Number'],
                    defaults={
                        'student_name': row['Student Name'],
                        'course_name': row['Course Name']
                    }
                )

            return redirect('attendance_list')
    else:
        form = UploadFileForm()

    return render(request, 'attendance/import.html', {'form': form})



def attendance_list(request):
    students = Student.objects.all().order_by('id')
    total_students = students.count()

    if total_students == 0:
        return render(request, 'attendance/attendance_list.html', {
            'no_students': True
        })

    current_index = request.session.get('current_index', 0)

    # If completed
    if current_index >= total_students:
        request.session['current_index'] = 0
        return redirect('absentees_list')

    student = students[current_index]

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "absent":
            today = timezone.now().date()

            Absence.objects.get_or_create(
                student=student,
                date=today
            )
        
        request.session['current_index'] = current_index + 1
        return redirect('attendance_list')

    progress_percent = int((current_index / total_students) * 100)

    return render(request, 'attendance/attendance_list.html', {
        'student': student,
        'current_index': current_index + 1,
        'total_students': total_students,
        'progress_percent': progress_percent
    })

def absentees_list(request):
    today = timezone.now().date()
    absentees = Absence.objects.filter(date=today)

    return render(request, 'attendance/absentees.html', {
        'absentees': absentees,
        'today': today
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
    



def dashboard(request):
    today = timezone.now().date()

    total_students = Student.objects.count()
    total_absent_today = Absence.objects.filter(date=today).count()

    total_present_today = total_students - total_absent_today

    attendance_percent = 0
    if total_students > 0:
        attendance_percent = int((total_present_today / total_students) * 100)

    course_stats = Student.objects.values('course_name') \
                                  .annotate(count=Count('id')) \
                                  .order_by('course_name')

    recent_absentees = Absence.objects.filter(date=today).select_related('student')

    context = {
        'total_students': total_students,
        'total_absent_today': total_absent_today,
        'total_present_today': total_present_today,
        'attendance_percent': attendance_percent,
        'course_stats': course_stats,
        'recent_absentees': recent_absentees,
        'today': today
    }

    return render(request, 'attendance/dashboard.html', context)



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