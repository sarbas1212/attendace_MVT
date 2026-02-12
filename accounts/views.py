from django.shortcuts import render
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView, LogoutView
# Create your views here.

class CustomLoginView(LoginView):
    template_name = 'attendance/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if user.role == 'STUDENT':
            return reverse_lazy('my_attendance')
        elif user.role == 'TEACHER':
            return reverse_lazy('teacher_dashboard')
        else:
            return reverse_lazy('dashboard')  # Admin

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('login')