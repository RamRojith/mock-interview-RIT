import json
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.db import connections
from django.db.utils import DatabaseError

from user_accounts.decorators import no_cache, is_super_user
from user_accounts.models import Role, Add_Department
from student_management.models import AssignApproval

logger = logging.getLogger(__name__)
ROLE_DB_ALIAS = "rit_approval_system"

BONAFIDE_CERTIFICATE_TYPES = (
    "Passport Application",
    "Bank Loan",
    "TNPSC Application Process",
    "Unorganised Workers Welfare Board",
    "Government Job Application",
    "Post Office",
    "Ulavar Identity Card",
    "Mason Association",
    "New Bank Account Opening Application",
    "Labour Welfare Board",
    "Higher Studies",
    "Nalavariyam Scholarship",
)
BONAFIDE_ALLOWED_SUBJECTS = set(BONAFIDE_CERTIFICATE_TYPES) | {"Other"}


# ============================================================
# ✅ Assign Approver Management (GET UI + POST Save)
# ============================================================
@no_cache
@is_super_user("student_management")   
@csrf_exempt
def assign_approval_management(request):
    """
    GET:
      Render UI with roles + departments

    POST:
      JSON body:
      {
        "creatorRole": <role_id>,
        "roleHierarchy": [
          {"id": <approver_role_id>, "isCrossDepartment": true/false, "departmentId": <dept_id|null>},
          ...
        ]
      }

      Deletes old rows for creatorRole and recreates in order (approver_level = index+1)
    """

    # ---------------------------
    # ✅ GET (UI Load)
    # ---------------------------
    if request.method == "GET":
        roles = Role.objects.using(ROLE_DB_ALIAS).all().order_by("role")
        departments = Add_Department.objects.all().order_by("Department")

        return render(
            request,
            "student_management/admin/assign_approval.html",
            {"roles": roles, "departments": departments},
        )

    # ---------------------------
    # ✅ POST (Save Hierarchy)
    # ---------------------------
    if request.method == "POST":
        try:
            raw = request.body.decode("utf-8") if isinstance(request.body, (bytes, bytearray)) else request.body
            data = json.loads(raw or "{}")

            creator_role_id = data.get("creatorRole")
            role_hierarchy = data.get("roleHierarchy", [])

            if not creator_role_id:
                return JsonResponse({"error": "creatorRole is required"}, status=400)

            try:
                creator_role_id = int(creator_role_id)
            except (TypeError, ValueError):
                return JsonResponse({"error": "creatorRole must be an integer"}, status=400)

            # ✅ ensure creator role exists in roles DB
            creator_exists = Role.objects.using(ROLE_DB_ALIAS).filter(id=creator_role_id).exists()
            if not creator_exists:
                return JsonResponse({"error": "Creator role not found"}, status=404)

            # ✅ remove old hierarchy for this creator
            AssignApproval.objects.filter(creator_role_id=creator_role_id).delete()

            # ✅ create new hierarchy
            for index, role_data in enumerate(role_hierarchy):
                approver_role_id = role_data.get("id")
                if not approver_role_id:
                    continue

                try:
                    approver_role_id = int(approver_role_id)
                except (TypeError, ValueError):
                    continue

                approver_exists = Role.objects.using(ROLE_DB_ALIAS).filter(id=approver_role_id).exists()
                if not approver_exists:
                    return JsonResponse({"error": f"Approver role not found: {approver_role_id}"}, status=404)

                is_cross_department = bool(role_data.get("isCrossDepartment", False))
                department_id = role_data.get("departmentId") or None

                # if cross dept is true -> department is mandatory
                if is_cross_department:
                    if not department_id:
                        return JsonResponse(
                            {"error": "departmentId is required when isCrossDepartment is true"},
                            status=400
                        )
                    try:
                        department_id = int(department_id)
                    except (TypeError, ValueError):
                        return JsonResponse({"error": "departmentId must be an integer"}, status=400)

                    # optional: validate department exists (local db)
                    if not Add_Department.objects.filter(id=department_id).exists():
                        return JsonResponse({"error": "Selected department not found"}, status=404)

                # ✅ IMPORTANT:
                # store only *_id to avoid cross-db FK problems
                AssignApproval.objects.create(
                    creator_role_id=creator_role_id,
                    approver_role_id=approver_role_id,
                    approver_level=index + 1,
                    is_cross_department_approver="YES" if is_cross_department else "NO",
                    approver_department_id=department_id if is_cross_department else None
                )

            return JsonResponse({"message": "Roles submitted successfully"}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            logger.exception("Error in assign_approval_management POST")
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)


