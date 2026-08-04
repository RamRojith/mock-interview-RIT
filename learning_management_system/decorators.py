from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from learning_management_system.models import LMS_Permissions

def lms_management(view_func):
    # @login_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Fetch and store role-based permissions
        permissions = {}
        role_permissions = LMS_Permissions.objects.filter(role=request.user.role)
        for permission in role_permissions:
            permissions[permission.function] = permission.permission  

        request.session['permissions'] = permissions

        # Store allowed pages (with friendly names)
        pages = {
            permission.function.replace('_', ' ').title(): permission.function
            for permission in role_permissions if permission.permission
        }
        # print("pages ---> ", pages)
        request.session['pages'] = sorted(pages.items(), key=lambda item: len(item[0]))
        # print("Pages->", request.session['pages'])

        # Set session flags
        request.session['auth'] = True
        request.session['app_name'] = "Learning Management System"  # Change this if needed

        return view_func(request, *args, **kwargs)

    return _wrapped_view
