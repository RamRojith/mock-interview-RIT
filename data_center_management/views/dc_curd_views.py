from django.contrib import messages
from django.shortcuts import render, redirect
from django.db import transaction

from data_center_management.decorators import data_center_management
from data_center_management.models import (
    DataCenterRequest,
    DataCenterRequestApprovers,
    DataCenterRequestApproversData,
)

from user_accounts.models import USER, PersonalDetails, AdmissionRecords
from student_management.models import StudentDetails
from faculty_management.models import general_information
from user_accounts.decorators import check_permission


from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone

from user_accounts.models import USER, Role, Add_Department, Department
from student_management.models import StudentDetails
from faculty_management.models import general_information
from data_center_management.models import (
    DataCenterRequest,
    DataCenterRequestApprovers,
    DataCenterRequestApproversData,
)
from user_accounts.models import PersonalDetails, AdmissionRecords
from data_center_management.decorators import data_center_management
from user_accounts.decorators import check_permission


APPROVAL_DB = "rit_approval_system"


def get_logged_in_role_obj(request):
    user = request.user

    cr_user = (
        USER.objects.using(APPROVAL_DB)
        .filter(email=user.email)
        .select_related("role")
        .first()
    )

    if not cr_user:
        return None

    return cr_user.role


def get_student_admission_mode(reg_no):
    """
    Fetch admission mode from external DB: admissionform1
    StudentDetails.reg_no -> PersonalDetails.registration_no
    PersonalDetails -> AdmissionRecords.PersonalDetailsId
    """
    if not reg_no:
        return None

    personal_details = (
        PersonalDetails.objects.using("admissionform1")
        .filter(registration_no=reg_no)
        .first()
    )

    if not personal_details:
        return None

    admission_record = (
        AdmissionRecords.objects.using("admissionform1")
        .filter(PersonalDetailsId=personal_details)
        .first()
    )

    if not admission_record:
        return None

    return (admission_record.Mode or "").strip()


def is_hosteller(mode):
    """
    STRICT hostel check.
    Only exact HOSTEL should return True.
    """
    if not mode:
        return False

    return mode.strip().upper() == "HOSTEL"


def build_student_dashboard_data(student):
    if not student:
        return None

    admission_mode = get_student_admission_mode(student.reg_no)

    return {
        "id": student.id,
        "name": student.name,
        "reg_no": student.reg_no,
        "email": student.email,
        "mobile_no": student.mobile_no,
        "department": student.department.Department if student.department else "",
        "gender": student.gender,
        "year": student.year,
        "semester": student.semester,
        "section": student.section,
        "admission_mode": admission_mode,
    }


def build_faculty_dashboard_data(faculty):
    if not faculty:
        return None

    return {
        "id": faculty.id,
        "faculty_id": getattr(faculty, "faculty_id", ""),
        "name": getattr(faculty, "name", ""),
        "college_email": getattr(faculty, "college_email", ""),
        "personal_email": getattr(faculty, "personal_email", ""),
        "phone": getattr(faculty, "phone", ""),
        "department": faculty.department.Department if faculty.department else "",
        "designation": str(faculty.designation) if getattr(faculty, "designation", None) else "",
    }


def get_external_role_name(role_id):
    if not role_id:
        return ""

    role_obj = (
        Role.objects.using(APPROVAL_DB)
        .filter(id=role_id)
        .values("role")
        .first()
    )
    return (role_obj or {}).get("role", "").strip()


def is_faculty_role(role_id):
    """
    No hardcoded role id.
    Faculty role is detected dynamically from Role table in rit_approval_system.
    """
    return get_external_role_name(role_id).lower() == "faculty"


def get_request_creator_department(dc_request):
    if not dc_request:
        return None

    if getattr(dc_request, "student_id", None) and getattr(dc_request.student, "department_id", None):
        return dc_request.student.department

    if getattr(dc_request, "faculty_id", None) and getattr(dc_request.faculty, "department_id", None):
        return dc_request.faculty.department

    return None


def get_student_ca(dc_request):
    """
    Faculty-role approval should go only to the student's CA.
    """
    if not dc_request:
        return None

    if getattr(dc_request, "student_id", None) and getattr(dc_request.student, "ca_id", None):
        return dc_request.student.ca

    return None


def resolve_wifi_approver_faculty(dc_request, route):
    """
    Resolve the approver faculty for a route purely from the configured
    hierarchy: match the approver role in the external USER table, honouring
    the same/cross department rule. No special-casing of any role name.
    """
    if not route or not route.approver_role_id:
        return None

    # CROSS-DEPARTMENT ROUTE:
    # Ticking "cross dept" alone means an application from ANY department may
    # reach this role, and ANY faculty holding this role may approve it. We do
    # NOT pin a single approver here — leave it open so the role-based check
    # governs who can act (see can_faculty_approve_entry).
    if str(route.is_cross_department_approver or "").upper() == "YES":
        return None

    # SAME-DEPARTMENT ROUTE: resolve an approver in the creator's department.
    approver_filter = {"role_id": route.approver_role_id}

    creator_department = get_request_creator_department(dc_request)
    if creator_department:
        dept_code = getattr(creator_department, "Department_code", None)

        if dept_code:
            ext_dept_id = (
                Department.objects.using(APPROVAL_DB)
                .filter(Department_code=dept_code)
                .values_list("id", flat=True)
                .first()
            )
            if ext_dept_id:
                approver_filter["Department_id"] = ext_dept_id

    approver_user = USER.objects.using(APPROVAL_DB).filter(**approver_filter).first()
    if not approver_user:
        return None

    approver_faculty = (
        general_information.objects
        .select_related("department", "designation")
        .filter(faculty_id=approver_user.Employee_id)
        .first()
    )

    return approver_faculty


def create_wifi_approver_chain(dc_request, creator_role_id, creator_faculty):
    """
    Create runtime approval rows in DataCenterRequestApproversData.
    Returns number of rows created.
    """
    if not dc_request or not creator_role_id:
        return 0

    # Avoid duplicate chain creation
    existing_count = DataCenterRequestApproversData.objects.filter(request=dc_request).count()
    if existing_count > 0:
        return existing_count

    routes = (
        DataCenterRequestApprovers.objects
        .select_related("approver_department")
        .filter(creator_role_id=creator_role_id)
        .order_by("approver_level", "id")
    )

    if not routes.exists():
        return 0

    created_rows = 0
    created_levels = set()

    for route in routes:
        level = route.approver_level

        # create only one row per level
        if level in created_levels:
            continue

        approver_faculty = resolve_wifi_approver_faculty(dc_request, route)

        DataCenterRequestApproversData.objects.create(
            request=dc_request,
            approver=approver_faculty,
            creator=creator_faculty,
            approver_role_id=route.approver_role_id,
            creator_role_id=creator_role_id,
            approver_level=level,
            status=DataCenterRequestApproversData.Status.PENDING,
            reason=None,
            acted_on=timezone.now(),
        )

        created_rows += 1
        created_levels.add(level)

    return created_rows


@data_center_management
@check_permission("wifi_application")
def wifi_application(request):
    user = request.user
    user_email = (getattr(user, "email", "") or "").strip()

    student = (
        StudentDetails.objects
        .filter(email__iexact=user_email)
        .select_related("department", "ca")
        .first()
    )

    faculty = None

    if not student:
        faculty = (
            general_information.objects
            .filter(college_email__iexact=user_email)
            .select_related("department", "designation")
            .first()
        )

    if not student and not faculty:
        messages.error(request, "Unable to identify user.")
        return redirect("dashboard")

    creator_role = get_logged_in_role_obj(request)

    if not creator_role:
        messages.error(request, "User role not found.")
        return redirect("dashboard")

    student_data = build_student_dashboard_data(student)
    faculty_data = build_faculty_dashboard_data(faculty)

    admission_mode = student_data.get("admission_mode") if student_data else None
    is_hosteller_flag = is_hosteller(admission_mode)

    # Show only requests raised by logged-in user
    if student:
        user_requests = (
            DataCenterRequest.objects
            .filter(student=student)
            .order_by("-created_at")
        )
    elif faculty:
        user_requests = (
            DataCenterRequest.objects
            .filter(faculty=faculty)
            .order_by("-created_at")
        )
    else:
        user_requests = DataCenterRequest.objects.none()

    context = {
        "student": student_data,
        "faculty": faculty_data,
        "admission_mode": admission_mode,
        "is_hosteller": is_hosteller_flag,
        "is_student_user": bool(student_data),
        "is_faculty_user": bool(faculty_data),
        "errors": {},
        "form_data": {},
        "user_requests": user_requests,
    }

    if request.method == "POST":
        cluster = request.POST.get("cluster", "").strip()
        room_no = request.POST.get("room_no", "").strip()
        ethernet_cable_required = request.POST.get("ethernet_cable_required") == "on"
        ethernet_mac_address = request.POST.get("ethernet_mac_address", "").strip()

        device_type = request.POST.get("device_type", "").strip()
        device_mac_address = request.POST.get("device_mac_address", "").strip()

        wifi_for_mobile_required = request.POST.get("wifi_for_mobile_required") == "on"
        mobile_no = request.POST.get("mobile_no", "").strip()
        mobile_static_mac_address = request.POST.get("mobile_static_mac_address", "").strip()

        is_for_event = request.POST.get("is_for_event") == "on"
        purpose = request.POST.get("purpose", "").strip()
        event_name = request.POST.get("event_name", "").strip()
        location = request.POST.get("location", "").strip()
        time_period = request.POST.get("time_period", "").strip()

        agreement = request.POST.get("agreement") == "on"

        errors = {}

        if is_hosteller_flag:
            if not cluster:
                errors["cluster"] = "Cluster is required"
            if not room_no:
                errors["room_no"] = "Room number is required"

        if not device_type:
            errors["device_type"] = "Device type required"

        if not device_mac_address:
            errors["device_mac_address"] = "WiFi MAC address required"

        if ethernet_cable_required:
            if not ethernet_mac_address:
                errors["ethernet_mac_address"] = "Ethernet MAC address required"

        if wifi_for_mobile_required:
            if not mobile_static_mac_address:
                errors["mobile_static_mac_address"] = "Mobile MAC required"

        if is_for_event:
            if not purpose:
                errors["purpose"] = "Purpose required"
            if not event_name:
                errors["event_name"] = "Event name required"
            if not location:
                errors["location"] = "Location required"
            if not time_period:
                errors["time_period"] = "Time period required"

        if not agreement:
            errors["agreement"] = "Accept agreement"

        if not errors:
            # Guard against duplicate submissions only when a MAC is supplied.
            # Blank optional MAC values should not make every request look like
            # the same device.
            if device_mac_address:
                dup_qs = DataCenterRequest.objects.filter(
                    status="PENDING",
                    device_mac_address=device_mac_address,
                )
                if student:
                    dup_qs = dup_qs.filter(student=student)
                else:
                    dup_qs = dup_qs.filter(faculty=faculty)

                if dup_qs.exists():
                    messages.info(
                        request,
                        "A pending request for this device already exists. Duplicate submission ignored."
                    )
                    return redirect("wifi_application")

            try:
                with transaction.atomic():
                    data_request = DataCenterRequest.objects.create(
                        creator_role_id=creator_role.id,
                        student_id=student.id if student else None,
                        faculty_id=faculty.id if faculty else None,
                        admission_mode=admission_mode,
                        cluster=cluster if is_hosteller_flag else None,
                        room_no=room_no if is_hosteller_flag else None,
                        ethernet_cable_required=ethernet_cable_required,
                        ethernet_mac_address=ethernet_mac_address if ethernet_cable_required else None,
                        device_type=device_type,
                        device_mac_address=device_mac_address,
                        wifi_for_mobile_required=wifi_for_mobile_required,
                        mobile_no=mobile_no or None,
                        mobile_static_mac_address=mobile_static_mac_address or None,
                        is_for_event=is_for_event,
                        purpose=purpose or None,
                        event_name=event_name or None,
                        location=location or None,
                        time_period=time_period or None,
                        agreement=agreement,
                        status="PENDING",
                    )

                    creator_faculty = faculty if faculty else None

                    created_rows = create_wifi_approver_chain(
                        dc_request=data_request,
                        creator_role_id=creator_role.id,
                        creator_faculty=creator_faculty,
                    )

                    if created_rows == 0:
                        data_request.status = "APPROVED"
                        data_request.save(update_fields=["status"])

                        messages.warning(
                            request,
                            "Request submitted, but no approval route matched. Request auto-approved."
                        )
                    else:
                        messages.success(request, "Request submitted successfully")

                    return redirect("wifi_application")

            except Exception as e:
                messages.error(request, f"Error: {str(e)}")

        context["errors"] = errors
        context["form_data"] = request.POST

    return render(
        request,
        "data_center_management/wifi/wifi_application.html",
        context
    )
 
 
from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect

from student_management.models import StudentDetails
from faculty_management.models import general_information
from data_center_management.models import NetworkQuery

from data_center_management.decorators import data_center_management
from user_accounts.decorators import check_permission