# ============================================================
# ✅ API: Load Matched + Unmatched Roles (NO FK dereference)
# ============================================================
@require_GET
def api_assign_role_to_employees(request, creatorRoleId):
    try:
        creator_role_id = int(creatorRoleId)
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid creatorRoleId"}, status=400)

    try:
        if not Role.objects.using(ROLE_DB_ALIAS).filter(id=creator_role_id).exists():
            return JsonResponse({"error": "Creator role not found"}, status=404)

        approvers = list(
            AssignApproval.objects
            .filter(creator_role_id=creator_role_id)
            .order_by("approver_level")
            .values("approver_role_id", "is_cross_department_approver", "approver_department_id")
        )

        approver_role_ids = [a["approver_role_id"] for a in approvers if a["approver_role_id"]]
        matched_ids_set = set(approver_role_ids)

        role_map = {}
        if approver_role_ids:
            role_map = {
                r["id"]: r["role"]
                for r in Role.objects.using(ROLE_DB_ALIAS)
                .filter(id__in=approver_role_ids)
                .values("id", "role")
            }

        matched_roles = []
        for a in approvers:
            rid = a["approver_role_id"]
            dept_id = a.get("approver_department_id")

            matched_roles.append({
                "id": rid,
                "role": role_map.get(rid, f"Role #{rid}"),
                "is_cross_department": (a["is_cross_department_approver"] == "YES"),

                # ✅ return BOTH keys (so any JS/html works)
                "approver_department_id": dept_id,
                "approver_department": dept_id,
            })

        roles_qs = Role.objects.using(ROLE_DB_ALIAS).exclude(id=creator_role_id)
        if matched_ids_set:
            roles_qs = roles_qs.exclude(id__in=matched_ids_set)

        unmatched_roles = list(roles_qs.order_by("role").values("id", "role"))
        unmatched_roles = [{"id": r["id"], "role": r["role"]} for r in unmatched_roles]

        return JsonResponse(
            {"matched_roles": matched_roles, "unmatched_roles": unmatched_roles},
            status=200
        )

    except Exception as e:
        logger.exception("api_assign_role_to_employees error: %s", e)
        return JsonResponse({"error": str(e)}, status=500)





import logging
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from student_management.models import (
    BonafideApplication,
    BonafideApprovalFlow,
    AssignApproval,
)
from user_accounts.models import (
    StudentDetails,
    PersonalDetails,
    AdmissionRecords,
    AcademicDetails,
)
from user_accounts.decorators import check_permission

from faculty_management.models import general_information

logger = logging.getLogger(__name__)


from datetime import date
import json
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from user_accounts.decorators import check_permission
from user_accounts.models import StudentDetails, PersonalDetails, AdmissionRecords, AcademicDetails, Role
from student_management.models import BonafideApplication, BonafideApprovalFlow, AssignApproval

logger = logging.getLogger(__name__)
ROLE_DB_ALIAS = "rit_approval_system"


def get_academic_year():
    today = date.today()
    current_year = today.year
    if today.month >= 6:
        return f"{current_year}-{current_year + 1}"
    else:
        return f"{current_year - 1}-{current_year}"


