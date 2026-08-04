from functools import wraps
from django.contrib.auth.decorators import login_required
from user_accounts.decorators import faculty_login_required
from feedback_management.models import FeedbackPermission

def feedback_management(view_func):
    # # print("faculty management decorator")
    # @faculty_login_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Fetch role permissions
        permissions={}
        role_permissions = FeedbackPermission.objects.filter(role=request.user.role)
        for permission in role_permissions:
            permissions[permission.function] = permission.permission  
        request.session['permissions'] = permissions
        request.session['app_name'] ="Feedback Management"
        # # print("App name => ", request.session['app_name'])
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
        # # print("Pages ===> ", request.session['pages'])
        # Authentication flag and app name
        request.session['auth'] = True
        request.session['app_name'] = "Feedback Management"

        return view_func(request, *args, **kwargs)

    return _wrapped_view