@data_center_management
@check_permission("query_application")
def query_application(request):
    user = request.user
    user_email = (getattr(user, "email", "") or "").strip()

    student = (
        StudentDetails.objects.filter(email__iexact=user_email)
        .select_related("department", "ca")
        .first()
    )

    faculty = None
    if not student:
        faculty = (
            general_information.objects.filter(college_email__iexact=user_email)
            .select_related("department", "designation")
            .first()
        )

    if not student and not faculty:
        messages.error(request, "Unable to identify user.")
        return redirect("dashboard")

    creator_role = get_logged_in_role_obj(request)
    if not creator_role:
        messages.error(request, "User role not found.")
        return redirect("dashboard")

    student_data = build_student_dashboard_data(student) if student else None
    faculty_data = build_faculty_dashboard_data(faculty) if faculty else None

    admission_mode = student_data.get("admission_mode") if student_data else None
    is_hosteller_flag = is_hosteller(admission_mode) if student_data else False

    if student:
        network_queries = NetworkQuery.objects.filter(student=student).order_by("-submitted_at")
    else:
        network_queries = NetworkQuery.objects.filter(faculty=faculty).order_by("-submitted_at")

    context = {
        "student": student_data,
        "faculty": faculty_data,
        "admission_mode": admission_mode,
        "is_hosteller": is_hosteller_flag,
        "is_student_user": bool(student_data),
        "is_faculty_user": bool(faculty_data),
        "network_queries": network_queries,
        "errors": {},
        "form_data": {},
    }

    if request.method == "POST":
        query_type = request.POST.get("query_type", "").strip()
        priority = request.POST.get("priority", NetworkQuery.Priority.MEDIUM).strip()
        subject = request.POST.get("subject", "").strip()
        description = request.POST.get("description", "").strip()
        connection_type = request.POST.get("connection_type", NetworkQuery.ConnectionType.WIFI).strip()
        location_details = request.POST.get("location_details", "Not specified").strip()
        device_type = request.POST.get("device_type", "mobile").strip()

        errors = {}

        if not query_type:
            errors["query_type"] = "Please select a query type."

        if not subject:
            errors["subject"] = "Subject is required."

        if not description:
            errors["description"] = "Please describe your issue."

        valid_student_types = {
            NetworkQuery.QueryType.HOSTEL_WIFI_SLOW,
            NetworkQuery.QueryType.HOSTEL_WIFI_DISCONNECTION,
            NetworkQuery.QueryType.HOSTEL_WIFI_NO_ACCESS,
            NetworkQuery.QueryType.HOSTEL_ETHERNET_NOT_WORKING,
            NetworkQuery.QueryType.HOSTEL_ETHERNET_SLOW,
            NetworkQuery.QueryType.HOSTEL_OTHERS,
            NetworkQuery.QueryType.DAYSCHOLAR_CAMPUS_WIFI_SLOW,
            NetworkQuery.QueryType.DAYSCHOLAR_CAMPUS_WIFI_DISCONNECTION,
            NetworkQuery.QueryType.DAYSCHOLAR_CAMPUS_WIFI_NO_ACCESS,
            NetworkQuery.QueryType.DAYSCHOLAR_LAB_NETWORK_ISSUES,
            NetworkQuery.QueryType.DAYSCHOLAR_LIBRARY_WIFI_ISSUES,
            NetworkQuery.QueryType.DAYSCHOLAR_OTHERS,
        }

        valid_faculty_types = {
            NetworkQuery.QueryType.FACULTY_WIFI_SLOW,
            NetworkQuery.QueryType.FACULTY_WIFI_DISCONNECTION,
            NetworkQuery.QueryType.FACULTY_WIFI_NO_ACCESS,
            NetworkQuery.QueryType.FACULTY_LAN_ISSUE,
            NetworkQuery.QueryType.FACULTY_LAB_NETWORK_ISSUE,
            NetworkQuery.QueryType.FACULTY_OTHERS,
        }

        if student and query_type not in valid_student_types:
            errors["query_type"] = "Invalid student query type selected."

        if faculty and query_type not in valid_faculty_types:
            errors["query_type"] = "Invalid faculty query type selected."

        valid_connection_types = {choice[0] for choice in NetworkQuery.ConnectionType.choices}
        if connection_type not in valid_connection_types:
            connection_type = NetworkQuery.ConnectionType.WIFI

        valid_priorities = {choice[0] for choice in NetworkQuery.Priority.choices}
        if priority not in valid_priorities:
            priority = NetworkQuery.Priority.MEDIUM

        if not errors:
            try:
                with transaction.atomic():
                    NetworkQuery.objects.create(
                        creator_role_id=creator_role.id,
                        student=student if student else None,
                        faculty=faculty if faculty else None,
                        user_type=(
                            NetworkQuery.UserType.STUDENT
                            if student
                            else NetworkQuery.UserType.FACULTY
                        ),
                        student_type=(
                            NetworkQuery.StudentType.HOSTEL
                            if student and is_hosteller_flag
                            else NetworkQuery.StudentType.DAYSCHOLAR
                            if student
                            else None
                        ),
                        query_type=query_type,
                        priority=priority,
                        subject=subject,
                        description=description,
                        connection_type=connection_type,
                        location_details=location_details or "Not specified",
                        device_type=device_type or "mobile",
                        status=NetworkQuery.Status.PENDING,
                    )

                messages.success(request, "Network query submitted successfully.")
                return redirect("query_application")

            except Exception as e:
                messages.error(request, f"Error: {str(e)}")

        context["errors"] = errors
        context["form_data"] = request.POST
    return render(
        request,
        "data_center_management/wifi/query_application.html",
        context,
    )
 




import logging

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from user_accounts.models import USER, Role, GlobalUsers
from faculty_management.models import general_information
from data_center_management.models import (
    DataCenterRequest,
    DataCenterRequestApprovers,
    DataCenterRequestApproversData,
)
from data_center_management.decorators import data_center_management
from user_accounts.decorators import check_permission

logger = logging.getLogger(__name__)

APPROVAL_DB = "rit_approval_system"


# =========================================================
# HELPERS
# =========================================================

def _normalize_emp_id(value):
    if value is None:
        return ""
    return str(value).strip()


def get_logged_in_external_user(request):
    """
    Resolve the EXACT external USER account (rit_approval_system) for the
    logged-in person.

    A single faculty may hold MULTIPLE accounts that share an Employee_id but
    carry different roles (the "switch account" feature re-logs the person in
    as a specific USER via its unique_id). Employee_id is NOT unique, so match
    the precise account first by unique_id, then by the unique email, and only
    fall back to the non-unique Employee_id.
    """
    user = getattr(request, "user", None)
    qs = USER.objects.using(APPROVAL_DB).all()

    unique_id = getattr(user, "unique_id", None)
    if unique_id:
        found = qs.filter(unique_id=unique_id).first()
        if found:
            return found

    email = getattr(user, "email", None)
    if email:
        found = qs.filter(email__iexact=email).first()
        if found:
            return found

    emp_id = getattr(user, "Employee_id", None)
    if emp_id:
        found = qs.filter(Employee_id=emp_id).first()
        if found:
            return found

    return None


def get_logged_in_faculty(request):
    """
    general_information is local DB.
    """
    emp_id = getattr(request.user, "Employee_id", None)
    email = getattr(request.user, "email", None)

    qs = general_information.objects.select_related("department", "designation")

    if emp_id:
        faculty = qs.filter(faculty_id=emp_id).first()
        if faculty:
            return faculty

    if email:
        faculty = qs.filter(college_email__iexact=email).first()
        if faculty:
            return faculty

    return None


def get_logged_in_role(request):
    ext_user = get_logged_in_external_user(request)
    if not ext_user or not ext_user.role_id:
        return None

    return Role.objects.using(APPROVAL_DB).filter(id=ext_user.role_id).first()


def is_global_user(faculty, role_id=None):
    if not faculty:
        return False

    faculty_emp_id = _normalize_emp_id(getattr(faculty, "faculty_id", None))
    role_id = str(role_id or "").strip()
    if not faculty_emp_id or not role_id:
        return False

    return GlobalUsers.objects.filter(
        employee_id=faculty_emp_id,
        role_id=role_id,
        global_user=True
    ).exists()


def get_role_name(role_id):
    if not role_id:
        return ""
    role_obj = Role.objects.using(APPROVAL_DB).filter(id=role_id).values("role").first()
    return (role_obj or {}).get("role", "").strip()


def is_faculty_role(role_id):
    return get_role_name(role_id).lower() == "faculty"


def get_current_pending_entry(dc_request):
    if not dc_request:
        return None

    return (
        dc_request.approval_entries
        .filter(status=DataCenterRequestApproversData.Status.PENDING)
        .order_by("approver_level", "id")
        .first()
    )


def is_current_approval_level(dc_request, entry_level):
    current = get_current_pending_entry(dc_request)
    return bool(current and current.approver_level == entry_level)


def get_request_creator_department(dc_request):
    if not dc_request:
        return None

    if getattr(dc_request, "student_id", None) and getattr(dc_request.student, "department_id", None):
        return dc_request.student.department

    if getattr(dc_request, "faculty_id", None) and getattr(dc_request.faculty, "department_id", None):
        return dc_request.faculty.department

    return None


def get_student_ca(dc_request):
    if not dc_request:
        return None

    if getattr(dc_request, "student_id", None) and getattr(dc_request.student, "ca_id", None):
        return dc_request.student.ca

    return None


def get_route_for_entry(entry):
    """
    Route row for this runtime approval entry.
    """
    if not entry or not entry.request_id:
        return None

    return (
        DataCenterRequestApprovers.objects
        .select_related("approver_department")
        .filter(
            creator_role_id=entry.creator_role_id,
            approver_role_id=entry.approver_role_id,
            approver_level=entry.approver_level,
        )
        .first()
    )


def get_logged_in_account_department_id(request):
    """
    Local Add_Department id of the CURRENTLY ACTIVE (switched) account.

    The same person can hold a role under several profiles, each tied to a
    different department in the external USER table (e.g. one "Data Center
    Incharge" profile in OFFICE and another in DATA CENTRE). The department that
    counts for approval is the one on the switched-in account — not the single
    home department stored on general_information. We read the active account's
    external Department and bridge it to the local Add_Department by code.
    """
    ext_user = get_logged_in_external_user(request)
    if not ext_user or not getattr(ext_user, "Department_id", None):
        return None

    ext_dept = (
        Department.objects.using(APPROVAL_DB)
        .filter(id=ext_user.Department_id)
        .values("Department", "Department_code")
        .first()
    )
    if not ext_dept:
        return None

    code = (ext_dept.get("Department_code") or "").strip()
    name = (ext_dept.get("Department") or "").strip()

    # Bridge external -> local. Department_code is the intended key, but the two
    # databases are not always consistent (e.g. AI&DS is "AD" externally but
    # "243" locally), so fall back to a case-insensitive name match.
    if code:
        local_id = (
            Add_Department.objects
            .filter(Department_code__iexact=code)
            .values_list("id", flat=True)
            .first()
        )
        if local_id:
            return local_id

    if name:
        local_id = (
            Add_Department.objects
            .filter(Department__iexact=name)
            .values_list("id", flat=True)
            .first()
        )
        if local_id:
            return local_id

    return None


def can_faculty_approve_entry(entry, faculty, logged_in_role, logged_in_dept_id=None):
    """
    Final rules (same for student and faculty creators):
    1. row must be pending
    2. only current pending level can act
    3. logged-in role must match approver_role_id
    4. department is evaluated against the ACTIVE (switched) account's
       department (logged_in_dept_id), not the person's home department
    5. global user bypasses the department restriction

    `logged_in_dept_id` is the local Add_Department id of the switched-in
    account (see get_logged_in_account_department_id). Falls back to the
    person's general_information department if not supplied.
    """
    if not entry or not faculty or not entry.request:
        return False

    if entry.status != DataCenterRequestApproversData.Status.PENDING:
        return False

    if not is_current_approval_level(entry.request, entry.approver_level):
        return False

    route = get_route_for_entry(entry)
    is_cross_department = bool(
        route and str(route.is_cross_department_approver or "").upper() == "YES"
    )

    role_matches = bool(
        logged_in_role
        and getattr(logged_in_role, "id", None)
        and str(logged_in_role.id) == str(entry.approver_role_id)
    )

    # Department of the ACTIVE profile (switched account) — the department that
    # actually counts for approval. Fall back to the home department only if the
    # account department could not be resolved.
    approver_dept_id = (
        logged_in_dept_id
        if logged_in_dept_id is not None
        else getattr(faculty, "department_id", None)
    )

    # --------------------------------------------------
    # CROSS-DEPARTMENT ROUTE
    # An application from ANY creator department reaches this role (no creator
    # department filter). WHERE the approver sits is driven by the hierarchy
    # configuration (never hardcoded):
    #   - a target department was chosen (e.g. Data Center) -> the active
    #     account must belong to THAT department;
    #   - no department chosen -> any faculty holding this role may approve.
    # Not pinned to a single person, so every matching profile can act.
    # --------------------------------------------------
    if is_cross_department:
        if not role_matches:
            return False
        if is_global_user(faculty, getattr(logged_in_role, "id", None)):
            return True
        if route and route.approver_department_id:
            return approver_dept_id == route.approver_department_id
        return True

    # --------------------------------------------------
    # GLOBAL USER of the matching role
    # A global approver sees EVERY step for their role, regardless of the
    # department and regardless of any pre-assigned/pinned approver.
    # --------------------------------------------------
    if role_matches and is_global_user(faculty, getattr(logged_in_role, "id", None)):
        return True

    # --------------------------------------------------
    # ASSIGNED APPROVER (same-department resolved person)
    # --------------------------------------------------
    if entry.approver_id:
        return entry.approver_id == faculty.id

    # --------------------------------------------------
    # ROLE MUST MATCH
    # --------------------------------------------------
    if not role_matches:
        return False

    # --------------------------------------------------
    # SAME-DEPARTMENT RULE
    # --------------------------------------------------
    if not route:
        return True

    creator_department = get_request_creator_department(entry.request)
    if creator_department:
        return approver_dept_id == creator_department.id

    return True




