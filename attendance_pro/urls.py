"""
attendance_pro/urls.py
Root URL configuration.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('app.urls')),
    path('accounts/', include('accounts.urls')),
    path('teachers/', include('teachers.urls')),
    path('departments/', include('departments.urls')),
    path('reports/', include('reports.urls')),
]
