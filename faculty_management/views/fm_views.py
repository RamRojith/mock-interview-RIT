from django.shortcuts import render,redirect,get_object_or_404
from user_accounts.decorators import no_cache,is_super_user
from django.contrib import messages
from course_management.models import PeriodAllocation, CourseHours, CourseEnrollment, AssignSubjectFaculty

from django.shortcuts import render
from datetime import datetime
from django.utils import timezone
from user_accounts.decorators import no_cache, check_permission

from faculty_management.models import Vision, general_information, Mission, Program_Educational_Objective, Program_specific_Outcomes
from user_accounts.models import Add_Department

from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Case, When, IntegerField
from django.db import transaction


@check_permission("vision_statement")
def vision_statement(request):
    current_year = datetime.now().year
    year_choices = [current_year - 1, current_year, current_year + 1, current_year + 2, current_year + 3]
    faculty = general_information.objects.get(faculty_id = request.user.Employee_id)
    faculty_department = Add_Department.objects.get(
        id=faculty.department.id, is_active=True
    )

    # Order: active first, then newest year, then newest id
    visions = (
        Vision.objects.filter(department=faculty_department)
        .annotate(active_int=Case(When(is_active=True, then=1), default=0, output_field=IntegerField()))
        .order_by('-active_int', '-year', '-id')
    )

    # Handle Edit fetch via GET (kept as-is)
    edit_id = request.GET.get('edit')
    vision_to_edit = None
    if edit_id:
        vision_to_edit = get_object_or_404(Vision, id=edit_id, department=faculty_department)

    # Handle Add/Update/Delete via POST (no more deletes over GET)
    if request.method == "POST":
        # DELETE via modal form
        delete_id = request.POST.get('delete_id')
        if delete_id:
            vision = get_object_or_404(Vision, id=delete_id, department=faculty_department)
            vision.delete()
            messages.success(request, "Vision deleted successfully.")
            return redirect('vision_statement')

        # ADD/UPDATE
        vision_id = request.POST.get('vision_id')
        year = request.POST.get('year')
        vision_text = (request.POST.get('vision_statement') or "").strip()
        is_active = request.POST.get('is_active') == "on"

        if not year or not vision_text:
            messages.error(request, "All fields are required.")
            return redirect('vision_statement')

        if vision_id:  # Update
            vision = get_object_or_404(Vision, id=vision_id, department=faculty_department)
            vision.year = year
            vision.vision_statement = vision_text
            vision.is_active = is_active
            vision.updated_at = timezone.now()
            vision.save()
            messages.success(request, "Vision updated successfully.")
        else:  # Create
            Vision.objects.create(
                department=faculty_department,
                year=year,
                vision_statement=vision_text,
                is_active=is_active,
                created_by=general_information.objects.filter(faculty_id=request.user.Employee_id).first()
            )
            messages.success(request, "Vision added successfully.")

        return redirect('vision_statement')

    context = {
        'visions': visions,
        'vision_to_edit': vision_to_edit,
        'faculty_department': faculty_department,
        'year_choices': year_choices,
        'current_year': current_year,
    }
    return render(request, 'faculty_management/faculty/statements/vision_statement.html', context)


