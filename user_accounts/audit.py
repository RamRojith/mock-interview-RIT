from __future__ import annotations

import json
import socket
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from threading import local
from uuid import uuid4
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from django.conf import settings
from django.utils import timezone


_audit_local = local()
SENSITIVE_FIELD_NAMES = {"password", "token", "secret", "api_key", "csrfmiddlewaretoken"}
DOCX_JSON_PATH = "customXml/audit-log.json"
EVENT_CHOICES = (
    ("login", "Login"),
    ("logout", "Logout"),
    ("page_visit", "Page Visit"),
    ("data_create", "Data Create"),
    ("data_update", "Data Update"),
    ("data_delete", "Data Delete"),
)
EVENT_LABELS = dict(EVENT_CHOICES)


def set_current_request(request):
    _audit_local.request = request


def get_current_request():
    return getattr(_audit_local, "request", None)


def clear_current_request():
    if hasattr(_audit_local, "request"):
        delattr(_audit_local, "request")


def serialize_value(value):
    if value is None:
        return None
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (int, float, bool, str)):
        return value
    if isinstance(value, dict):
        return {str(key): serialize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [serialize_value(item) for item in value]
    if hasattr(value, "name"):
        return getattr(value, "name", "") or str(value)
    return str(value)


def _is_sensitive(field_name: str) -> bool:
    lowered = (field_name or "").lower()
    return any(token in lowered for token in SENSITIVE_FIELD_NAMES)


def model_snapshot(instance):
    data = {}
    for field in instance._meta.concrete_fields:
        field_name = field.name
        value_name = field.attname if getattr(field, "is_relation", False) else field_name

        if _is_sensitive(field_name):
            data[field_name] = "[REDACTED]"
            continue

        try:
            value = getattr(instance, value_name)
        except Exception:
            value = None

        data[field_name] = serialize_value(value)
    return data


def diff_snapshots(old_data, new_data):
    changed = {}
    all_keys = set(old_data.keys()) | set(new_data.keys())
    for key in sorted(all_keys):
        old_value = old_data.get(key)
        new_value = new_data.get(key)
        if old_value != new_value:
            changed[key] = {
                "from": old_value,
                "to": new_value,
            }
    return changed


def resolve_client_ip(request):
    for header_name in ("HTTP_X_FORWARDED_FOR", "HTTP_X_REAL_IP", "HTTP_CF_CONNECTING_IP"):
        header_value = (request.META.get(header_name, "") or "").strip()
        if header_value:
            if header_name == "HTTP_X_FORWARDED_FOR":
                return header_value.split(",")[0].strip()
            return header_value

    remote_addr = (request.META.get("REMOTE_ADDR", "") or "").strip()
    if remote_addr in {"127.0.0.1", "::1", "localhost"}:
        lan_ip = resolve_local_network_ip()
        return lan_ip or remote_addr
    return remote_addr


def resolve_local_network_ip():
    try:
        hostname = socket.gethostname()
        host_info = socket.gethostbyname_ex(hostname)
        for ip_address in host_info[2]:
            if ip_address and not ip_address.startswith("127."):
                return ip_address
    except Exception:
        pass

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("10.255.255.255", 1))
            ip_address = sock.getsockname()[0]
            if ip_address and not ip_address.startswith("127."):
                return ip_address
    except Exception:
        pass

    return ""


def get_actor_payload(user):
    role = getattr(user, "role", None)
    department = getattr(user, "Department", None)
    return {
        "user_id": getattr(user, "pk", None) or getattr(user, "id", None),
        "employee_id": getattr(user, "Employee_id", "") or "",
        "username": getattr(user, "username", "") or str(user),
        "email": getattr(user, "email", "") or "",
        "role_name": getattr(role, "role", "") or getattr(role, "name", "") or "",
        "department_name": getattr(department, "Department", "") or "",
    }


def get_request_details(request):
    resolver_match = getattr(request, "resolver_match", None)
    view_name = ""
    app_label = ""

    if resolver_match:
        view_name = resolver_match.view_name or resolver_match.url_name or ""
        func = getattr(resolver_match, "func", None)
        module_name = getattr(func, "__module__", "")
        app_label = module_name.split(".", 1)[0] if module_name else ""

    if not app_label:
        app_label = request.path.strip("/").split("/", 1)[0] or "home"

    session_key = ""
    if hasattr(request, "session"):
        session_key = request.session.session_key or ""

    return {
        "path": request.path,
        "method": request.method,
        "view_name": view_name,
        "page_title": humanize_label(view_name or request.path),
        "app_label": app_label,
        "session_key": session_key,
        "ip_address": resolve_client_ip(request),
        "user_agent": request.META.get("HTTP_USER_AGENT", ""),
    }


