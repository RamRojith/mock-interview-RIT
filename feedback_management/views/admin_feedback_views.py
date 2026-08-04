from django.shortcuts import render
from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import redirect
from faculty_management.decorators import faculty_management
from user_accounts.models import Role, Department
import re
from user_accounts.decorators import faculty_login_required, no_cache, is_super_user, check_permission
from feedback_management.models import *
from feedback_management.decorators import feedback_management


@feedback_management
def feedback_home(request):
    # print("feedback home page ")
    request.session['current_page'] = 'feedback_home'
    return redirect('home')

@check_permission('feedback_hello')
def feedback_hello(request):
    return render(request, 'feedback_hello.html')

@no_cache
@is_super_user('feedback_management')
def feedback_assign_permission(request):
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
                    permission_obj = FeedbackPermission.objects.filter(
                        role=role, function=extract_data[1]
                    ).first()
                    
                    if permission_obj:
                        permission_obj.permission = permission
                        permission_obj.save()
                    else:
                        # Create a new FeedbackPermission object
                        FeedbackPermission.objects.create(
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
    return redirect('feedback_management')



from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from feedback_management.models import gradeupload


@no_cache
@is_super_user('feedback_management')
def grade_upload(request, pk=None):
    edit_obj = None
    if pk:
        edit_obj = get_object_or_404(gradeupload, pk=pk)

    if request.method == "POST":
        grade = (request.POST.get("grade") or "").strip().upper()
        marks = (request.POST.get("marks") or "").strip()

        if not grade:
            messages.error(request, "Grade is required.")
            if edit_obj:
                return redirect("grade_upload_edit", pk=edit_obj.id)
            return redirect("grade_upload")

        try:
            marks = int(marks)
        except ValueError:
            messages.error(request, "Marks must be a valid number.")
            if edit_obj:
                return redirect("grade_upload_edit", pk=edit_obj.id)
            return redirect("grade_upload")

        if marks < 0:
            messages.error(request, "Marks cannot be negative.")
            if edit_obj:
                return redirect("grade_upload_edit", pk=edit_obj.id)
            return redirect("grade_upload")

        if edit_obj:
            edit_obj.grade = grade
            edit_obj.marks = marks
            edit_obj.save()
            messages.success(request, "Grade updated successfully.")
            return redirect("grade_upload")
        else:
            gradeupload.objects.create(
                grade=grade,
                marks=marks
            )
            messages.success(request, "Grade uploaded successfully.")
            return redirect("grade_upload")

    grades = gradeupload.objects.all().order_by("marks")

    return render(request, "feedback_management/admin/grade_upload.html", {
        "grades": grades,
        "edit_obj": edit_obj,
    })


@no_cache
@is_super_user('feedback_management')
def grade_upload_edit(request, pk):
    return grade_upload(request, pk=pk)


@no_cache
@is_super_user('feedback_management')
def grade_upload_delete(request, pk):
    obj = get_object_or_404(gradeupload, pk=pk)
    obj.delete()
    messages.success(request, "Grade deleted successfully.")
    return redirect("grade_upload")




from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.core.paginator import Paginator

from user_accounts.models import Role
from feedback_management.models import feedback_data_Permission



def feedback_permission(request):
    edit_permission = None

    # ---------- DELETE ----------
    if request.method == "POST" and request.POST.get("action") == "delete":
        perm_id = request.POST.get("perm_id")
        feedback_data_Permission.objects.filter(id=perm_id).delete()
        messages.success(request, "Feedback permission deleted successfully.")
        return redirect("feedback_permission")

    # ---------- EDIT LOAD ----------
    if request.method == "GET" and request.GET.get("edit"):
        edit_permission = get_object_or_404(
            feedback_data_Permission,
            id=request.GET.get("edit")
        )

    # ---------- CREATE / UPDATE ----------
    if request.method == "POST" and request.POST.get("action") == "save":
        role_ids = request.POST.getlist("roles[]")
        can_view_all = request.POST.get("can_view_all_feedback_data") == "on"
        can_view_dept = request.POST.get("can_view_department_feedback_data") == "on"
        perm_id = request.POST.get("perm_id")

        if perm_id:
            feedback_data_Permission.objects.filter(id=perm_id).update(
                can_view_all_feedback_data=can_view_all,
                can_view_department_feedback_data=can_view_dept,
            )
            messages.success(request, "Feedback permission updated successfully.")
            return redirect("feedback_permission")

        if not role_ids:
            messages.error(request, "At least one role is required.")
            return redirect("feedback_permission")

        for role_id in role_ids:
            feedback_data_Permission.objects.update_or_create(
                role_id=role_id,
                defaults={
                    "can_view_all_feedback_data": can_view_all,
                    "can_view_department_feedback_data": can_view_dept,
                }
            )

        messages.success(request, "Feedback permission saved successfully.")
        return redirect("feedback_permission")

    roles = Role.objects.using("rit_approval_system").all()

    context = {
        "roles": roles,
        "edit_permission": edit_permission,
    }
    return render(request, "feedback_management/admin/feedback_permission.html", context)


@require_GET
def feedback_permission_api(request):
    search = (request.GET.get("search") or "").strip()
    page = int(request.GET.get("page", 1))

    permissions = feedback_data_Permission.objects.all().order_by("id")

    roles_qs = Role.objects.using("rit_approval_system").all()
    role_map = {r.id: r.role for r in roles_qs}

    if search:
        role_ids = list(
            roles_qs.filter(role__icontains=search).values_list("id", flat=True)
        )
        if not role_ids:
            permissions = feedback_data_Permission.objects.none()
        else:
            permissions = permissions.filter(role_id__in=role_ids)

    page_size = 25
    paginator = Paginator(permissions, page_size)
    page_obj = paginator.get_page(page)

    data = [
        {
            "id": perm.id,
            "role": role_map.get(perm.role_id, "Unknown"),
            "can_view_all": perm.can_view_all_feedback_data,
            "can_view_dept": perm.can_view_department_feedback_data,
        }
        for perm in page_obj
    ]

    return JsonResponse({
        "results": data,
        "page": page_obj.number,
        "total_pages": paginator.num_pages,
        "has_next": page_obj.has_next(),
        "has_prev": page_obj.has_previous(),
        "total_count": paginator.count,
        "page_size": page_size,
    })





from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.core.paginator import Paginator

from user_accounts.models import Role
from feedback_management.models import end_survey_data_Permission


def end_survey_permission(request):
    edit_permission = None

    # ---------- DELETE ----------
    if request.method == "POST" and request.POST.get("action") == "delete":
        perm_id = request.POST.get("perm_id")
        end_survey_data_Permission.objects.filter(id=perm_id).delete()
        messages.success(request, "End survey permission deleted successfully.")
        return redirect("end_survey_permission")

    # ---------- EDIT LOAD ----------
    if request.method == "GET" and request.GET.get("edit"):
        edit_permission = get_object_or_404(
            end_survey_data_Permission,
            id=request.GET.get("edit")
        )

    # ---------- CREATE / UPDATE ----------
    if request.method == "POST" and request.POST.get("action") == "save":
        role_ids = request.POST.getlist("roles[]")
        can_view_all = request.POST.get("can_view_all_end_survey_data") == "on"
        can_view_dept = request.POST.get("can_view_department_end_survey_data") == "on"
        perm_id = request.POST.get("perm_id")

        if perm_id:
            end_survey_data_Permission.objects.filter(id=perm_id).update(
                can_view_all_end_survey_data=can_view_all,
                can_view_department_end_survey_data=can_view_dept,
            )
            messages.success(request, "End survey permission updated successfully.")
            return redirect("end_survey_permission")

        if not role_ids:
            messages.error(request, "At least one role is required.")
            return redirect("end_survey_permission")

        for role_id in role_ids:
            end_survey_data_Permission.objects.update_or_create(
                role_id=role_id,
                defaults={
                    "can_view_all_end_survey_data": can_view_all,
                    "can_view_department_end_survey_data": can_view_dept,
                }
            )

        messages.success(request, "End survey permission saved successfully.")
        return redirect("end_survey_permission")

    roles = Role.objects.using("rit_approval_system").all()

    context = {
        "roles": roles,
        "edit_permission": edit_permission,
    }
    return render(request, "feedback_management/admin/end_survey_permission.html", context)


@require_GET
def end_survey_permission_api(request):
    search = (request.GET.get("search") or "").strip()
    page = int(request.GET.get("page", 1))

    permissions = end_survey_data_Permission.objects.all().order_by("id")

    roles_qs = Role.objects.using("rit_approval_system").all()
    role_map = {r.id: r.role for r in roles_qs}

    if search:
        role_ids = list(
            roles_qs.filter(role__icontains=search).values_list("id", flat=True)
        )
        if not role_ids:
            permissions = end_survey_data_Permission.objects.none()
        else:
            permissions = permissions.filter(role_id__in=role_ids)

    page_size = 25
    paginator = Paginator(permissions, page_size)
    page_obj = paginator.get_page(page)

    data = [
        {
            "id": perm.id,
            "role": role_map.get(perm.role_id, "Unknown"),
            "can_view_all": perm.can_view_all_end_survey_data,
            "can_view_dept": perm.can_view_department_end_survey_data,
        }
        for perm in page_obj
    ]

    return JsonResponse({
        "results": data,
        "page": page_obj.number,
        "total_pages": paginator.num_pages,
        "has_next": page_obj.has_next(),
        "has_prev": page_obj.has_previous(),
        "total_count": paginator.count,
        "page_size": page_size,
    })




from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

def program_exit_permission(request):
    edit_permission = None

    # ---------- DELETE ----------
    if request.method == "POST" and request.POST.get("action") == "delete":
        perm_id = request.POST.get("perm_id")
        program_exit_Permission.objects.filter(id=perm_id).delete()
        messages.success(request, "Program exit permission deleted successfully.")
        return redirect("program_exit_permission")

    # ---------- EDIT LOAD ----------
    if request.method == "GET" and request.GET.get("edit"):
        edit_permission = get_object_or_404(
            program_exit_Permission,
            id=request.GET.get("edit")
        )

    # ---------- CREATE / UPDATE ----------
    if request.method == "POST" and request.POST.get("action") == "save":
        role_ids = request.POST.getlist("roles[]")
        can_view_all = request.POST.get("can_view_all_program_exit_data") == "on"
        can_view_dept = request.POST.get("can_view_department_program_exit_data") == "on"
        perm_id = request.POST.get("perm_id")

        # UPDATE
        if perm_id:
            program_exit_Permission.objects.filter(id=perm_id).update(
                can_view_all_program_exit_data=can_view_all,
                can_view_department_program_exit_data=can_view_dept,
            )
            messages.success(request, "Program exit permission updated successfully.")
            return redirect("program_exit_permission")

        # CREATE
        if not role_ids:
            messages.error(request, "At least one role is required.")
            return redirect("program_exit_permission")

        for role_id in role_ids:
            program_exit_Permission.objects.update_or_create(
                role_id=role_id,
                defaults={
                    "can_view_all_program_exit_data": can_view_all,
                    "can_view_department_program_exit_data": can_view_dept,
                }
            )

        messages.success(request, "Program exit permission saved successfully.")
        return redirect("program_exit_permission")

    roles = Role.objects.using("rit_approval_system").all()

    context = {
        "roles": roles,
        "edit_permission": edit_permission,
    }
    return render(
        request,
        "feedback_management/admin/program_exit_permission.html",
        context
    )


@require_GET
def program_exit_permission_api(request):
    search = (request.GET.get("search") or "").strip()
    page = int(request.GET.get("page", 1))

    permissions = program_exit_Permission.objects.all().order_by("id")

    roles_qs = Role.objects.using("rit_approval_system").all()
    role_map = {r.id: r.role for r in roles_qs}

    if search:
        role_ids = list(
            roles_qs.filter(role__icontains=search).values_list("id", flat=True)
        )
        if not role_ids:
            permissions = program_exit_Permission.objects.none()
        else:
            permissions = permissions.filter(role_id__in=role_ids)

    page_size = 25
    paginator = Paginator(permissions, page_size)
    page_obj = paginator.get_page(page)

    data = [
        {
            "id": perm.id,
            "role": role_map.get(perm.role_id, "Unknown"),
            "can_view_all": perm.can_view_all_program_exit_data,
            "can_view_dept": perm.can_view_department_program_exit_data,
        }
        for perm in page_obj
    ]

    return JsonResponse({
        "results": data,
        "page": page_obj.number,
        "total_pages": paginator.num_pages,
        "has_next": page_obj.has_next(),
        "has_prev": page_obj.has_previous(),
        "total_count": paginator.count,
        "page_size": page_size,
    })




def course_exit_permission(request):
    edit_permission = None

    if request.method == "POST" and request.POST.get("action") == "delete":
        perm_id = request.POST.get("perm_id")
        course_exit_Permission.objects.filter(id=perm_id).delete()
        messages.success(request, "Course exit permission deleted successfully.")
        return redirect("course_exit_permission")

    if request.method == "GET" and request.GET.get("edit"):
        edit_permission = get_object_or_404(
            course_exit_Permission,
            id=request.GET.get("edit")
        )

    if request.method == "POST" and request.POST.get("action") == "save":
        role_ids = request.POST.getlist("roles[]")
        can_view_all = request.POST.get("can_view_all_course_exit_data") == "on"
        can_view_dept = request.POST.get("can_view_department_course_exit_data") == "on"
        perm_id = request.POST.get("perm_id")

        if perm_id:
            course_exit_Permission.objects.filter(id=perm_id).update(
                can_view_all_course_exit_data=can_view_all,
                can_view_department_course_exit_data=can_view_dept,
            )
            messages.success(request, "Course exit permission updated successfully.")
            return redirect("course_exit_permission")

        if not role_ids:
            messages.error(request, "At least one role is required.")
            return redirect("course_exit_permission")

        for role_id in role_ids:
            course_exit_Permission.objects.update_or_create(
                role_id=role_id,
                defaults={
                    "can_view_all_course_exit_data": can_view_all,
                    "can_view_department_course_exit_data": can_view_dept,
                }
            )

        messages.success(request, "Course exit permission saved successfully.")
        return redirect("course_exit_permission")

    roles = Role.objects.using("rit_approval_system").all()

    context = {
        "roles": roles,
        "edit_permission": edit_permission,
    }
    return render(
        request,
        "feedback_management/admin/course_exit_permission.html",
        context
    )
 

@require_GET
def course_exit_permission_api(request):
    search = (request.GET.get("search") or "").strip()
    page = int(request.GET.get("page", 1))

    permissions = course_exit_Permission.objects.all().order_by("id")

    roles_qs = Role.objects.using("rit_approval_system").all()
    role_map = {r.id: r.role for r in roles_qs}

    if search:
        role_ids = list(
            roles_qs.filter(role__icontains=search).values_list("id", flat=True)
        )
        if not role_ids:
            permissions = course_exit_Permission.objects.none()
        else:
            permissions = permissions.filter(role_id__in=role_ids)

    page_size = 25
    paginator = Paginator(permissions, page_size)
    page_obj = paginator.get_page(page)

    data = [
        {
            "id": perm.id,
            "role": role_map.get(perm.role_id, "Unknown"),
            "can_view_all": perm.can_view_all_course_exit_data,
            "can_view_dept": perm.can_view_department_course_exit_data,
        }
        for perm in page_obj
    ]

    return JsonResponse({
        "results": data,
        "page": page_obj.number,
        "total_pages": paginator.num_pages,
        "has_next": page_obj.has_next(),
        "has_prev": page_obj.has_previous(),
        "total_count": paginator.count,
        "page_size": page_size,
    })
 
 