def build_wifi_approval_flow(dc_request):
    """
    Ordered approval chain for a WiFi request, resolved from the runtime
    approval rows (which were snapshotted from the DC approval hierarchy for
    the creator's role). Each step carries its role name, status, who acted,
    and whether it is the current pending step — for the flow/stepper UI.
    """
    if not dc_request:
        return []

    entries = list(
        dc_request.approval_entries
        .select_related("approver")
        .order_by("approver_level", "id")
    )

    # first still-pending step is the "current" one
    current_id = None
    for e in entries:
        if e.status == DataCenterRequestApproversData.Status.PENDING:
            current_id = e.id
            break

    steps = []
    for e in entries:
        steps.append({
            "level": e.approver_level,
            "role_name": get_role_name(e.approver_role_id) or f"Role#{e.approver_role_id}",
            "status": e.status,
            "approver_name": getattr(e.approver, "name", "") if e.approver_id else "",
            "acted_on": e.acted_on,
            "reason": e.reason,
            "is_current": (e.id == current_id),
        })
    return steps


@data_center_management
@check_permission("wifi_application_approval")
def wifi_application_approval(request):
    logged_in_faculty = get_logged_in_faculty(request)
    logged_in_role = get_logged_in_role(request)
    logged_in_dept_id = get_logged_in_account_department_id(request)

    if not logged_in_faculty:
        messages.error(request, "Approver faculty record not found.")
        return redirect("dashboard")

    if request.method == "POST":
        entry_id = request.POST.get("entry_id")
        action = (request.POST.get("action") or "").strip().lower()
        remarks = (request.POST.get("remarks") or "").strip()

        if not entry_id:
            messages.error(request, "Approval entry ID is required.")
            return redirect("wifi_application_approval")

        if action not in ["approve", "reject"]:
            messages.error(request, "Invalid action.")
            return redirect("wifi_application_approval")

        try:
            with transaction.atomic():
                entry = get_object_or_404(
                    DataCenterRequestApproversData.objects
                    .select_for_update()
                    .select_related(
                        "request",
                        "request__student",
                        "request__student__department",
                        "request__student__ca",
                        "request__faculty",
                        "request__faculty__department",
                        "approver",
                        "creator",
                    ),
                    id=entry_id,
                )

                dc_request = entry.request

                if dc_request.status in ["APPROVED", "REJECTED"]:
                    messages.error(request, "This request is already closed.")
                    return redirect("wifi_application_approval")

                if entry.status != DataCenterRequestApproversData.Status.PENDING:
                    messages.error(request, "This approval step is already processed.")
                    return redirect("wifi_application_approval")

                if not can_faculty_approve_entry(entry, logged_in_faculty, logged_in_role, logged_in_dept_id):
                    messages.error(request, "You are not authorized to approve this step.")
                    return redirect("wifi_application_approval")

                entry.approver = logged_in_faculty
                entry.acted_on = timezone.now()

                if action == "approve":
                    entry.status = DataCenterRequestApproversData.Status.APPROVED
                    entry.reason = remarks or f"Approved by {logged_in_faculty.name}"
                    entry.save(update_fields=["approver", "acted_on", "status", "reason"])

                    has_pending = dc_request.approval_entries.filter(
                        status=DataCenterRequestApproversData.Status.PENDING
                    ).exists()

                    dc_request.status = "PENDING" if has_pending else "APPROVED"
                    dc_request.save(update_fields=["status"])

                    messages.success(request, f"Request #{dc_request.id} approved successfully.")

                else:
                    if not remarks:
                        messages.error(request, "Rejection reason is required.")
                        return redirect("wifi_application_approval")

                    entry.status = DataCenterRequestApproversData.Status.REJECTED
                    entry.reason = remarks
                    entry.save(update_fields=["approver", "acted_on", "status", "reason"])

                    dc_request.approval_entries.filter(
                        status=DataCenterRequestApproversData.Status.PENDING
                    ).exclude(id=entry.id).update(
                        status=DataCenterRequestApproversData.Status.REJECTED,
                        reason=f"Auto rejected after rejection at level {entry.approver_level}",
                        acted_on=timezone.now(),
                    )

                    dc_request.status = "REJECTED"
                    dc_request.save(update_fields=["status"])

                    messages.success(request, f"Request #{dc_request.id} rejected successfully.")

        except Exception as e:
            logger.exception("wifi_application_approval failed")
            messages.error(request, f"Approval failed: {str(e)}")

        return redirect("wifi_application_approval")

    pending_entries = (
        DataCenterRequestApproversData.objects
        .select_related(
            "request",
            "request__student",
            "request__student__department",
            "request__student__ca",
            "request__faculty",
            "request__faculty__department",
            "approver",
            "creator",
        )
        .filter(
            status=DataCenterRequestApproversData.Status.PENDING,
            request__status="PENDING",
        )
        .order_by("request_id", "approver_level", "id")
    )

    actionable_entries = []
    for entry in pending_entries:
        if can_faculty_approve_entry(entry, logged_in_faculty, logged_in_role, logged_in_dept_id):
            entry.request.flow_steps = build_wifi_approval_flow(entry.request)
            entry.request.creator_role_name = get_role_name(entry.request.creator_role_id)
            actionable_entries.append(entry)

    my_actions = list(
        DataCenterRequestApproversData.objects
        .select_related(
            "request",
            "request__student",
            "request__faculty",
            "approver",
            "creator",
        )
        .filter(approver=logged_in_faculty)
        .exclude(status=DataCenterRequestApproversData.Status.PENDING)
        .order_by("-acted_on", "-id")[:20]
    )
    for item in my_actions:
        item.request.flow_steps = build_wifi_approval_flow(item.request)
        item.request.creator_role_name = get_role_name(item.request.creator_role_id)

    # Department of the ACTIVE (switched) profile — show this on the header card,
    # not the person's single home department.
    logged_in_department = None
    if logged_in_dept_id is not None:
        logged_in_department = (
            Add_Department.objects
            .filter(id=logged_in_dept_id)
            .values_list("Department", flat=True)
            .first()
        )
    if not logged_in_department:
        logged_in_department = getattr(
            getattr(logged_in_faculty, "department", None), "Department", None
        )

    return render(
        request,
        "data_center_management/wifi/wifi_application_approval.html",
        {
            "actionable_entries": actionable_entries,
            "my_actions": my_actions,
            "logged_in_faculty": logged_in_faculty,
            "logged_in_role": get_role_name(getattr(logged_in_role, "id", None)),
            "logged_in_department": logged_in_department,
            "is_global_user": is_global_user(
                logged_in_faculty,
                getattr(logged_in_role, "id", None),
            ),
        },
    )
 


from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect
from django.utils import timezone

from faculty_management.models import general_information
from data_center_management.models import NetworkQuery



@login_required
def queries_approval(request):
    user_email = (getattr(request.user, "email", "") or "").strip()

    logged_in_faculty = (
        general_information.objects
        .select_related("department", "designation")
        .filter(college_email__iexact=user_email)
        .first()
    )

    if not logged_in_faculty:
        messages.error(request, "Only faculty approvers can access this page.")
        return redirect("dashboard")

    logged_in_role = getattr(getattr(request.user, "role", None), "name", None) or "Approver"

    if request.method == "POST":
        query_id = request.POST.get("query_id")
        action = request.POST.get("action")
        remarks = request.POST.get("remarks", "").strip()

        query_obj = get_object_or_404(NetworkQuery, id=query_id)

        if query_obj.status != NetworkQuery.Status.PENDING:
            messages.warning(request, "Only pending queries can be processed from this page.")
            return redirect("queries_approval")

        if action == "process":
            query_obj.status = NetworkQuery.Status.IN_PROGRESS
            query_obj.assigned_approver = logged_in_faculty
            query_obj.approver_remarks = remarks
            query_obj.approved_at = timezone.now()
            query_obj.save()

            messages.success(request, f"{query_obj.query_id} moved to processing.")

        elif action == "reject":
            query_obj.status = NetworkQuery.Status.REJECTED
            query_obj.assigned_approver = logged_in_faculty
            query_obj.approver_remarks = remarks
            query_obj.rejection_reason = remarks
            query_obj.rejected_at = timezone.now()
            query_obj.save()

            messages.error(request, f"{query_obj.query_id} rejected.")
        else:
            messages.warning(request, "Invalid action.")

        return redirect("queries_approval")

    pending_queries = (
        NetworkQuery.objects
        .select_related("student", "faculty", "assigned_approver")
        .filter(status=NetworkQuery.Status.PENDING)
        .order_by("submitted_at")
    )

    processed_queries = (
        NetworkQuery.objects
        .select_related("student", "faculty", "assigned_approver")
        .filter(assigned_approver=logged_in_faculty)
        .exclude(status=NetworkQuery.Status.PENDING)
        .order_by("-updated_at")[:20]
    )

    context = {
        "logged_in_faculty": logged_in_faculty,
        "logged_in_role": logged_in_role,
        "pending_queries": pending_queries,
        "processed_queries": processed_queries,
    }
    return render(request, "data_center_management/wifi/queries_approval.html", context)
     
 


@login_required
def queries_resolve(request):
    user_email = (getattr(request.user, "email", "") or "").strip()

    logged_in_faculty = (
        general_information.objects
        .select_related("department", "designation")
        .filter(college_email__iexact=user_email)
        .first()
    )

    if not logged_in_faculty:
        messages.error(request, "Only faculty/incharge can access this page.")
        return redirect("dashboard")

    if request.method == "POST":
        query_id = request.POST.get("query_id")
        action = request.POST.get("action")
        solution_notes = request.POST.get("solution_notes", "").strip()

        query_obj = get_object_or_404(NetworkQuery, id=query_id)

        if query_obj.status != NetworkQuery.Status.IN_PROGRESS:
            messages.warning(request, "Only in-progress queries can be completed from this page.")
            return redirect("queries_resolve")

        if action == "resolve":
            query_obj.status = NetworkQuery.Status.RESOLVED
            query_obj.solved_by = logged_in_faculty
            query_obj.solved_at = timezone.now()
            query_obj.solution_notes = solution_notes
            query_obj.save()

            messages.success(request, f"{query_obj.query_id} marked as resolved.")

        elif action == "close":
            query_obj.status = NetworkQuery.Status.CLOSED
            query_obj.closed_by = logged_in_faculty
            query_obj.closed_at = timezone.now()
            query_obj.closing_notes = solution_notes
            query_obj.save()

            messages.success(request, f"{query_obj.query_id} closed successfully.")
        else:
            messages.warning(request, "Invalid action.")

        return redirect("queries_resolve")

    active_queries = (
        NetworkQuery.objects
        .select_related("student", "faculty", "assigned_approver")
        .filter(status=NetworkQuery.Status.IN_PROGRESS)
        .order_by("updated_at")
    )

    completed_queries = (
        NetworkQuery.objects
        .select_related("student", "faculty", "assigned_approver", "solved_by", "closed_by")
        .filter(status__in=[NetworkQuery.Status.RESOLVED, NetworkQuery.Status.CLOSED])
        .order_by("-updated_at")[:30]
    )

    # Full register: every network query (all statuses) so the incharge always
    # has a complete, searchable record even when nothing is in-progress.
    all_queries = (
        NetworkQuery.objects
        .select_related(
            "student", "student__department",
            "faculty", "faculty__department",
            "assigned_approver", "solved_by", "closed_by",
        )
        .order_by("-submitted_at")
    )

    context = {
        "active_queries": active_queries,
        "completed_queries": completed_queries,
        "all_queries": all_queries,
    }
    return render(request, "data_center_management/wifi/queries_resolve.html", context)
 
    
    
from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from data_center_management.decorators import data_center_management
from user_accounts.decorators import check_permission
from data_center_management.models import DataCenterRequest, WifiCredential


