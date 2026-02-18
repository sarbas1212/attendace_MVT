"""
teachers/urls.py
URL patterns for teacher management and teacher dashboard.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('', views.list_teachers, name='list_teachers'),
    path('add/', views.add_teacher, name='add_teacher'),
    path('<int:pk>/edit/', views.edit_teacher, name='edit_teacher'),
    path('<int:pk>/delete/', views.delete_teacher, name='delete_teacher'),
    path('assign/', views.assign_teacher_department, name='assign_teacher_department'),
]
