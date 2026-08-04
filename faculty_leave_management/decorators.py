from functools import wraps
from user_accounts.decorators import custom_forbidden
from faculty_leave_management.models import LeavePermissionFunction
from django.shortcuts import redirect


def faculty_leave_management(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login_view")

        role = getattr(request.user, "role", None)
        if role is None:
            return custom_forbidden(request)

        # Fetch role permissions
        role_permissions = LeavePermissionFunction.objects.filter(role=role)
        permissions = {
            perm.function: perm.permission
            for perm in role_permissions
        }
        request.session['permissions'] = permissions
        pages = {
            perm.function.replace('_', ' ').title(): perm.function
            for perm in role_permissions
            if perm.permission
        }
        request.session['pages'] = sorted(
            pages.items(), key=lambda item: len(item[0]), reverse=True
        )
        page= sorted(
            pages.items(), key=lambda item: len(item[0]), reverse=True
        )
        # Authentication flag and app name
        request.session['auth'] = True
        request.session['app_name'] = "Leave Management"

        return view_func(request, *args, **kwargs)

    return _wrapped_view