@check_permission("mission_statement")
def mission_statement(request):
    # --- Determine department ---
    try:
        faculty = general_information.objects.get(faculty_id = request.user.Employee_id)
        faculty_department = Add_Department.objects.get(
        id=faculty.department.id, is_active=True
    )
    except Add_Department.DoesNotExist:
        faculty_department = None

    current_year = timezone.now().year
    year_choices = [current_year - 1] + [current_year + i for i in range(0, 5)]  # prev + next 4 years

    # --- Query all missions ---
    missions = Mission.objects.filter(department=faculty_department).order_by("-year", "-created_at")

    # --- Identify editing or deleting ---
    mission_to_edit = None
    if "edit" in request.GET:
        mission_to_edit = get_object_or_404(Mission, id=request.GET.get("edit"))

    # --- Handle Delete ---
    if request.method == "POST" and request.POST.get("delete_id"):
        mission_id = request.POST.get("delete_id")
        Mission.objects.filter(id=mission_id).delete()
        messages.success(request, "Mission statement deleted successfully.")
        return redirect("mission_statement")

    # --- Handle Add/Edit ---
    if request.method == "POST" and not request.POST.get("delete_id"):
        mission_id = request.POST.get("mission_id")
        mission_text = request.POST.get("mission_statement", "").strip()
        year = request.POST.get("year")
        is_active = True if request.POST.get("is_active") == "on" else False

        if not mission_text:
            messages.error(request, "Mission statement cannot be empty.")
            return redirect("mission_statement")

        if not faculty_department:
            messages.error(request, "Department not found.")
            return redirect("mission_statement")

        # If editing
        if mission_id:
            mission = get_object_or_404(Mission, id=mission_id)
            mission.mission_statement = mission_text
            mission.year = year
            mission.is_active = is_active
            mission.save()
            messages.success(request, "Mission statement updated successfully.")
        else:
            Mission.objects.create(
                department=faculty_department,
                mission_statement=mission_text,
                year=year,
                is_active=is_active,
                created_by=general_information.objects.filter(faculty_id=request.user.Employee_id).first(),
            )
            messages.success(request, "Mission statement added successfully.")

        return redirect("mission_statement")

    context = {
        "missions": missions,
        "faculty_department": faculty_department,
        "mission_to_edit": mission_to_edit,
        "year_choices": year_choices,
        "current_year": current_year,
    }
    return render(request, "faculty_management/faculty/statements/mission_statement.html", context)

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json



@check_permission("program_educational_objectives")
@csrf_exempt
def program_educational_objectives(request):
    """Handles List, Add, Edit, Delete with Django messages."""
    current_year = datetime.now().year

    faculty = general_information.objects.get(faculty_id = request.user.Employee_id)
    department = Add_Department.objects.get(
        id=faculty.department.id, is_active=True
    )

    # --- POST actions ---
    if request.method == "POST":
        action = request.POST.get("action")

        # ADD / EDIT
        if action in ["add", "edit"]:
            year = int(request.POST.get("year", current_year))
            batch = request.POST.get("batch", "").strip()
            is_active = bool(request.POST.get("is_active", False))
            peo_code = request.POST.get("peo_code", "").strip()
            peo_id = request.POST.get("peo_id")
            
            peos = [request.POST.get("peos", "").strip()]

            if not peos or not peos[0]:
                messages.warning(request, "Please enter a valid PEO statement.")
                return redirect(request.path)

            if action == "add":
                with transaction.atomic():
                    for text in peos:
                        if text:
                            Program_Educational_Objective.objects.create(
    department=department,
    peo_code=peo_code if peo_code else None,
    peo_statement=text,
    created_by=faculty,
    year=year,
    batch=batch,
    is_active=is_active,
)
                messages.success(request, "PEO added successfully.")
            else:
                peo = get_object_or_404(Program_Educational_Objective, id=peo_id)
                peo.peo_code = peo_code if peo_code else None
                peo.peo_statement = peos[0]
                peo.batch = batch
                peo.year = year
                peo.is_active = is_active
                peo.save()
                messages.success(request, f"PEO ({peo.peo_code or 'No code'}) updated successfully.")

            return redirect(request.path)

        # DELETE
        elif action == "delete":
            peo_id = request.POST.get("peo_id")
            
            if not peo_id:
                messages.error(request, "Invalid delete request.")
                return redirect(request.path)

            deleted, _ = Program_Educational_Objective.objects.filter(id=peo_id).delete()
            if deleted:
                messages.warning(request, "PEO deleted successfully.")
            else:
                messages.error(request, "PEO not found or already deleted.")
            return redirect(request.path)

    # --- GET: Display page ---
    peos = Program_Educational_Objective.objects.filter(department=department)\
        .select_related("department")\
        .order_by("-year", "peo_code", "-created_at")

    year_choices = list(range(current_year - 1, current_year + 4))
    batches = StudentDetails.objects.values_list(
    "batch", flat=True
).distinct().order_by("batch")

    return render(request, "faculty_management/faculty/statements/program_educational_objectives.html", {
        "peos": peos,
        "year_choices": year_choices,
        "current_year": current_year,
        "department": department,
        "batches": batches,
    })



