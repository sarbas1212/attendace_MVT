"""
accounts/views.py
Authentication views: login, logout, role-based redirect,
admin registration, activation, password reset, and subscription pages.
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
from django.utils import timezone


import razorpay
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt


class CustomLoginView(LoginView):
    template_name = 'attendance/account/login.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['admin_exists'] = User.objects.filter(role=User.Role.ADMIN).exists()
        return context

    def post(self, request, *args, **kwargs):
        identifier = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # Allow email login by mapping email -> username
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

        # Force password change first
        if getattr(user, "must_change_password", False):
            return reverse_lazy('force_password_change')

        # If admin selected a plan before registering, go to subscription after login
        selected_plan = self.request.session.pop('selected_plan', None)
        if user.is_admin and selected_plan in ['MONTHLY', 'YEARLY']:
            return reverse_lazy('subscription')

        # Normal role redirects
        if user.is_student:
            return reverse_lazy('student_dashboard')
        if user.is_teacher:
            return reverse_lazy('teacher_dashboard')
        return reverse_lazy('dashboard')


class AdminRegisterView(View):
    """
    SaaS onboarding:
    - Creates Organization
    - Starts Free Trial (7 days)
    - Creates Admin User (inactive)
    - Sends activation email
    """
    template_name = 'attendance/account/register_admin.html'

    def dispatch(self, request, *args, **kwargs):
        # Multi-org enabled: do not block if admins exist
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        form = AdminRegisterForm()

        # Capture pre-selected plan from landing page
        plan = request.GET.get('plan')
        if plan in ['MONTHLY', 'YEARLY']:
            request.session['selected_plan'] = plan

        return render(request, self.template_name, {'form': form})

    @transaction.atomic
    def post(self, request):
        form = AdminRegisterForm(request.POST)

        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        try:
            email = form.cleaned_data['email'].strip().lower()

            # 1) Create organization
            organization = Organization.objects.create(
                name=form.cleaned_data['organization_name'].strip(),
                email=email,
            )

            # 2) Start free trial
            if hasattr(organization, "start_trial"):
                organization.start_trial(days=7)

            # 3) Create admin user
            user = form.save(commit=False)
            user.organization = organization
            user.username = email  # email as username
            user.email = email
            user.is_active = False
            user.save()

            # 4) Send activation email
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
    """
    Email activation for newly created admin
    """
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

        return render(request, 'attendance/account/activation_invalid.html')


class ForcePasswordChangeView(PasswordChangeView):
    template_name = 'attendance/account/force_password_change.html'
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
    template_name = 'attendance/account/password_reset_form.html'
    email_template_name = 'attendance/emails/password_reset_email.html'
    subject_template_name = 'attendance/emails/password_reset_subject.txt'
    html_email_template_name = 'attendance/emails/password_reset_email.html'
    success_url = reverse_lazy('password_reset_done')


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'attendance/account/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'attendance/account/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'attendance/password_reset_complete.html'

    def get(self, request, *args, **kwargs):
        messages.success(request, "Your password has been successfully updated. You may now log in.")
        return redirect('login')


def unauthorized_view(request):
    return render(request, 'attendance/account/unauthorized.html')


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




@require_POST
@role_required(['ADMIN'])
def create_order(request):
    plan = request.POST.get('plan')
    if plan not in ['MONTHLY', 'YEARLY']:
        return JsonResponse({'error': 'Invalid plan'}, status=400)

    amount = 99900 if plan == "MONTHLY" else 999900

    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    except Exception as e:
        return JsonResponse({'error': f'Razorpay client init failed: {str(e)}'}, status=500)

    try:
        order = client.order.create({
            "amount": amount,
            "currency": "INR",
            "payment_capture": 1
        })
    except Exception as e:
        # Show real reason in development
        if settings.DEBUG:
            return JsonResponse({'error': f'Razorpay order create failed: {str(e)}'}, status=500)
        return JsonResponse({'error': 'Unable to create Razorpay order. Try again.'}, status=500)

    org = request.user.organization
    org.razorpay_order_id = order.get("id")
    org.save(update_fields=["razorpay_order_id"])

    return JsonResponse({
        "key": settings.RAZORPAY_KEY_ID,
        "order_id": order["id"],
        "amount": amount
    })


@csrf_exempt
@require_POST
@role_required(['ADMIN'])
def payment_success(request):
    plan = request.POST.get("plan")
    payment_id = request.POST.get("payment_id")

    if plan not in ['MONTHLY', 'YEARLY'] or not payment_id:
        return JsonResponse({"error": "Invalid request"}, status=400)

    org = request.user.organization
    org.razorpay_payment_id = payment_id
    org.save(update_fields=["razorpay_payment_id"])

    try:
        if plan == "MONTHLY":
            org.activate_monthly()
        else:
            org.activate_yearly()
    except Exception:
        return JsonResponse({"error": "Payment received but activation failed"}, status=500)

    return JsonResponse({"status": "success"})





@role_required(['ADMIN', 'TEACHER', 'STUDENT'])
def account_profile(request):
    user = request.user
    org = getattr(user, "organization", None)

    context = {
        "profile_user": user,
        "org": org,
        "today": timezone.now().date(),
        "trial_ok": org.is_trial_valid() if org and hasattr(org, "is_trial_valid") else False,
        "sub_ok": org.is_subscription_valid() if org and hasattr(org, "is_subscription_valid") else False,
    }
    return render(request, "attendance/account/profile.html", context)