def _fetch_personal_and_admission(aadhar):
    personal = admission_record = academic = None
    try:
        personal = PersonalDetails.objects.using("admissionform1").get(Aadhaar_Number=aadhar)
        admission_record = AdmissionRecords.objects.using("admissionform1").filter(
            PersonalDetailsId=personal.id
        ).first()
        if admission_record:
            academic_id = getattr(admission_record, "AcademicDetailsId_id", None)
            if academic_id:
                academic = AcademicDetails.objects.using("admissionform1").filter(id=academic_id).first()
    except PersonalDetails.DoesNotExist:
        personal = None
    return personal, admission_record, academic


@csrf_exempt
@check_permission("bonafide_apply")
def bonafide_apply(request):
    reg_no = (
        request.GET.get("reg_no")
        or request.POST.get("reg_no")
        or getattr(request.user, "Employee_id", None)
        or ""
    )

    student_name = father_name = department_name = year_display = ""

    if reg_no:
        student = StudentDetails.objects.filter(reg_no=reg_no).select_related("department").first()
        if student:
            student_name = student.name or ""
            department_name = getattr(student.department, "Department", "")
            year_value = str(student.year or "")
            year_display = {"1": "1st Year", "2": "2nd Year", "3": "3rd Year", "4": "4th Year"}.get(year_value, year_value)

            aadhar_raw = getattr(student, "aadhar_number", None) or getattr(student, "aadhar", None)
            if aadhar_raw:
                aadhar = "".join(ch for ch in str(aadhar_raw).strip() if ch.isdigit())
                try:
                    personal, _, _ = _fetch_personal_and_admission(aadhar)
                    father_name = getattr(personal, "father_name", "N/A") if personal else "N/A"
                except Exception:
                    father_name = "N/A"
            else:
                father_name = "N/A"

    # ✅ POST: Create Application
    if request.method == "POST":
        subject = request.POST.get("subject", "").strip()
        other_reason = request.POST.get("other_reason", "").strip()
        applicant_regno = request.POST.get("reg_no", reg_no)

        if subject not in BONAFIDE_ALLOWED_SUBJECTS:
            return JsonResponse({"status": "error", "message": "Please select a valid certificate type."}, status=400)
        if subject == "Other" and not other_reason:
            return JsonResponse({"status": "error", "message": "Please specify your requirement."}, status=400)
        if subject != "Other":
            other_reason = ""

        student_obj = StudentDetails.objects.filter(reg_no=applicant_regno).select_related("department").first()
        if not student_obj:
            return JsonResponse({"error": "Student not found"}, status=400)

        bonafide_app = BonafideApplication.objects.create(
            student=student_obj,
            subject=subject,
            other_reason=other_reason,
            father_name=father_name,
            department=student_obj.department,
            year_display=year_display,
            status="Pending",
            batch=student_obj.batch,
            year=student_obj.year,
            semester=student_obj.semester,
            regulation=student_obj.regulation,
            academic_year=get_academic_year(),
        )

        student_dept_id = getattr(student_obj.department, "id", None)

        # ✅ FIX: Find creator role = Student (from roles DB)
        student_creator_role_id = (
            Role.objects.using(ROLE_DB_ALIAS)
            .filter(role__iexact="Student")
            .values_list("id", flat=True)
            .first()
        )

        if not student_creator_role_id:
            # no mapping => auto approve OR keep pending as you wish
            bonafide_app.status = "Approved"
            bonafide_app.save(update_fields=["status"])
            return JsonResponse({"status": "success", "message": "Bonafide submitted (no approver mapping found)"}, status=200)

        # ✅ FIX: Pick FIRST APPROVER only for this creator role
        first_approval = (
            AssignApproval.objects
            .filter(creator_role_id=student_creator_role_id, approver_level=1)
            .values("approver_role_id", "approver_level", "is_cross_department_approver", "approver_department_id")
            .first()
        )

        if first_approval:
            # ✅ department routing
            if first_approval["is_cross_department_approver"] == "YES":
                route_dept_id = first_approval["approver_department_id"]
            else:
                route_dept_id = student_dept_id

            BonafideApprovalFlow.objects.create(
                application=bonafide_app,
                approver_role_id=first_approval["approver_role_id"],
                approver_department_id=route_dept_id,
                approver_level=first_approval["approver_level"],
                status="Pending",
                created_on=timezone.now(),
            )
        else:
            bonafide_app.status = "Approved"
            bonafide_app.save(update_fields=["status"])

        return JsonResponse({"status": "success", "message": "Bonafide application submitted successfully"}, status=200)

    applied_bonafides = BonafideApplication.objects.filter(student__reg_no=reg_no).order_by("-applied_on")
    return render(
        request,
        "student_management/bonafide/bonafide_apply.html",
        {
            "student_name": student_name,
            "father_name": father_name,
            "department_name": department_name,
            "year_display": year_display,
            "reg_no": reg_no,
            "applied_bonafides": applied_bonafides,
            "certificate_types": BONAFIDE_CERTIFICATE_TYPES,
        },
    )



