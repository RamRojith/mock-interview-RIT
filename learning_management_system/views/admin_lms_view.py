

import re
from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from user_accounts.decorators import check_permission, is_super_user, no_cache
from learning_management_system.models import LMS_Permissions
from user_accounts.models import Role  # or wherever your Role model is



@no_cache
@is_super_user('lms_management')
def lms_assign_permission(request):
    if request.method == 'POST':  
        permissions = request.POST
        for role_name, role_permissions in permissions.items():
            if role_name.startswith('permissions'):
                try:
                    # Extract data from role_name using regex
                    extract_data = list(re.findall(r'\[([^\]]+)\]', role_name))
                    if len(extract_data) < 2:  # Ensure there are at least role and function
                        messages.warning(request,f"Invalid format in role_name: {role_name}. Skipping.")
                        continue
                    
                    extract_data.append(role_permissions)

                    # Retrieve the role (Handle if the role does not exist)
                    try:
                        role = Role.objects.using("rit_approval_system").get(role=extract_data[0])

                    except Role.DoesNotExist:
                        messages.error(request,f"Role {extract_data[0]} does not exist.")
                        messages.error(request, f"Role '{extract_data[0]}' does not exist. Skipping this entry.")
                        continue
                    
                    # Parse permissions - handle the case where role_permissions is a list (unlikely with POST data)
                    if isinstance(role_permissions, list):  # Handle list case
                        role_permissions = role_permissions[0]
                    
                    # Convert permission to boolean (True/False)
                    permission = extract_data[2] == 'true'
       

                    # Find or create FeedbackPermission object
                    permission_obj = LMS_Permissions.objects.filter(
                        role=role, function=extract_data[1]
                    ).first()
                    
                    if permission_obj:
                        permission_obj.permission = permission
                        permission_obj.save()
                    else:
                        # Create a new LMS_Permissions object
                        LMS_Permissions.objects.create(
                            role=role,
                            function=extract_data[1],
                            permission=permission
                        )
                except Exception as e:
                    # Catch unexpected errors and log them
                    messages.error(request,f"Error processing role '{role_name}': {str(e)}")
                    messages.error(request, f"An error occurred while processing '{role_name}': {str(e)}")

    # Redirect to admin dashboard after processing
    messages.success(request,"The permission changes have been successfully applied.")
    return redirect('lms_management')





from learning_management_system.decorators import lms_management


from django.http import HttpResponseForbidden

@lms_management
def lms_home(request):
    # # print("cm home page ")
    request.session['current_page'] = 'cm_home'
    # # print("Sfsdfsdk")
    return redirect('home')


ALLOWED_IPS = [
    "172.16.4.249:9000",   
   
   
]

def allow_only_ips(view_func):
    def wrapper(request, *args, **kwargs):
        ip = get_client_ip(request)

        if ip not in ALLOWED_IPS:
            return HttpResponseForbidden("Access denied: Unauthorized IP")

        return view_func(request, *args, **kwargs)
    return wrapper


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')



@check_permission("lms_hello")
@allow_only_ips
def lms_hello(request):
    return render(request, "lms_hello.html")
