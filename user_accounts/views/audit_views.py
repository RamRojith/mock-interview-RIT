from datetime import datetime

from django.core.paginator import EmptyPage, Paginator
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from user_accounts.audit import (
    EVENT_CHOICES,
    daily_docx_absolute_path,
    daily_docx_url,
    event_label,
    load_log_entries,
    parse_entry_datetime,
)
from user_accounts.decorators import is_super_user, no_cache


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _docx_url_if_exists(log_date):
    if not log_date:
        return ""
    docx_path = daily_docx_absolute_path(log_date)
    if docx_path.exists():
        return daily_docx_url(log_date)
    return ""


def _matches_search(entry, query):
    haystack = " ".join(
        str(entry.get(key) or "")
        for key in [
            "username",
            "employee_id",
            "email",
            "role_name",
            "department_name",
            "path",
            "view_name",
            "model_name",
            "object_repr",
            "description",
            "app_label",
        ]
    ).lower()
    return query.lower() in haystack


@no_cache
@is_super_user("admin_management")
def system_audit_logs(request):
    today = timezone.localdate()
    return render(
        request,
        "admin/system_audit_logs.html",
        {
            "today": today.strftime("%Y-%m-%d"),
            "today_docx_url": _docx_url_if_exists(today),
            "event_choices": EVENT_CHOICES,
        },
    )


@no_cache
@is_super_user("admin_management")
def system_audit_logs_data(request):
    q = (request.GET.get("q") or "").strip()
    event_type = (request.GET.get("event_type") or "").strip()
    app_label = (request.GET.get("app_label") or "").strip()
    model_name = (request.GET.get("model_name") or "").strip()
    log_date = _parse_date(request.GET.get("log_date"))
    from_date = _parse_date(request.GET.get("from_date"))
    to_date = _parse_date(request.GET.get("to_date"))

    try:
        page = int(request.GET.get("page", 1))
    except Exception:
        page = 1

    try:
        page_size = int(request.GET.get("page_size", 25))
    except Exception:
        page_size = 25

    all_entries = load_log_entries(log_date=log_date, from_date=from_date, to_date=to_date)
    filtered_entries = list(all_entries)

    if event_type:
        filtered_entries = [entry for entry in filtered_entries if entry.get("event_type") == event_type]

    if app_label:
        filtered_entries = [entry for entry in filtered_entries if (entry.get("app_label") or "").lower() == app_label.lower()]

    if model_name:
        filtered_entries = [entry for entry in filtered_entries if (entry.get("model_name") or "").lower() == model_name.lower()]

    if q:
        filtered_entries = [entry for entry in filtered_entries if _matches_search(entry, q)]

    total = len(filtered_entries)
    login_count = len([entry for entry in filtered_entries if entry.get("event_type") == "login"])
    page_visit_count = len([entry for entry in filtered_entries if entry.get("event_type") == "page_visit"])
    change_count = len(
        [
            entry
            for entry in filtered_entries
            if entry.get("event_type") in {"data_create", "data_update", "data_delete"}
        ]
    )

    paginator = Paginator(filtered_entries, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages if paginator.num_pages else 1)

    start_index = (page_obj.number - 1) * page_size
    results = []
    for index, entry in enumerate(page_obj.object_list, start=1):
        created_local = parse_entry_datetime(entry)
        results.append(
            {
                "sno": start_index + index,
                "id": entry.get("id"),
                "created_at": created_local.strftime("%Y-%m-%d %I:%M:%S %p"),
                "event_type": entry.get("event_type", ""),
                "event_label": event_label(entry.get("event_type", "")),
                "username": entry.get("username") or "-",
                "employee_id": entry.get("employee_id") or "-",
                "email": entry.get("email") or "-",
                "role_name": entry.get("role_name") or "-",
                "department_name": entry.get("department_name") or "-",
                "path": entry.get("path") or "-",
                "view_name": entry.get("view_name") or "-",
                "app_label": entry.get("app_label") or "-",
                "model_name": entry.get("model_name") or "-",
                "object_repr": entry.get("object_repr") or "-",
                "description": entry.get("description") or "-",
                "status_code": entry.get("status_code") or "",
                "ip_address": entry.get("ip_address") or "-",
                "changed_fields": entry.get("changed_fields") or {},
            }
        )

    selected_docx_url = ""
    if log_date:
        selected_docx_url = _docx_url_if_exists(log_date)
    elif from_date and to_date and from_date == to_date:
        selected_docx_url = _docx_url_if_exists(from_date)

    app_options = sorted(
        {entry.get("app_label") for entry in all_entries if entry.get("app_label")}
    )
    model_options = sorted(
        {entry.get("model_name") for entry in all_entries if entry.get("model_name")}
    )

    return JsonResponse(
        {
            "results": results,
            "stats": {
                "total": total,
                "logins": login_count,
                "page_visits": page_visit_count,
                "changes": change_count,
            },
            "filters": {
                "app_options": app_options,
                "model_options": model_options,
            },
            "downloads": {
                "selected_docx_url": selected_docx_url,
                "today_docx_url": _docx_url_if_exists(timezone.localdate()),
            },
            "pagination": {
                "page": page_obj.number,
                "page_size": page_size,
                "total": total,
                "total_pages": paginator.num_pages,
                "has_next": page_obj.has_next(),
                "has_prev": page_obj.has_previous(),
            },
        }
    )