def humanize_label(value):
    cleaned = (value or "").strip().strip("/")
    if not cleaned:
        return "Home"
    last_bit = cleaned.split(":")[-1].split("/")[-1]
    return last_bit.replace("_", " ").replace("-", " ").title()


def should_track_model(sender):
    meta = getattr(sender, "_meta", None)
    if not meta:
        return False
    if meta.app_label.startswith("django"):
        return False
    if meta.app_label == "sessions":
        return False
    if meta.app_label == "contenttypes":
        return False
    if meta.app_label == "admin":
        return False
    if meta.app_label == "user_accounts" and meta.model_name == "auditlog":
        return False
    return True


def event_label(event_type: str) -> str:
    return EVENT_LABELS.get(event_type, humanize_label(event_type))


def daily_docx_relative_path(log_date: date) -> Path:
    return Path("logs") / log_date.strftime("%Y") / log_date.strftime("%m") / f"{log_date.strftime('%d')}.docx"


def daily_docx_absolute_path(log_date: date) -> Path:
    return Path(settings.MEDIA_ROOT) / daily_docx_relative_path(log_date)


def daily_docx_url(log_date: date) -> str:
    relative = str(daily_docx_relative_path(log_date)).replace("\\", "/")
    return f"{settings.MEDIA_URL.rstrip('/')}/{relative}"


def format_changed_fields(changed_fields):
    if not changed_fields:
        return ""

    parts = []
    for field_name, change in changed_fields.items():
        old_value = serialize_value(change.get("from"))
        new_value = serialize_value(change.get("to"))
        parts.append(f"{field_name}: {old_value} -> {new_value}")
    return " | ".join(parts)


def _xml_escape(value):
    return escape("" if value is None else str(value))


def _paragraph_xml(
    text: str,
    *,
    bold: bool = False,
    size: int | None = None,
    color: str | None = None,
    spacing_before: int | None = None,
    spacing_after: int | None = None,
    jc: str | None = None,
):
    text = text or ""
    lines = text.splitlines() or [""]
    paragraph_props = []
    if spacing_before is not None or spacing_after is not None or jc:
        spacing_bits = []
        if spacing_before is not None:
            spacing_bits.append(f'w:before="{spacing_before}"')
        if spacing_after is not None:
            spacing_bits.append(f'w:after="{spacing_after}"')
        spacing_xml = f"<w:spacing {' '.join(spacing_bits)}/>" if spacing_bits else ""
        jc_xml = f'<w:jc w:val="{jc}"/>' if jc else ""
        paragraph_props.append(f"<w:pPr>{spacing_xml}{jc_xml}</w:pPr>")

    run_parts = []
    for index, line in enumerate(lines):
        escaped_line = _xml_escape(line)
        run_style = []
        if bold:
            run_style.append("<w:b/>")
        if size is not None:
            run_style.append(f'<w:sz w:val="{size}"/>')
        if color:
            run_style.append(f'<w:color w:val="{color}"/>')
        style_xml = f"<w:rPr>{''.join(run_style)}</w:rPr>" if run_style else ""
        run_parts.append(f"<w:r>{style_xml}<w:t xml:space=\"preserve\">{escaped_line}</w:t></w:r>")
        if index != len(lines) - 1:
            run_parts.append("<w:r><w:br/></w:r>")
    return f"<w:p>{''.join(paragraph_props)}{''.join(run_parts)}</w:p>"


def _separator_xml():
    return (
        "<w:p>"
        "<w:pPr><w:spacing w:before=\"60\" w:after=\"120\"/></w:pPr>"
        "<w:r><w:rPr><w:color w:val=\"D7E3F4\"/><w:sz w:val=\"8\"/></w:rPr>"
        "<w:t>______________________________________________________________</w:t>"
        "</w:r>"
        "</w:p>"
    )


def _count_events(entries):
    counts = {key: 0 for key, _ in EVENT_CHOICES}
    for entry in entries:
        event_type = entry.get("event_type", "")
        if event_type in counts:
            counts[event_type] += 1
    return counts


