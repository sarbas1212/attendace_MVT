from django.urls import path
from . import views

urlpatterns = [

    # path('login/', CustomLoginView.as_view(), name='login'),
    # path('logout/', CustomLogoutView.as_view(), name='logout'),

    path('import/', views.import_students, name='import_students'),
    path('attendance/', views.attendance_list, name='attendance_list'),
    path('absentees/', views.absentees_list, name='absentees_list'),
    path('mark/', views.mark_attendance, name='mark_attendance'),
    path('', views.dashboard, name='dashboard'),
    path('students/', views.students_list, name='students_list'),
    path('edit-attendance/', views.edit_attendance, name='edit_attendance'),

    path('students/edit/<int:pk>/', views.edit_student, name='edit_student'),
    path('students/delete/<int:pk>/', views.delete_student, name='delete_student'),

    # path('teacher-dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    # path('add-teacher/', add_teacher, name='add_teacher'),
    # path('teachers/', views.list_teachers, name='list_teachers'),
    # path('add-department/', views.add_department, name='add_department'),
    # path('departments/', views.list_departments, name='list_departments'),
    # # urls.py
    # path('assign-teacher-department/', views.assign_teacher_department, name='assign_teacher_department'),


]
