from django.urls import path
from . import views
from .views import CustomLoginView, CustomLogoutView

urlpatterns = [
    # Auth
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),

    # Organization onboarding (Admin Registration)
    path('admin-register/', views.AdminRegisterView.as_view(), name='admin_register'),

    # Activation
    path('activate/<uidb64>/<token>/', views.ActivateAdminAccountView.as_view(), name='activate_admin_account'),

    # Force password change
    path('force-password-change/', views.ForcePasswordChangeView.as_view(), name='force_password_change'),

    # Password Reset (custom)
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Unauthorized
    path('unauthorized/', views.unauthorized_view, name='unauthorized'),

    # Subscription pages
    path('subscription/', views.subscription_page, name='subscription'),
    path('subscription-expired/', views.subscription_expired, name='subscription_expired'),

    # Razorpay payment endpoints (IMPORTANT)
    path('create-order/', views.create_order, name='create_order'),
    path('payment-success/', views.payment_success, name='payment_success'),

    # Google redirect helper
    path('google-login/', views.google_login_redirect, name='google_login'),

    path('account/', views.account_profile, name='account_profile'),
]