def _build_docx_document_xml(entries, log_date: date):
    counts = _count_events(entries)
    generated_at = timezone.localtime().strftime("%d-%m-%Y %I:%M %p")
    body_parts = [
        _paragraph_xml(
            "RAMCO ERP - SYSTEM AUDIT REPORT",
            bold=True,
            size=34,
            color="173B7A",
            spacing_after=90,
            jc="center",
        ),
        _paragraph_xml(
            f"Daily activity register for {log_date.strftime('%d %B %Y')}",
            size=22,
            color="4C627A",
            spacing_after=180,
            jc="center",
        ),
        _paragraph_xml(
            f"Generated on {generated_at}",
            bold=True,
            size=18,
            color="6A7F95",
            spacing_after=260,
            jc="center",
        ),
        _paragraph_xml(
            "Executive Summary",
            bold=True,
            size=24,
            color="173B7A",
            spacing_before=120,
            spacing_after=120,
        ),
        _paragraph_xml(
            f"Total Entries: {len(entries)} | "
            f"Logins: {counts['login']} | "
            f"Logouts: {counts['logout']} | "
            f"Page Visits: {counts['page_visit']} | "
            f"Data Creates: {counts['data_create']} | "
            f"Data Updates: {counts['data_update']} | "
            f"Data Deletes: {counts['data_delete']}",
            size=19,
            color="34495E",
            spacing_after=220,
        ),
        _paragraph_xml(
            "Detailed Event Trail",
            bold=True,
            size=24,
            color="173B7A",
            spacing_before=100,
            spacing_after=160,
        ),
    ]

    for index, entry in enumerate(entries, start=1):
        created_at = parse_entry_datetime(entry)
        event_type = entry.get("event_type", "")
        username = entry.get("username") or "Unknown User"
        employee_id = entry.get("employee_id") or ""
        role_name = entry.get("role_name") or "Not specified"
        department_name = entry.get("department_name") or "Not specified"
        ip_address = entry.get("ip_address") or "Not captured"
        path = entry.get("path") or "Not captured"
        view_name = entry.get("view_name") or "Not captured"
        model_name = entry.get("model_name") or ""
        app_label = entry.get("app_label") or ""
        object_repr = entry.get("object_repr") or "Not captured"
        status_code = entry.get("status_code") or "N/A"

        heading = f"{index:02d}. {event_label(event_type)}  |  {created_at.strftime('%I:%M:%S %p')}  |  {username}"
        if employee_id:
            heading = f"{heading} ({employee_id})"

        body_parts.append(
            _paragraph_xml(
                heading,
                bold=True,
                size=21,
                color="173B7A",
                spacing_before=120,
                spacing_after=60,
            )
        )
        body_parts.append(
            _paragraph_xml(
                f"Role: {role_name} | Department: {department_name} | HTTP Status: {status_code}",
                size=18,
                color="42566B",
                spacing_after=40,
            )
        )
        body_parts.append(
            _paragraph_xml(
                f"View: {view_name} | Path: {path}",
                size=18,
                color="42566B",
                spacing_after=40,
            )
        )
        body_parts.append(
            _paragraph_xml(
                f"Model Context: {(app_label + '.' + model_name).strip('.')} | Record: {object_repr}",
                size=18,
                color="42566B",
                spacing_after=40,
            )
        )
        body_parts.append(
            _paragraph_xml(
                f"Source IP: {ip_address}",
                size=18,
                color="42566B",
                spacing_after=70,
            )
        )
        if entry.get("description"):
            body_parts.append(
                _paragraph_xml(
                    f"Description: {entry['description']}",
                    size=19,
                    color="1E2E3E",
                    spacing_after=70,
                )
            )

        changed_summary = format_changed_fields(entry.get("changed_fields") or {})
        if changed_summary:
            body_parts.append(
                _paragraph_xml(
                    f"Field Changes: {changed_summary}",
                    size=18,
                    color="7A4E00",
                    spacing_after=120,
                )
            )

        body_parts.append(_separator_xml())

    body_xml = "".join(body_parts)
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">"
        f"<w:body>{body_xml}"
        "<w:sectPr>"
        "<w:pgSz w:w=\"12240\" w:h=\"15840\"/>"
        "<w:pgMar w:top=\"1440\" w:right=\"1440\" w:bottom=\"1440\" w:left=\"1440\" "
        "w:header=\"708\" w:footer=\"708\" w:gutter=\"0\"/>"
        "</w:sectPr>"
        "</w:body></w:document>"
    )


def _build_docx_payload(entries):
    return json.dumps({"entries": entries}, ensure_ascii=False, indent=2)


