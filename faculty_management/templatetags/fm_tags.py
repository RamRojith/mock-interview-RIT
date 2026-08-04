from django import template
from django.db.models import Q
from course_management.models import Regulations
from faculty_management.models import FacultyFunction, Announcement, general_information
from user_accounts.models import USER, Role
from user_accounts.models import StudentDetails

                                
register = template.Library()

@register.simple_tag
def regulations():
    return Regulations.objects.all()

@register.filter(name='replace_underscore')
def replace_underscore(value):
    return value.replace('_', ' ').title()

@register.simple_tag
def fm_current_function():
    view_name = fm_view_names()
    user_roles=Role.objects.using("rit_approval_system").filter().distinct()
    # # print("Roles => ", user_roles)
    data=[view_name,user_roles]
    return data

@register.simple_tag
def has_permission(role, function):
    permission_obj = (
        FacultyFunction.objects
        .filter(role=role, function=function)
        .order_by("-id")
        .first()
    )

    if permission_obj:
        return permission_obj.permission

    return False

from django.urls import get_resolver
from django.urls.resolvers import URLPattern
from faculty_management.fm_urls import fm_control_urls

def fm_view_names():
    resolver = get_resolver(fm_control_urls)
    view_names = []
    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLPattern):
            view_names.append(pattern.name)
    return view_names

# NEW: dict accessor for templates
@register.filter(name='get_item')
def get_item(d, key):
    try:
        return d.get(key)
    except Exception:
        return None

from django import template
from django.db.models import Q
from django.utils import timezone


# @register.simple_tag(takes_context=True)
# def get_user_announcements(context, limit=None):

#     # print("\n================ ANNOUNCEMENT DEBUG START ================\n")

#     request = context.get("request")
#     # print("Request => ", request)

#     if not request:
#         # print("❌ No request found in context")
#         return Announcement.objects.none()

#     # print("User Authenticated => ", request.user.is_authenticated)

#     if not request.user.is_authenticated:
#         # print("❌ User not authenticated")
#         return Announcement.objects.none()

#     user = request.user
#     # print("User => ", user)
#     # print("Employee ID => ", getattr(user, "Employee_id", None))

#     if not hasattr(user, 'Employee_id') or not user.Employee_id:
#         # print("❌ User has no Employee_id")
#         return Announcement.objects.none()

#     faculty_info = (
#         general_information.objects
#         .filter(faculty_id=user.Employee_id)
#         .select_related("department")
#         .first()
#     )

#     # print("Faculty Info => ", faculty_info)

#     if not faculty_info:
#         # print("❌ No faculty record found")
#         return Announcement.objects.none()

#     user_department = getattr(faculty_info, "department", None)
#     user_role = getattr(user, "role", None)

#     # print("User Department => ", user_department)
#     # print("User Role => ", user_role)

#     # ---------------- Visibility Query ----------------
#     query = Q()

#     if user_role:
#         # print("Adding Role Filter => roles__id =", user_role.id)
#         query |= Q(roles__id=user_role.id)

#     if user_department:
#         # print("Adding Department Filter => departments =", user_department)
#         query |= Q(departments=user_department)

#     # print("Adding User Specific Filter => users =", faculty_info)
#     query |= Q(users=faculty_info)

#     # print("Adding Global Announcement Filter")
#     query |= (
#         Q(roles__isnull=True) &
#         Q(departments__isnull=True) &
#         Q(users__isnull=True)
#     )

#     # print("Final Visibility Query => ", query)

#     # ---------------- Notify Window ----------------
#     # now = timezone.now()
#     now = timezone.localtime()
#     # print("Current Time => ", now)

#     notify_query = Q()

#     notify_query = (
#     (Q(notify_from__lte=now) | Q(notify_from__isnull=True)) &
#     (Q(notify_to__gte=now) | Q(notify_to__isnull=True))
# )
#     notify_query |= Q(notify_from__isnull=True)
#     notify_query |= Q(notify_to__isnull=True)

#     # print("Notify Query => ", notify_query)

#     # ---------------- Execute Query ----------------
#     announcements = (
#     Announcement.objects
#     .filter(query)
#     .filter(notify_query)
#     .filter(is_active=True)
#     .distinct()
#     .order_by("-created_at")
# )

#     # print("\nGenerated SQL Query =>")
#     # print(announcements.query)

#     # print("\nAnnouncements Count => ", announcements.count())

#     for a in announcements:
#         # print(
#             f"""
# Announcement ID: {a.id}
# Title: {a.title}
# Notify From: {a.notify_from}
# Notify To: {a.notify_to}
# Active: {a.is_active}
# Created At: {a.created_at}
# -----------------------------
# """
#         )