from faculty_management.models import Announcement
from user_accounts.models import Role
from collections import defaultdict

from datetime import date
from django.shortcuts import render, redirect
from django.contrib import messages

def get_academic_year():
    """
    Dynamically returns academic year string.
    Example:
      If current month >= June → '2025-2026'
      Else (Jan–May) → '2024-2025'
    """
    today = date.today()
    current_year = today.year
    if today.month >= 6:  # June or later
        return f"{current_year}-{current_year + 1}"
    else:  # Before June → part of previous cycle
        return f"{current_year - 1}-{current_year}"

# @check_permission("upload_announcement")
# def upload_announcement(request):
#     roles = Role.objects.using("rit_approval_system").all()
#     departments = Add_Department.objects.all()
#     users = general_information.objects.all()

#     try:
#         department = Add_Department.objects.only("id", "Department", "degree").get(
#             Department__iexact=request.user.Department.Department, is_active=True
#         )
#     except Add_Department.DoesNotExist:
#         messages.error(request, "Your department is not found or inactive.")
#         return redirect(request.path)

#     faculty = general_information.objects.filter(
#         faculty_id=request.user.Employee_id,
#         department=department,
#         department__degree=department.degree,
#     ).first()

#     edit_id = request.GET.get("edit")
#     edit_instance = Announcement.objects.filter(id=edit_id).first() if edit_id else None

#     # Delete
#     delete_id = request.GET.get("delete")
#     if delete_id:
#         Announcement.objects.filter(id=delete_id).delete()
#         messages.success(request, "Announcement deleted successfully!")
#         return redirect("upload_announcement")

#     # Toggle Active/Inactive
#     toggle_id = request.GET.get("toggle")
#     if toggle_id:
#         ann = get_object_or_404(Announcement, id=toggle_id)
#         ann.is_active = not ann.is_active
#         ann.save()
#         messages.success(request, f"Announcement {'activated' if ann.is_active else 'deactivated'} successfully!")
#         return redirect("upload_announcement")

#     # Convert list to ints safely
#     def to_int_list(lst):
#         res = []
#         for x in lst:
#             try:
#                 res.append(int(x))
#             except Exception:
#                 pass
#         return res

#     # Handle POST
#     if request.method == "POST":
#         # allow cancel while editing
#         if "cancel" in request.POST:
#             return redirect("upload_announcement")

#         title = request.POST.get("title")
#         message = request.POST.get("message")
#         academic_year = request.POST.get("academic_year")
#         file = request.FILES.get("attachment")
#         venue = request.POST.get("venue")
#         date = request.POST.get("date")
#         time = request.POST.get("time")
#         notify_from = request.POST.get("notify_from")
#         notify_to = request.POST.get("notify_to")
#         # print("File uploaded:", file)
#         # print("file uploaded:", bool(file))

#         role_ids = to_int_list(request.POST.getlist("roles"))
#         dept_ids = to_int_list(request.POST.getlist("departments"))
#         user_ids = to_int_list(request.POST.getlist("users"))

#         if edit_instance:
#             edit_instance.title = title
#             edit_instance.message = message
#             edit_instance.academic_year = academic_year
#             edit_instance.venue = venue
#             edit_instance.date = date if date else None
#             edit_instance.time = time if time else None
#             edit_instance.notify_from = notify_from if notify_from else None
#             edit_instance.notify_to = notify_to if notify_to else None
#             if file:
#                 edit_instance.attachment = file
#             edit_instance.updated_by = faculty
#             edit_instance.save()

#             # Clear and manually insert role IDs into through table
#             through_model = Announcement.roles.through
#             through_model.objects.filter(announcement_id=edit_instance.id).delete()
#             for rid in role_ids:
#                 through_model.objects.create(announcement_id=edit_instance.id, role_id=rid)

