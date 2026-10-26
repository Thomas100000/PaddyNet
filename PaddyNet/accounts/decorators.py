from functools import wraps
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied
from django.contrib import messages


def role_required(*allowed_roles):
    """
    Decorator that checks if the logged-in user has one of the allowed roles.
    - Unauthenticated users are redirected to login.
    - Authenticated users with the wrong role get a 403 PermissionDenied response,
      which renders the custom 403.html template.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')

            user_role = getattr(request.user, 'role', None)

            # Superusers or users with an allowed role can proceed
            if request.user.is_superuser or user_role in allowed_roles:
                return view_func(request, *args, **kwargs)

            # Authenticated but wrong role — return 403
            raise PermissionDenied

        return _wrapped_view
    return decorator