@data_center_management
@check_permission("wifi_application_approval")
def wifi_approved_credentials(request):
    if request.method == "POST":
        request_id = request.POST.get("request_id")
        wifi_user_id = (request.POST.get("wifi_user_id") or "").strip()
        wifi_password = (request.POST.get("wifi_password") or "").strip()
        action = (request.POST.get("action") or "").strip()

        dc_request = get_object_or_404(
            DataCenterRequest.objects.select_related(
                "student",
                "student__department",
                "faculty",
                "faculty__department",
            ),
            id=request_id,
            status="APPROVED",
        )

        if not wifi_user_id or not wifi_password:
            messages.error(request, "WiFi ID and password are required.")
            return redirect("wifi_approved_credentials")

        credential, created = WifiCredential.objects.update_or_create(
            request=dc_request,
            defaults={
                "wifi_user_id": wifi_user_id,
                "wifi_password": wifi_password,
                "created_by_name": getattr(request.user, "username", "") or getattr(request.user, "email", ""),
            }
        )

        if action == "save_and_send":
            recipient_email = None
            recipient_name = "User"

            if dc_request.student:
                recipient_email = dc_request.student.email
                recipient_name = dc_request.student.name
            elif dc_request.faculty:
                recipient_email = dc_request.faculty.college_email or dc_request.faculty.personal_email
                recipient_name = dc_request.faculty.name

            if not recipient_email:
                messages.error(request, f"Email not found for Request #{dc_request.id}.")
                return redirect("wifi_approved_credentials")

            subject = "WiFi Request Approved - Credentials"
            message = f"""
Dear {recipient_name},

Your WiFi request has been approved.

WiFi User ID: {wifi_user_id}
WiFi Password: {wifi_password}

Request ID: {dc_request.id}

Please keep these credentials secure.

Regards,
Data Center Management
            """.strip()

            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    recipient_list=[recipient_email],
                    fail_silently=False,
                )

                credential.sent_to_user = True
                credential.sent_at = timezone.now()
                credential.save(update_fields=["sent_to_user", "sent_at", "updated_at"])

                messages.success(
                    request,
                    f"Credentials sent successfully to {recipient_email}."
                )
            except Exception as e:
                messages.error(request, f"Saved, but email sending failed: {str(e)}")
        else:
            messages.success(request, "Credentials saved successfully.")

        return redirect("wifi_approved_credentials")

    unsent_approved_requests = (
        DataCenterRequest.objects.select_related(
            "student",
            "student__department",
            "faculty",
            "faculty__department",
        )
        .filter(status="APPROVED")
        .filter(
            Q(wifi_credential__isnull=True) |
            Q(wifi_credential__sent_to_user=False)
        )
        .order_by("-created_at")
    )

    student_requests = unsent_approved_requests.filter(student__isnull=False)
    faculty_requests = unsent_approved_requests.filter(faculty__isnull=False)

    context = {
        "student_requests": student_requests,
        "faculty_requests": faculty_requests,
    }
    return render(
        request,
        "data_center_management/wifi/wifi_approved_credentials.html",
        context
    )
 
 
    
from django.contrib import messages
from django.shortcuts import redirect, render

from data_center_management.decorators import data_center_management
from user_accounts.decorators import check_permission
from student_management.models import StudentDetails
from faculty_management.models import general_information
from data_center_management.models import DataCenterRequest


from django.contrib import messages
from django.shortcuts import redirect, render

from data_center_management.decorators import data_center_management
from user_accounts.decorators import check_permission
from student_management.models import StudentDetails
from faculty_management.models import general_information
from data_center_management.models import DataCenterRequest


@check_permission("user_wifi_credentials")
def user_wifi_credentials(request):
    user = request.user
    user_email = (getattr(user, "email", "") or "").strip()

    student = StudentDetails.objects.filter(
        email__iexact=user_email
    ).select_related("department").first()

    faculty = None
    if not student:
        faculty = general_information.objects.filter(
            college_email__iexact=user_email
        ).select_related("department").first()

    if not student and not faculty:
        messages.error(request, "Unable to identify user.")
        return redirect("dashboard")

    filters = {
        "status": "APPROVED",
        "wifi_credential__isnull": False,
        "wifi_credential__sent_to_user": True,
    }

    if student:
        filters["student"] = student
    else:
        filters["faculty"] = faculty

    credential_requests = (
        DataCenterRequest.objects.select_related(
            "student",
            "student__department",
            "faculty",
            "faculty__department",
        )
        .filter(**filters)
        .order_by("-created_at")
    )

    context = {
        "credential_requests": credential_requests,
        "student": student,
        "faculty": faculty,
    }
    return render(
        request,
        "data_center_management/wifi/user_wifi_credentials.html",
        context
    )
    






import logging

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from user_accounts.models import USER, Role, Add_Department, Department, GlobalUsers
from faculty_management.models import general_information
from data_center_management.decorators import data_center_management
from user_accounts.decorators import check_permission

from data_center_management.models import (
    DataCenterRequestApprovers,
    GuestWifiRequest,
    GuestWifiRequestApproversData,
)

logger = logging.getLogger(__name__)

APPROVAL_DB = "rit_approval_system"


# =========================================================
# HELPERS
# =========================================================

def _normalize_emp_id(value):
    if value is None:
        return ""
    return str(value).strip()


def get_logged_in_external_user(request):
    """
    Resolve the EXACT external USER account (rit_approval_system) for the
    logged-in person.

    A single faculty may hold MULTIPLE accounts that share an Employee_id but
    carry different roles (the "switch account" feature re-logs the person in
    as a specific USER via its unique_id). Employee_id is NOT unique, so match
    the precise account first by unique_id, then by the unique email, and only
    fall back to the non-unique Employee_id.
    """
    user = getattr(request, "user", None)
    qs = USER.objects.using(APPROVAL_DB).all()

    unique_id = getattr(user, "unique_id", None)
    if unique_id:
        found = qs.filter(unique_id=unique_id).first()
        if found:
            return found

    email = getattr(user, "email", None)
    if email:
        found = qs.filter(email__iexact=email).first()
        if found:
            return found

    emp_id = getattr(user, "Employee_id", None)
    if emp_id:
        found = qs.filter(Employee_id=emp_id).first()
        if found:
            return found

    return None


def get_logged_in_faculty(request):
    """
    general_information is local DB.
    """
    emp_id = getattr(request.user, "Employee_id", None)
    email = getattr(request.user, "email", None)

    qs = general_information.objects.select_related("department", "designation")

    if emp_id:
        faculty = qs.filter(faculty_id=emp_id).first()
        if faculty:
            return faculty

    if email:
        faculty = qs.filter(college_email__iexact=email).first()
        if faculty:
            return faculty

    return None


def get_logged_in_role(request):
    ext_user = get_logged_in_external_user(request)
    if not ext_user or not ext_user.role_id:
        return None

    return Role.objects.using(APPROVAL_DB).filter(id=ext_user.role_id).first()


def get_logged_in_role_obj(request):
    user = request.user

    cr_user = (
        USER.objects.using(APPROVAL_DB)
        .filter(email=user.email)
        .select_related("role")
        .first()
    )

    if not cr_user:
        return None

    return cr_user.role


def build_faculty_dashboard_data(faculty):
    if not faculty:
        return None

    return {
        "id": faculty.id,
        "faculty_id": getattr(faculty, "faculty_id", ""),
        "name": getattr(faculty, "name", ""),
        "college_email": getattr(faculty, "college_email", ""),
        "personal_email": getattr(faculty, "personal_email", ""),
        "phone": getattr(faculty, "phone", ""),
        "department": faculty.department.Department if getattr(faculty, "department", None) else "",
        "designation": str(faculty.designation) if getattr(faculty, "designation", None) else "",
    }


def get_role_name(role_id):
    if not role_id:
        return ""
    role_obj = Role.objects.using(APPROVAL_DB).filter(id=role_id).values("role").first()
    return (role_obj or {}).get("role", "").strip()


def is_global_user(faculty, role_id=None):
    if not faculty:
        return False

    faculty_emp_id = _normalize_emp_id(getattr(faculty, "faculty_id", None))
    role_id = str(role_id or "").strip()
    if not faculty_emp_id or not role_id:
        return False

    return GlobalUsers.objects.filter(
        employee_id=faculty_emp_id,
        role_id=role_id,
        global_user=True
    ).exists()


def get_guest_request_creator_department(guest_request):
    if not guest_request:
        return None

    if getattr(guest_request, "faculty_id", None) and getattr(guest_request.faculty, "department_id", None):
        return guest_request.faculty.department

    return None


def resolve_guest_wifi_approver_faculty(guest_request, route):
    if not route or not route.approver_role_id:
        return None

    approver_filter = {"role_id": route.approver_role_id}

    if str(route.is_cross_department_approver or "").upper() == "YES":
        if route.approver_department_id:
            local_dept = Add_Department.objects.filter(id=route.approver_department_id).first()
            dept_code = getattr(local_dept, "Department_code", None)

            if dept_code:
                ext_dept_id = (
                    Department.objects.using(APPROVAL_DB)
                    .filter(Department_code=dept_code)
                    .values_list("id", flat=True)
                    .first()
                )
                if ext_dept_id:
                    approver_filter["Department_id"] = ext_dept_id
    else:
        creator_department = get_guest_request_creator_department(guest_request)
        if creator_department:
            dept_code = getattr(creator_department, "Department_code", None)

            if dept_code:
                ext_dept_id = (
                    Department.objects.using(APPROVAL_DB)
                    .filter(Department_code=dept_code)
                    .values_list("id", flat=True)
                    .first()
                )
                if ext_dept_id:
                    approver_filter["Department_id"] = ext_dept_id

    approver_user = USER.objects.using(APPROVAL_DB).filter(**approver_filter).first()
    if not approver_user:
        return None

    approver_faculty = (
        general_information.objects
        .select_related("department", "designation")
        .filter(faculty_id=approver_user.Employee_id)
        .first()
    )

    return approver_faculty


def create_guest_wifi_approver_chain(guest_request, creator_role_id, creator_faculty):
    """
    Creates runtime rows in GuestWifiRequestApproversData.
    """
    if not guest_request or not creator_role_id:
        return 0

    existing_count = GuestWifiRequestApproversData.objects.filter(request=guest_request).count()
    if existing_count > 0:
        return existing_count

    routes = (
        DataCenterRequestApprovers.objects
        .select_related("approver_department")
        .filter(creator_role_id=creator_role_id)
        .order_by("approver_level", "id")
    )

    if not routes.exists():
        return 0

    created_rows = 0
    created_levels = set()

    for route in routes:
        level = route.approver_level

        if level in created_levels:
            continue

        approver_faculty = resolve_guest_wifi_approver_faculty(guest_request, route)

        # skip invalid mapping
        if not approver_faculty:
            continue

        GuestWifiRequestApproversData.objects.create(
            request=guest_request,
            approver=approver_faculty,
            creator=creator_faculty,
            approver_role_id=route.approver_role_id,
            creator_role_id=creator_role_id,
            approver_level=level,
            status=GuestWifiRequestApproversData.Status.PENDING,
            reason=None,
            acted_on=timezone.now(),
        )

        created_rows += 1
        created_levels.add(level)

    return created_rows


def get_current_pending_guest_entry(guest_request):
    if not guest_request:
        return None

    return (
        guest_request.approval_entries
        .filter(status=GuestWifiRequestApproversData.Status.PENDING)
        .order_by("approver_level", "id")
        .first()
    )


def is_current_guest_approval_level(guest_request, entry_level):
    current = get_current_pending_guest_entry(guest_request)
    return bool(current and current.approver_level == entry_level)


def get_guest_route_for_entry(entry):
    if not entry or not entry.request_id:
        return None

    return (
        DataCenterRequestApprovers.objects
        .select_related("approver_department")
        .filter(
            creator_role_id=entry.creator_role_id,
            approver_role_id=entry.approver_role_id,
            approver_level=entry.approver_level,
        )
        .first()
    )


def can_faculty_approve_guest_entry(entry, faculty, logged_in_role, logged_in_dept_id=None):
    """
    Rules:
    1. row must be pending
    2. only current pending level can act
    3. if specific approver assigned, only that person can act
    4. otherwise role must match
    5. global user bypasses department restriction only
    6. normal users must satisfy same/cross department rule
    """
    if not entry or not faculty or not entry.request:
        return False

    if entry.status != GuestWifiRequestApproversData.Status.PENDING:
        return False

    if not is_current_guest_approval_level(entry.request, entry.approver_level):
        return False

    route = get_guest_route_for_entry(entry)
    is_cross_department = bool(
        route and str(route.is_cross_department_approver or "").upper() == "YES"
    )

    role_matches = bool(
        logged_in_role
        and getattr(logged_in_role, "id", None)
        and str(logged_in_role.id) == str(entry.approver_role_id)
    )

    # Department of the ACTIVE (switched) profile — see can_faculty_approve_entry.
    approver_dept_id = (
        logged_in_dept_id
        if logged_in_dept_id is not None
        else getattr(faculty, "department_id", None)
    )

    # CROSS-DEPARTMENT: any creator department reaches this role. If a target
    # department was chosen in the hierarchy, the ACTIVE account must belong to
    # it; otherwise any faculty holding this role may approve. Not pinned.
    if is_cross_department:
        if not role_matches:
            return False
        if is_global_user(faculty, getattr(logged_in_role, "id", None)):
            return True
        if route and route.approver_department_id:
            return approver_dept_id == route.approver_department_id
        return True

    # Global approver of the matching role sees every step, bypassing the
    # department and any pinned approver.
    if role_matches and is_global_user(faculty, getattr(logged_in_role, "id", None)):
        return True

    # Same-department resolved person.
    if entry.approver_id:
        return entry.approver_id == faculty.id

    if not role_matches:
        return False

    if not route:
        return True

    creator_department = get_guest_request_creator_department(entry.request)
    if creator_department:
        return approver_dept_id == creator_department.id

    return True


