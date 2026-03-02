from django.urls import path
from . import views

urlpatterns = [
    path('hub/', views.reports_hub, name='reports_hub'),
]
