from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from .models import User

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

        # 1. ALLOW PUBLIC ROUTES
        if path.startswith(settings.STATIC_URL) or path.startswith(settings.MEDIA_URL) or path.startswith('/admin/'):
            return self.get_response(request)

        public_routes = [
            reverse('index'),             # <--- ADD THIS: Your Landing Page
            reverse('login'),
            reverse('password_reset'),
            reverse('password_reset_done'),
            reverse('password_reset_complete'),
            reverse('unauthorized'),
        ]
        
        # Dynamic check for reset/activation
        if path in public_routes or path.startswith('/accounts/reset/') or path.startswith('/accounts/activate/'):
            return self.get_response(request)

        # 2. ANONYMOUS USER PROTECTION
        if not user.is_authenticated:
            # Change redirect from 'login' to 'index'
            return redirect('index') 

        # 3. FORCE PASSWORD CHANGE ENFORCEMENT
        if user.must_change_password:
            allowed = [reverse('force_password_change'), reverse('logout')]
            if path not in allowed:
                return redirect('force_password_change')
            return self.get_response(request)

        # 4. ROLE-BASED PATH PROTECTION
        
        # ADMIN ONLY ROUTES
        admin_prefixes = ['/teachers/', '/departments/', '/admin-dashboard/', '/accounts/admin-register/']
        if any(path.startswith(prefix) for prefix in admin_prefixes):
            if user.role != User.Role.ADMIN:
                return redirect('unauthorized')

        # TEACHER & ADMIN ROUTES (Attendance & Teacher Dashboard)
        teacher_prefixes = ['/attendance/', '/teacher-dashboard/', '/reports/'] 
        if any(path.startswith(prefix) for prefix in teacher_prefixes):
            if user.role not in [User.Role.ADMIN, User.Role.TEACHER]:
                return redirect('unauthorized')

        # STUDENT PROTECTION (Prevent students from accessing any management routes)
        if user.role == User.Role.STUDENT:
            # List of allowed prefixes for students
            student_allowed = ['/student-dashboard/', '/my-attendance/', '/logout/', '/password-reset/']
            # If a student tries to access something NOT in their allowed list
            if not any(path.startswith(prefix) for prefix in student_allowed):
                # But allow them to see the index/home page if applicable
                if path != '/':
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