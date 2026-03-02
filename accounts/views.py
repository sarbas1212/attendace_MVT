"""
accounts/views.py
Authentication views: login, logout, role-based redirect, and one-time admin registration.
"""
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.contrib import messages
from django.views import View
from django.shortcuts import render, redirect

# Internal imports
from .forms import AdminRegisterForm
from .models import User

from .utils import send_admin_activation_email

from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str  
from django.contrib.auth.tokens import default_token_generator


from django.contrib.auth.views import (
    PasswordResetView, 
    PasswordResetDoneView, 
    PasswordResetConfirmView, 
    PasswordResetCompleteView
)

from django.contrib.auth import logout
from django.contrib.auth.views import LogoutView

class CustomLoginView(LoginView):
    template_name = 'attendance/login.html'
    
    def get_context_data(self, **kwargs):
        """Pass admin_exists to template to show/hide registration link."""
        context = super().get_context_data(**kwargs)
        context['admin_exists'] = User.objects.filter(role=User.Role.ADMIN).exists()
        return context
    
    def get_success_url(self):
        user = self.request.user
        # FORCE CHANGE CHECK FIRST
        if user.must_change_password:
            return reverse_lazy('force_password_change')
            
        if user.is_student:
            return reverse_lazy('student_dashboard')
        elif user.is_teacher:
            return reverse_lazy('teacher_dashboard')
        return reverse_lazy('dashboard')

class AdminRegisterView(View):
    def dispatch(self, request, *args, **kwargs):
        if User.objects.filter(role=User.Role.ADMIN).exists():
            messages.error(request, "Admin registration is disabled.")
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        form = AdminRegisterForm()
        return render(request, 'attendance/register_admin.html', {'form': form})

    def post(self, request):
        form = AdminRegisterForm(request.POST)
        if form.is_valid():
            # Create user but do not activate yet
            user = form.save(commit=False)
            user.is_active = False 
            user.save()
            
            try:
                send_admin_activation_email(user, request)
                messages.success(request, "Registration successful! An activation email has been sent to your inbox.")
            except Exception as e:
                messages.error(request, "Registration successful, but the email system failed. Please contact support.")
            
            return redirect('login')
        return render(request, 'attendance/register_admin.html', {'form': form})

class ActivateAdminAccountView(View):
    """View to process the token link clicked in the email."""
    def get(self, request, uidb64, token):
        try:
            # Decode the user ID from the URL
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        # Verify the token is valid and belongs to this user
        if user is not None and default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            messages.success(request, "Your account has been activated! You can now log in.")
            return redirect('login')
        else:
            # Token is invalid or expired
            return render(request, 'attendance/activation_invalid.html')

class ForcePasswordChangeView(PasswordChangeView):
    template_name = 'attendance/force_password_change.html'
    success_url = reverse_lazy('login')
    
    def form_valid(self, form):
        # Set the flag to False once password is changed
        user = self.request.user
        user.must_change_password = False
        user.save()
        messages.success(self.request, "Password updated successfully. Please log in again.")
        return super().form_valid(form)

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('login')
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)
        return super().dispatch(request, *args, **kwargs)



class CustomPasswordResetView(PasswordResetView):
    template_name = 'attendance/password_reset_form.html'
    email_template_name = 'attendance/emails/password_reset_email.html'
    subject_template_name = 'attendance/emails/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')
    html_email_template_name = 'attendance/emails/password_reset_email.html' # Required for HTML emails

class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'attendance/password_reset_done.html'

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'attendance/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')

class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'attendance/password_reset_complete.html'
    
    def get(self, request, *args, **kwargs):
        messages.success(request, "Your password has been successfully updated. You may now log in.")
        return redirect('login')
    


def unauthorized_view(request):
    return render(request, 'attendance/unauthorized.html')