# --------------------------------------------------------
# 🔹 Bonafide Approval Dashboard View
# --------------------------------------------------------


from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction

from user_accounts.decorators import check_permission
from faculty_management.models import general_information
from student_management.models import AssignApproval, BonafideApplication, BonafideApprovalFlow


logger = logging.getLogger(__name__)
ROLE_DB_ALIAS = "rit_approval_system"


import logging
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from user_accounts.decorators import check_permission
from faculty_management.models import general_information
from student_management.models import AssignApproval, BonafideApplication, BonafideApprovalFlow
from user_accounts.models import Role

logger = logging.getLogger(__name__)
ROLE_DB_ALIAS = "rit_approval_system"


@check_permission("bonafide_approve_view")
def bonafide_approve_view(request):
    approver_role_id = getattr(request.user, "role_id", None)

    faculty_info = general_information.objects.filter(faculty_id=request.user.Employee_id).first()
    approver_dept_id = getattr(faculty_info, "department_id", None)

    if not approver_role_id:
        return JsonResponse({"error": "Approver role not found"}, status=400)

    # ✅ CREATOR ROLE = Student chain
    student_creator_role_id = (
        Role.objects.using(ROLE_DB_ALIAS)
        .filter(role__iexact="Student")
        .values_list("id", flat=True)
        .first()
    )
    if not student_creator_role_id:
        return JsonResponse({"error": "Student creator role not configured in roles DB"}, status=500)

    # ✅ Cross-department approver => driven by the "Cross Dept" checkbox set on the
    # Assign Approver Management page (AssignApproval.is_cross_department_approver),
    # NOT a hardcoded list of role names. Any role marked cross-department for this
    # creator chain can view/act on applications regardless of their own department.
    is_global_approver = AssignApproval.objects.filter(
        creator_role_id=student_creator_role_id,
        approver_role_id=approver_role_id,
        is_cross_department_approver="YES",
    ).exists()

    # -----------------------------------------------------
    # ✅ POST — Approve / Reject
    # -----------------------------------------------------
    if request.method == "POST":
        app_id = request.POST.get("application_id")
        action = request.POST.get("action")
        remarks = (request.POST.get("remarks") or "").strip()

        if not app_id or action not in ["approve", "reject"]:
            return JsonResponse({"error": "Invalid request"}, status=400)

        app = get_object_or_404(BonafideApplication, id=app_id)

        # ✅ IMPORTANT:
        # - normal approver: match by role + department
        # - global approver: match by role only
        current_flow_qs = BonafideApprovalFlow.objects.filter(
            application=app,
            approver_role_id=approver_role_id,
            status="Pending",
        )

        if not is_global_approver:
            if not approver_dept_id:
                return JsonResponse({"error": "Approver department not found"}, status=400)
            current_flow_qs = current_flow_qs.filter(approver_department_id=approver_dept_id)

        current_flow = current_flow_qs.first()

        if not current_flow:
            return JsonResponse({"error": "Not authorized / already processed"}, status=403)

        with transaction.atomic():
            current_flow.status = "Approved" if action == "approve" else "Rejected"
            current_flow.remarks = remarks
            current_flow.acted_on = timezone.now()
            current_flow.save(update_fields=["status", "remarks", "acted_on"])

            if action == "reject":
                app.status = "Rejected"
                app.save(update_fields=["status"])
                return JsonResponse({"message": "Application rejected successfully"}, status=200)

            # ✅ NEXT APPROVER from Student chain
            next_approval = (
                AssignApproval.objects
                .filter(
                    creator_role_id=student_creator_role_id,
                    approver_level=current_flow.approver_level + 1
                )
                .values("approver_role_id", "approver_level", "is_cross_department_approver", "approver_department_id")
                .first()
            )

            if next_approval:
                # ✅ route department
                if next_approval["is_cross_department_approver"] == "YES":
                    next_dept_id = next_approval["approver_department_id"]
                else:
                    next_dept_id = app.department_id

                exists = BonafideApprovalFlow.objects.filter(
                    application=app,
                    approver_role_id=next_approval["approver_role_id"],
                    approver_department_id=next_dept_id,
                    approver_level=next_approval["approver_level"],
                    status="Pending"
                ).exists()

                if not exists:
                    BonafideApprovalFlow.objects.create(
                        application=app,
                        approver_role_id=next_approval["approver_role_id"],
                        approver_department_id=next_dept_id,
                        approver_level=next_approval["approver_level"],
                        status="Pending",
                    )

                app.status = "Pending"
                app.save(update_fields=["status"])
                return JsonResponse({"message": "Moved to next approver"}, status=200)

            app.status = "Approved"
            app.save(update_fields=["status"])
            return JsonResponse({"message": "Application approved successfully (Final)"}, status=200)

    # -----------------------------------------------------
    # ✅ GET — Pending & Past
    # -----------------------------------------------------
    pending_qs = BonafideApprovalFlow.objects.filter(
        approver_role_id=approver_role_id,
        status="Pending",
    )
    past_qs = BonafideApprovalFlow.objects.filter(
        approver_role_id=approver_role_id,
    ).exclude(status="Pending")

    if not is_global_approver:
        if not approver_dept_id:
            return JsonResponse({"error": "Approver department not found"}, status=400)
        pending_qs = pending_qs.filter(approver_department_id=approver_dept_id)
        past_qs = past_qs.filter(approver_department_id=approver_dept_id)

    pending_flows = pending_qs.select_related("application", "application__student", "approver_department")
    past_flows = past_qs.select_related("application", "application__student", "approver_department")

    return render(
        request,
        "student_management/bonafide/bonafide_approve.html",
        {"pending_flows": pending_flows, "past_flows": past_flows},
    )
 




