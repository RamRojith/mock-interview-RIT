from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from user_accounts.decorators import faculty_login_required
from data_center_management.models import Data_Center_Permission

def data_center_management(view_func):
    
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Use the raw external role id instead of request.user.role to avoid
        # cross-database FK resolution against the default database.
        permissions = {}
        role_id = getattr(request.user, "role_id", None)
        role_permissions = Data_Center_Permission.objects.filter(role_id=role_id)
        for permission in role_permissions:
            permissions[permission.function] = permission.permission  
        request.session['permissions'] = permissions
        request.session['app_name'] ="Data Center Management"
        
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
        request.session['app_name'] = "Data Center Management"

        return view_func(request, *args, **kwargs)

    return _wrapped_view






