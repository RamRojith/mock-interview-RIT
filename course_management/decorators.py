from functools import wraps
from course_management.models import CourseandexaminationFunction
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from user_accounts.decorators import faculty_login_required

def course_management(view_func):
    
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Fetch role permissions
        permissions={}
        role_permissions = CourseandexaminationFunction.objects.filter(role=request.user.role)
        for permission in role_permissions:
            permissions[permission.function] = permission.permission  
        request.session['permissions'] = permissions
        request.session['app_name'] ="Course & Examination"
        
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
        request.session['app_name'] = "Course & Examination"

        return view_func(request, *args, **kwargs)

    return _wrapped_view







