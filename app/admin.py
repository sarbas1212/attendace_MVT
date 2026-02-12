from django.contrib import admin
from .models import  Student, Absence
from departments.models import Department
from teachers.models import Teachers

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_name', 'roll_number', 'course_name', 'department')
    list_filter = ('department', 'course_name')

@admin.register(Teachers)
class TeachersAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'department')

@admin.register(Absence)
class AbsenceAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'date_time')
    list_filter = ('date', 'student__department')
