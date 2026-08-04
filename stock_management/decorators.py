from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from user_accounts.decorators import faculty_login_required
from stock_management.models import Stock_Permission

def stock_management(view_func):

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Admin (superuser): keep the existing admin sidebar untouched — do NOT
        # build a stock module sidebar for any card. The existing sidebar is enough.
        if getattr(request.user, "is_superuser", False):
            return view_func(request, *args, **kwargs)

        # Fetch role permissions
        permissions={}
        role_permissions = Stock_Permission.objects.filter(role=request.user.role)
        for permission in role_permissions:
            permissions[permission.function] = permission.permission
        request.session['permissions'] = permissions
        request.session['app_name'] ="Stock Management"

        request.session['pages'] = list(
            sorted(
                {word.replace('_', ' ').title(): word
                for word in set([permission.function
                                for permission in role_permissions
                                if permission.permission] )
                }.items(),
                key=lambda item: len(item[0]),
                reverse=False
            )
        )

        request.session['auth'] = True
        request.session['app_name'] = "Stock Management"

        return view_func(request, *args, **kwargs)

    return _wrapped_view
