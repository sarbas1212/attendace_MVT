from django.urls import path, include
from . import views
from .views import CustomLoginView, CustomLogoutView

urlpatterns = [

    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),

    # Password Reset
    path('', include('django.contrib.auth.urls')),
]