def attach_role_names_to_guest_request(guest_request):
    """
    Attach dynamic role names for template usage without DB relation.
    """
    if not guest_request:
        return guest_request

    flows = guest_request.approval_entries.all().order_by("approver_level", "id")
    for flow in flows:
        flow.approver_role_name = get_role_name(flow.approver_role_id)
        flow.creator_role_name = get_role_name(flow.creator_role_id)

    return guest_request


def attach_role_names_to_entries(entries):
    for entry in entries:
        entry.approver_role_name = get_role_name(entry.approver_role_id)
        entry.creator_role_name = get_role_name(entry.creator_role_id)

        if getattr(entry, "request", None):
            attach_role_names_to_guest_request(entry.request)

    return entries


# =========================================================
# GUEST WIFI APPLICATION
# =========================================================

@data_center_management
@check_permission("guest_wifi_application")
def guest_wifi_application(request):
    user = request.user
    user_email = (getattr(user, "email", "") or "").strip()

    faculty = (
        general_information.objects
        .filter(college_email__iexact=user_email)
        .select_related("department", "designation")
        .first()
    )

    if not faculty:
        messages.error(request, "Only faculty/staff can raise guest WiFi requests.")
        return redirect("dashboard")

    creator_role = get_logged_in_role_obj(request)
    if not creator_role:
        messages.error(request, "User role not found.")
        return redirect("dashboard")

    faculty_data = build_faculty_dashboard_data(faculty)

    user_requests = (
        GuestWifiRequest.objects
        .filter(faculty=faculty)
        .prefetch_related("approval_entries", "approval_entries__approver")
        .order_by("-created_at")
    )

    user_requests = list(user_requests)
    for req in user_requests:
        attach_role_names_to_guest_request(req)

    context = {
        "faculty": faculty_data,
        "errors": {},
        "form_data": {},
        "user_requests": user_requests,
    }

    if request.method == "POST":
        guest_name = request.POST.get("guest_name", "").strip()
        guest_mobile_no = request.POST.get("guest_mobile_no", "").strip()
        guest_email = request.POST.get("guest_email", "").strip()
        guest_organization = request.POST.get("guest_organization", "").strip()

        purpose_of_visit = request.POST.get("purpose_of_visit", "").strip()
        reason = request.POST.get("reason", "").strip()

        visit_date_raw = request.POST.get("visit_date", "").strip()
        access_from_raw = request.POST.get("access_from", "").strip()
        access_to_raw = request.POST.get("access_to", "").strip()

        device_type = request.POST.get("device_type", "").strip()
        device_mac_address = request.POST.get("device_mac_address", "").strip()
        mobile_static_mac_address = request.POST.get("mobile_static_mac_address", "").strip()

        agreement = request.POST.get("agreement") == "on"

        errors = {}

        visit_date = parse_date(visit_date_raw) if visit_date_raw else None
        access_from = parse_datetime(access_from_raw) if access_from_raw else None
        access_to = parse_datetime(access_to_raw) if access_to_raw else None

        if not guest_name:
            errors["guest_name"] = "Guest name is required"

        if not guest_mobile_no:
            errors["guest_mobile_no"] = "Guest mobile number is required"

        if not purpose_of_visit:
            errors["purpose_of_visit"] = "Purpose of visit is required"

        if not reason:
            errors["reason"] = "Reason is required"

        if not visit_date_raw:
            errors["visit_date"] = "Visit date is required"
        elif not visit_date:
            errors["visit_date"] = "Invalid visit date"

        if not access_from_raw:
            errors["access_from"] = "Access from is required"
        elif not access_from:
            errors["access_from"] = "Invalid access from datetime"

        if not access_to_raw:
            errors["access_to"] = "Access to is required"
        elif not access_to:
            errors["access_to"] = "Invalid access to datetime"

        if access_from and access_to and access_to <= access_from:
            errors["access_to"] = "Access to must be greater than access from"

        if not device_type:
            errors["device_type"] = "Device type is required"

        if not device_mac_address:
            errors["device_mac_address"] = "Device MAC address is required"

        if not agreement:
            errors["agreement"] = "Please accept the declaration"

        if not errors:
            try:
                with transaction.atomic():
                    guest_request = GuestWifiRequest.objects.create(
                        creator_role_id=creator_role.id,
                        faculty=faculty,
                        guest_name=guest_name,
                        guest_mobile_no=guest_mobile_no,
                        guest_email=guest_email or None,
                        guest_organization=guest_organization or None,
                        purpose_of_visit=purpose_of_visit,
                        reason=reason,
                        visit_date=visit_date,
                        access_from=access_from,
                        access_to=access_to,
                        device_type=device_type,
                        device_mac_address=device_mac_address,
                        mobile_static_mac_address=mobile_static_mac_address or None,
                        agreement=agreement,
                        status="PENDING",
                    )

                    created_rows = create_guest_wifi_approver_chain(
                        guest_request=guest_request,
                        creator_role_id=creator_role.id,
                        creator_faculty=faculty,
                    )

                    if created_rows == 0:
                        guest_request.status = "APPROVED"
                        guest_request.save(update_fields=["status"])
                        messages.warning(
                            request,
                            "Request submitted, but no approval route matched. Request auto-approved."
                        )
                    else:
                        messages.success(request, "Guest WiFi request submitted successfully.")

                    return redirect("guest_wifi_application")

            except Exception as e:
                logger.exception("guest_wifi_application failed")
                messages.error(request, f"Error: {str(e)}")

        context["errors"] = errors
        context["form_data"] = request.POST

    return render(
        request,
        "data_center_management/wifi/guest_wifi_application.html",
        context,
    )
 



@data_center_management
@check_permission("guest_wifi_approval")
def guest_wifi_approval(request):
    logged_in_faculty = get_logged_in_faculty(request)
    logged_in_role = get_logged_in_role(request)
    logged_in_dept_id = get_logged_in_account_department_id(request)

    if not logged_in_faculty:
        messages.error(request, "Approver faculty record not found.")
        return redirect("dashboard")

    if request.method == "POST":
        entry_id = request.POST.get("entry_id")
        action = (request.POST.get("action") or "").strip().lower()
        remarks = (request.POST.get("remarks") or "").strip()

        if not entry_id:
            messages.error(request, "Approval entry ID is required.")
            return redirect("guest_wifi_approval")

        if action not in ["approve", "reject"]:
            messages.error(request, "Invalid action.")
            return redirect("guest_wifi_approval")

        try:
            with transaction.atomic():
                entry = get_object_or_404(
                    GuestWifiRequestApproversData.objects
                    .select_for_update()
                    .select_related(
                        "request",
                        "request__faculty",
                        "request__faculty__department",
                        "approver",
                        "creator",
                    ),
                    id=entry_id,
                )

                guest_request = entry.request

                if guest_request.status in ["APPROVED", "REJECTED"]:
                    messages.error(request, "This request is already closed.")
                    return redirect("guest_wifi_approval")

                if entry.status != GuestWifiRequestApproversData.Status.PENDING:
                    messages.error(request, "This approval step is already processed.")
                    return redirect("guest_wifi_approval")

                if not can_faculty_approve_guest_entry(entry, logged_in_faculty, logged_in_role, logged_in_dept_id):
                    messages.error(request, "You are not authorized to approve this step.")
                    return redirect("guest_wifi_approval")

                entry.approver = logged_in_faculty
                entry.acted_on = timezone.now()

                if action == "approve":
                    entry.status = GuestWifiRequestApproversData.Status.APPROVED
                    entry.reason = remarks or f"Approved by {logged_in_faculty.name}"
                    entry.save(update_fields=["approver", "acted_on", "status", "reason"])

                    has_pending = guest_request.approval_entries.filter(
                        status=GuestWifiRequestApproversData.Status.PENDING
                    ).exists()

                    guest_request.status = "PENDING" if has_pending else "APPROVED"
                    guest_request.save(update_fields=["status", "updated_at"])

                    messages.success(request, f"Guest WiFi Request #{guest_request.id} approved successfully.")

                else:
                    if not remarks:
                        messages.error(request, "Rejection reason is required.")
                        return redirect("guest_wifi_approval")

                    entry.status = GuestWifiRequestApproversData.Status.REJECTED
                    entry.reason = remarks
                    entry.save(update_fields=["approver", "acted_on", "status", "reason"])

                    guest_request.approval_entries.filter(
                        status=GuestWifiRequestApproversData.Status.PENDING
                    ).exclude(id=entry.id).update(
                        status=GuestWifiRequestApproversData.Status.REJECTED,
                        reason=f"Auto rejected after rejection at level {entry.approver_level}",
                        acted_on=timezone.now(),
                    )

                    guest_request.status = "REJECTED"
                    guest_request.save(update_fields=["status", "updated_at"])

                    messages.success(request, f"Guest WiFi Request #{guest_request.id} rejected successfully.")

        except Exception as e:
            logger.exception("guest_wifi_approval failed")
            messages.error(request, f"Approval failed: {str(e)}")

        return redirect("guest_wifi_approval")

    pending_entries = (
        GuestWifiRequestApproversData.objects
        .select_related(
            "request",
            "request__faculty",
            "request__faculty__department",
            "approver",
            "creator",
        )
        .filter(
            status=GuestWifiRequestApproversData.Status.PENDING,
            request__status="PENDING",
        )
        .order_by("request_id", "approver_level", "id")
    )

    actionable_entries = []
    for entry in pending_entries:
        if can_faculty_approve_guest_entry(entry, logged_in_faculty, logged_in_role, logged_in_dept_id):
            actionable_entries.append(entry)

    attach_role_names_to_entries(actionable_entries)

    my_actions = list(
        GuestWifiRequestApproversData.objects
        .select_related(
            "request",
            "request__faculty",
            "request__faculty__department",
            "approver",
            "creator",
        )
        .filter(approver=logged_in_faculty)
        .exclude(status=GuestWifiRequestApproversData.Status.PENDING)
        .order_by("-acted_on", "-id")[:20]
    )

    attach_role_names_to_entries(my_actions)

    return render(
        request,
        "data_center_management/wifi/guest_wifi_approval.html",
        {
            "actionable_entries": actionable_entries,
            "my_actions": my_actions,
            "logged_in_faculty": logged_in_faculty,
            "logged_in_role": get_role_name(getattr(logged_in_role, "id", None)),
            "is_global_user": is_global_user(
                logged_in_faculty,
                getattr(logged_in_role, "id", None),
            ),
        },
    )
    
    
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from student_management.models import StudentDetails
from faculty_management.models import general_information
from data_center_management.models import SystemSupportRequest

from data_center_management.decorators import data_center_management
from user_accounts.decorators import check_permission


@data_center_management
@check_permission("system_support_application")
def system_support_application(request):
    user = request.user
    user_email = (getattr(user, "email", "") or "").strip()

    student = (
        StudentDetails.objects.filter(email__iexact=user_email)
        .select_related("department", "ca")
        .first()
    )

    faculty = None
    if not student:
        faculty = (
            general_information.objects.filter(college_email__iexact=user_email)
            .select_related("department", "designation")
            .first()
        )

    if not student and not faculty:
        messages.error(request, "Unable to identify user.")
        return redirect("dashboard")

    creator_role_obj = get_logged_in_role_obj(request)
    if not creator_role_obj:
        messages.error(request, "User role not found.")
        return redirect("dashboard")

    student_data = build_student_dashboard_data(student) if student else None
    faculty_data = build_faculty_dashboard_data(faculty) if faculty else None

    if student:
        support_requests = SystemSupportRequest.objects.filter(student=student).order_by("-submitted_at")
    else:
        support_requests = SystemSupportRequest.objects.filter(
            faculty_id=getattr(faculty, "id", None)
        ).order_by("-submitted_at")

    context = {
        "student": student_data,
        "faculty": faculty_data,
        "is_student_user": bool(student_data),
        "is_faculty_user": bool(faculty_data),
        "support_requests": support_requests,
        "errors": {},
        "form_data": {},
    }

    if request.method == "POST":
        issue_type = request.POST.get("issue_type", "").strip()
        priority = request.POST.get("priority", SystemSupportRequest.Priority.MEDIUM).strip()
        subject = request.POST.get("subject", "").strip()
        description = request.POST.get("description", "").strip()
        preferred_contact_method = request.POST.get(
            "preferred_contact_method",
            SystemSupportRequest.PreferredContactMethod.EMAIL,
        ).strip()
        mobile_number = request.POST.get("mobile_number", "").strip()

        errors = {}

        if not issue_type:
            errors["issue_type"] = "Please select an issue type."

        if not subject:
            errors["subject"] = "Subject is required."

        if not description:
            errors["description"] = "Please describe your issue."

        valid_issue_types = {choice[0] for choice in SystemSupportRequest.IssueType.choices}
        valid_priorities = {choice[0] for choice in SystemSupportRequest.Priority.choices}
        valid_contact_methods = {
            choice[0] for choice in SystemSupportRequest.PreferredContactMethod.choices
        }

        if issue_type not in valid_issue_types:
            errors["issue_type"] = "Invalid issue type selected."

        if priority not in valid_priorities:
            priority = SystemSupportRequest.Priority.MEDIUM

        if preferred_contact_method not in valid_contact_methods:
            preferred_contact_method = SystemSupportRequest.PreferredContactMethod.EMAIL

        if not errors:
            try:
                with transaction.atomic():
                    SystemSupportRequest.objects.create(
                        creator_role_id=getattr(creator_role_obj, "id", None),
                        creator_role_name=getattr(creator_role_obj, "name", ""),
                        created_by_user_id=getattr(request.user, "id", None),
                        created_by_user_name=(
                            getattr(request.user, "username", "")
                            or getattr(request.user, "email", "")
                            or ""
                        ),
                        student=student if student else None,
                        faculty_id=getattr(faculty, "id", None) if faculty else None,
                        faculty_name=getattr(faculty, "name", "") if faculty else "",
                        faculty_email=getattr(faculty, "college_email", "") if faculty else "",
                        faculty_department=str(getattr(faculty, "department", "") or "") if faculty else "",
                        faculty_designation=str(getattr(faculty, "designation", "") or "") if faculty else "",
                        user_type=(
                            SystemSupportRequest.UserType.STUDENT
                            if student
                            else SystemSupportRequest.UserType.FACULTY
                        ),
                        issue_type=issue_type,
                        subject=subject,
                        description=description,
                        preferred_contact_method=preferred_contact_method,
                        mobile_number=mobile_number,
                        priority=priority,
                        status=SystemSupportRequest.Status.PENDING,
                    )

                messages.success(request, "System support request submitted successfully.")
                return redirect("system_support_application")

            except Exception as e:
                messages.error(request, f"Error: {str(e)}")

        context["errors"] = errors
        context["form_data"] = request.POST

    return render(
        request,
        "data_center_management/wifi/system_support_application.html",
        context,
    )