#     if limit:
#         # print("Applying Limit => ", limit)
#         announcements = announcements[:limit]

#     # print("\n================ ANNOUNCEMENT DEBUG END ================\n")

#     return announcements


# @register.simple_tag(takes_context=True)
# def get_user_announcements(context, limit=None):

#     request = context.get("request")
#     if not request or not request.user.is_authenticated:
#         return Announcement.objects.none()

#     user = request.user

#     if not hasattr(user, 'Employee_id') or not user.Employee_id:
#         return Announcement.objects.none()

#     faculty_info = (
#         general_information.objects
#         .filter(faculty_id=user.Employee_id)
#         .select_related("department")
#         .first()
#     )

#     if not faculty_info:
#         return Announcement.objects.none()

#     user_department = getattr(faculty_info, "department", None)
#     user_role = getattr(user, "role", None)

#     # ---------------- Visibility Query ----------------
#     query = Q()

#     if user_role:
#         query |= Q(roles__id=user_role.id)

#     if user_department:
#         query |= Q(departments=user_department)

#     query |= Q(users=faculty_info)

#     # Global announcements
#     query |= (
#         Q(roles__isnull=True) &
#         Q(departments__isnull=True) &
#         Q(users__isnull=True)
#     )

#     # ---------------- Notify Window ----------------
#     now = timezone.localtime()

#     notify_query = (
#         (Q(notify_from__lte=now) | Q(notify_from__isnull=True)) &
#         (Q(notify_to__gte=now) | Q(notify_to__isnull=True))
#     )

#     # ---------------- Execute Query ----------------
#     announcements = (
#         Announcement.objects
#         .filter(query)
#         .filter(notify_query)
#         .filter(is_active=True)
#         .distinct()
#         .order_by("-created_at")
#     )

#     if limit:
#         announcements = announcements[:limit]

#     return announcements

# @register.simple_tag(takes_context=True)
# def get_user_announcements(context, limit=None):

#     request = context.get("request")

#     if not request:
#         return Announcement.objects.none()

#     if not request.user.is_authenticated:
#         return Announcement.objects.none()

#     user = request.user

#     faculty_info = None
#     student_info = None
#     user_department = None
#     user_role = getattr(user, "role", None)

#     # ---------------- Identify User Type ----------------
#     if getattr(user, "is_student", False):

#         student_info = (
#             StudentDetails.objects
#             .filter(reg_no=user.Employee_id)
#             .select_related("department")
#             .first()
#         )

#         if not student_info:
#             return Announcement.objects.none()

#         user_department = getattr(student_info, "department", None)

#     elif user.is_staff:

#         if not hasattr(user, 'Employee_id') or not user.Employee_id:
#             return Announcement.objects.none()

#         faculty_info = (
#             general_information.objects
#             .filter(faculty_id=user.Employee_id)
#             .select_related("department")
#             .first()
#         )

#         if not faculty_info:
#             return Announcement.objects.none()

#         user_department = getattr(faculty_info, "department", None)
#         user_role = getattr(user, "role", None)

#     # ---------------- Visibility Query ----------------
#     query = Q()

#     if user_role:
#         query |= Q(roles__id=user_role.id)

#     if user_department:
#         query |= Q(departments=user_department)

#     if faculty_info:
#         query |= Q(users=faculty_info)

#     # Global announcements
#     query |= (
#         Q(roles__isnull=True) &
#         Q(departments__isnull=True) &
#         Q(users__isnull=True)
#     )

#     # ---------------- Notify Window ----------------
#     now = timezone.localtime()

#     notify_query = (
#         (Q(notify_from__lte=now) | Q(notify_from__isnull=True)) &
#         (Q(notify_to__gte=now) | Q(notify_to__isnull=True))
#     )

#     # ---------------- Execute Query ----------------
#     announcements = (
#         Announcement.objects
#         .filter(query)
#         .filter(notify_query)
#         .filter(is_active=True)
#         .distinct()
#         .order_by("-created_at")
#     )

#     if limit:
#         announcements = announcements[:limit]

#     return announcements


# @register.simple_tag(takes_context=True)
# def get_user_announcements(context, limit=None):
#     print("\n==================== get_user_announcements START ====================")

#     request = context.get("request")

#     if not request:
#         print("DEBUG: No request found in context.")
#         print("==================== END ====================\n")
#         return Announcement.objects.none()

#     if not request.user.is_authenticated:
#         print("DEBUG: User is not authenticated.")
#         print("==================== END ====================\n")
#         return Announcement.objects.none()