#             # Local models can safely use set()
#             edit_instance.departments.set(dept_ids)
#             edit_instance.users.set(user_ids)

#             messages.success(request, "Announcement updated successfully!")
#             return redirect("upload_announcement")

#         # Create new record
#         ann = Announcement.objects.create(
#             title=title,
#             message=message,
#             academic_year=academic_year,
#             venue=venue,
#             date=date if date else None,
#             time=time if time else None,
#             notify_from=notify_from if notify_from else None,
#             notify_to=notify_to if notify_to else None,
#             attachment=file,
#             created_by=faculty,
#             updated_by=faculty,
#             faculty=faculty
#         )

#         # Insert roles manually into through table (no ORM cross-db issue)
#         through_model = Announcement.roles.through
#         for rid in role_ids:
#             through_model.objects.create(announcement_id=ann.id, role_id=rid)

#         # Add departments and users normally
#         if dept_ids:
#             ann.departments.set(dept_ids)
#         if user_ids:
#             ann.users.set(user_ids)

#         messages.success(request, "Announcement uploaded successfully!")
#         return redirect("upload_announcement")

#     # READ section: build announcement_meta for safe template rendering
#     announcements = Announcement.objects.all()

#     # collect role_ids from through table for all announcements in one query
#     ann_ids = [a.id for a in announcements]
#     through_model = Announcement.roles.through
#     through_rows = through_model.objects.filter(announcement_id__in=ann_ids).values_list(
#         "announcement_id", "role_id"
#     ) if ann_ids else []

#     ann_role_ids_map = defaultdict(list)
#     all_role_ids = set()
#     for ann_id, role_id in through_rows:
#         ann_role_ids_map[ann_id].append(role_id)
#         all_role_ids.add(role_id)

#     # Fetch role names from external DB for all_role_ids (if any)
#     role_name_map = {}
#     if all_role_ids:
#         # safely query external DB for these role ids
#         roles_qs = Role.objects.using("rit_approval_system").filter(id__in=list(all_role_ids)).values("id", "role")
#         for r in roles_qs:
#             role_name_map[r["id"]] = r["role"]

#     # Build announcement_meta list (announcement + displayable data)
#     announcement_meta = []
#     for ann in announcements:
#         role_ids_for_ann = ann_role_ids_map.get(ann.id, [])
#         role_names_for_ann = [role_name_map.get(rid, f"ID:{rid}") for rid in role_ids_for_ann]

#         depts = list(ann.departments.all())  # local models, safe
#         users_linked = list(ann.users.all())

#         announcement_meta.append({
#             "announcement": ann,
#             "role_ids": role_ids_for_ann,
#             "role_names": role_names_for_ann,
#             "departments": depts,
#             "users": users_linked,
#         })

#     # For edit preselection (safe read from through table)
#     if edit_instance:
#         edit_roles = ann_role_ids_map.get(edit_instance.id, [])
#     else:
#         edit_roles = []

#     context = {
#         "roles": roles,  # available role list for form selection
#         "departments": departments,
#         "users": users,
#         "announcements": announcements,
#         "announcement_meta": announcement_meta,
#         "edit_instance": edit_instance,
#         "edit_roles": edit_roles,
#         "academic_year": get_academic_year(),
#     }
#     return render(request, "faculty_management/upload_announcement.html", context)


from collections import defaultdict
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from collections import defaultdict
from datetime import datetime
from collections import defaultdict
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.utils.dateparse import parse_datetime

