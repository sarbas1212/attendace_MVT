"""
app/admin.py
Django admin configuration for core models.
"""
from django.contrib import admin
from .models import Student, Absence
from departments.models import Department
from teachers.models import TeacherAssignment


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_name', 'roll_number', 'department', 'is_active', 'created_at')
    list_filter = ('department', 'is_active')
    search_fields = ('student_name', 'roll_number')


@admin.register(TeacherAssignment)
class TeacherAssignmentAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'department', 'subject', 'is_class_teacher', 'created_at')
    list_filter = ('department', 'is_class_teacher')
    search_fields = ('teacher__username', 'teacher__first_name', 'subject')


@admin.register(Absence)
class AbsenceAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'marked_by', 'created_at')
    list_filter = ('date', 'student__department')
    search_fields = ('student__student_name', 'student__roll_number')
    date_hierarchy = 'date'
