from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

# Roles allowed to access the Faculty Mock Interview module. Only Faculty and
# Head of Department (HOD) are authorized. Every other ERP role is denied.
AUTHORIZED_FACULTY_MOCK_INTERVIEW_ROLES = frozenset({
    "faculty",
    "hod",
    "head of department",
    "head of the department",
})


def is_student_user(user):
    employee_id = str(getattr(user, "Employee_id", "") or "").strip()
    return bool(
        getattr(user, "is_authenticated", False)
        and getattr(user, "is_active", True)
        and getattr(user, "is_student", False)
        and employee_id
    )


def user_role_name(user):
    """Return the normalized (lowercased) ERP role name for a user."""
    role = getattr(user, "role", None)
    return str(getattr(role, "role", "") or "").strip().lower()


def is_faculty_or_hod(user):
    """Return True only for authorized users of the Faculty Mock Interview module.

    Only the Faculty and Head of Department (HOD) ERP roles may access the
    Faculty Mock Interview module. Superusers bypass role checks, matching the
    rest of the ERP RBAC. Students, parents, and every other ERP role are
    denied.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_student", False):
        return False
    if getattr(user, "is_parent", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return user_role_name(user) in AUTHORIZED_FACULTY_MOCK_INTERVIEW_ROLES


def student_identity(user):
    """Return database-safe identity fields for the authenticated ERP student."""
    if not is_student_user(user):
        raise PermissionDenied("A valid student Employee ID is required.")
    return {
        "student_employee_id": str(user.Employee_id).strip(),
        "student_name": str(getattr(user, "username", "") or "").strip()[:500],
    }


def student_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not getattr(request.user, "is_authenticated", False):
            return redirect_to_login(request.get_full_path())
        if not is_student_user(request.user):
            raise PermissionDenied("Mock interviews are available to students only.")
        return view_func(request, *args, **kwargs)

    return wrapped
