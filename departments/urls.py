from django.urls import path
from . import views

urlpatterns = [

    path('add-department/', views.add_department, name='add_department'),
    path('departments/', views.list_departments, name='list_departments'),

    
]
