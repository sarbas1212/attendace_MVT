from django.urls import path
from . import views

urlpatterns = [
    path('import/', views.import_students, name='import_students'),
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('absentees/', views.absentees_list, name='absentees_list'),
    path('mark/', views.mark_attendance, name='mark_attendance'),
    path('', views.dashboard, name='dashboard'),
    path('students/', views.students_list, name='students_list'),
    path('edit-attendance/', views.edit_attendance, name='edit_attendance'),

    path('students/edit/<int:pk>/', views.edit_student, name='edit_student'),
    path('students/delete/<int:pk>/', views.delete_student, name='delete_student'),





]
