from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied
from functools import wraps

def role_required(allowed_roles=None):
    if allowed_roles is None:
        allowed_roles = []

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')  # redirects to your login URL

            if request.user.role not in allowed_roles:
                raise PermissionDenied  # 403 if role is not allowed

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