def write_daily_docx(log_date: date, entries):
    target_path = daily_docx_absolute_path(log_date)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    normalized_entries = sorted(entries, key=lambda item: item.get("created_at", ""))

    content_types_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
        "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
        "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
        "<Default Extension=\"json\" ContentType=\"application/json\"/>"
        "<Override PartName=\"/word/document.xml\" "
        "ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>"
        "</Types>"
    )
    rels_xml = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
        "<Relationship Id=\"rId1\" "
        "Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" "
        "Target=\"word/document.xml\"/>"
        "</Relationships>"
    )
    document_xml = _build_docx_document_xml(normalized_entries, log_date)
    json_payload = _build_docx_payload(normalized_entries)

    with ZipFile(target_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("_rels/.rels", rels_xml)
        archive.writestr("word/document.xml", document_xml)
        archive.writestr(DOCX_JSON_PATH, json_payload)


def _normalize_entry(entry):
    normalized = {
        "id": entry.get("id") or uuid4().hex,
        "created_at": entry.get("created_at") or timezone.now().isoformat(),
        "event_type": entry.get("event_type", ""),
        "user_id": serialize_value(entry.get("user_id")),
        "employee_id": serialize_value(entry.get("employee_id")) or "",
        "username": serialize_value(entry.get("username")) or "",
        "email": serialize_value(entry.get("email")) or "",
        "role_name": serialize_value(entry.get("role_name")) or "",
        "department_name": serialize_value(entry.get("department_name")) or "",
        "session_key": serialize_value(entry.get("session_key")) or "",
        "ip_address": serialize_value(entry.get("ip_address")) or "",
        "user_agent": serialize_value(entry.get("user_agent")) or "",
        "path": serialize_value(entry.get("path")) or "",
        "method": serialize_value(entry.get("method")) or "",
        "view_name": serialize_value(entry.get("view_name")) or "",
        "page_title": serialize_value(entry.get("page_title")) or "",
        "app_label": serialize_value(entry.get("app_label")) or "",
        "model_name": serialize_value(entry.get("model_name")) or "",
        "object_pk": serialize_value(entry.get("object_pk")) or "",
        "object_repr": serialize_value(entry.get("object_repr")) or "",
        "description": serialize_value(entry.get("description")) or "",
        "changed_fields": serialize_value(entry.get("changed_fields") or {}),
        "metadata": serialize_value(entry.get("metadata") or {}),
        "status_code": serialize_value(entry.get("status_code")),
    }
    return normalized


def load_daily_log_entries(log_date: date):
    docx_path = daily_docx_absolute_path(log_date)
    if not docx_path.exists():
        return []

    try:
        with ZipFile(docx_path, "r") as archive:
            if DOCX_JSON_PATH not in archive.namelist():
                return []
            payload = archive.read(DOCX_JSON_PATH).decode("utf-8")
            data = json.loads(payload)
    except Exception:
        return []

    return [_normalize_entry(entry) for entry in data.get("entries", [])]


def append_audit_log(**kwargs):
    now = timezone.localtime()
    entry = _normalize_entry(
        {
            **kwargs,
            "id": kwargs.get("id") or f"{now.strftime('%Y%m%d%H%M%S%f')}-{uuid4().hex[:8]}",
            "created_at": kwargs.get("created_at") or now.isoformat(),
        }
    )
    log_date = parse_entry_datetime(entry).date()
    entries = load_daily_log_entries(log_date)
    entries.append(entry)
    write_daily_docx(log_date, entries)
    return entry


def parse_entry_datetime(entry):
    value = entry.get("created_at")
    if isinstance(value, datetime):
        dt_value = value
    else:
        try:
            dt_value = datetime.fromisoformat(value)
        except Exception:
            dt_value = timezone.now()

    if timezone.is_naive(dt_value):
        dt_value = timezone.make_aware(dt_value, timezone.get_current_timezone())
    return timezone.localtime(dt_value)


def load_log_entries(log_date=None, from_date=None, to_date=None):
    base_path = Path(settings.MEDIA_ROOT) / "logs"
    if not base_path.exists():
        return []

    if log_date:
        entries = load_daily_log_entries(log_date)
        return sorted(entries, key=lambda item: item.get("created_at", ""), reverse=True)

    docx_files = sorted(base_path.rglob("*.docx"), reverse=True)
    collected = []
    for docx_file in docx_files:
        try:
            file_date = date(
                int(docx_file.parent.parent.name),
                int(docx_file.parent.name),
                int(docx_file.stem),
            )
        except Exception:
            continue

        if from_date and file_date < from_date:
            continue
        if to_date and file_date > to_date:
            continue

        collected.extend(load_daily_log_entries(file_date))

    return sorted(collected, key=lambda item: item.get("created_at", ""), reverse=True)