# ----- ---------------------------------------------------
# 🔹 Delete Bonafide Record
# --------------------------------------------------------


@csrf_exempt
def delete_bonafide_request(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)
    app_id = request.POST.get("application_id")
    if not app_id:
        return JsonResponse({"error": "Missing application ID"}, status=400)

    try:
        BonafideApplication.objects.filter(id=app_id).delete()
        BonafideApprovalFlow.objects.filter(application_id=app_id).delete()
        return JsonResponse({"success": True})
    except Exception as e:
        logger.exception("Error deleting bonafide record: %s", e)
        return JsonResponse({"error": "Failed to delete record"}, status=500)




def split_text(c, text, max_width):
    """
    Helper: Split long text into multiple lines fitting in max_width.
    """
    words = text.split()
    lines, line = [], ""
    for word in words:
        test_line = f"{line} {word}".strip()
        if c.stringWidth(test_line, "Helvetica", 12) <= max_width:
            line = test_line
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def draw_justified_text(c, text, left_x, right_x, start_y, line_height, font="Helvetica", size=12):
    """
    Draw text with justified alignment between left_x and right_x.
    """
    c.setFont(font, size)
    words = text.split()
    line, lines = [], []
    space_width = c.stringWidth(" ", font, size)
    max_width = right_x - left_x

    # Word wrap into lines
    for word in words:
        test_line = " ".join(line + [word])
        if c.stringWidth(test_line, font, size) <= max_width:
            line.append(word)
        else:
            lines.append(line)
            line = [word]
    if line:
        lines.append(line)

    y = start_y
    for i, line in enumerate(lines):
        if not line:
            continue
        if i == len(lines) - 1 or len(line) == 1:
            # Last line or single word → left align
            c.drawString(left_x, y, " ".join(line))
        else:
            line_text = " ".join(line)
            total_text_width = c.stringWidth(line_text, font, size)
            extra_space = (max_width - total_text_width) / (len(line) - 1)
            x = left_x
            for w in line:
                c.drawString(x, y, w)
                x += c.stringWidth(w, font, size) + extra_space
        y -= line_height



