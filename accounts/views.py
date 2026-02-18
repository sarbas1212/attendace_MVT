"""
accounts/views.py
Authentication views: login, logout, role-based redirect.
"""
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView, LogoutView


class CustomLoginView(LoginView):
    """Role-aware login — redirects each role to its appropriate dashboard."""
    template_name = 'attendance/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if user.is_student:
            return reverse_lazy('student_dashboard')
        elif user.is_teacher:
            return reverse_lazy('teacher_dashboard')
        return reverse_lazy('dashboard')  # Admin


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('login')