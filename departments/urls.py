"""
departments/urls.py
URL patterns for department management.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.list_departments, name='list_departments'),
    path('add/', views.add_department, name='add_department'),
    path('<int:pk>/edit/', views.edit_department, name='edit_department'),
    path('<int:pk>/delete/', views.delete_department, name='delete_department'),
]