@login_required
def system_support_approval(request):
    user_email = (getattr(request.user, "email", "") or "").strip()

    logged_in_faculty = (
        general_information.objects
        .select_related("department", "designation")
        .filter(college_email__iexact=user_email)
        .first()
    )

    if not logged_in_faculty:
        messages.error(request, "Only faculty approvers can access this page.")
        return redirect("dashboard")

    logged_in_role = getattr(getattr(request.user, "role", None), "name", None) or "Approver"

    if request.method == "POST":
        request_id = request.POST.get("request_id")
        action = request.POST.get("action")
        remarks = request.POST.get("remarks", "").strip()

        request_obj = get_object_or_404(SystemSupportRequest, id=request_id)

        if request_obj.status != SystemSupportRequest.Status.PENDING:
            messages.warning(request, "Only pending requests can be processed from this page.")
            return redirect("system_support_approval")

        if action == "process":
            request_obj.status = SystemSupportRequest.Status.IN_PROGRESS
            request_obj.assigned_approver_id = getattr(logged_in_faculty, "id", None)
            request_obj.assigned_approver_name = getattr(logged_in_faculty, "name", "") or ""
            request_obj.assigned_approver_email = getattr(logged_in_faculty, "college_email", "") or ""
            request_obj.approver_remarks = remarks
            request_obj.approved_at = timezone.now()
            request_obj.save()

            messages.success(request, f"{request_obj.application_id} moved to processing.")

        elif action == "reject":
            request_obj.status = SystemSupportRequest.Status.REJECTED
            request_obj.assigned_approver_id = getattr(logged_in_faculty, "id", None)
            request_obj.assigned_approver_name = getattr(logged_in_faculty, "name", "") or ""
            request_obj.assigned_approver_email = getattr(logged_in_faculty, "college_email", "") or ""
            request_obj.approver_remarks = remarks
            request_obj.rejection_reason = remarks
            request_obj.rejected_at = timezone.now()
            request_obj.save()

            messages.error(request, f"{request_obj.application_id} rejected.")
        else:
            messages.warning(request, "Invalid action.")

        return redirect("system_support_approval")

    pending_requests = (
        SystemSupportRequest.objects
        .select_related("student")
        .filter(status=SystemSupportRequest.Status.PENDING)
        .order_by("submitted_at")
    )

    processed_requests = (
        SystemSupportRequest.objects
        .select_related("student")
        .filter(assigned_approver_id=getattr(logged_in_faculty, "id", None))
        .exclude(status=SystemSupportRequest.Status.PENDING)
        .order_by("-updated_at")[:20]
    )

    context = {
        "logged_in_faculty": logged_in_faculty,
        "logged_in_role": logged_in_role,
        "pending_requests": pending_requests,
        "processed_requests": processed_requests,
    }
    return render(
        request,
        "data_center_management/wifi/system_support_approval.html",
        context,
    )


@login_required
def system_support_resolve(request):
    user_email = (getattr(request.user, "email", "") or "").strip()

    logged_in_faculty = (
        general_information.objects
        .select_related("department", "designation")
        .filter(college_email__iexact=user_email)
        .first()
    )

    if not logged_in_faculty:
        messages.error(request, "Only faculty/incharge can access this page.")
        return redirect("dashboard")

    if request.method == "POST":
        request_id = request.POST.get("request_id")
        action = request.POST.get("action")
        solution_notes = request.POST.get("solution_notes", "").strip()

        request_obj = get_object_or_404(SystemSupportRequest, id=request_id)

        if request_obj.status != SystemSupportRequest.Status.IN_PROGRESS:
            messages.warning(request, "Only in-progress requests can be completed from this page.")
            return redirect("system_support_resolve")

        if action == "resolve":
            request_obj.status = SystemSupportRequest.Status.RESOLVED
            request_obj.solved_by_id = getattr(logged_in_faculty, "id", None)
            request_obj.solved_by_name = getattr(logged_in_faculty, "name", "") or ""
            request_obj.solved_by_email = getattr(logged_in_faculty, "college_email", "") or ""
            request_obj.solved_at = timezone.now()
            request_obj.resolution_notes = solution_notes
            request_obj.save()

            messages.success(request, f"{request_obj.application_id} marked as resolved.")

        elif action == "close":
            request_obj.status = SystemSupportRequest.Status.CLOSED
            request_obj.closed_by_id = getattr(logged_in_faculty, "id", None)
            request_obj.closed_by_name = getattr(logged_in_faculty, "name", "") or ""
            request_obj.closed_by_email = getattr(logged_in_faculty, "college_email", "") or ""
            request_obj.closed_at = timezone.now()
            request_obj.closing_notes = solution_notes
            request_obj.save()

            messages.success(request, f"{request_obj.application_id} closed successfully.")
        else:
            messages.warning(request, "Invalid action.")

        return redirect("system_support_resolve")

    active_requests = (
        SystemSupportRequest.objects
        .select_related("student")
        .filter(status=SystemSupportRequest.Status.IN_PROGRESS)
        .order_by("updated_at")
    )

    completed_requests = (
        SystemSupportRequest.objects
        .select_related("student")
        .filter(
            status__in=[
                SystemSupportRequest.Status.RESOLVED,
                SystemSupportRequest.Status.CLOSED,
            ]
        )
        .order_by("-updated_at")[:30]
    )

    context = {
        "active_requests": active_requests,
        "completed_requests": completed_requests,
    }
    return render(
        request,
        "data_center_management/wifi/system_support_resolve.html",
        context,
    )


def get_student_by_reg_no(request):
    reg_no = request.GET.get("reg_no", "").strip()

    if not reg_no:
        return JsonResponse({
            "success": False,
            "message": "Register number is required."
        })

    student = StudentDetails.objects.filter(
        reg_no__iexact=reg_no,
        is_active=True
    ).first()

    if not student:
        return JsonResponse({
            "success": False,
            "message": "Student not found."
        })

    return JsonResponse({
        "success": True,
        "student_name": student.name or "",
        "email": student.email or "",
    })


from datetime import timedelta

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone

from data_center_management.models import EmailReloginApplication
from faculty_management.models import general_information
from student_management.models import StudentDetails

@check_permission("email_relogin_apllication")
def email_relogin_apllication(request):
    faculty = None
    errors = {}
    form_data = {}

    user_email = (getattr(request.user, "email", "") or "").strip()

    if request.user.is_authenticated:
        faculty = general_information.objects.filter(
            college_email__iexact=user_email
        ).first()

    if request.method == "POST":
        form_data = request.POST.copy()

        reg_no = request.POST.get("reg_no", "").strip()
        reason = request.POST.get("reason", "").strip()
        agreement = request.POST.get("agreement")

        student = None

        if not reg_no:
            errors["reg_no"] = "Register number is required."
        else:
            student = StudentDetails.objects.filter(
                reg_no__iexact=reg_no,
                is_active=True
            ).first()

            if not student:
                errors["reg_no"] = "Student not found for this register number."

        if not reason:
            errors["reason"] = "Reason is required."

        if not agreement:
            errors["agreement"] = "Please accept the declaration."

        if not errors:
            EmailReloginApplication.objects.create(
                faculty=faculty,
                student=student,
                reason=reason,
                agreement=True,
                status=EmailReloginApplication.Status.PENDING,
            )

            messages.success(request, "Email relogin application submitted successfully.")
            return redirect("email_relogin_apllication")

    user_requests = (
        EmailReloginApplication.objects
        .select_related("student", "faculty")
        .filter(faculty=faculty)
        .order_by("-created_at")
    ) if faculty else []

    return render(
        request,
        "data_center_management/dc_admin/email_relogin_apllication.html",
        {
            "faculty": faculty,
            "errors": errors,
            "form_data": form_data,
            "user_requests": user_requests,
        }
    )
    

@check_permission("email_relogin_approval")
def email_relogin_approval(request):
    user_email = (getattr(request.user, "email", "") or "").strip()

    logged_in_faculty = (
        general_information.objects
        .select_related("department", "designation")
        .filter(college_email__iexact=user_email)
        .first()
    )

    if not logged_in_faculty:
        messages.error(request, "Only faculty approvers can access this page.")
        return redirect("dashboard")

    logged_in_role = getattr(getattr(request.user, "role", None), "name", None) or "Approver"

    if request.method == "POST":
        application_id = request.POST.get("application_id")
        action = request.POST.get("action")
        remarks = request.POST.get("remarks", "").strip()

        application = get_object_or_404(
            EmailReloginApplication,
            id=application_id
        )

        if application.status != EmailReloginApplication.Status.PENDING:
            messages.warning(request, "Only pending applications can be processed.")
            return redirect("email_relogin_approval")

        if action == "approve":
            application.status = EmailReloginApplication.Status.APPROVED
            application.processed_by = logged_in_faculty
            application.approver_remarks = remarks
            application.approved_at = timezone.now()
            application.rejected_at = None
            application.save()

            messages.success(request, "Email relogin application approved successfully.")

        elif action == "reject":
            application.status = EmailReloginApplication.Status.REJECTED
            application.processed_by = logged_in_faculty
            application.approver_remarks = remarks
            application.rejected_at = timezone.now()
            application.approved_at = None
            application.save()

            messages.error(request, "Email relogin application rejected.")

        else:
            messages.warning(request, "Invalid action.")

        return redirect("email_relogin_approval")

    pending_applications = (
        EmailReloginApplication.objects
        .select_related("faculty", "student")
        .filter(status=EmailReloginApplication.Status.PENDING)
        .order_by("created_at")
    )

    processed_applications = (
        EmailReloginApplication.objects
        .select_related("faculty", "student", "processed_by")
        .filter(processed_by=logged_in_faculty)
        .exclude(status=EmailReloginApplication.Status.PENDING)
        .order_by("-updated_at")[:20]
    )

    return render(
        request,
        "data_center_management/dc_admin/email_relogin_approval.html",
        {
            "logged_in_faculty": logged_in_faculty,
            "logged_in_role": logged_in_role,
            "pending_applications": pending_applications,
            "processed_applications": processed_applications,
        }
    )
    
    
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

from data_center_management.models import EmailReloginApplication


from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

from data_center_management.models import EmailReloginApplication


@check_permission("email_relogin_dashboard")
def email_relogin_dashboard(request):
    now = timezone.now()

    if request.method == "POST":
        application_id = request.POST.get("application_id")
        action = request.POST.get("action")

        application = get_object_or_404(
            EmailReloginApplication,
            id=application_id,
            status=EmailReloginApplication.Status.APPROVED
        )

        if action == "deactivate":
            application.status = EmailReloginApplication.Status.DEACTIVATED
            application.deactivated_at = timezone.now()
            application.save()

            messages.success(
                request,
                "Email relogin access deactivated successfully."
            )

        return redirect("email_relogin_dashboard")

    approved_requests = (
        EmailReloginApplication.objects
        .select_related("faculty", "processed_by", "student")
        .filter(status=EmailReloginApplication.Status.APPROVED)
        .order_by("-approved_at")
    )

    deactivated_requests = (
        EmailReloginApplication.objects
        .select_related("faculty", "processed_by", "student")
        .filter(status=EmailReloginApplication.Status.DEACTIVATED)
        .order_by("-deactivated_at")
    )

    dashboard_requests = []

    for request_obj in approved_requests:
        valid_until = None
        is_expired = False
        remaining_text = "-"

        if request_obj.approved_at:
            valid_until = request_obj.approved_at + timedelta(days=3)
            is_expired = now >= valid_until

            if is_expired:
                remaining_text = "Time Up"
            else:
                remaining = valid_until - now
                days = remaining.days
                hours = remaining.seconds // 3600
                minutes = (remaining.seconds % 3600) // 60

                remaining_text = f"{days} day(s), {hours} hour(s), {minutes} minute(s) left"

        dashboard_requests.append({
            "application": request_obj,
            "valid_until": valid_until,
            "is_expired": is_expired,
            "remaining_text": remaining_text,
        })

    return render(
        request,
        "data_center_management/dc_admin/email_relogin_dashboard.html",
        {
            "dashboard_requests": dashboard_requests,
            "deactivated_requests": deactivated_requests,
            "now": now,
        }
    )