#     user = request.user
#     user_role = getattr(user, "role", None)
#     user_role_id = getattr(user_role, "id", None)
#     employee_id = getattr(user, "Employee_id", None)

#     print(f"DEBUG: Logged in user        : {user}")
#     print(f"DEBUG: Employee_id          : {employee_id}")
#     print(f"DEBUG: is_student           : {getattr(user, 'is_student', False)}")
#     print(f"DEBUG: role                 : {user_role}")
#     print(f"DEBUG: role_id              : {user_role_id}")

#     faculty_info = None
#     student_info = None
#     user_department = None

#     # ---------------- Identify User Type ----------------
#     if getattr(user, "is_student", False):
#         print("\n----- USER TYPE: STUDENT -----")

#         student_info = (
#             StudentDetails.objects
#             .filter(reg_no=employee_id)
#             .select_related("department")
#             .first()
#         )

#         print("DEBUG: student_info         :", student_info)

#         if not student_info:
#             print("DEBUG: No student_info found.")
#             print("==================== END ====================\n")
#             return Announcement.objects.none()

#         user_department = getattr(student_info, "department", None)

#         print("DEBUG: student department   :", user_department)

#     else:
#         print("\n----- USER TYPE: ROLE-BASED FACULTY/USER -----")

#         if not employee_id:
#             print("DEBUG: No Employee_id found.")
#             print("==================== END ====================\n")
#             return Announcement.objects.none()

#         faculty_info = (
#             general_information.objects
#             .filter(faculty_id=employee_id)
#             .select_related("department")
#             .first()
#         )

#         print("DEBUG: faculty_info         :", faculty_info)

#         if not faculty_info:
#             print("DEBUG: No faculty_info found.")
#             print("==================== END ====================\n")
#             return Announcement.objects.none()

#         user_department = getattr(faculty_info, "department", None)

#         print("DEBUG: faculty department   :", user_department)

#     # ---------------- Notify Window ----------------
#     now = timezone.localtime()

#     print("\n----- NOTIFY WINDOW -----")
#     print("DEBUG: Current time         :", now)

#     notify_query = (
#         (Q(notify_from__lte=now) | Q(notify_from__isnull=True)) &
#         (Q(notify_to__gte=now) | Q(notify_to__isnull=True))
#     )

#     print("DEBUG: notify_query         :", notify_query)

#     # ---------------- Visibility Logic ----------------
#     print("\n----- BUILDING VISIBILITY QUERY -----")
#     visibility_query = Q()

#     # 1. Global announcements
#     print("DEBUG: CASE 1 added -> Global announcements")
#     visibility_query |= (
#         Q(roles__isnull=True) &
#         Q(departments__isnull=True) &
#         Q(users__isnull=True)
#     )

#     # 2. Role only
#     if user_role_id:
#         print(f"DEBUG: CASE 2 added -> Role only | role_id={user_role_id}")
#         visibility_query |= (
#             Q(roles__id=user_role_id) &
#             Q(departments__isnull=True) &
#             Q(users__isnull=True)
#         )

#     # 3. Department only
#     if user_department:
#         print(f"DEBUG: CASE 3 added -> Department only | department={user_department}")
#         visibility_query |= (
#             Q(roles__isnull=True) &
#             Q(departments=user_department) &
#             Q(users__isnull=True)
#         )

#     # 4. User only
#     if faculty_info:
#         print(f"DEBUG: CASE 4 added -> User only | faculty={faculty_info}")
#         visibility_query |= (
#             Q(roles__isnull=True) &
#             Q(departments__isnull=True) &
#             Q(users=faculty_info)
#         )

#     # 5. Role + Department
#     if user_role_id and user_department:
#         print(f"DEBUG: CASE 5 added -> Role + Department | role_id={user_role_id}, department={user_department}")
#         visibility_query |= (
#             Q(roles__id=user_role_id) &
#             Q(departments=user_department) &
#             Q(users__isnull=True)
#         )

#     # 6. Role + User
#     if user_role_id and faculty_info:
#         print(f"DEBUG: CASE 6 added -> Role + User | role_id={user_role_id}, faculty={faculty_info}")
#         visibility_query |= (
#             Q(roles__id=user_role_id) &
#             Q(departments__isnull=True) &
#             Q(users=faculty_info)
#         )

#     # 7. Department + User
#     if user_department and faculty_info:
#         print(f"DEBUG: CASE 7 added -> Department + User | department={user_department}, faculty={faculty_info}")
#         visibility_query |= (
#             Q(roles__isnull=True) &
#             Q(departments=user_department) &
#             Q(users=faculty_info)
#         )

