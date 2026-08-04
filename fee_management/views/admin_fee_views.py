from django.http import HttpResponse
from django.shortcuts import render, redirect


from django.shortcuts import render, redirect
from django.contrib import messages
from datetime import datetime

from django.shortcuts import render, redirect
from django.contrib import messages
from datetime import datetime, timedelta


from user_accounts.models import USER
from django.utils import timezone
from collections import defaultdict
from user_accounts.decorators import faculty_login_required, no_cache, is_super_user
from user_accounts.models import Role
import re
from fee_management.models import FeePerimissonFunction
from user_accounts.decorators import check_permission
from fee_management.decorators import fee_management

@check_permission("fee_hello")
def fee_hello(request):
    return render(request, "em_hello.html")




# @faculty_login_required
@fee_management
def fee_home(request):
    # print("fm home page ")
    request.session['current_page'] = 'fee_home'
    return redirect('home')




@faculty_login_required
@no_cache
@is_super_user('course_management')
def fee_assign_permission(request):
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
       
                    
                    # Find or create ApprovalPermissionFunction object
                    permission_obj = FeePerimissonFunction.objects.filter(
                        role=role, function=extract_data[1]
                    ).first()
                    
                    if permission_obj:
                        permission_obj.permission = permission
                        permission_obj.save()
                    else:
                        # Create a new ApprovalPermissionFunction object
                        FeePerimissonFunction.objects.create(
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
    return redirect('fee_management')



from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.core.paginator import Paginator

from user_accounts.models import Role
from fee_management.models import Fee_Permission


def assign_fee_view_permission(request):
    edit_permission = None

    # ---------- DELETE ----------
    if request.method == "POST" and request.POST.get("action") == "delete":
        perm_id = request.POST.get("perm_id")
        Fee_Permission.objects.filter(id=perm_id).delete()
        messages.success(request, "Fee view permission deleted")
        return redirect("assign_fee_view_permission")

    # ---------- EDIT LOAD (optional future use) ----------
    if request.method == "GET" and request.GET.get("edit"):
        edit_permission = get_object_or_404(
            Fee_Permission, id=request.GET.get("edit")
        )

    # ---------- CREATE / UPDATE ----------
    if request.method == "POST" and request.POST.get("action") == "save":
        role_ids = request.POST.getlist("roles[]")
        can_view_all = request.POST.get("can_view_all_fee") == "on"
        can_view_dept = request.POST.get("can_view_department_fee") == "on"
        perm_id = request.POST.get("perm_id")

        if not role_ids:
            messages.error(request, "At least one role is required")
            return redirect("assign_fee_view_permission")

        # ---- EDIT (single record) ----
        if perm_id:
            Fee_Permission.objects.filter(id=perm_id).update(
                can_view_all_fee=can_view_all,
                can_view_department_fee=can_view_dept,
            )
        else:
            # ---- CREATE (bulk roles) ----
            for role_id in role_ids:
                Fee_Permission.objects.update_or_create(
                    role_id=role_id,
                    defaults={
                        "can_view_all_fee": can_view_all,
                        "can_view_department_fee": can_view_dept,
                    }
                )

        messages.success(request, "Fee view permission saved successfully")
        return redirect("assign_fee_view_permission")

    # ---------- PAGE LOAD ----------
    roles = Role.objects.using("rit_approval_system").all()

    context = {
        "roles": roles,
        "edit_permission": edit_permission,
    }

    return render(
        request,
        "fee_management/permissions/fee_view_permission.html",
        context
    )
  

# ---------------- AJAX API ----------------
@require_GET
def fee_view_permission_api(request):
    search = request.GET.get("search", "").strip()
    page = int(request.GET.get("page", 1))

    permissions = Fee_Permission.objects.all().order_by("id")

    # ---- FETCH ROLES FROM OTHER DB ----
    roles_qs = Role.objects.using("rit_approval_system").all()
    role_map = {r.id: r.role for r in roles_qs}

    # ---- SEARCH BY ROLE NAME ----
    if search:
        role_ids = list(
            roles_qs.filter(role__icontains=search)
                    .values_list("id", flat=True)
        )

        if not role_ids:
            permissions = Fee_Permission.objects.none()
        else:
            permissions = permissions.filter(role_id__in=role_ids)

    paginator = Paginator(permissions, 25)
    page_obj = paginator.get_page(page)

    data = [
        {
            "id": perm.id,
            "role": role_map.get(perm.role_id, "Unknown"),
            "can_view_all": perm.can_view_all_fee,
            "can_view_dept": perm.can_view_department_fee,
        }
        for perm in page_obj
    ]

    return JsonResponse({
        "results": data,
        "page": page_obj.number,
        "total_pages": paginator.num_pages,
        "has_next": page_obj.has_next(),
        "has_prev": page_obj.has_previous(),
    })
  