# =========================================================
# APPLICATION DASHBOARD
# One consolidated register of every Data Center application
# (WiFi, Network Query, Guest WiFi, System Support, Email Relogin)
# with student/faculty filter, name & register-number search,
# and a filter-aware PDF export.
# =========================================================
import io
from datetime import datetime
from xml.sax.saxutils import escape as _xml_escape

from django.http import JsonResponse, HttpResponse

from data_center_management.models import (
    DataCenterRequest,
    NetworkQuery,
    GuestWifiRequest,
    SystemSupportRequest,
    EmailReloginApplication,
)


APP_TYPE_CHOICES = [
    ("all", "All Applications"),
    ("wifi", "WiFi Application"),
    ("query", "Network Query"),
    ("guest", "Guest WiFi"),
    ("system_support", "System Support"),
    ("email_relogin", "Email Relogin"),
]

USER_TYPE_CHOICES = [
    ("all", "All Users"),
    ("student", "Student"),
    ("faculty", "Faculty"),
]


def _dc_dash_dept_name(dept):
    if not dept:
        return ""
    return getattr(dept, "Department", None) or str(dept)


def _dc_dash_student_fields(student):
    return {
        "user_type": "Student",
        "name": getattr(student, "name", "") or "",
        "register_no": getattr(student, "reg_no", "") or "",
        "department": _dc_dash_dept_name(getattr(student, "department", None)),
        "email": getattr(student, "email", "") or "",
        "year": str(getattr(student, "year", "") or "").strip(),
        "gender": getattr(student, "gender", "") or "",
    }


def _dc_dash_faculty_fields(faculty):
    return {
        "user_type": "Faculty",
        "name": getattr(faculty, "name", "") or "",
        "register_no": str(getattr(faculty, "faculty_id", "") or ""),
        "department": _dc_dash_dept_name(getattr(faculty, "department", None)),
        "email": (
            getattr(faculty, "college_email", "")
            or getattr(faculty, "personal_email", "")
            or ""
        ),
        "year": "",
        "gender": getattr(faculty, "gender", "") or "",
    }


def _dc_dash_person(student, faculty):
    if student:
        return _dc_dash_student_fields(student)
    if faculty:
        return _dc_dash_faculty_fields(faculty)
    return {"user_type": "-", "name": "", "register_no": "", "department": "", "email": "", "year": "", "gender": ""}


def _dc_dash_year_label(year):
    """Normalize a raw student year value into a display label."""
    y = str(year or "").strip()
    if not y:
        return ""
    mapping = {
        "1": "1st Year", "i": "1st Year", "first": "1st Year",
        "2": "2nd Year", "ii": "2nd Year", "second": "2nd Year",
        "3": "3rd Year", "iii": "3rd Year", "third": "3rd Year",
        "4": "Final Year", "iv": "Final Year", "fourth": "Final Year", "final": "Final Year",
    }
    return mapping.get(y.lower(), f"Year {y}")


def _dc_bool_label(value):
    if value is None:
        return "-"
    return "Yes" if value else "No"


def _dc_fmt_dt(dt, fmt="%d-%m-%Y %I:%M %p"):
    if not dt:
        return "-"
    try:
        if timezone.is_aware(dt):
            dt = timezone.localtime(dt)
        return dt.strftime(fmt)
    except Exception:
        return "-"


def _dc_dash_row_to_json(r):
    """Shared JSON-safe shape for a dashboard row (initial page load + AJAX filter + View modal)."""
    return {
        "app_type": r["app_type"],
        "app_type_key": r["app_type_key"],
        "reference": r["reference"],
        "name": r["name"] or "-",
        "register_no": r["register_no"] or "-",
        "user_type": r["user_type"],
        "gender": r.get("gender") or "-",
        "department": r["department"] or "-",
        "email": r["email"] or "-",
        "year": r.get("year_label") or "-",
        "student_type": r.get("student_type") or "-",
        "status": r["status"],
        "status_key": r["status_key"],
        "detail": r["detail"] or "-",
        "submitted_at": (
            r["submitted_at"].strftime("%d-%m-%Y %I:%M %p")
            if r["submitted_at"] else "-"
        ),
        "extra": r.get("extra") or [],
    }


def _collect_dc_application_rows():
    """Build a normalized row (same keys for every type) for all applications."""
    rows = []

    # ---- WiFi applications -------------------------------------------------
    for obj in DataCenterRequest.objects.select_related(
        "student", "student__department", "faculty", "faculty__department"
    ):
        person = _dc_dash_person(obj.student, obj.faculty)
        if obj.is_for_event and obj.event_name:
            detail = f"Event: {obj.event_name}"
        elif obj.device_type:
            detail = obj.get_device_type_display()
        else:
            detail = "WiFi access request"

        if obj.student:
            student_type = "Hostel" if is_hosteller(obj.admission_mode) else "Dayscholar"
        else:
            student_type = ""

        extra = [
            {"label": "Device Type", "value": obj.get_device_type_display() if obj.device_type else "-"},
            {"label": "Device MAC Address", "value": obj.device_mac_address or "-"},
            {"label": "Ethernet Cable Required", "value": _dc_bool_label(obj.ethernet_cable_required)},
        ]
        if obj.ethernet_cable_required:
            extra.append({"label": "Ethernet MAC Address", "value": obj.ethernet_mac_address or "-"})
        extra.append({"label": "Mobile WiFi Required", "value": _dc_bool_label(obj.wifi_for_mobile_required)})
        if obj.wifi_for_mobile_required:
            extra.append({"label": "Mobile Number", "value": obj.mobile_no or "-"})
            extra.append({"label": "Mobile Static MAC", "value": obj.mobile_static_mac_address or "-"})
        if obj.cluster or obj.room_no:
            extra.append({"label": "Cluster", "value": obj.cluster or "-"})
            extra.append({"label": "Room No", "value": obj.room_no or "-"})
        if obj.admission_mode:
            extra.append({"label": "Admission Mode", "value": obj.admission_mode})
        if obj.is_for_event:
            extra.append({"label": "Event Name", "value": obj.event_name or "-"})
            extra.append({"label": "Event Location", "value": obj.location or "-"})
            extra.append({"label": "Time Period", "value": obj.time_period or "-"})
            extra.append({"label": "Purpose", "value": obj.purpose or "-"})
        extra.append({"label": "Agreement Accepted", "value": _dc_bool_label(obj.agreement)})

        rows.append({
            "app_type": "WiFi Application",
            "app_type_key": "wifi",
            "reference": f"DCR-{obj.id}",
            "status": (obj.status or "PENDING").title(),
            "status_key": (obj.status or "PENDING").lower(),
            "submitted_at": obj.created_at,
            "detail": detail,
            "student_type": student_type,
            "extra": extra,
            **person,
        })

    # ---- Network queries ---------------------------------------------------
    for obj in NetworkQuery.objects.select_related(
        "student", "student__department", "faculty", "faculty__department"
    ):
        person = _dc_dash_person(obj.student, obj.faculty)

        extra = [
            {"label": "Query Type", "value": obj.get_query_type_display() if obj.query_type else "-"},
            {"label": "Priority", "value": obj.get_priority_display() if obj.priority else "-"},
            {"label": "Connection Type", "value": obj.get_connection_type_display() if obj.connection_type else "-"},
            {"label": "Device Type", "value": obj.device_type or "-"},
            {"label": "Location Details", "value": obj.location_details or "-"},
            {"label": "Description", "value": obj.description or "-"},
        ]
        if obj.approver_remarks:
            extra.append({"label": "Approver Remarks", "value": obj.approver_remarks})
        if obj.solution_notes:
            extra.append({"label": "Solution Notes", "value": obj.solution_notes})
        if obj.closing_notes:
            extra.append({"label": "Closing Notes", "value": obj.closing_notes})
        if obj.rejection_reason:
            extra.append({"label": "Rejection Reason", "value": obj.rejection_reason})

        rows.append({
            "app_type": "Network Query",
            "app_type_key": "query",
            "reference": obj.query_id or f"NQ-{obj.id}",
            "status": obj.get_status_display(),
            "status_key": (obj.status or "").lower(),
            "submitted_at": obj.submitted_at,
            "detail": obj.subject or "",
            "student_type": (obj.get_student_type_display() if obj.student_type else ""),
            "extra": extra,
            **person,
        })

    # ---- Guest WiFi (raised by faculty on behalf of an external guest) -----
    for obj in GuestWifiRequest.objects.select_related("faculty", "faculty__department"):
        faculty_fields = _dc_dash_faculty_fields(obj.faculty) if obj.faculty else {}

        extra = [
            {"label": "Raised By (Faculty)", "value": faculty_fields.get("name") or "-"},
            {"label": "Guest Mobile No", "value": obj.guest_mobile_no or "-"},
            {"label": "Guest Organization", "value": obj.guest_organization or "-"},
            {"label": "Purpose of Visit", "value": obj.get_purpose_of_visit_display() if obj.purpose_of_visit else "-"},
            {"label": "Reason", "value": obj.reason or "-"},
            {"label": "Visit Date", "value": obj.visit_date.strftime("%d-%m-%Y") if obj.visit_date else "-"},
            {"label": "Access From", "value": _dc_fmt_dt(obj.access_from)},
            {"label": "Access To", "value": _dc_fmt_dt(obj.access_to)},
            {"label": "Device Type", "value": obj.device_type or "-"},
            {"label": "Device MAC Address", "value": obj.device_mac_address or "-"},
            {"label": "Mobile Static MAC", "value": obj.mobile_static_mac_address or "-"},
        ]

        rows.append({
            "app_type": "Guest WiFi",
            "app_type_key": "guest",
            "reference": f"GWR-{obj.id}",
            "status": (obj.status or "PENDING").title(),
            "status_key": (obj.status or "PENDING").lower(),
            "submitted_at": obj.created_at,
            "detail": f"Raised by {faculty_fields.get('name') or '-'}",
            "user_type": "Faculty",
            "name": obj.guest_name or "-",
            "register_no": "-",
            "department": faculty_fields.get("department", ""),
            "email": obj.guest_email or faculty_fields.get("email", ""),
            "year": "",
            "gender": "-",
            "student_type": "",
            "extra": extra,
        })

    # ---- System support ----------------------------------------------------
    for obj in SystemSupportRequest.objects.select_related("student", "student__department"):
        if obj.user_type == SystemSupportRequest.UserType.STUDENT and obj.student:
            person = _dc_dash_student_fields(obj.student)
        else:
            person = {
                "user_type": "Faculty",
                "name": obj.faculty_name or "",
                "register_no": str(obj.faculty_id or ""),
                "department": obj.faculty_department or "",
                "email": obj.faculty_email or "",
                "year": "",
                "gender": "-",
            }
        extra = [
            {"label": "Issue Type", "value": obj.get_issue_type_display() if obj.issue_type else "-"},
            {"label": "Subject", "value": obj.subject or "-"},
            {"label": "Description", "value": obj.description or "-"},
            {"label": "Preferred Contact Method", "value": obj.get_preferred_contact_method_display() if obj.preferred_contact_method else "-"},
            {"label": "Mobile Number", "value": obj.mobile_number or "-"},
            {"label": "Priority", "value": obj.get_priority_display() if obj.priority else "-"},
        ]
        if obj.approver_remarks:
            extra.append({"label": "Approver Remarks", "value": obj.approver_remarks})
        if obj.rejection_reason:
            extra.append({"label": "Rejection Reason", "value": obj.rejection_reason})
        if obj.resolution_notes:
            extra.append({"label": "Resolution Notes", "value": obj.resolution_notes})
        if obj.closing_notes:
            extra.append({"label": "Closing Notes", "value": obj.closing_notes})

        rows.append({
            "app_type": "System Support",
            "app_type_key": "system_support",
            "reference": obj.application_id or f"SSR-{obj.id}",
            "status": obj.get_status_display(),
            "status_key": (obj.status or "").lower(),
            "submitted_at": obj.submitted_at,
            "detail": obj.get_issue_type_display() if obj.issue_type else (obj.subject or ""),
            "student_type": "",
            "extra": extra,
            **person,
        })

    # ---- Email relogin (raised by faculty, usually for a student) ----------
    for obj in EmailReloginApplication.objects.select_related(
        "student", "student__department", "faculty", "faculty__department"
    ):
        person = _dc_dash_person(obj.student, obj.faculty)

        extra = [
            {"label": "Reason", "value": obj.reason or "-"},
            {"label": "Agreement Accepted", "value": _dc_bool_label(obj.agreement)},
        ]
        if obj.approver_remarks:
            extra.append({"label": "Approver Remarks", "value": obj.approver_remarks})

        rows.append({
            "app_type": "Email Relogin",
            "app_type_key": "email_relogin",
            "reference": f"ERL-{obj.id}",
            "status": obj.get_status_display(),
            "status_key": (obj.status or "").lower(),
            "submitted_at": obj.created_at,
            "detail": (obj.reason or "")[:100],
            "student_type": "",
            "extra": extra,
            **person,
        })

    return rows


