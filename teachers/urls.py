from django.urls import path
from . import views


urlpatterns = [



    path('teacher-dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('add-teacher/', views.add_teacher, name='add_teacher'),
    path('teachers/', views.list_teachers, name='list_teachers'),
    path('assign-teacher-department/', views.assign_teacher_department, name='assign_teacher_department'),
    path('teachers/edit/<int:pk>/', views.edit_teacher, name='edit_teacher'),
    path('teachers/delete/<int:pk>/', views.delete_teacher, name='delete_teacher'),

]