@check_permission("upload_announcement")
def upload_announcement(request):
    roles = Role.objects.using("rit_approval_system").all()
    departments = Add_Department.objects.all()
    users = general_information.objects.all()

    faculty = general_information.objects.get(faculty_id=request.user.Employee_id)

    try:
        department = faculty.department
    except Add_Department.DoesNotExist:
        messages.error(request, "Your department is not found or inactive.")
        return redirect(request.path)

    faculty = general_information.objects.filter(
        faculty_id=request.user.Employee_id,
        department=department,
        department__degree=department.degree,
    ).first()

    edit_id = request.GET.get("edit")
    edit_instance = Announcement.objects.filter(id=edit_id).first() if edit_id else None

    # DELETE
    delete_id = request.GET.get("delete")
    if delete_id:
        Announcement.objects.filter(id=delete_id).delete()
        messages.success(request, "Announcement deleted successfully!")
        return redirect("upload_announcement")

    # TOGGLE
    toggle_id = request.GET.get("toggle")
    if toggle_id:
        ann = get_object_or_404(Announcement, id=toggle_id)
        ann.is_active = not ann.is_active
        ann.save()
        messages.success(
            request,
            f"Announcement {'activated' if ann.is_active else 'deactivated'} successfully!",
        )
        return redirect("upload_announcement")

    def to_int_list(lst):
        out = []
        for x in lst:
            try:
                out.append(int(x))
            except Exception:
                pass
        return out

    def parse_dt_local(val: str):
        if not val:
            return None
        dt = parse_datetime(val)
        if not dt:
            return None
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
        return dt

    if request.method == "POST":

        if "cancel" in request.POST:
            return redirect("upload_announcement")

        # ✅ ROW FILE UPLOAD
        row_upload_id = request.POST.get("row_upload_id")
        if row_upload_id:
            ann = get_object_or_404(Announcement, id=row_upload_id)

            attachment = request.FILES.get("attachment")
            extra_file = request.FILES.get("file")

            updated = False
            if attachment:
                ann.attachment = attachment
                updated = True
            if extra_file:
                ann.file = extra_file
                updated = True

            if updated:
                ann.updated_by = faculty
                ann.save()
                messages.success(request, "Row file upload updated successfully!")
            else:
                messages.warning(request, "Please choose a file to upload.")

            return redirect("upload_announcement")

        # ✅ MAIN FORM
        title = request.POST.get("title")
        message_txt = request.POST.get("message")
        academic_year = request.POST.get("academic_year")

        venue = request.POST.get("venue")
        date = request.POST.get("date")
        time_val = request.POST.get("time")

        notify_from = parse_dt_local(request.POST.get("notify_from"))
        notify_to = parse_dt_local(request.POST.get("notify_to"))

        # 🔥 VALIDATION (NEW)
        if notify_from and notify_to and notify_from > notify_to:
            messages.error(request, "End date must be after start date.")
            return redirect("upload_announcement")

        attachment = request.FILES.get("attachment")
        extra_file = request.FILES.get("file")

        role_ids = to_int_list(request.POST.getlist("roles"))
        dept_ids = to_int_list(request.POST.getlist("departments"))
        user_ids = to_int_list(request.POST.getlist("users"))

        # ===== EDIT =====
        if edit_instance:
            edit_instance.title = title
            edit_instance.message = message_txt
            edit_instance.academic_year = academic_year

            edit_instance.venue = venue
            edit_instance.date = date if date else None
            edit_instance.time = time_val if time_val else None

            # ✅ OPTIONAL FIELDS
            edit_instance.notify_from = notify_from
            edit_instance.notify_to = notify_to

            if attachment:
                edit_instance.attachment = attachment
            if extra_file:
                edit_instance.file = extra_file

            edit_instance.updated_by = faculty
            edit_instance.save()

            # roles cross-db safe
            through_model = Announcement.roles.through
            through_model.objects.filter(announcement_id=edit_instance.id).delete()

            for rid in role_ids:
                through_model.objects.create(
                    announcement_id=edit_instance.id,
                    role_id=rid
                )

            edit_instance.departments.set(dept_ids)
            edit_instance.users.set(user_ids)

            messages.success(request, "Announcement updated successfully!")
            return redirect("upload_announcement")

        # ===== CREATE =====
        ann = Announcement.objects.create(
            title=title,
            message=message_txt,
            academic_year=academic_year,

            venue=venue,
            date=date if date else None,
            time=time_val if time_val else None,

            # ✅ OPTIONAL FIELDS
            notify_from=notify_from,
            notify_to=notify_to,

            attachment=attachment,
            file=extra_file,

            created_by=faculty,
            updated_by=faculty,
            faculty=faculty
        )

        # roles cross-db safe
        through_model = Announcement.roles.through
        for rid in role_ids:
            through_model.objects.create(
                announcement_id=ann.id,
                role_id=rid
            )

        if dept_ids:
            ann.departments.set(dept_ids)
        if user_ids:
            ann.users.set(user_ids)

        messages.success(request, "Announcement uploaded successfully!")
        return redirect("upload_announcement")

    # ===== READ =====
    announcements = Announcement.objects.filter(faculty=faculty)
    ann_ids = [a.id for a in announcements]

    through_model = Announcement.roles.through
    through_rows = (
        through_model.objects.filter(announcement_id__in=ann_ids)
        .values_list("announcement_id", "role_id")
        if ann_ids else []
    )

    ann_role_ids_map = defaultdict(list)
    all_role_ids = set()

    for ann_id, role_id in through_rows:
        ann_role_ids_map[ann_id].append(role_id)
        all_role_ids.add(role_id)

    role_name_map = {}
    if all_role_ids:
        roles_qs = Role.objects.using("rit_approval_system").filter(
            id__in=list(all_role_ids)
        ).values("id", "role")

        for r in roles_qs:
            role_name_map[r["id"]] = r["role"]

    announcement_meta = []

    for ann in announcements:
        role_ids_for_ann = ann_role_ids_map.get(ann.id, [])
        role_names_for_ann = [
            role_name_map.get(rid, f"ID:{rid}") for rid in role_ids_for_ann
        ]

        announcement_meta.append({
            "announcement": ann,
            "role_ids": role_ids_for_ann,
            "role_names": role_names_for_ann,
            "departments": list(ann.departments.all()),
            "users": list(ann.users.all()),
        })

    edit_roles = ann_role_ids_map.get(edit_instance.id, []) if edit_instance else []

    context = {
        "roles": roles,
        "departments": departments,
        "users": users,
        "announcements": announcements,
        "announcement_meta": announcement_meta,
        "edit_instance": edit_instance,
        "edit_roles": edit_roles,
        "academic_year": get_academic_year(),
    }

    return render(request, "faculty_management/upload_announcement.html", context)

