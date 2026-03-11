"""
accounts/views.py
Authentication views: login, logout, role-based redirect,
one-time admin registration, and subscription pages.
"""
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import render, redirect
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views import View
from django.db import transaction

from accounts.decorators import role_required
from organizations.models import Organization
from .forms import AdminRegisterForm
from .models import User
from .utils import send_admin_activation_email


class CustomLoginView(LoginView):
    template_name = 'attendance/login.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['admin_exists'] = User.objects.filter(role=User.Role.ADMIN).exists()
        return context

    def post(self, request, *args, **kwargs):
        identifier = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user_obj = User.objects.filter(email__iexact=identifier).first()
        username = user_obj.username if user_obj else identifier

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect(self.get_success_url())

        messages.error(request, "Invalid login credentials.")
        return render(request, self.template_name, {
            'admin_exists': User.objects.filter(role=User.Role.ADMIN).exists()
        })

    def get_success_url(self):
        user = self.request.user

        if user.must_change_password:
            return reverse_lazy('force_password_change')

        if user.is_student:
            return reverse_lazy('student_dashboard')
        if user.is_teacher:
            return reverse_lazy('teacher_dashboard')
        return reverse_lazy('dashboard')


class AdminRegisterView(View):
    template_name = 'attendance/register_admin.html'

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        form = AdminRegisterForm()
        return render(request, self.template_name, {'form': form})

    @transaction.atomic
    def post(self, request):
        form = AdminRegisterForm(request.POST)

        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        try:
            email = form.cleaned_data['email'].strip().lower()

            organization = Organization.objects.create(
                name=form.cleaned_data['organization_name'].strip(),
                email=email,
                plan='FREE',
            )

            user = form.save(commit=False)
            user.organization = organization
            user.username = email
            user.email = email
            user.is_active = False
            user.save()

            try:
                send_admin_activation_email(user, request)
                messages.success(
                    request,
                    "Registration successful. Please check your email to activate your account."
                )
            except Exception:
                messages.warning(
                    request,
                    "Account created, but activation email could not be sent. Please check email configuration."
                )

            return redirect('login')

        except Exception:
            messages.error(request, "Unable to complete registration. Please try again.")
            return render(request, self.template_name, {'form': form})


class ActivateAdminAccountView(View):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            user.is_active = True
            user.save(update_fields=['is_active'])
            messages.success(request, "Your account has been activated. You can now sign in.")
            return redirect('login')

        return render(request, 'attendance/activation_invalid.html')


class ForcePasswordChangeView(PasswordChangeView):
    template_name = 'attendance/force_password_change.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        user = self.request.user
        user.must_change_password = False
        user.save(update_fields=['must_change_password'])
        messages.success(self.request, "Password updated successfully. Please log in again.")
        return super().form_valid(form)


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('index')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logout(request)
        return super().dispatch(request, *args, **kwargs)


class CustomPasswordResetView(PasswordResetView):
    template_name = 'attendance/password_reset_form.html'
    email_template_name = 'attendance/emails/password_reset_email.html'
    subject_template_name = 'attendance/emails/password_reset_subject.txt'
    html_email_template_name = 'attendance/emails/password_reset_email.html'
    success_url = reverse_lazy('password_reset_done')


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


@role_required(['ADMIN'])
def subscription_page(request):
    return render(
        request,
        'attendance/subscriptions/subscription.html',
        {'organization': request.user.organization}
    )


def subscription_expired(request):
    return render(request, 'attendance/subscriptions/subscription_expired.html')


def google_login_redirect(request):
    return redirect('/accounts/social/google/login/?process=login')