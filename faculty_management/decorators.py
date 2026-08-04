from functools import wraps
from faculty_management.models import FacultyFunction
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from user_accounts.decorators import faculty_login_required

def faculty_management(view_func):
    # # print("faculty management decorator")
    # @faculty_login_required
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Fetch role permissions
        permissions={}
        role_permissions = FacultyFunction.objects.filter(role=request.user.role)
        for permission in role_permissions:
            permissions[permission.function] = permission.permission  
        request.session['permissions'] = permissions
        request.session['app_name'] ="Faculty Management"
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
        
        # CRITICAL: Add Seminar Hall Booking pages for ALL faculty users
        # These pages should be available to everyone in Faculty Management
        current_pages = request.session.get('pages', [])
        
        # Remove old seminar hall booking menu items if they exist
        filtered_pages = [
            page for page in current_pages 
            if page[1] not in ['seminar_hall_booking', 'shb_my_approvals', 'shb_all_applications']
        ]
        
        # Check if hub already exists
        has_shb_hub = any(page[1] == 'shb_hub' for page in filtered_pages)
        
        # Add single seminar hall booking hub menu item
        if not has_shb_hub:
            new_pages = []
            inserted = False
            for page in filtered_pages:
                new_pages.append(page)
                if page[1] == 'faculty_timetable' and not inserted:
                    new_pages.append(('Seminar Hall Booking', 'shb_hub'))
                    inserted = True
            
            # If faculty_timetable not found, append at the end
            if not inserted:
                new_pages.append(('Seminar Hall Booking', 'shb_hub'))
            
            request.session['pages'] = new_pages
        else:
            request.session['pages'] = filtered_pages
        
        # # print("Pages ===> ", request.session['pages'])
        # Authentication flag and app name
        request.session['auth'] = True
        request.session['app_name'] = "Faculty Management"

        return view_func(request, *args, **kwargs)

    return _wrapped_view







