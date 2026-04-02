from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from django.utils import timezone


class EnforcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and getattr(request.user, "must_change_password", False):
            allowed_urls = [
                reverse('force_password_change'),
                reverse('logout'),
            ]
            if request.path not in allowed_urls and not request.path.startswith('/admin/'):
                return redirect('force_password_change')

        return self.get_response(request)


class RoleBasedAccessMiddleware:
    """
    Global enterprise-level access control:
    - Public routes allowed
    - Auth required for protected routes
    - Must-change-password enforcement
    - Subscription/trial enforcement
    - Role-based route enforcement
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        user = request.user

        # 1) Allow static/media/admin
        if (
            path.startswith(settings.STATIC_URL)
            or path.startswith(settings.MEDIA_URL)
            or path.startswith('/admin/')
        ):
            return self.get_response(request)

        # 2) Public routes (no login required)
        public_routes = [
            reverse('index'),
            reverse('login'),
            reverse('password_reset'),
            reverse('password_reset_done'),
            reverse('password_reset_complete'),
            reverse('unauthorized'),
            reverse('admin_register'),
        ]

        if (
            path in public_routes
            or path.startswith('/accounts/reset/')
            or path.startswith('/accounts/activate/')
            or path.startswith('/accounts/social/')  # allauth routes
            or path.startswith('/accounts/google-login/')  # your redirect route if used
        ):
            return self.get_response(request)

        # 3) Anonymous users → index
        if not user.is_authenticated:
            return redirect('index')

        # 4) Ensure organization exists
        if not getattr(user, "organization", None):
            return redirect('unauthorized')

        org = user.organization

        # 5) Must change password enforcement
        if getattr(user, "must_change_password", False):
            allowed = [reverse('force_password_change'), reverse('logout')]
            if path not in allowed:
                return redirect('force_password_change')
            return self.get_response(request)

        # 6) Subscription / Trial enforcement (ADMIN only triggers payment gating)
        # Allow admins to access subscription/payment pages always
        subscription_allowed_prefixes = [
            '/accounts/subscription/',
            '/accounts/create-order/',
            '/accounts/payment-success/',
            '/accounts/subscription-expired/',
        ]

        is_subscription_path = any(path.startswith(p) for p in subscription_allowed_prefixes)

        # If trial is valid OR subscription is valid → allow
        trial_ok = hasattr(org, "is_trial_valid") and org.is_trial_valid()
        sub_ok = hasattr(org, "is_subscription_valid") and org.is_subscription_valid()

        # If admin and both trial+subscription invalid -> force subscription page
        if user.role == user.Role.ADMIN and not (trial_ok or sub_ok):
            if not is_subscription_path:
                return redirect('subscription')

        # Teachers/Students should also be blocked when org is expired (unless you want read-only access)
        if user.role in [user.Role.TEACHER, user.Role.STUDENT] and not (trial_ok or sub_ok):
            if not is_subscription_path:
                return redirect('subscription_expired')

        # 7) Role-based route protections
        
        # ═══════════════════════════════════════════════════════════════
        # TEACHER-ACCESSIBLE ROUTES (check BEFORE admin-only prefixes!)
        # ═══════════════════════════════════════════════════════════════
        teacher_accessible_routes = [
            '/teachers/dashboard/',
        ]

        if any(path == route or path.startswith(route) for route in teacher_accessible_routes):
            if user.role not in [user.Role.ADMIN, user.Role.TEACHER]:
                return redirect('unauthorized')
            return self.get_response(request) 
        # Admin-only routes
        admin_prefixes = [
            '/teachers/',
            '/departments/',
            '/admin-dashboard/',
        ]
        if any(path.startswith(prefix) for prefix in admin_prefixes):
            if user.role != user.Role.ADMIN:
                return redirect('unauthorized')

        # Admin + Teacher routes
        teacher_prefixes = [
            '/attendance/',
            '/teacher-dashboard/',
            '/reports/',
            '/calendar/',
        ]
        if any(path.startswith(prefix) for prefix in teacher_prefixes):
            if user.role not in [user.Role.ADMIN, user.Role.TEACHER]:
                return redirect('unauthorized')

        # Student allowed routes (adjust if needed)
        if user.role == user.Role.STUDENT:
            student_allowed = [
                '/student-dashboard/',
                '/my-attendance/',
                '/logout/',
                '/accounts/password-reset/',
                '/accounts/password-reset/done/',
                '/accounts/reset/',
            ]
            if not any(path.startswith(prefix) for prefix in student_allowed):
                return redirect('unauthorized')

        return self.get_response(request)


class DisableCacheMiddleware:
    """
    Prevents caching for authenticated pages to block back-button after logout.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.user.is_authenticated:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

        return response