def _dc_dash_sort_key(row):
    dt = row.get("submitted_at")
    try:
        return dt.timestamp() if dt else 0.0
    except Exception:
        return 0.0


def _row_local_date(row):
    dt = row.get("submitted_at")
    if not dt:
        return None
    try:
        return timezone.localtime(dt).date() if timezone.is_aware(dt) else dt.date()
    except Exception:
        try:
            return dt.date()
        except Exception:
            return None


def _filter_dc_application_rows(rows, filters):
    app_type = (filters.get("app_type") or "all").lower()
    user_type = (filters.get("user_type") or "all").lower()
    status = (filters.get("status") or "all").lower()
    department = (filters.get("department") or "all").strip().lower()
    year = (filters.get("year") or "all").strip().lower()
    q = (filters.get("q") or "").strip().lower()
    date_from = filters.get("date_from")   # date or None
    date_to = filters.get("date_to")       # date or None

    result = []
    for row in rows:
        if app_type != "all" and row["app_type_key"] != app_type:
            continue
        if user_type != "all" and row["user_type"].lower() != user_type:
            continue
        if status != "all" and row["status_key"] != status:
            continue
        if department != "all" and str(row.get("department", "")).strip().lower() != department:
            continue
        if year != "all" and str(row.get("year", "")).strip().lower() != year:
            continue

        if date_from or date_to:
            row_date = _row_local_date(row)
            if row_date is None:
                continue
            if date_from and row_date < date_from:
                continue
            if date_to and row_date > date_to:
                continue

        if q:
            haystack = " ".join([
                str(row.get("name", "")),
                str(row.get("register_no", "")),
                str(row.get("reference", "")),
                str(row.get("email", "")),
            ]).lower()
            if q not in haystack:
                continue
        result.append(row)

    result.sort(key=_dc_dash_sort_key, reverse=True)
    return result


def _summarize_dc_rows(rows):
    """Build the summary-card numbers from an already-filtered row set."""
    summary = {
        "total": len(rows),
        "by_type": {
            "wifi": 0,
            "query": 0,
            "guest": 0,
            "system_support": 0,
            "email_relogin": 0,
        },
        "by_user": {"student": 0, "faculty": 0},
        "wifi_hostel": 0,
        "wifi_dayscholar": 0,
        "wifi_by_year": {},   # label -> count (WiFi student applications)
    }

    for row in rows:
        key = row.get("app_type_key")
        if key in summary["by_type"]:
            summary["by_type"][key] += 1

        ut = (row.get("user_type") or "").lower()
        if ut in summary["by_user"]:
            summary["by_user"][ut] += 1

        if key == "wifi":
            stype = (row.get("student_type") or "").lower()
            if stype == "hostel":
                summary["wifi_hostel"] += 1
            elif stype == "dayscholar":
                summary["wifi_dayscholar"] += 1

            if row.get("user_type") == "Student":
                label = _dc_dash_year_label(row.get("year")) or "Unspecified"
                summary["wifi_by_year"][label] = summary["wifi_by_year"].get(label, 0) + 1

    # stable, human order for the year buckets
    year_order = ["1st Year", "2nd Year", "3rd Year", "Final Year"]
    ordered_years = {}
    for lbl in year_order:
        if lbl in summary["wifi_by_year"]:
            ordered_years[lbl] = summary["wifi_by_year"][lbl]
    for lbl, val in sorted(summary["wifi_by_year"].items()):
        if lbl not in ordered_years:
            ordered_years[lbl] = val
    summary["wifi_by_year"] = ordered_years

    return summary


def _dc_application_dashboard_pdf(rows, filter_summary, summary=None):
    """Render the filtered rows as a landscape PDF register (reportlab)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

    buffer = io.BytesIO()
    styles = getSampleStyleSheet()

    PRIMARY = colors.HexColor("#1a4b8c")
    BORDER = colors.HexColor("#cfd8e3")
    ROW_BG = colors.HexColor("#f4f8ff")

    title_style = ParagraphStyle(
        "dc_dash_title", parent=styles["Heading1"], fontName="Helvetica-Bold",
        fontSize=15, textColor=PRIMARY, alignment=TA_CENTER, spaceAfter=2,
    )
    sub_style = ParagraphStyle(
        "dc_dash_sub", parent=styles["Normal"], fontName="Helvetica",
        fontSize=8.5, textColor=colors.HexColor("#4b5563"), alignment=TA_CENTER, spaceAfter=8,
    )
    th = ParagraphStyle(
        "dc_dash_th", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=8.5, textColor=colors.white, alignment=TA_CENTER,
    )
    td = ParagraphStyle(
        "dc_dash_td", parent=styles["Normal"], fontName="Helvetica",
        fontSize=8, textColor=colors.HexColor("#1f2937"), alignment=TA_LEFT, wordWrap="CJK",
    )

    def P(value, style=td):
        return Paragraph(_xml_escape(str(value if value not in (None, "") else "-")), style)

    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        leftMargin=10 * mm, rightMargin=10 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
        title="Data Center Applications Register",
    )

    elements = [
        Paragraph("RAMCO INSTITUTE OF TECHNOLOGY", title_style),
        Paragraph("Data Center Management - Applications Register", sub_style),
        P(filter_summary, sub_style),
    ]

    # Summary strip (counts by type / user / hostel-dayscholar / year).
    if summary:
        by_type = summary.get("by_type", {})
        parts = [
            f"Total: {summary.get('total', 0)}",
            f"WiFi: {by_type.get('wifi', 0)}",
            f"Query: {by_type.get('query', 0)}",
            f"Guest: {by_type.get('guest', 0)}",
            f"System Support: {by_type.get('system_support', 0)}",
            f"Email Relogin: {by_type.get('email_relogin', 0)}",
            f"Students: {summary.get('by_user', {}).get('student', 0)}",
            f"Faculty: {summary.get('by_user', {}).get('faculty', 0)}",
        ]
        elements.append(P("  |  ".join(parts), sub_style))

        wifi_parts = [
            f"WiFi Hostel: {summary.get('wifi_hostel', 0)}",
            f"WiFi Dayscholar: {summary.get('wifi_dayscholar', 0)}",
        ]
        for lbl, val in (summary.get("wifi_by_year") or {}).items():
            wifi_parts.append(f"{lbl}: {val}")
        elements.append(P("  |  ".join(wifi_parts), sub_style))

    elements.append(Spacer(1, 3 * mm))

    headers = [
        "S.No", "Type", "Reference", "Applicant", "Reg / ID No",
        "User", "Department", "College Email", "Status", "Submitted On",
    ]
    data = [[Paragraph(h, th) for h in headers]]

    for i, row in enumerate(rows, start=1):
        submitted = row.get("submitted_at")
        submitted_txt = submitted.strftime("%d-%m-%Y %I:%M %p") if submitted else "-"
        data.append([
            P(i), P(row.get("app_type")), P(row.get("reference")),
            P(row.get("name")), P(row.get("register_no")), P(row.get("user_type")),
            P(row.get("department")), P(row.get("email")), P(row.get("status")),
            P(submitted_txt),
        ])

    if not rows:
        data.append([P("No records match the selected filters.")] +
                    [P("") for _ in range(len(headers) - 1)])

    col_widths = [11*mm, 25*mm, 22*mm, 40*mm, 24*mm, 16*mm, 38*mm, 48*mm, 22*mm, 31*mm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_BG]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 6 * mm))
    elements.append(Paragraph(
        f"Total records: {len(rows)}     Generated: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}",
        sub_style,
    ))

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="data_center_applications.pdf"'
    return response


@data_center_management
@check_permission("application_dashboard")
def application_dashboard(request):
    app_type = request.GET.get("app_type", "all")
    user_type = request.GET.get("user_type", "all")
    status = request.GET.get("status", "all")
    department = request.GET.get("department", "all")
    year = request.GET.get("year", "all")
    q = request.GET.get("q", "")
    export = (request.GET.get("export") or "").strip().lower()
    out_format = (request.GET.get("format") or "").strip().lower()

    # ----- Department lock (HOD-style scoping) --------------------------------
    # A non-global, non-superuser viewer (e.g. an HOD) is restricted to the
    # department of their ACTIVE (switched) profile — they only see their own
    # department's applications, and the department filter is locked server-side.
    # Global users / superusers keep full, all-department access.
    department_locked = False
    locked_department_name = None

    viewer_is_super = bool(getattr(request.user, "is_superuser", False))
    viewer_role = get_logged_in_role(request)
    viewer_is_global = is_global_user(
        get_logged_in_faculty(request),
        getattr(viewer_role, "id", None),
    )

    if not viewer_is_super and not viewer_is_global:
        viewer_dept_id = get_logged_in_account_department_id(request)
        if viewer_dept_id:
            locked_department_name = (
                Add_Department.objects
                .filter(id=viewer_dept_id)
                .values_list("Department", flat=True)
                .first()
            )
        if locked_department_name:
            department = locked_department_name   # override any incoming value
            department_locked = True

    # ----- Date range (default = TODAY when no date params are supplied) -----
    today = timezone.localdate()
    has_date_params = ("date_from" in request.GET) or ("date_to" in request.GET)

    date_from_raw = (request.GET.get("date_from") or "").strip()
    date_to_raw = (request.GET.get("date_to") or "").strip()

    if not has_date_params:
        date_from = today
        date_to = today
    else:
        date_from = parse_date(date_from_raw) if date_from_raw else None
        date_to = parse_date(date_to_raw) if date_to_raw else None

    # keep from <= to
    if date_from and date_to and date_from > date_to:
        date_from, date_to = date_to, date_from

    all_rows = _collect_dc_application_rows()

    # Build the status dropdown from the full dataset so options stay stable.
    status_map = {}
    for row in all_rows:
        if row["status_key"] and row["status_key"] not in status_map:
            status_map[row["status_key"]] = row["status"]
    status_choices = [("all", "All Statuses")] + sorted(
        status_map.items(), key=lambda kv: kv[1]
    )

    # Department dropdown (local departments).
    department_choices = [("all", "All Departments")] + [
        (d.Department, d.Department)
        for d in Add_Department.objects.all().order_by("Department")
        if d.Department
    ]

    # Year dropdown (distinct student years present in the data).
    year_seen = {}
    for row in all_rows:
        raw = str(row.get("year", "") or "").strip()
        if raw and raw not in year_seen:
            year_seen[raw] = _dc_dash_year_label(raw)
    year_choices = [("all", "All Years")] + sorted(
        year_seen.items(), key=lambda kv: kv[1]
    )

    filters = {
        "app_type": app_type,
        "user_type": user_type,
        "status": status,
        "department": department,
        "year": year,
        "q": q,
        "date_from": date_from,
        "date_to": date_to,
    }

    rows = _filter_dc_application_rows(all_rows, filters)
    for r in rows:
        r["year_label"] = _dc_dash_year_label(r.get("year"))
    summary = _summarize_dc_rows(rows)

    app_type_label = dict(APP_TYPE_CHOICES).get(app_type.lower(), "All Applications")
    user_type_label = dict(USER_TYPE_CHOICES).get(user_type.lower(), "All Users")
    status_label = dict(status_choices).get(status.lower(), "All Statuses")
    dept_label = department if department and department.lower() != "all" else "All Departments"
    year_label = dict(year_choices).get(year, "All Years") if year != "all" else "All Years"
    date_label = "All dates"
    if date_from and date_to:
        date_label = f"{date_from.strftime('%d-%m-%Y')} to {date_to.strftime('%d-%m-%Y')}"
    elif date_from:
        date_label = f"From {date_from.strftime('%d-%m-%Y')}"
    elif date_to:
        date_label = f"Up to {date_to.strftime('%d-%m-%Y')}"

    filter_summary = (
        f"Type: {app_type_label} | User: {user_type_label} | Status: {status_label} | "
        f"Dept: {dept_label} | Year: {year_label} | Dates: {date_label} | Search: {q or '-'}"
    )

    if export == "pdf":
        return _dc_application_dashboard_pdf(rows, filter_summary, summary)

    if out_format == "json":
        return JsonResponse({
            "count": len(rows),
            "summary": summary,
            "rows": [_dc_dash_row_to_json(r) for r in rows],
        })

    rows_for_json = [_dc_dash_row_to_json(r) for r in rows]

    context = {
        "rows": rows,
        "rows_for_json": rows_for_json,
        "summary": summary,
        "total_count": len(all_rows),
        "filtered_count": len(rows),
        "app_type_choices": APP_TYPE_CHOICES,
        "user_type_choices": USER_TYPE_CHOICES,
        "status_choices": status_choices,
        "department_choices": department_choices,
        "year_choices": year_choices,
        "department_locked": department_locked,
        "locked_department_name": locked_department_name,
        "selected": {
            "app_type": app_type.lower(),
            "user_type": user_type.lower(),
            "status": status.lower(),
            "department": department,
            "year": year,
            "q": q,
            "date_from": date_from.strftime("%Y-%m-%d") if date_from else "",
            "date_to": date_to.strftime("%Y-%m-%d") if date_to else "",
        },
    }
    return render(
        request,
        "data_center_management/dashboard/application_dashboard.html",
        context,
    )