from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Frame



def bonafide_view_pdf(request, app_id):
    """
    Generate Bonafide Certificate PDF (clean official format matching printed RIT certificate),
    with justified text and bold name/year/department.
    """
    app = get_object_or_404(BonafideApplication, id=app_id)
    student = app.student

    # Prepare response as PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename=Bonafide_{student.reg_no}.pdf'

    c = canvas.Canvas(response, pagesize=A4)
    c.setTitle("Bonafide_Certificate")

    page_w, page_h = A4

    left_margin = 25 * mm
    right_margin = page_w - 25 * mm
    # Start the complete certificate content 4.5 cm below the top edge.
    top_margin = page_h - 45 * mm
    bottom_margin = 20 * mm

    # ----------------------------------------------------------
    # 🔹 Title & Date
    # ----------------------------------------------------------
    c.setFont("Helvetica", 11)
    c.drawRightString(right_margin, top_margin, f"Date: {datetime.now().strftime('%d/%m/%Y')}")
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(page_w / 2.0, top_margin - 10 * mm, "Bonafide Certificate")

    # ----------------------------------------------------------
    # 🔹 Body (Justified)
    # ----------------------------------------------------------
    year_display = getattr(app, "year_display", "")
    dept_name = getattr(app, "department", "")
    degree = getattr(app.department.degree, "degree_code", "")

    academic_year = getattr(app, "academic_year", "")

    purpose_text = app.other_reason if app.subject == "Other" and app.other_reason else app.subject
    if not purpose_text:
        purpose_text = "Official Purpose"

    body_html = (
        f"<font size=12>"
        f"This is to certify that <b>{student.name.upper()}</b> (<b>{student.reg_no}</b>) S/o Mr.{app.father_name} "
        f"is a Bonafide student of our College, studying in <b>{year_display}</b> "
        f"<b>{degree} - {dept_name}</b> during the Academic Year <b>{academic_year}</b>.<br/><br/>"
        f"This Certificate is issued for applying {purpose_text} Purpose only."
        f"</font>"
    )

    style = ParagraphStyle(
        name="Justify",
        fontName="Helvetica",
        fontSize=12,
        leading=20,
        alignment=4,
        spaceAfter=15,
    )

    paragraph = Paragraph(body_html, style)

    # Keep the certificate paragraph centred below the date and title.
    body_top = top_margin - (30 * mm)
    frame_height = 80 * mm
    frame_width = page_w - (60 * mm)
    frame_left = (page_w - frame_width) / 2
    frame = Frame(
        frame_left,
        body_top - frame_height,
        frame_width,
        frame_height,
        showBoundary=0,
    )
    frame.addFromList([paragraph], c)

    # -------------------------------------------------------
    # 🔹 Signature + Date
    # -------------------------------------------------------
    final_flow = app.approval_flow.filter(status="Approved").order_by('-acted_on').first()
    approved_date = final_flow.acted_on if final_flow else datetime.now()
    approved_date_str = approved_date.strftime('%d/%m/%Y')

    # Principal
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(right_margin, bottom_margin + 110, "PRINCIPAL")

    # Approved Date
    c.setFont("Helvetica", 11)
    c.drawRightString(right_margin, bottom_margin + 95, f"Date: {approved_date_str}")

    # -------------------------------------------------------
    # 🔹 Computer-Generated Certificate Notice (NEW)
    # -------------------------------------------------------
    c.setFont("Helvetica-Oblique", 10)
    c.setFillColor(colors.black)
    c.drawCentredString(
        page_w / 2.0, 
        bottom_margin + 60,
        "This is a e-generated bonafide certificate."
    )

    c.showPage()
    c.save()
    return response








