import json

from django.shortcuts import redirect, render

from django.shortcuts import render,redirect
from django.contrib import messages
import re
from requests import request
from user_accounts.models import Role
from django.shortcuts import render, get_object_or_404
from user_accounts.decorators import check_permission, is_super_user, no_cache, faculty_login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from data_center_management.models import Data_Center_Permission, DataCenterRequestApprovers
from data_center_management.decorators import data_center_management
from user_accounts.models import Add_Department , User
import logging
logger = logging.getLogger(__name__)


APPROVAL_DB = "rit_approval_system"

@no_cache
@is_super_user('data_center_management')
def dc_assign_permission(request):
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
       
                    
                    # Update the existing permission row for this role+function,
                    # or create it if missing (single instance, not a QuerySet).
                    Data_Center_Permission.objects.update_or_create(
                        role_id=role.id,
                        function=extract_data[1],
                        defaults={"permission": permission},
                    )
                except Exception as e:
                    # Catch unexpected errors and log them
                    messages.error(request,f"Error processing role '{role_name}': {str(e)}")
                    messages.error(request, f"An error occurred while processing '{role_name}': {str(e)}")

    # Redirect to admin dashboard after processing
    messages.success(request,"The permission changes have been successfully applied.")
    return redirect('data_center_management')
 


# @faculty_login_required
@data_center_management
def dc_home(request):
    request.session['current_page'] = 'dc_home'

    return redirect('home')

@data_center_management
@check_permission("dc_hello")
def dc_hello(request):
    return render(request, "dc_hello.html")



@data_center_management
@check_permission("dc_approval_system")
def dc_approval_system(request):
    if request.method == "GET":
        roles = Role.objects.using(APPROVAL_DB).all()
        departments = Add_Department.objects.all()

        # Lookup maps so we can resolve names for the cross-DB Role FKs and
        # for the local department FK without extra per-row queries.
        role_name_map = {r.id: r.role for r in roles}
        dept_name_map = {d.id: d.Department for d in departments}

        # Build the already-configured approval flows, grouped by creator role
        # and ordered by approver level, for the read-only "saved flows" list
        # and for client-side editing.
        existing_flows = {}
        approver_rows = (
            DataCenterRequestApprovers.objects
            .all()
            .order_by("creator_role_id", "approver_level", "id")
        )
        for row in approver_rows:
            creator_id = row.creator_role_id
            if creator_id not in existing_flows:
                existing_flows[creator_id] = {
                    "creator_role_id": creator_id,
                    "creator_role_name": role_name_map.get(creator_id, f"Role #{creator_id}"),
                    "levels": [],
                }

            is_cross = str(row.is_cross_department_approver or "").upper() == "YES"
            existing_flows[creator_id]["levels"].append({
                "approver_role_id": row.approver_role_id,
                "approver_role_name": role_name_map.get(
                    row.approver_role_id, f"Role #{row.approver_role_id}"
                ),
                "approver_level": row.approver_level,
                "is_cross_department": is_cross,
                "department_id": row.approver_department_id,
                "department_name": dept_name_map.get(row.approver_department_id, ""),
            })

        existing_flows = sorted(
            existing_flows.values(),
            key=lambda f: f["creator_role_name"].lower(),
        )

        return render(
            request,
            "data_center_management/admin/dc_approval_system.html",
            {
                "roles": roles,
                "departments": departments,
                "existing_flows": existing_flows,
                "existing_flows_json": json.dumps(existing_flows),
            },
        )

    if request.method == "POST":
        try:
            raw = (request.body or b"").decode("utf-8").strip()
            if not raw:
                return JsonResponse({"error": "Empty body"}, status=400)

            data = json.loads(raw)

            creator_role_id_raw = data.get("creatorRole")
            role_hierarchy = data.get("roleHierarchy", [])

            try:
                creator_role_id = int(creator_role_id_raw)
            except (TypeError, ValueError):
                return JsonResponse({"error": "Invalid creatorRole"}, status=400)

            if not isinstance(role_hierarchy, list):
                return JsonResponse({"error": "roleHierarchy must be a list"}, status=400)

            def _to_bool(value):
                if isinstance(value, bool):
                    return value
                if value is None:
                    return False
                if isinstance(value, (int, float)):
                    return bool(value)
                return str(value).strip().lower() in ("1", "true", "yes", "y", "on")

            def _to_int_or_none(value):
                if value in (None, "", "null", "None", "undefined"):
                    return None
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return None

            DataCenterRequestApprovers.objects.filter(
                creator_role_id=creator_role_id
            ).delete()

            for index, role_data in enumerate(role_hierarchy):
                role_id_raw = role_data.get("id")
                try:
                    approver_role_id = int(role_id_raw)
                except (TypeError, ValueError):
                    return JsonResponse(
                        {"error": f"Invalid role id: {role_id_raw}"},
                        status=400,
                    )

                is_cross_department = _to_bool(role_data.get("isCrossDepartment", False))
                dept_id = _to_int_or_none(role_data.get("departmentId"))

                if is_cross_department and not dept_id:
                    return JsonResponse(
                        {
                            "error": (
                                f"Department is required for cross-department approver "
                                f"(role_id={approver_role_id})."
                            )
                        },
                        status=400,
                    )

                department_obj = Add_Department.objects.filter(id=dept_id).first() if dept_id else None

                if is_cross_department and dept_id and not department_obj:
                    return JsonResponse(
                        {"error": f"Department not found: {dept_id}"},
                        status=404,
                    )

                DataCenterRequestApprovers.objects.create(
                    creator_role_id=creator_role_id,
                    approver_role_id=approver_role_id,
                    approver_level=index + 1,
                    is_cross_department_approver="YES" if is_cross_department else "NO",
                    approver_department=department_obj,
                )

            return JsonResponse(
                {"message": "Data center request roles submitted successfully"},
                status=200,
            )

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            logger.exception("Error in dc_approval_system POST")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)
 
 
  






