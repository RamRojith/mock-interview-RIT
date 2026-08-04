"""
Shared helpers for the stock_management app.
Follows the same conventions as data_center_management (session role lookup, etc.).
"""
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from user_accounts.models import USER, Role
from faculty_management.models import general_information
from stock_management.models import Notification, StockAuditLog

APPROVAL_DB = "rit_approval_system"


# ------------------------------------------------------------------
# Logged-in user resolution
# ------------------------------------------------------------------
def get_logged_in_faculty(request):
    email = (getattr(request.user, "email", "") or "").strip()
    if not email:
        return None
    return (
        general_information.objects
        .filter(college_email__iexact=email)
        .select_related("department", "designation")
        .first()
    )


def get_logged_in_role_obj(request):
    user = request.user
    cr_user = (
        USER.objects.using(APPROVAL_DB)
        .filter(email=getattr(user, "email", ""))
        .select_related("role")
        .first()
    )
    return cr_user.role if cr_user else None


def get_role_name(request):
    role = get_logged_in_role_obj(request)
    name = (getattr(role, "role", "") or "")
    # fall back to the local user's role if the approval DB has nothing
    if not name:
        local_role = getattr(request.user, "role", None)
        name = getattr(local_role, "role", "") or ""
    return name.upper()


# ------------------------------------------------------------------
# Role gate helpers (superuser passes all gates)
# ------------------------------------------------------------------
def is_super(request):
    return bool(getattr(request.user, "is_superuser", False))


def is_principal(request):
    return is_super(request) or "PRINCIPAL" in get_role_name(request)


def is_hod(request):
    n = get_role_name(request)
    return is_super(request) or "HOD" in n or "HEAD" in n


def is_iso(request):
    return is_super(request) or "ISO" in get_role_name(request)


def is_incharge(request):
    return is_super(request) or "INCHARGE" in get_role_name(request)


def is_faculty(request):
    return is_super(request) or "FACULTY" in get_role_name(request) or "STAFF" in get_role_name(request)


# ------------------------------------------------------------------
# Department / asset-tag helpers
# ------------------------------------------------------------------
def dept_code(department):
    if not department:
        return "GEN"
    # Add_Department stores the code in `Department_code`
    code = getattr(department, "Department_code", None) or getattr(department, "code", None)
    if code:
        return str(code).upper()
    name = getattr(department, "Department", "") or getattr(department, "name", "") or "GEN"
    return "".join(name.split())[:4].upper() or "GEN"


def current_financial_year():
    today = timezone.localdate()
    if today.month >= 4:  # Apr - Mar financial year
        return f"{today.year}-{str(today.year + 1)[-2:]}"
    return f"{today.year - 1}-{str(today.year)[-2:]}"


def generate_asset_tag(entry, index):
    """RIT-{DEPT}-{YYYY}-{NNNN} unique per department per year."""
    from stock_management.models import StockItem
    dept = entry.register.lab.department
    dc = dept_code(dept)
    year = timezone.localdate().year
    prefix = f"RIT-{dc}-{year}-"
    last = (
        StockItem.objects.filter(asset_tag__startswith=prefix)
        .order_by("-asset_tag").first()
    )
    if last and last.asset_tag.split("-")[-1].isdigit():
        start = int(last.asset_tag.split("-")[-1])
    else:
        start = 0
    return f"{prefix}{start + index:04d}"


# ------------------------------------------------------------------
# Notifications & audit
# ------------------------------------------------------------------
def notify(recipient, notification_type, title, message, action_url=None, target=None):
    if not recipient:
        return None
    ct = None
    oid = None
    if target is not None:
        ct = ContentType.objects.get_for_model(target.__class__)
        oid = target.pk
    return Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        action_url=action_url,
        content_type=ct,
        object_id=oid,
    )


def get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def audit(request, action, target=None, previous_status=None, new_status=None, remarks=None):
    actor = get_logged_in_faculty(request)
    ct = None
    oid = None
    if target is not None:
        ct = ContentType.objects.get_for_model(target.__class__)
        oid = target.pk
    return StockAuditLog.objects.create(
        actor=actor,
        action=action,
        content_type=ct,
        object_id=oid,
        previous_status=previous_status,
        new_status=new_status,
        remarks=remarks,
        ip_address=get_client_ip(request),
    )
