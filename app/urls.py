"""
app/urls.py
URL patterns for the core attendance module.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    # # Dashboard
    # path('', views.dashboard, name='dashboard'),

    # Student self-service
    path('my-attendance/', views.student_dashboard, name='student_dashboard'),

    # Attendance
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('absentees/', views.absentees_list, name='absentees_list'),

    # Student import
    path('import/', views.import_students, name='import_students'),

    # Student management
    path('students/', views.select_department, name='select_department'),
    path('students/department/<int:dept_id>/', views.students_list, name='students_list'),
    path('students/<int:pk>/detail/', views.student_detail, name='student_detail'),
    path('students/<int:pk>/edit/', views.edit_student, name='edit_student'),
    path('students/<int:pk>/delete/', views.delete_student, name='delete_student'),
    path('students/<int:pk>/reset-password/', views.reset_student_password, name='reset_student_password'),
    path('students/<int:pk>/change-password/', views.change_student_password, name='change_student_password'),
    path('students/<int:pk>/upload-photo/', views.upload_student_photo, name='upload_student_photo'),

    path('calendar/', views.calendar_view, name='calendar'),

    # app/urls.py
    path('debug/s3/', views.test_s3_config, name='test_s3'),
    # app/urls.py
    path('debug/photos/', views.debug_student_photos, name='debug_photos'),
]



