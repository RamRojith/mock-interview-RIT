from django.utils.deprecation import MiddlewareMixin

from user_accounts.audit import (
    append_audit_log,
    clear_current_request,
    get_actor_payload,
    get_request_details,
    set_current_request,
)


class AuditLogMiddleware(MiddlewareMixin):
    def process_request(self, request):
        set_current_request(request)

    def process_response(self, request, response):
        try:
            self._log_page_visit(request, response)
        finally:
            clear_current_request()
        return response

    def process_exception(self, request, exception):
        clear_current_request()
        return None

    def _log_page_visit(self, request, response):
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return

        if request.method != "GET":
            return

        if request.path.startswith("/static/") or request.path.startswith("/media/"):
            return

        content_type = (response.get("Content-Type", "") or "").split(";")[0].strip().lower()
        if content_type != "text/html":
            return

        details = get_request_details(request)
        actor = get_actor_payload(user)

        append_audit_log(
            event_type="page_visit",
            description=f"Visited {details['page_title']}",
            status_code=getattr(response, "status_code", None),
            **actor,
            **details,
        )
