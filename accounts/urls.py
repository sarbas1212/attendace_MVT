from django.urls import path, include
from . import views
from .views import CustomLoginView, CustomLogoutView

urlpatterns = [

    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('admin-register/', views.AdminRegisterView.as_view(), name='admin_register'),
    # Activation URL
    path('activate/<uidb64>/<token>/', views.ActivateAdminAccountView.as_view(), name='activate_admin_account'),    
    path('force-password-change/', views.ForcePasswordChangeView.as_view(), name='force_password_change'),
    # Password Reset
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),

    path('unauthorized/', views.unauthorized_view, name='unauthorized'),
]