from user_accounts.models import StudentDetails 



@check_permission("program_specific_outcomes")
@csrf_exempt
def program_specific_outcomes(request):
    """Handles List, Add, Edit, Delete with Django messages."""
    current_year = datetime.now().year

    # ✅ Resolve department safely
    faculty = general_information.objects.get(faculty_id = request.user.Employee_id)
    department = Add_Department.objects.get(
        id=faculty.department.id, is_active=True
    )

    if request.method == "POST":
        action = request.POST.get("action")

        # ---------------- ADD / EDIT ----------------
        if action in ["add", "edit"]:
            # year
            try:
                year = int(request.POST.get("year") or current_year)
            except Exception:
                year = current_year

            # ✅ checkbox parsing (on/off)
            is_active = (request.POST.get("is_active") == "on")
            batch = (request.POST.get("batch") or "").strip()

            # ✅ NEW: PSO CODE
            pso_code = (request.POST.get("pso_code") or "").strip()
            

            pso_id = request.POST.get("pso_id")
            pso_statement = (request.POST.get("psos") or "").strip()

            if not pso_statement:
                messages.warning(request, "Please enter a valid PSO statement.")
                return redirect(request.path)

            if action == "add":
                # ✅ IMPORTANT: We DO NOT deactivate other PSOs.
                # Department can have multiple active PSOs.
                with transaction.atomic():
                    Program_specific_Outcomes.objects.create(
    department=department,
    batch=batch,
    pso_code=pso_code,
    pso_statement=pso_statement,
    created_by=faculty,
    year=year,
    is_active=is_active,
)
                messages.success(request, "PSO added successfully.")
                return redirect(request.path)

            # EDIT
            pso = get_object_or_404(Program_specific_Outcomes, id=pso_id, department=department)
            pso.batch = batch
            pso.pso_code = pso_code              # ✅ saved
            pso.pso_statement = pso_statement
            pso.year = year
            pso.is_active = is_active
            pso.save()
            messages.success(request, f"PSO (Year {year}) updated successfully.")
            return redirect(request.path)

        # ---------------- DELETE ----------------
        if action == "delete":
            pso_id = request.POST.get("pso_id")
            if not pso_id:
                messages.error(request, "Invalid delete request.")
                return redirect(request.path)

            deleted, _ = Program_specific_Outcomes.objects.filter(id=pso_id, department=department).delete()
            if deleted:
                messages.warning(request, "PSO deleted successfully.")
            else:
                messages.error(request, "PSO not found or already deleted.")
            return redirect(request.path)

    # ✅ GET
    psos = (
        Program_specific_Outcomes.objects
        .filter(department=department)
        .select_related("department")
        .order_by("-created_at")
    )
    year_choices = list(range(current_year - 1, current_year + 4))
    batches = StudentDetails.objects.values_list("batch", flat=True).distinct().order_by("batch")

    return render(request, "faculty_management/faculty/statements/program_specific_outcomes.html", {
        "psos": psos,
        "year_choices": year_choices,
        "current_year": current_year,
        "department": department,
        "batches": batches,
    })




