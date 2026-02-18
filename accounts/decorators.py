"""
accounts/decorators.py
Role-based access control decorator for function-based views.
"""
from functools import wraps
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied


def role_required(allowed_roles=None):
    """
    Decorator that restricts view access to users whose role
    is in the *allowed_roles* list.

    Usage::

        @role_required(['ADMIN', 'TEACHER'])
        def my_view(request):
            ...
    """
    if allowed_roles is None:
        allowed_roles = []

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.role not in allowed_roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
