import json
import logging

from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST

from user_accounts.models import USER
from user_accounts.models import StudentDetails
from faculty_management.models import general_information
from course_management.models import AssignSubjectFaculty

from .chatbot_logic import ERPBot
from .question_catalog import build_question_groups


logger = logging.getLogger(__name__)
HISTORY_KEY = "erp_chat_history"
MAX_QUERY_LENGTH = 1200
MAX_HISTORY_MESSAGES = 40


def _chat_identity(request):
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return None

    employee_id = str(getattr(user, "Employee_id", "") or "").strip()
    is_admin = (
        bool(getattr(user, "is_superuser", False))
        or employee_id == "0000"
        or request.session.get("app_name") == "Admin Portal"
    )

    if not employee_id:
        return None
    if is_admin:
        return employee_id, "Admin"
    if bool(getattr(user, "is_parent", False)):
        return None
    if bool(getattr(user, "is_student", False)):
        return employee_id, "Student"

    role = getattr(getattr(user, "role", None), "role", None)
    role = str(role or "").strip()

    if not role:
        return None
    return employee_id, role


def _all_roles(employee_id, fallback_role):
    if fallback_role == "Student":
        return ["Student"]

    try:
        roles = list(
            USER.objects.using("rit_approval_system")
            .filter(Employee_id=employee_id, is_active=True)
            .exclude(role__role__isnull=True)
            .values_list("role__role", flat=True)
            .distinct()
        )
    except Exception:
        logger.warning("Unable to load all faculty roles", exc_info=True)
        roles = []

    # CA, Mentor, and subject responsibilities are operational assignments in
    # the academic database. They do not always have matching duplicate USER
    # rows in the approval database, so include them in the authorization set.
    try:
        faculty = general_information.objects.filter(
            faculty_id=str(employee_id)
        ).first()
        if faculty:
            active_students = StudentDetails.objects.filter(
                is_active=True,
                is_discontinued=False,
            )
            if active_students.filter(ca=faculty).exists():
                roles.append("Class Advisor")
            if active_students.filter(mentor=faculty).exists():
                roles.append("Mentor")
            if AssignSubjectFaculty.objects.filter(
                faculty=faculty, is_active=True
            ).exists():
                roles.append("Faculty")
    except Exception:
        logger.warning(
            "Unable to load academic role assignments for employee %s",
            employee_id,
            exc_info=True,
        )

    roles = list(dict.fromkeys(
        str(role).strip() for role in roles if str(role or "").strip()
    ))
    if fallback_role == "Admin":
        return ["Admin", *[role for role in roles if role != "Admin"]]
    return roles or [fallback_role]


def _resolve_effective_role(current_role, all_roles):
    """Resolve the highest-scope active ERP role without relying on role IDs."""
    roles = [str(role or "").strip() for role in all_roles if str(role or "").strip()]
    normalized = {" ".join(role.lower().split()): role for role in roles}

    role_precedence = [
        ({"admin", "administrator"}, "Admin"),
        ({"vice principal"}, "Vice Principal"),
        ({"hod", "head of department", "head of the department"}, "HOD"),
        ({"advisor", "ca", "class advisor"}, "Class Advisor"),
        ({"mentor"}, "Mentor"),
        ({"subject faculty", "subject teacher", "teacher", "faculty"}, "Faculty"),
    ]
    for aliases, canonical_role in role_precedence:
        if aliases.intersection(normalized):
            return canonical_role
    return str(current_role or "").strip()


def _error(message, status):
    return JsonResponse({"success": False, "error": message}, status=status)


def _append_history(request, role, content):
    history_items = request.session.get(HISTORY_KEY, [])
    history_items.append({"role": role, "content": content})
    request.session[HISTORY_KEY] = history_items[-MAX_HISTORY_MESSAGES:]
    request.session.modified = True


@require_http_methods(["GET"])
def questions(request):
    """Return quick questions allowed by the authenticated user's ERP roles."""
    identity = _chat_identity(request)
    if not identity:
        return _error("Authenticated ERP user access is required.", 403)

    employee_id, active_role = identity
    roles = _all_roles(employee_id, active_role)
    return JsonResponse({
        "success": True,
        "groups": build_question_groups(roles),
    })


@require_POST
def chat(request):
    identity = _chat_identity(request)
    if not identity:
        return _error("Authenticated ERP user access is required.", 403)

    try:
        payload = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error("Invalid JSON request.", 400)

    query = payload.get("query", "")
    if not isinstance(query, str):
        return _error("Query must be text.", 400)
    query = query.strip()
    if not query:
        return _error("Please enter a question.", 400)
    if len(query) > MAX_QUERY_LENGTH:
        return _error(f"Query cannot exceed {MAX_QUERY_LENGTH} characters.", 400)

    employee_id, active_role = identity
    all_roles = _all_roles(employee_id, active_role)
    rate_key = f"erp_chat_rate:{employee_id}"
    request_count = cache.get(rate_key, 0)
    if request_count >= 30:
        return _error("Too many requests. Please wait a minute and try again.", 429)
    if request_count:
        try:
            cache.incr(rate_key)
        except ValueError:
            cache.set(rate_key, 1, 60)
    else:
        cache.set(rate_key, 1, 60)

    greeted_key = f"chatbot_greeted_{employee_id}"
    is_first_message = not request.session.get(greeted_key, False)

    try:
        response_text = ERPBot(conversation_state=request.session).process_query(
            query,
            employee_id,
            role=active_role,
            all_roles=all_roles,
            is_first_message=is_first_message,
        )
    except Exception:
        logger.exception("ERP chatbot request failed for employee %s", employee_id)
        return _error("The ERP assistant could not complete that request. Please try again.", 500)

    request.session[greeted_key] = True
    _append_history(request, "user", query)
    _append_history(request, "assistant", response_text)

    return JsonResponse({"success": True, "response": response_text})


@require_http_methods(["GET", "DELETE"])
def history(request):
    if not _chat_identity(request):
        return _error("Authenticated ERP user access is required.", 403)

    if request.method == "DELETE":
        request.session.pop(HISTORY_KEY, None)
        for key in list(request.session.keys()):
            if key.startswith("chatbot_greeted_"):
                request.session.pop(key, None)
        request.session.modified = True
        return JsonResponse({"success": True, "history": []})

    return JsonResponse({
        "success": True,
        "history": request.session.get(HISTORY_KEY, []),
    })