#     # 8. Role + Department + User
#     if user_role_id and user_department and faculty_info:
#         print(
#             f"DEBUG: CASE 8 added -> Role + Department + User | "
#             f"role_id={user_role_id}, department={user_department}, faculty={faculty_info}"
#         )
#         visibility_query |= (
#             Q(roles__id=user_role_id) &
#             Q(departments=user_department) &
#             Q(users=faculty_info)
#         )

#     print("\nDEBUG: Final visibility_query :", visibility_query)

#     # ---------------- Execute Query ----------------
#     print("\n----- EXECUTING FINAL QUERY -----")

#     announcements = (
#         Announcement.objects
#         .filter(visibility_query)
#         .filter(notify_query)
#         .filter(is_active=True)
#         .distinct()
#         .order_by("-created_at")
#     )

#     print("DEBUG: Matching announcements count before limit:", announcements.count())

#     for ann in announcements:
#         print(
#             f"DEBUG: MATCHED -> ID={ann.id}, "
#             f"Title={getattr(ann, 'title', '')}, "
#             f"Created={getattr(ann, 'created_at', None)}"
#         )

#     if limit:
#         print(f"DEBUG: Applying limit = {limit}")
#         announcements = announcements[:limit]

#     print("==================== get_user_announcements END ====================\n")
#     return announcements



@register.simple_tag(takes_context=True)
def get_user_announcements(context, limit=None):
    request = context.get("request")

    if not request or not request.user.is_authenticated:
        return Announcement.objects.none()

    user = request.user
    user_role = getattr(user, "role", None)
    user_role_id = getattr(user_role, "id", None)
    employee_id = getattr(user, "Employee_id", None)

    faculty_info = None
    student_info = None
    user_department = None

    # ---------------- Identify User Type ----------------
    if getattr(user, "is_student", False):
        student_info = (
            StudentDetails.objects
            .filter(reg_no=employee_id)
            .select_related("department")
            .first()
        )

        if not student_info:
            return Announcement.objects.none()

        user_department = getattr(student_info, "department", None)

    else:
        if not employee_id:
            return Announcement.objects.none()

        faculty_info = (
            general_information.objects
            .filter(faculty_id=employee_id)
            .select_related("department")
            .first()
        )

        if not faculty_info:
            return Announcement.objects.none()

        user_department = getattr(faculty_info, "department", None)

    # ---------------- Notify Window ----------------
    now = timezone.localtime()

    notify_query = (
        (Q(notify_from__lte=now) | Q(notify_from__isnull=True)) &
        (Q(notify_to__gte=now) | Q(notify_to__isnull=True))
    )

    # ---------------- Visibility Logic ----------------
    visibility_query = Q()

    # 1. Global announcements
    visibility_query |= (
        Q(roles__isnull=True) &
        Q(departments__isnull=True) &
        Q(users__isnull=True)
    )

    # 2. Role only
    if user_role_id:
        visibility_query |= (
            Q(roles__id=user_role_id) &
            Q(departments__isnull=True) &
            Q(users__isnull=True)
        )

    # 3. Department only
    if user_department:
        visibility_query |= (
            Q(roles__isnull=True) &
            Q(departments=user_department) &
            Q(users__isnull=True)
        )

    # 4. User only
    if faculty_info:
        visibility_query |= (
            Q(roles__isnull=True) &
            Q(departments__isnull=True) &
            Q(users=faculty_info)
        )

    # 5. Role + Department
    if user_role_id and user_department:
        visibility_query |= (
            Q(roles__id=user_role_id) &
            Q(departments=user_department) &
            Q(users__isnull=True)
        )

    # 6. Role + User
    if user_role_id and faculty_info:
        visibility_query |= (
            Q(roles__id=user_role_id) &
            Q(departments__isnull=True) &
            Q(users=faculty_info)
        )

    # 7. Department + User
    if user_department and faculty_info:
        visibility_query |= (
            Q(roles__isnull=True) &
            Q(departments=user_department) &
            Q(users=faculty_info)
        )

    # 8. Role + Department + User
    if user_role_id and user_department and faculty_info:
        visibility_query |= (
            Q(roles__id=user_role_id) &
            Q(departments=user_department) &
            Q(users=faculty_info)
        )

    # ---------------- Execute Query ----------------
    announcements = (
        Announcement.objects
        .filter(visibility_query)
        .filter(notify_query)
        .filter(is_active=True)
        .distinct()
        .order_by("-created_at")
    )

    if limit:
        announcements = announcements[:limit]

    return announcements