@csrf_exempt
@check_permission("bonafide_apply")
def bonafide_edit(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    app_id = data.get("application_id")
    subject = (data.get("subject") or "").strip()
    other_reason = (data.get("other_reason") or "").strip()

    if not app_id or not subject:
        return JsonResponse({"error": "Missing required fields"}, status=400)
    if subject not in BONAFIDE_ALLOWED_SUBJECTS:
        return JsonResponse({"error": "Please select a valid certificate type"}, status=400)
    if subject == "Other" and not other_reason:
        return JsonResponse({"error": "Please specify your requirement"}, status=400)

    app = get_object_or_404(BonafideApplication, id=app_id)

 
    if app.status != "Pending":
        return JsonResponse({"error": "Cannot edit. Application already processed."}, status=403)

 
    app.subject = subject
    app.other_reason = other_reason if subject == "Other" else ""
    app.save(update_fields=["subject", "other_reason"])

    return JsonResponse({"status": "success", "message": "Application updated successfully"})





from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.db import transaction
from user_accounts.models import StudentDetails, Add_Department
from faculty_management.models import general_information

@check_permission("update_umis_id")
def update_umis_id(request):
    emp_id=request.user.Employee_id
    # Logged-in faculty department name
    faculty = general_information.objects.get(faculty_id=emp_id)
    # print(faculty.department)

    try:
        department = Add_Department.objects.get(id=faculty.department.id)
    except Add_Department.DoesNotExist:
        messages.error(request, "Department not found.")
        return redirect("home")

    faculty_department = general_information.objects.filter(
        faculty_id=request.user.Employee_id,
        department=department
    ).first()

    # GET batch from URL, NOT POST
    selected_batch = request.GET.get("batch")

    batches = StudentDetails.objects.filter(
        department=department
    ).values_list("batch", flat=True).distinct().order_by("batch")

    students = None

    # --------------------------- SAVE (POST) ----------------------------
    if request.method == "POST" and "save_umis" in request.POST:

        selected_batch = request.POST.get("selected_batch")

        try:
            with transaction.atomic():
                for key, value in request.POST.items():
                    if key.startswith("umis_"):
                        student_id = key.split("_")[1]
                        StudentDetails.objects.filter(id=student_id).update(
                            umis_id=value.strip()
                        )

            messages.success(request, "UMIS IDs updated successfully.")

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

        # CRITICAL FIX: REDIRECT AFTER SAVE → NO RESUBMISSION ON REFRESH
        return redirect(f"{reverse('update_umis_id')}?batch={selected_batch}")

    # --------------------------- LOAD (POST) ----------------------------
    if request.method == "POST" and "load_students" in request.POST:
        selected_batch = request.POST.get("batch")

        # REDIRECT to clean GET URL 
        return redirect(f"{reverse('update_umis_id')}?batch={selected_batch}")

    # --------------------------- GET Students ----------------------------
    if selected_batch:
        students = StudentDetails.objects.filter(
            department=department,
            batch=selected_batch
        ).order_by("name")

    context = {
        "faculty_department": faculty_department,
        "department": department,
        "batches": batches,
        "students": students,
        "selected_batch": selected_batch,
    }

    return render(request, "student_management/faculty/update_umis_id.html", context)


# student_management/views/sm_views.py