def wifi_form(request):
    return render(request, 'faculty_management/faculty/data_center/wifi_form.html') 



from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Sum, Q
from django.shortcuts import render

from faculty_management.models import general_information, DesignationMaster
from user_accounts.models import Add_Department
from django.core.paginator import Paginator



from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import render

@check_permission("faculty_analysis_dashboard")
def faculty_analysis_dashboard(request):
    academic_department_ids = request.GET.getlist("academic_departments")
    non_academic_department_ids = request.GET.getlist("non_academic_departments")
    designation_ids = request.GET.getlist("designation")
    approval = request.GET.get("approval", "").strip()
    appointment_type = request.GET.get("appointment_type", "").strip()
    nature_of_duties = request.GET.get("nature_of_duties", "").strip()
    gender = request.GET.get("gender", "").strip()
    search = request.GET.get("search", "").strip()

    academic_department_ids = [x for x in academic_department_ids if str(x).isdigit()]
    non_academic_department_ids = [x for x in non_academic_department_ids if str(x).isdigit()]
    designation_ids = [x for x in designation_ids if str(x).isdigit()]

    selected_academic = bool(academic_department_ids)
    selected_non_academic = bool(non_academic_department_ids)

    faculty_qs = (
        general_information.objects
        .select_related("department", "designation")
        .all()
        .order_by("name")
    )
    
    selected_department_ids = academic_department_ids + non_academic_department_ids
    if selected_department_ids:
        faculty_qs = faculty_qs.filter(department_id__in=selected_department_ids)
    
    if selected_academic and not selected_non_academic:
        faculty_qs = faculty_qs.filter(
            department__is_academic=True,
            designation__is_teaching=True
        )
    elif selected_non_academic and not selected_academic:
        faculty_qs = faculty_qs.filter(
            department__is_academic=False,
            designation__is_teaching=False
        )
    elif selected_academic and selected_non_academic:
        faculty_qs = faculty_qs.filter(
            Q(
                department__is_academic=True,
                designation__is_teaching=True
            ) |
            Q(
                department__is_academic=False,
                designation__is_teaching=False
            )
        )
    else:
        # default dashboard view
        faculty_qs = faculty_qs.filter(designation__is_teaching=True)

    if designation_ids:
        faculty_qs = faculty_qs.filter(designation_id__in=designation_ids)

    if approval:
        faculty_qs = faculty_qs.filter(approval=approval)

    if appointment_type:
        faculty_qs = faculty_qs.filter(appointment_type=appointment_type)

    if nature_of_duties:
        faculty_qs = faculty_qs.filter(nature_of_duties=nature_of_duties)

    if gender:
        faculty_qs = faculty_qs.filter(gender=gender)

    if search:
        faculty_qs = faculty_qs.filter(
            Q(name__icontains=search) |
            Q(faculty_id__icontains=search) |
            Q(college_email__icontains=search) |
            Q(personal_email__icontains=search) |
            Q(PAN_number__icontains=search) |
            Q(Aadhar_number__icontains=search)
        )

    total_faculty = faculty_qs.count()

    approved_count = faculty_qs.filter(approval="Approved").count()
    pending_count = faculty_qs.filter(approval="Pending").count()

    regular_count = faculty_qs.filter(appointment_type="Regular").count()
    contract_count = faculty_qs.filter(appointment_type="Contract").count()
    adhoc_count = faculty_qs.filter(appointment_type="Adhoc").count()

    teaching_count = faculty_qs.filter(nature_of_duties="Teaching").count()
    research_count = faculty_qs.filter(nature_of_duties="Research").count()
    administration_count = faculty_qs.filter(nature_of_duties="Administration").count()

    male_count = faculty_qs.filter(gender=general_information.GenderChoices.MALE).count()
    female_count = faculty_qs.filter(gender=general_information.GenderChoices.FEMALE).count()
    transgender_count = faculty_qs.filter(gender=general_information.GenderChoices.TRANSGENDER).count()
    other_gender_count = faculty_qs.filter(gender=general_information.GenderChoices.OTHER).count()

    department_data = list(
        faculty_qs.values("department__Department")
        .annotate(total=Count("id"))
        .order_by("department__Department")
    )
    department_labels = [item["department__Department"] or "No Department" for item in department_data]
    department_counts = [item["total"] for item in department_data]

    designation_data = list(
        faculty_qs.values("designation__designation_name")
        .annotate(total=Count("id"))
        .order_by("designation__designation_name")
    )
    designation_labels = [item["designation__designation_name"] or "No Designation" for item in designation_data]
    designation_counts = [item["total"] for item in designation_data]

    gender_data = list(
        faculty_qs.values("gender")
        .annotate(total=Count("id"))
        .order_by("gender")
    )
    gender_labels = [item["gender"] or "Not Set" for item in gender_data]
    gender_counts = [item["total"] for item in gender_data]

    paginator = Paginator(faculty_qs, 50)
    page_number = request.GET.get("page")
    faculty_page = paginator.get_page(page_number)

    academic_departments = Add_Department.objects.filter(is_academic=True, is_active=True).order_by("Department")
    non_academic_departments = Add_Department.objects.filter(is_academic=False, is_active=True).order_by("Department")

    all_designations = DesignationMaster.objects.all().order_by("designation_name")

    if selected_academic and not selected_non_academic:
        designations = all_designations.filter(is_teaching=True)
    elif selected_non_academic and not selected_academic:
        designations = all_designations.filter(is_teaching=False)
    else:
        designations = all_designations
    context = {
        "faculty_qs": faculty_page,
        "faculty_page": faculty_page,

        "academic_departments": academic_departments,
        "non_academic_departments": non_academic_departments,
        "designations": designations,
        "all_designations": all_designations,
        "gender_choices": general_information.GenderChoices.choices,

        "total_faculty": total_faculty,
        "approved_count": approved_count,
        "pending_count": pending_count,
        "regular_count": regular_count,
        "contract_count": contract_count,
        "adhoc_count": adhoc_count,
        "teaching_count": teaching_count,
        "research_count": research_count,
        "administration_count": administration_count,

        "male_count": male_count,
        "female_count": female_count,
        "transgender_count": transgender_count,
        "other_gender_count": other_gender_count,

        "department_labels": department_labels,
        "department_counts": department_counts,
        "designation_labels": designation_labels,
        "designation_counts": designation_counts,
        "gender_labels": gender_labels,
        "gender_counts": gender_counts,

        "selected_academic_departments": academic_department_ids,
        "selected_non_academic_departments": non_academic_department_ids,
        "selected_designations": designation_ids,
        "selected_approval": approval,
        "selected_appointment_type": appointment_type,
        "selected_nature_of_duties": nature_of_duties,
        "selected_gender": gender,
        "search": search,
    }

    return render(request, "faculty_management/faculty_analysis_dashboard.html", context)

