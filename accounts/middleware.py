from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from .models import User
from django.utils import timezone

class EnforcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.must_change_password:
            allowed_urls = [
                reverse('force_password_change'),
                reverse('logout'),
                # Add admin URLs if you want admins to be exempt
            ]
            
            if request.path not in allowed_urls and not request.path.startswith('/admin/'):
                return redirect('force_password_change')

        return self.get_response(request)
    

class RoleBasedAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        user = request.user

        # ✅ 1. Allow static, media, admin
        if (
            path.startswith(settings.STATIC_URL)
            or path.startswith(settings.MEDIA_URL)
            or path.startswith('/admin/')
        ):
            return self.get_response(request)

        public_routes = [
            reverse('index'),
            reverse('login'),
            reverse('password_reset'),
            reverse('password_reset_done'),
            reverse('password_reset_complete'),
            reverse('unauthorized'),
        ]

        if (
            path in public_routes
            or path.startswith('/accounts/reset/')
            or path.startswith('/accounts/activate/')
        ):
            return self.get_response(request)

        # ✅ 2. Anonymous users
        if not user.is_authenticated:
            return redirect('index')

        # ✅ 3. Enforce Organization existence
        if not user.organization:
            return redirect('unauthorized')

        # ✅ 4. Enforce Subscription Validity
        org = user.organization
        if org.plan != "FREE":
            if not org.subscription_end or org.subscription_end < timezone.now().date():
                return redirect('subscription_expired')

        # ✅ 5. Force Password Change
        if user.must_change_password:
            allowed = [reverse('force_password_change'), reverse('logout')]
            if path not in allowed:
                return redirect('force_password_change')

        # ✅ 6. Role-based Access Control

        # Admin only routes
        admin_prefixes = [
            '/teachers/',
            '/departments/',
            '/admin-dashboard/',
            '/accounts/admin-register/',
        ]

        if any(path.startswith(prefix) for prefix in admin_prefixes):
            if user.role != user.Role.ADMIN:
                return redirect('unauthorized')

        # Teacher + Admin routes
        teacher_prefixes = [
            '/attendance/',
            '/teacher-dashboard/',
            '/reports/',
            '/calendar/',
        ]

        if any(path.startswith(prefix) for prefix in teacher_prefixes):
            if user.role not in [user.Role.ADMIN, user.Role.TEACHER]:
                return redirect('unauthorized')

        # Student isolation
        if user.role == user.Role.STUDENT:
            student_allowed = [
                '/student-dashboard/',
                '/logout/',
                '/password-reset/',
            ]
            if not any(path.startswith(prefix) for prefix in student_allowed):
                return redirect('unauthorized')

        return self.get_response(request)

class DisableCacheMiddleware:
    """
    Prevents the browser from caching sensitive pages.
    Ensures that clicking the 'Back' button after logout 
    forces a fresh request to the server.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Only apply to authenticated users to avoid caching dashboard data
        if request.user.is_authenticated:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            
        return response