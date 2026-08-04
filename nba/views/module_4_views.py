# nba/views.py
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
import re

from nba.models import EnrolmentRatioFirstYear, SanctionedIntake
from user_accounts.models import Add_Department
from student_management.models import StudentDetails
from user_accounts.decorators import check_permission

from nba.utils.utils_intake import get_effective_intake, _to_year_int

# ==========================
# Utility: Extract year safely
# ==========================
YEAR_RE = re.compile(r"^(19|20)\d{2}")

def get_batches_by_department(request):
    """
    JSON API:
    Returns distinct admission years (start years) for a given department
    from StudentDetails.batch.

    Example output:
    { "batches": [2025, 2024, 2023] }
    """
    dept_id = request.GET.get("department_id")
    if not dept_id:
        return JsonResponse({"batches": []})

    raw_batches = (
        StudentDetails.objects
        .filter(department_id=dept_id)
        .values_list("batch", flat=True)
        .distinct()
    )

    parsed_years = []
    for val in raw_batches:
        if not val:
            continue
        s = str(val).strip()
        m = YEAR_RE.match(s)
        if m:
            try:
                parsed_years.append(int(m.group(0)))
            except ValueError:
                continue

    parsed_years = sorted(set(parsed_years), reverse=True)
    return JsonResponse({"batches": parsed_years})


def get_intake_snapshot(request):
    """
    GET params:
      - department_id (required)
      - cay_start_year (required, int)

    Returns:
    {
      "ok": true,
      "cay":   {"year": 2024, "label": "2024-25", "intake": 180, "source_year": 2023},
      "caym1": {"year": 2023, "label": "2023-24", "intake": 180, "source_year": 2023},
      "caym2": {"year": 2022, "label": "2022-23", "intake": 120, "source_year": 2021}
    }
    """
    dept_id = request.GET.get("department_id")
    cay_start_year = request.GET.get("cay_start_year")

    if not dept_id or not cay_start_year:
        return JsonResponse({"ok": False, "error": "department_id and cay_start_year are required"}, status=400)

    try:
        dept = Add_Department.objects.select_related("degree").get(pk=dept_id)
    except Add_Department.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Invalid department_id"}, status=404)

    y0 = _to_year_int(cay_start_year)
    if y0 is None:
        return JsonResponse({"ok": False, "error": "Invalid cay_start_year"}, status=400)

    degree_id = dept.degree_id or None

    def end_short(y): return str((y + 1) % 100).zfill(2)
    def mk_label(y): return f"{y}-{end_short(y)}"

    # Compute intake + source year chosen
    def snapshot_for(target_y):
        qs = (SanctionedIntake.objects
              .filter(department_id=dept.id, degree_id=degree_id)
              .values("year", "sanctioned_intake"))

        best_year = None
        best_intake = 0
        for row in qs:
            y = _to_year_int(row.get("year"))
            if y is None:
                continue
            if y <= target_y and (best_year is None or y > best_year):
                best_year = y
                best_intake = int(row.get("sanctioned_intake") or 0)

        return {
            "year": target_y,
            "label": mk_label(target_y),
            "intake": best_intake,
            "source_year": best_year
        }

    data = {
        "ok": True,
        "cay": snapshot_for(y0),
        "caym1": snapshot_for(y0 - 1),
        "caym2": snapshot_for(y0 - 2),
    }
    return JsonResponse(data, status=200)


# ==================================
# New: Past enrolments API (for dynamic cards on dept selection)
# ==================================

def get_past_enrolments(request):
    """
    GET ?department_id=<id>
    Returns last 10 enrolment rows for a department as JSON (newest first).
    """
    dept_id = request.GET.get("department_id")
    if not dept_id:
        return JsonResponse({"ok": False, "error": "department_id is required"}, status=400)

    qs = (EnrolmentRatioFirstYear.objects
          .filter(department_id=dept_id)
          .order_by("-id")[:10])

    def serialize(e):
        return {
            "id": e.id,
            "academic_year_range": e.academic_year_range,
            "average_er": e.average_er,
            "er_cay": e.er_cay,
            "er_caym1": e.er_caym1,
            "er_caym2": e.er_caym2,
            "sanctioned_intake_cay": e.sanctioned_intake_cay,
            "sanctioned_intake_caym1": e.sanctioned_intake_caym1,
            "sanctioned_intake_caym2": e.sanctioned_intake_caym2,
            "marks_awarded": e.marks_awarded,
            "is_verified": bool(e.is_verified),
            "admin_remarks": e.admin_remarks or "",
        }

    return JsonResponse({"ok": True, "entries": [serialize(e) for e in qs]}, status=200)


# ==================================
# Main view: Enrolment Ratio form (submission-only; no admin verification)
# ==================================
@check_permission("nba_students_performance")
def add_enrolment_ratio(request):
    departments = Add_Department.objects.filter(is_active=True)

    # Track which department is in focus (for initial render)
    selected_dept_id = request.POST.get("department") or request.GET.get("department") or None

    latest_entry = None
    past_entries = []

    if selected_dept_id:
        try:
            sel_dept = Add_Department.objects.get(pk=selected_dept_id)
        except Add_Department.DoesNotExist:
            sel_dept = None

        if sel_dept:
            qs = EnrolmentRatioFirstYear.objects.filter(department=sel_dept).order_by("-id")
            latest_entry = qs.first()
            past_entries = list(qs[:10])  # for cards at the bottom (initial history; JS can replace via API)

    if request.method == "POST":
        dept_id = request.POST.get("department")
        if not dept_id:
            messages.error(request, "Department is required.")
            return redirect("add_enrolment_ratio")

        try:
            dept = Add_Department.objects.select_related("degree").get(pk=dept_id)
        except Add_Department.DoesNotExist:
            messages.error(request, "Invalid department.")
            return redirect("add_enrolment_ratio")

        # Labels
        academic_year_range = request.POST.get("academic_year_range")
        cay_label  = request.POST.get("cay_year_label") or ""
        m1_label   = request.POST.get("caym1_year_label") or ""
        m2_label   = request.POST.get("caym2_year_label") or ""

        if not academic_year_range:
            academic_year_range = f"CAY {cay_label}, CAYm1 {m1_label}, CAYm2 {m2_label}"

        # Parse "YYYY-YY" -> YYYY
        def parse_start_year(label: str) -> int:
            s = (label or "").strip().split("-")[0]
            y = _to_year_int(s)
            return y or 0

        y0 = parse_start_year(cay_label)
        y1 = parse_start_year(m1_label)
        y2 = parse_start_year(m2_label)

        # Recompute N (authoritative carry-forward from SanctionedIntake)
        degree_id = dept.degree_id or None
        N_cay   = get_effective_intake(dept.id, degree_id, y0) if y0 else 0
        N_caym1 = get_effective_intake(dept.id, degree_id, y1) if y1 else 0
        N_caym2 = get_effective_intake(dept.id, degree_id, y2) if y2 else 0

        # N1/N4 from POST
        to_int = lambda k: int(request.POST.get(k) or 0)
        N1_cay, N4_cay = to_int("admitted_cay"), to_int("supernumerary_cay")
        N1_m1,  N4_m1  = to_int("admitted_caym1"), to_int("supernumerary_caym1")
        N1_m2,  N4_m2  = to_int("admitted_caym2"), to_int("supernumerary_caym2")

        # Compute ER server-side (ignore client-side numbers)
        def er(N, N1, N4):
            return round(((N1 + N4) / N) * 100, 2) if N else 0.00

        er1 = er(N_cay,   N1_cay, N4_cay)
        er2 = er(N_caym1, N1_m1,  N4_m1)
        er3 = er(N_caym2, N1_m2,  N4_m2)

        avg = round((er1 + er2 + er3) / 3.0, 2)
        points = round(20 * (avg / 100.0), 2)

        def marks_from_avg(a):
            if a >= 90: return 20
            if a >= 80: return 17
            if a >= 70: return 14
            if a >= 60: return 11
            if a >= 50: return 8
            if a >= 40: return 5
            return 0

        marks = marks_from_avg(avg)

        # Submission only (no verification/remarks workflow)
        EnrolmentRatioFirstYear.objects.create(
            academic_year_range=academic_year_range,
            department=dept,
            sanctioned_intake_cay=N_cay,
            sanctioned_intake_caym1=N_caym1,
            sanctioned_intake_caym2=N_caym2,
            admitted_cay=N1_cay,
            admitted_caym1=N1_m1,
            admitted_caym2=N1_m2,
            supernumerary_cay=N4_cay,
            supernumerary_caym1=N4_m1,
            supernumerary_caym2=N4_m2,
            er_cay=er1,
            er_caym1=er2,
            er_caym2=er3,
            average_er=avg,
            er_points=points,
            marks_awarded=marks,
            is_verified=False,         # immediate finalization
            admin_remarks=None,       # no remarks flow
        )

        messages.success(request, "Enrolment ratio saved.")
        # Clean redirect (no ?department=...), front-end should remember/load selection and past via API
        return redirect(request.path)

    return render(
        request,
        "nba_management/add_enrolment_ratio.html",
        {
            "departments": departments,
            "selected_dept_id": selected_dept_id,
            "latest_entry": latest_entry,
            "recent_entries": [],     # legacy key kept empty; safe for templates referencing it
            "past_entries": past_entries,
        },
    )



from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from user_accounts.decorators import check_permission

from user_accounts.models import Add_Department
from nba.models import SuccessRateStipulated
from user_accounts.models import StudentDetails

import re

# ==========================
# Year extraction helper (e.g. from "2023-24")
# ==========================
YEAR_RE = re.compile(r"^(19|20)\d{2}")

# ---------------------------------------------------
# 1) API: Get Batches for Department (dropdown helper)
# ---------------------------------------------------
def get_batches_by_department(request):
    """
    Returns distinct admission start years from StudentDetails.batch
    for a given department. For example:
      GET ?department_id=5
      -> { "batches": [2025, 2024, 2023] }
    """
    dept_id = request.GET.get("department_id")
    if not dept_id:
        return JsonResponse({"batches": []})

    raw_batches = (
        StudentDetails.objects
        .filter(department_id=dept_id)
        .values_list("batch", flat=True)
        .distinct()
    )

    years = []
    for val in raw_batches:
        if not val:
            continue
        s = str(val).strip()
        m = YEAR_RE.match(s)
        if m:
            try:
                years.append(int(m.group(0)))
            except ValueError:
                continue

    years = sorted(set(years), reverse=True)
    return JsonResponse({"batches": years})

# ---------------------------------------------------
# 2) API: Get past SR entries (cards on dept selection)
# ---------------------------------------------------
def get_past_success_rate_entries(request):
    """
    Returns last 10 SuccessRateStipulated rows for a department as JSON.
    Includes verification status and admin remarks.
    """
    dept_id = request.GET.get("department_id")
    if not dept_id:
        return JsonResponse({"ok": False, "error": "department_id is required"}, status=400)

    qs = (
        SuccessRateStipulated.objects
        .filter(department_id=dept_id)
        .order_by("-id")[:10]
    )

    def serialize(r):
        return {
            "id": r.id,
            "academic_year_range": r.academic_year_range or "",
            "lyg_label": r.lyg_label or "",
            "lygm1_label": r.lygm1_label or "",
            "lygm2_label": r.lygm2_label or "",
            "a_lyg": int(r.a_lyg or 0),
            "a_lygm1": int(r.a_lygm1 or 0),
            "a_lygm2": int(r.a_lygm2 or 0),
            "b_lyg": int(r.b_lyg or 0),
            "b_lygm1": int(r.b_lygm1 or 0),
            "b_lygm2": int(r.b_lygm2 or 0),
            "sr_1": float(r.sr_1 or 0),
            "sr_2": float(r.sr_2 or 0),
            "sr_3": float(r.sr_3 or 0),
            "average_sr": float(r.average_sr or 0),
            "sr_points": float(r.sr_points or 0),
            "is_verified": bool(r.is_verified),
            "admin_remarks": r.admin_remarks or "",
        }

    return JsonResponse({"ok": True, "entries": [serialize(x) for x in qs]}, status=200)

# ---------------------------------------------------
# 3) Form view: Add SR entry (pure save)
# ---------------------------------------------------
@check_permission("nba_students_performance")
def add_success_rate_stipulated(request):
    """
    Displays and saves SuccessRateStipulated entries.
    The client computes SR values; server only persists.
    Shows recent entries + latest status if department preselected.
    """
    departments = Add_Department.objects.filter(is_active=True)
    selected_dept_id = request.POST.get("department") or request.GET.get("department") or None

    latest_entry = None
    past_entries = []
    if selected_dept_id:
        qs = SuccessRateStipulated.objects.filter(department_id=selected_dept_id).order_by("-id")
        latest_entry = qs.first()
        past_entries = list(qs[:10])

    if request.method == "POST":
        dept_id = request.POST.get("department")
        if not dept_id:
            messages.error(request, "Department is required.")
            return redirect("add_success_rate_stipulated")

        # Labels
        academic_year_range = (request.POST.get("academic_year_range") or "").strip()
        lyg_label   = (request.POST.get("lyg_label") or "").strip()
        lygm1_label = (request.POST.get("lygm1_label") or "").strip()
        lygm2_label = (request.POST.get("lygm2_label") or "").strip()

        # Converters
        def to_int(name):
            try:
                return int(request.POST.get(name) or 0)
            except ValueError:
                return 0

        def to_float(name):
            try:
                return float(request.POST.get(name) or 0)
            except ValueError:
                return 0.0

        # Values
        a_lyg   = to_int("a_lyg")
        a_lygm1 = to_int("a_lygm1")
        a_lygm2 = to_int("a_lygm2")
        b_lyg   = to_int("b_lyg")
        b_lygm1 = to_int("b_lygm1")
        b_lygm2 = to_int("b_lygm2")
        sr1 = to_float("sr_1")
        sr2 = to_float("sr_2")
        sr3 = to_float("sr_3")
        avg = to_float("average_sr")
        pts = to_float("sr_points")

        SuccessRateStipulated.objects.create(
            department_id=dept_id,
            academic_year_range=academic_year_range,
            lyg_label=lyg_label, lygm1_label=lygm1_label, lygm2_label=lygm2_label,
            a_lyg=a_lyg, a_lygm1=a_lygm1, a_lygm2=a_lygm2,
            b_lyg=b_lyg, b_lygm1=b_lygm1, b_lygm2=b_lygm2,
            sr_1=sr1, sr_2=sr2, sr_3=sr3,
            average_sr=avg, sr_points=pts,
            marks_awarded=int(pts),
            is_verified=False,
            admin_remarks=None,
        )

        messages.success(request, "Success Rate saved.")
        return redirect(request.path)

    return render(
        request,
        "nba_management/add_success_rate_stipulated.html",
        {
            "departments": departments,
            "selected_dept_id": selected_dept_id,
            "latest_entry": latest_entry,
            "past_entries": past_entries,
        },
    )




# nba/views.py (or a dedicated views_api.py imported in urls)
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
import re

from user_accounts.decorators import check_permission
from user_accounts.models import Add_Department, StudentDetails
from nba.models import AcademicPerformanceFirstYear

# Reuse the same year regex helper used elsewhere
YEAR_RE = re.compile(r"^(19|20)\d{2}")

# ---------- 1) API: Batches for Department ----------
def get_batches_by_department(request):
    """
    Returns distinct admission start years from StudentDetails.batch for a department.
    { "batches": [2025, 2024, 2023] }
    """
    dept_id = request.GET.get("department_id")
    if not dept_id:
        return JsonResponse({"batches": []})

    raw = (StudentDetails.objects
           .filter(department_id=dept_id)
           .values_list("batch", flat=True)
           .distinct())
    years = []
    for v in raw:
        if not v: 
            continue
        s = str(v).strip()
        m = YEAR_RE.match(s)
        if m:
            try:
                years.append(int(m.group(0)))
            except ValueError:
                pass
    years = sorted(set(years), reverse=True)
    return JsonResponse({"batches": years})

# ---------- 2) API: Past entries (cards) ----------
def get_past_academic_api_entries(request):
    """
    GET ?department_id=<id>
    Returns last 10 API rows for a department (newest first).
    """
    dept_id = request.GET.get("department_id")
    if not dept_id:
        return JsonResponse({"ok": False, "error": "department_id is required"}, status=400)

    qs = (AcademicPerformanceFirstYear.objects
          .filter(department_id=dept_id)
          .order_by("-id")[:10])

    def ser(r):
        return {
            "id": r.id,
            "academic_year_range": r.academic_year_range or "",
            "caym1_label": r.caym1_label or "",
            "caym2_label": r.caym2_label or "",
            "caym3_label": r.caym3_label or "",
            "x_caym1": float(r.x_caym1 or 0),
            "x_caym2": float(r.x_caym2 or 0),
            "x_caym3": float(r.x_caym3 or 0),
            "y_caym1": int(r.y_caym1 or 0),
            "y_caym2": int(r.y_caym2 or 0),
            "y_caym3": int(r.y_caym3 or 0),
            "z_caym1": int(r.z_caym1 or 0),
            "z_caym2": int(r.z_caym2 or 0),
            "z_caym3": int(r.z_caym3 or 0),
            "api_1": float(r.api_1 or 0),
            "api_2": float(r.api_2 or 0),
            "api_3": float(r.api_3 or 0),
            "average_api": float(r.average_api or 0),
            "marks_awarded": float(r.marks_awarded or 0),
            "is_verified": bool(r.is_verified),
            "admin_remarks": r.admin_remarks or "",
        }

    return JsonResponse({"ok": True, "entries": [ser(x) for x in qs]}, status=200)

# ---------- 3) Form view ----------
@check_permission("nba_students_performance")
def add_academic_performance_first_year(request):
    """
    Submission-only view (no admin verification here).
    Client computes API values; server recomputes to be authoritative.
    """
    departments = Add_Department.objects.filter(is_active=True)
    selected_dept_id = request.POST.get("department") or request.GET.get("department") or None

    latest_entry = None
    past_entries = []
    if selected_dept_id:
        qs = AcademicPerformanceFirstYear.objects.filter(department_id=selected_dept_id).order_by("-id")
        latest_entry = qs.first()
        past_entries = list(qs[:10])

    if request.method == "POST":
        dept_id = request.POST.get("department")
        if not dept_id:
            messages.error(request, "Department is required.")
            return redirect("add_academic_performance_first_year")

        # Labels
        caym1_label = (request.POST.get("caym1_label") or "").strip()
        caym2_label = (request.POST.get("caym2_label") or "").strip()
        caym3_label = (request.POST.get("caym3_label") or "").strip()

        academic_year_range = (request.POST.get("academic_year_range") or "").strip()
        if not academic_year_range:
            academic_year_range = f"{caym1_label} / {caym2_label} / {caym3_label}"

        # Parsers
        def to_int(k): 
            try: return int(request.POST.get(k) or 0)
            except ValueError: return 0
        def to_float(k):
            try: return float(request.POST.get(k) or 0.0)
            except ValueError: return 0.0

        # X (0..10), Y, Z
        x1, x2, x3 = to_float("x_caym1"), to_float("x_caym2"), to_float("x_caym3")
        y1, y2, y3 = to_int("y_caym1"), to_int("y_caym2"), to_int("y_caym3")
        z1, z2, z3 = to_int("z_caym1"), to_int("z_caym2"), to_int("z_caym3")

        def api(x, y, z): 
            return round(x * (y / z), 2) if z else 0.00

        a1 = api(x1, y1, z1)
        a2 = api(x2, y2, z2)
        a3 = api(x3, y3, z3)
        avg = round((a1 + a2 + a3) / 3.0, 2)

        # Weight 10 → marks = average_api
        marks = avg

        AcademicPerformanceFirstYear.objects.create(
            department_id=dept_id,
            caym1_label=caym1_label, caym2_label=caym2_label, caym3_label=caym3_label,
            academic_year_range=academic_year_range,
            x_caym1=x1, x_caym2=x2, x_caym3=x3,
            y_caym1=y1, y_caym2=y2, y_caym3=y3,
            z_caym1=z1, z_caym2=z2, z_caym3=z3,
            api_1=a1, api_2=a2, api_3=a3,
            average_api=avg, marks_awarded=marks, max_marks=10,
            is_verified=False, admin_remarks=None,
        )

        messages.success(request, "Academic Performance (API) saved.")
        return redirect(request.path)

    return render(
        request,
        "nba_management/add_academic_performance_first_year.html",
        {
            "departments": departments,
            "selected_dept_id": selected_dept_id,
            "latest_entry": latest_entry,
            "past_entries": past_entries,
        },
    )


# nba/views.py (append to your existing file)
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from user_accounts.decorators import check_permission
from user_accounts.models import Add_Department, StudentDetails
from nba.models import AcademicPerformanceSecondYear
import re

YEAR_RE = re.compile(r"^(19|20)\d{2}")

def get_batches_by_department(request):
    """If you already have this working elsewhere, keep that; shown here for completeness."""
    dept_id = request.GET.get("department_id")
    if not dept_id:
        return JsonResponse({"batches": []})
    raw = (StudentDetails.objects
           .filter(department_id=dept_id)
           .values_list("batch", flat=True)
           .distinct())
    years = []
    for v in raw:
        if not v: 
            continue
        m = YEAR_RE.match(str(v).strip())
        if m:
            try: years.append(int(m.group(0)))
            except ValueError: pass
    return JsonResponse({"batches": sorted(set(years), reverse=True)})

def get_past_academic_api2_entries(request):
    """
    GET ?department_id=<id>
    Return last 10 AcademicPerformanceSecondYear rows.
    """
    dept_id = request.GET.get("department_id")
    if not dept_id:
        return JsonResponse({"ok": False, "error": "department_id is required"}, status=400)

    qs = (AcademicPerformanceSecondYear.objects
          .filter(department_id=dept_id)
          .order_by("-id")[:10])

    def ser(r):
        return {
            "id": r.id,
            "academic_year_range": r.academic_year_range or "",
            "caym1_label": r.caym1_label or "",
            "caym2_label": r.caym2_label or "",
            "caym3_label": r.caym3_label or "",
            "x_caym1": float(r.x_caym1 or 0),
            "x_caym2": float(r.x_caym2 or 0),
            "x_caym3": float(r.x_caym3 or 0),
            "y_caym1": int(r.y_caym1 or 0),
            "y_caym2": int(r.y_caym2 or 0),
            "y_caym3": int(r.y_caym3 or 0),
            "z_caym1": int(r.z_caym1 or 0),
            "z_caym2": int(r.z_caym2 or 0),
            "z_caym3": int(r.z_caym3 or 0),
            "api_1": float(r.api_1 or 0),
            "api_2": float(r.api_2 or 0),
            "api_3": float(r.api_3 or 0),
            "average_api": float(r.average_api or 0),
            "marks_awarded": float(r.marks_awarded or 0),
            "is_verified": bool(r.is_verified),
            "admin_remarks": r.admin_remarks or "",
        }

    return JsonResponse({"ok": True, "entries": [ser(x) for x in qs]}, status=200)

@check_permission("nba_students_performance")
def add_academic_performance_second_year(request):
    """
    Submission-only form for Table 4.4 (Second Year).
    Server recomputes API to be authoritative: API = X * (Y/Z), Average = mean(API_i), marks=Average (out of 10).
    """
    departments = Add_Department.objects.filter(is_active=True)
    selected_dept_id = request.POST.get("department") or request.GET.get("department") or None

    latest_entry, past_entries = None, []
    if selected_dept_id:
        qs = AcademicPerformanceSecondYear.objects.filter(department_id=selected_dept_id).order_by("-id")
        latest_entry = qs.first()
        past_entries  = list(qs[:10])

    if request.method == "POST":
        dept_id = request.POST.get("department")
        if not dept_id:
            messages.error(request, "Department is required.")
            return redirect("add_academic_performance_second_year")

        # Labels
        caym1_label = (request.POST.get("caym1_label") or "").strip()
        caym2_label = (request.POST.get("caym2_label") or "").strip()
        caym3_label = (request.POST.get("caym3_label") or "").strip()

        academic_year_range = (request.POST.get("academic_year_range") or "").strip()
        if not academic_year_range:
            academic_year_range = f"{caym1_label} / {caym2_label} / {caym3_label}"

        # Parsers
        def to_int(k): 
            try: return int(request.POST.get(k) or 0)
            except ValueError: return 0
        def to_float(k):
            try: return float(request.POST.get(k) or 0.0)
            except ValueError: return 0.0

        x1, x2, x3 = to_float("x_caym1"), to_float("x_caym2"), to_float("x_caym3")
        y1, y2, y3 = to_int("y_caym1"), to_int("y_caym2"), to_int("y_caym3")
        z1, z2, z3 = to_int("z_caym1"), to_int("z_caym2"), to_int("z_caym3")

        def api(x, y, z): 
            return round(x * (y / z), 2) if z else 0.00

        a1, a2, a3 = api(x1,y1,z1), api(x2,y2,z2), api(x3,y3,z3)
        avg = round((a1 + a2 + a3) / 3.0, 2)
        marks = avg  # out of 10

        AcademicPerformanceSecondYear.objects.create(
            department_id=dept_id,
            caym1_label=caym1_label, caym2_label=caym2_label, caym3_label=caym3_label,
            academic_year_range=academic_year_range,
            x_caym1=x1, x_caym2=x2, x_caym3=x3,
            y_caym1=y1, y_caym2=y2, y_caym3=y3,
            z_caym1=z1, z_caym2=z2, z_caym3=z3,
            api_1=a1, api_2=a2, api_3=a3,
            average_api=avg, marks_awarded=marks, max_marks=10,
            is_verified=False, admin_remarks=None,
        )

        messages.success(request, "Academic Performance (Second Year) saved.")
        return redirect(request.path)

    return render(
        request,
        "nba_management/add_academic_performance_second_year.html",
        {
            "departments": departments,
            "selected_dept_id": selected_dept_id,
            "latest_entry": latest_entry,
            "past_entries": past_entries,
        },
    )

# nba/views.py  (append these; reuse your existing YEAR_RE and get_batches_by_department if present)
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages

from user_accounts.decorators import check_permission
from user_accounts.models import Add_Department, StudentDetails
from nba.models import AcademicPerformanceThirdYear

# ---- Past entries API (cards) ----
def get_past_academic_api_third_year_entries(request):
    """
    GET ?department_id=<id>
    Returns last 10 Third-Year API rows for a department (newest first).
    """
    dept_id = request.GET.get("department_id")
    if not dept_id:
        return JsonResponse({"ok": False, "error": "department_id is required"}, status=400)

    qs = (AcademicPerformanceThirdYear.objects
          .filter(department_id=dept_id)
          .order_by("-id")[:10])

    def ser(r):
        return {
            "id": r.id,
            "academic_year_range": r.academic_year_range or "",
            "caym1_label": r.caym1_label or "",
            "caym2_label": r.caym2_label or "",
            "caym3_label": r.caym3_label or "",
            "x_caym1": float(r.x_caym1 or 0), "x_caym2": float(r.x_caym2 or 0), "x_caym3": float(r.x_caym3 or 0),
            "y_caym1": int(r.y_caym1 or 0),   "y_caym2": int(r.y_caym2 or 0),   "y_caym3": int(r.y_caym3 or 0),
            "z_caym1": int(r.z_caym1 or 0),   "z_caym2": int(r.z_caym2 or 0),   "z_caym3": int(r.z_caym3 or 0),
            "api_1": float(r.api_1 or 0), "api_2": float(r.api_2 or 0), "api_3": float(r.api_3 or 0),
            "average_api": float(r.average_api or 0),
            "marks_awarded": float(r.marks_awarded or 0),
            "is_verified": bool(r.is_verified),
            "admin_remarks": r.admin_remarks or "",
        }

    return JsonResponse({"ok": True, "entries": [ser(x) for x in qs]}, status=200)

# ---- Form view (submission-only) ----
@check_permission("nba_students_performance")
def add_academic_performance_third_year(request):
    """
    Displays and saves AcademicPerformanceThirdYear entries.
    Server recomputes API values from X/Y/Z.
    """
    departments = Add_Department.objects.filter(is_active=True)
    selected_dept_id = request.POST.get("department") or request.GET.get("department") or None

    latest_entry = None
    past_entries = []
    if selected_dept_id:
        qs = AcademicPerformanceThirdYear.objects.filter(department_id=selected_dept_id).order_by("-id")
        latest_entry = qs.first()
        past_entries = list(qs[:10])

    if request.method == "POST":
        dept_id = request.POST.get("department")
        if not dept_id:
            messages.error(request, "Department is required.")
            return redirect("add_academic_performance_third_year")

        # Labels
        caym1_label = (request.POST.get("caym1_label") or "").strip()
        caym2_label = (request.POST.get("caym2_label") or "").strip()
        caym3_label = (request.POST.get("caym3_label") or "").strip()

        academic_year_range = (request.POST.get("academic_year_range") or "").strip()
        if not academic_year_range:
            academic_year_range = f"{caym1_label} / {caym2_label} / {caym3_label}"

        # Parsers
        def to_int(k):
            try: return int(request.POST.get(k) or 0)
            except ValueError: return 0
        def to_float(k):
            try: return float(request.POST.get(k) or 0.0)
            except ValueError: return 0.0

        x1, x2, x3 = to_float("x_caym1"), to_float("x_caym2"), to_float("x_caym3")
        y1, y2, y3 = to_int("y_caym1"), to_int("y_caym2"), to_int("y_caym3")
        z1, z2, z3 = to_int("z_caym1"), to_int("z_caym2"), to_int("z_caym3")

        def api(x, y, z): return round(x * (y / z), 2) if z else 0.00

        a1, a2, a3 = api(x1, y1, z1), api(x2, y2, z2), api(x3, y3, z3)
        avg = round((a1 + a2 + a3) / 3.0, 2)
        marks = avg  # out of 10

        AcademicPerformanceThirdYear.objects.create(
            department_id=dept_id,
            caym1_label=caym1_label, caym2_label=caym2_label, caym3_label=caym3_label,
            academic_year_range=academic_year_range,
            x_caym1=x1, x_caym2=x2, x_caym3=x3,
            y_caym1=y1, y_caym2=y2, y_caym3=y3,
            z_caym1=z1, z_caym2=z2, z_caym3=z3,
            api_1=a1, api_2=a2, api_3=a3,
            average_api=avg, marks_awarded=marks, max_marks=10,
            is_verified=False, admin_remarks=None,
        )

        messages.success(request, "Third-Year Academic Performance (API) saved.")
        return redirect(request.path)

    return render(
        request,
        "nba_management/add_academic_performance_third_year.html",
        {
            "departments": departments,
            "selected_dept_id": selected_dept_id,
            "latest_entry": latest_entry,
            "past_entries": past_entries,
        },
    )


# nba/views.py (append these)
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
import re

from user_accounts.decorators import check_permission
from user_accounts.models import Add_Department, StudentDetails
from nba.models import PlacementHigherStudiesEntrepreneurship

YEAR_RE = re.compile(r"^(19|20)\d{2}")  # reuse safely

def get_batches_by_department(request):
    """Return distinct start years from StudentDetails.batch for a department."""
    dept_id = request.GET.get("department_id")
    if not dept_id:
        return JsonResponse({"batches": []})
    raw = (StudentDetails.objects
           .filter(department_id=dept_id)
           .values_list("batch", flat=True)
           .distinct())
    years = []
    for v in raw:
        if not v: continue
        m = YEAR_RE.match(str(v).strip())
        if m:
            try: years.append(int(m.group(0)))
            except ValueError: pass
    return JsonResponse({"batches": sorted(set(years), reverse=True)})

# ---------- Past entries (cards) ----------
def get_past_placement_entries(request):
    """
    GET ?department_id=<id>
    Return last 10 Placement rows for dept (newest first).
    """
    dept_id = request.GET.get("department_id")
    if not dept_id:
        return JsonResponse({"ok": False, "error": "department_id is required"}, status=400)

    qs = (PlacementHigherStudiesEntrepreneurship.objects
          .filter(department_id=dept_id)
          .order_by("-id")[:10])

    def ser(r):
        return {
            "id": r.id,
            "academic_year_range": r.academic_year_range or "",
            "lyg_label": r.lyg_label or "",
            "lygm1_label": r.lygm1_label or "",
            "lygm2_label": r.lygm2_label or "",
            "fs_lyg": int(r.fs_lyg or 0), "fs_lygm1": int(r.fs_lygm1 or 0), "fs_lygm2": int(r.fs_lygm2 or 0),
            "x_lyg": int(r.x_lyg or 0), "y_lyg": int(r.y_lyg or 0), "z_lyg": int(r.z_lyg or 0),
            "x_lygm1": int(r.x_lygm1 or 0), "y_lygm1": int(r.y_lygm1 or 0), "z_lygm1": int(r.z_lygm1 or 0),
            "x_lygm2": int(r.x_lygm2 or 0), "y_lygm2": int(r.y_lygm2 or 0), "z_lygm2": int(r.z_lygm2 or 0),
            "p_1": float(r.p_1 or 0), "p_2": float(r.p_2 or 0), "p_3": float(r.p_3 or 0),
            "average_p": float(r.average_p or 0),
            "placement_points": float(r.placement_points or 0),
            "is_verified": bool(r.is_verified),
            "admin_remarks": r.admin_remarks or "",
        }
    return JsonResponse({"ok": True, "entries": [ser(x) for x in qs]}, status=200)

# ---------- Form view ----------
@check_permission("nba_students_performance")
def add_placement_hs_entre(request):
    """
    Submission-only; server recomputes P and points.
    """
    departments = Add_Department.objects.filter(is_active=True)
    selected_dept_id = request.POST.get("department") or request.GET.get("department") or None

    latest_entry = None
    past_entries = []
    if selected_dept_id:
        qs = PlacementHigherStudiesEntrepreneurship.objects.filter(department_id=selected_dept_id).order_by("-id")
        latest_entry = qs.first()
        past_entries = list(qs[:10])

    if request.method == "POST":
        dept_id = request.POST.get("department")
        if not dept_id:
            messages.error(request, "Department is required.")
            return redirect("add_placement_hs_entre")

        # Labels
        lyg_label   = (request.POST.get("lyg_label") or "").strip()
        lygm1_label = (request.POST.get("lygm1_label") or "").strip()
        lygm2_label = (request.POST.get("lygm2_label") or "").strip()
        academic_year_range = (request.POST.get("academic_year_range") or "").strip()
        if not academic_year_range:
            academic_year_range = f"{lyg_label} / {lygm1_label} / {lygm2_label}"

        def to_int(k):
            try: return int(request.POST.get(k) or 0)
            except ValueError: return 0

        # Numbers
        fs1, fs2, fs3 = to_int("fs_lyg"), to_int("fs_lygm1"), to_int("fs_lygm2")
        x1, y1, z1 = to_int("x_lyg"), to_int("y_lyg"), to_int("z_lyg")
        x2, y2, z2 = to_int("x_lygm1"), to_int("y_lygm1"), to_int("z_lygm1")
        x3, y3, z3 = to_int("x_lygm2"), to_int("y_lygm2"), to_int("z_lygm2")

        def p(fs, x, y, z): return round(((x + y + z) / fs) * 100, 2) if fs else 0.00

        p1, p2, p3 = p(fs1, x1, y1, z1), p(fs2, x2, y2, z2), p(fs3, x3, y3, z3)
        avg = round((p1 + p2 + p3) / 3.0, 2)
        points = round(0.3 * avg, 2)  # out of 30

        PlacementHigherStudiesEntrepreneurship.objects.create(
            department_id=dept_id,
            lyg_label=lyg_label, lygm1_label=lygm1_label, lygm2_label=lygm2_label,
            academic_year_range=academic_year_range,
            fs_lyg=fs1, fs_lygm1=fs2, fs_lygm2=fs3,
            x_lyg=x1, y_lyg=y1, z_lyg=z1,
            x_lygm1=x2, y_lygm1=y2, z_lygm1=z2,
            x_lygm2=x3, y_lygm2=y3, z_lygm2=z3,
            p_1=p1, p_2=p2, p_3=p3,
            average_p=avg, placement_points=points, max_marks=30,
            is_verified=False, admin_remarks=None,
        )

        messages.success(request, "Placement / Higher Studies / Entrepreneurship saved.")
        return redirect(request.path)

    return render(
        request,
        "nba_management/add_placement_hs_entre.html",
        {
            "departments": departments,
            "selected_dept_id": selected_dept_id,
            "latest_entry": latest_entry,
            "past_entries": past_entries,
        },
    )


from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from datetime import  datetime
from decimal import Decimal
from user_accounts.decorators import check_permission
from user_accounts.models import Add_Department
from nba.models import *
# =====================================================================
# ------------------------------ 4.7.1 ------------------------------
# =====================================================================

@check_permission("nba_students_performance")
def add_societies(request):
    """
    4.7.1 — Societies & Events
    Flow:
    - Select department
    - Table-1: add societies (creates a new submission with given AY)
    - If dept has societies, Table-2 appears with 3 sections: CAYm1/CAYm2/CAYm3
    - Save events attaches to chosen (or latest) submission
    """
    departments = Add_Department.objects.filter(is_active=True)
    selected = request.GET.get("department") or request.POST.get("department") or ""

    ctx = {
        "departments": departments,
        "selected_dept_id": selected,
        "latest_entry": None,
        "show_events": False,
        "societies_for_dropdown": [],
        "event_submissions": [],
    }

    if selected:
        latest = (
            SocietiesSubmission.objects.filter(department_id=selected)
            .order_by("-id").first()
        )
        ctx["latest_entry"] = latest

        has_societies = SocietyChapter.objects.filter(submission__department_id=selected).exists()
        ctx["show_events"] = has_societies

        ctx["societies_for_dropdown"] = list(
            SocietyChapter.objects
            .filter(submission__department_id=selected)
            .values("id", "name", "type")
            .order_by("name", "id")
        )

        ctx["event_submissions"] = [
            {
                "id": s.id,
                "ay": s.academic_year_range or "",
                "created_str": s.created_at.strftime("%d-%m-%Y") if s.created_at else "",
            }
            for s in SocietiesSubmission.objects.filter(department_id=selected).order_by("-id")
        ]

    action = request.POST.get("action", "")

    # ================= SAVE SOCIETIES (Table-1) =================
    if request.method == "POST" and action == "save_societies":
        dept_id = selected
        ay = (request.POST.get("academic_year_range") or "").strip()
        if not dept_id:
            messages.error(request, "Select a department.")
            return redirect("add_societies")
        if not ay:
            messages.error(request, "Academic Year is required.")
            return redirect(f"{request.path}?department={dept_id}")

        names  = request.POST.getlist("society_name[]")
        types  = request.POST.getlist("society_type[]")
        scopes = request.POST.getlist("society_scope[]")
        years  = request.POST.getlist("inauguration_year[]")

        if not any((nm or "").strip() for nm in names):
            messages.error(request, "Add at least one society row.")
            return redirect(f"{request.path}?department={dept_id}")

        with transaction.atomic():
            sub = SocietiesSubmission.objects.create(
                department_id=dept_id, academic_year_range=ay
            )
            for i, nm in enumerate(names):
                nm = (nm or "").strip()
                if not nm:
                    continue
                t = types[i] if i < len(types) and types[i] else "Society"
                sc = scopes[i] if i < len(scopes) and scopes[i] else None
                yr = None
                if i < len(years) and years[i]:
                    try: yr = int(years[i])
                    except ValueError: yr = None

                SocietyChapter.objects.create(
                    submission=sub,
                    department_id=dept_id,
                    name=nm, type=t, scope=sc, inauguration_year=yr
                )

        messages.success(request, "Society/Club/Chapter rows saved.")
        return redirect(f"{request.path}?department={dept_id}")

    # ================= SAVE EVENTS (Table-2; CAYm1/2/3) =================
    if request.method == "POST" and action == "save_events":
        dept_id = selected
        if not dept_id:
            messages.error(request, "Select a department.")
            return redirect("add_societies")

        sub_id = (request.POST.get("events_submission_id") or "").strip()
        if sub_id:
            target_sub = get_object_or_404(SocietiesSubmission, pk=sub_id, department_id=dept_id)
        else:
            target_sub = (
                SocietiesSubmission.objects.filter(department_id=dept_id)
                .order_by("-id").first()
            )
            if not target_sub:
                messages.error(request, "No submission found to attach events.")
                return redirect(f"{request.path}?department={dept_id}")

        def save_bucket(bucket_key: str):
            # society_CAYm1[], event_CAYm1[], body_CAYm1[], level_CAYm1[], date_CAYm1[]
            society_ids = request.POST.getlist(f"society_{bucket_key}[]")
            titles      = request.POST.getlist(f"event_{bucket_key}[]")
            bodies      = request.POST.getlist(f"body_{bucket_key}[]")
            levels      = request.POST.getlist(f"level_{bucket_key}[]")
            dates       = request.POST.getlist(f"date_{bucket_key}[]")

            for i, title in enumerate(titles):
                title = (title or "").strip()
                if not title:
                    continue

                soc = None
                if i < len(society_ids) and society_ids[i]:
                    try:
                        soc = SocietyChapter.objects.select_related("submission").get(pk=int(society_ids[i]))
                        if str(soc.submission.department_id) != str(dept_id):
                            soc = None
                    except (ValueError, SocietyChapter.DoesNotExist):
                        soc = None

                dt = None
                if i < len(dates) and dates[i]:
                    try: dt = datetime.strptime(dates[i], "%Y-%m-%d").date()
                    except ValueError: dt = None

                lvl = levels[i] if i < len(levels) else None
                body = bodies[i] if i < len(bodies) else None

                SocietyEvent.objects.create(
                    submission=target_sub,
                    society=soc,
                    cay_bucket=bucket_key,  # "CAYm1" / "CAYm2" / "CAYm3"
                    event_title=title,
                    body_name=(body or None),
                    level=lvl or None,
                    date=dt
                )

        with transaction.atomic():
            save_bucket("CAYm1")
            save_bucket("CAYm2")
            save_bucket("CAYm3")

        # Recompute counts + marks
        state = nat = intl = 0
        c1 = c2 = c3 = 0
        for e in target_sub.events.all():
            if e.cay_bucket == "CAYm1": c1 += 1
            if e.cay_bucket == "CAYm2": c2 += 1
            if e.cay_bucket == "CAYm3": c3 += 1
            if e.level == "State": state += 1
            elif e.level == "National": nat += 1
            elif e.level == "International": intl += 1

        target_sub.caym1_events_count = c1
        target_sub.caym2_events_count = c2
        target_sub.caym3_events_count = c3
        target_sub.state_events_count = state
        target_sub.national_events_count = nat
        target_sub.international_events_count = intl

        total = Decimal("0.10") * Decimal(state + nat) + Decimal("0.50") * Decimal(intl)
        cap = Decimal(str(target_sub.max_marks or 5))
        target_sub.marks_awarded = min(total, cap)
        target_sub.save()

        messages.success(request, "Events saved to submission.")
        return redirect(f"{request.path}?department={dept_id}")

    return render(request, "nba_management/pa_471_societies.html", ctx)


def past_societies(request):
    """Return last 10 submissions with societies + events (for cards)."""
    dept_id = request.GET.get("department_id")
    if not dept_id:
        return JsonResponse({"ok": False, "error": "department_id is required"}, status=400)

    subs = SocietiesSubmission.objects.filter(department_id=dept_id).order_by("-id")[:10]
    entries = []

    for s in subs:
        societies = [{
            "name": sc.name or "",
            "type": sc.type or "",
            "scope": sc.scope or "",
            "year": sc.inauguration_year or "",
        } for sc in s.society_chapters.all()]

        events = [{
            "society": (e.society.name if e.society else ""),
            "event": e.event_title or "",
            "body": e.body_name or "",
            "level": e.level or "",
            "date": e.date.strftime("%d-%m-%Y") if e.date else "",
            "bucket": e.cay_bucket or "",
        } for e in s.events.all().order_by("cay_bucket", "-date", "id")]

        entries.append({
            "id": s.id,
            "academic_year_range": s.academic_year_range or "",
            "is_verified": bool(s.is_verified),
            "admin_remarks": s.admin_remarks or "",
            "created_at": s.created_at.strftime("%d-%m-%Y") if s.created_at else "",
            "marks_awarded": str(s.marks_awarded or Decimal("0.00")),
            "max_marks": s.max_marks or 5,
            "state_events": s.state_events_count or 0,
            "national_events": s.national_events_count or 0,
            "international_events": s.international_events_count or 0,
            "caym1": s.caym1_events_count or 0,
            "caym2": s.caym2_events_count or 0,
            "caym3": s.caym3_events_count or 0,
            "societies": societies,
            "events": events
        })
    return JsonResponse({"ok": True, "entries": entries})


# =====================================================================
# ------------------------------ 4.7.2 ------------------------------
# =====================================================================
from django.utils.timezone import localdate


def student_lookup(request):
    """
    GET ?department_id=..&reg_no=..
    - Trim & uppercase the reg_no for comparison
    - First try inside selected department (case-insensitive)
    - If not found, try global search (case-insensitive)
    - If found globally but in another dept, return ok with mismatch flag
    """
    dept_id = (request.GET.get("department_id") or "").strip()
    raw_reg = (request.GET.get("reg_no") or "").strip()
    if not dept_id or not raw_reg:
        return JsonResponse({"ok": False, "error": "department_id and reg_no are required"}, status=400)

    # normalize: collapse spaces to single, strip, and uppercase for display
    norm_reg = " ".join(raw_reg.split()).upper()

    # 1) try inside department (case-insensitive)
    qs_in = StudentDetails.objects.filter(department_id=dept_id, reg_no__iexact=norm_reg)
    s = qs_in.first()

    # 2) fallback: try global case-insensitive match
    dept_mismatch = False
    if not s:
        s = StudentDetails.objects.filter(reg_no__iexact=norm_reg).first()
        if s:
            dept_mismatch = (str(s.department_id) != str(dept_id))

    if not s:
        # last-ditch: sometimes reg_no saved with stray spaces — normalize in Python
        # pull small set and compare normalized
        candidates = StudentDetails.objects.filter(reg_no__isnull=False)
        def normalize_db(v): return " ".join(str(v).split()).upper()
        for cand in candidates[:5000]:  # guardrail
            if normalize_db(cand.reg_no) == norm_reg:
                s = cand
                dept_mismatch = (str(cand.department_id) != str(dept_id))
                break

    if not s:
        return JsonResponse({"ok": False, "error": "No student found for this Register Number."}, status=404)

    data = {
        "name": s.name or "",
        "reg_no": s.reg_no or "",
        "batch": s.batch or "",
        "year": s.year or "",
        "section": s.section or "",
        "email": s.email or "",
        "mobile_no": s.mobile_no or "",
        "gender": s.gender or "",
        "department_id": s.department_id,
        "department_name": getattr(s.department, "Department", "") if s.department else "",
        "dept_mismatch": dept_mismatch,
    }
    return JsonResponse({"ok": True, "student": data, "server_time": localdate().isoformat()})

# ==========================
# 4.7.2 — Add / Save / Past
# ==========================
@check_permission("nba_students_performance")
def add_student_events(request):
    """
    4.7.2 Student’s Participations in Professional Events
    - Select department
    - Create submission with AY
    - Add rows in 3 buckets: CAYm1 / CAYm2 / CAYm3
    - Marks: 0.10*(State+National) + 0.50*International, cap at 10
    """
    departments = Add_Department.objects.filter(is_active=True)
    selected = request.POST.get("department") or request.GET.get("department") or ""

    ctx = {
        "departments": departments,
        "selected_dept_id": selected,
        "latest_entry": None,
        "event_submissions": [],
    }

    if selected:
        latest = StudentEventsSubmission.objects.filter(department_id=selected).order_by("-id").first()
        ctx["latest_entry"] = latest
        ctx["event_submissions"] = [
            {
                "id": s.id,
                "ay": s.academic_year_range or "",
                "created_str": s.created_at.strftime("%d-%m-%Y") if s.created_at else "",
            }
            for s in StudentEventsSubmission.objects.filter(department_id=selected).order_by("-id")
        ]

    action = request.POST.get("action", "")

    # ---------- CREATE SUBMISSION ONLY (with AY) ----------
    if request.method == "POST" and action == "create_submission":
        dept_id = selected
        ay = (request.POST.get("academic_year_range") or "").strip()
        if not dept_id:
            messages.error(request, "Select a department.")
            return redirect("add_student_events")
        if not ay:
            messages.error(request, "Academic Year is required.")
            return redirect(f"{request.path}?department={dept_id}")

        StudentEventsSubmission.objects.create(department_id=dept_id, academic_year_range=ay)
        messages.success(request, "Submission created. You can now add student events.")
        return redirect(f"{request.path}?department={dept_id}")

    # ---------- SAVE EVENTS INTO A SUBMISSION ----------
    if request.method == "POST" and action == "save_events":
        dept_id = selected
        if not dept_id:
            messages.error(request, "Select a department.")
            return redirect("add_student_events")

        sub_id = (request.POST.get("events_submission_id") or "").strip()
        if sub_id:
            target = get_object_or_404(StudentEventsSubmission, pk=sub_id, department_id=dept_id)
        else:
            target = (StudentEventsSubmission.objects.filter(department_id=dept_id)
                      .order_by("-id").first())
            if not target:
                messages.error(request, "Create a submission (AY) before adding rows.")
                return redirect(f"{request.path}?department={dept_id}")

        def save_bucket(bucket: str):
            students = request.POST.getlist(f"student_{bucket}[]")
            titles   = request.POST.getlist(f"title_{bucket}[]")
            levels   = request.POST.getlist(f"level_{bucket}[]")
            dates    = request.POST.getlist(f"date_{bucket}[]")
            awards   = request.POST.getlist(f"award_{bucket}[]")
            for i, stu in enumerate(students):
                stu = (stu or "").strip()
                if not stu:
                    continue
                title = (titles[i] if i < len(titles) else "") or ""
                lvl   = (levels[i] if i < len(levels) else "") or None
                dt    = None
                if i < len(dates) and dates[i]:
                    try:
                        dt = datetime.strptime(dates[i], "%Y-%m-%d").date()
                    except ValueError:
                        dt = None
                award = (awards[i] if i < len(awards) else "") or ""
                StudentEventRow.objects.create(
                    submission=target,
                    cay_bucket=bucket,
                    student=stu,
                    event_title=title,
                    level=lvl,
                    date=dt,
                    award=award
                )

        with transaction.atomic():
            save_bucket("CAYm1")
            save_bucket("CAYm2")
            save_bucket("CAYm3")

        # recompute counts and marks
        state = nat = intl = 0
        c1 = c2 = c3 = 0
        for e in target.student_event_rows.all():
            if e.cay_bucket == "CAYm1": c1 += 1
            if e.cay_bucket == "CAYm2": c2 += 1
            if e.cay_bucket == "CAYm3": c3 += 1
            if e.level == "State": state += 1
            elif e.level == "National": nat += 1
            elif e.level == "International": intl += 1

        target.caym1_count = c1
        target.caym2_count = c2
        target.caym3_count = c3
        target.state_events_count = state
        target.national_events_count = nat
        target.international_events_count = intl

        total = Decimal("0.10") * Decimal(state + nat) + Decimal("0.50") * Decimal(intl)
        cap = Decimal(str(target.max_marks or 10))
        target.marks_awarded = min(total, cap)
        target.save()

        messages.success(request, "Student events saved.")
        return redirect(f"{request.path}?department={dept_id}")

    return render(request, "nba_management/pa_472_events.html", ctx)


def past_student_events(request):
    dept_id = request.GET.get("department_id")
    if not dept_id:
        return JsonResponse({"ok": False, "error": "department_id is required"}, status=400)

    qs = StudentEventsSubmission.objects.filter(department_id=dept_id).order_by("-id")[:10]
    entries = []
    for s in qs:
        rows = [{
            "bucket": r.cay_bucket or "",
            "student": r.student or "",
            "event_title": r.event_title or "",
            "level": r.level or "",
            "date": r.date.strftime("%d-%m-%Y") if r.date else "",
            "award": r.award or "",
        } for r in s.student_event_rows.all().order_by("cay_bucket", "-date", "id")]

        entries.append({
            "id": s.id,
            "academic_year_range": s.academic_year_range or "",
            "is_verified": bool(s.is_verified),
            "admin_remarks": s.admin_remarks or "",
            "created_at": s.created_at.strftime("%d-%m-%Y") if s.created_at else "",
            "marks_awarded": str(s.marks_awarded),
            "max_marks": s.max_marks,
            "state": s.state_events_count or 0,
            "national": s.national_events_count or 0,
            "international": s.international_events_count or 0,
            "caym1": s.caym1_count or 0,
            "caym2": s.caym2_count or 0,
            "caym3": s.caym3_count or 0,
            "rows": rows
        })
    return JsonResponse({"ok": True, "entries": entries})





# =====================================================================
# ------------------------------ 4.7.3 ------------------------------
# =====================================================================

@check_permission("nba_students_performance")
def add_deptpubs(request):
    """
    4.7.3 — Department publications (Journals/Magazines/Newsletters) in CAYm1/2/3 blocks.
    - Select Department
    - Set Academic Year
    - Add rows per CAY block (saves as one submission)
    """
    departments = Add_Department.objects.filter(is_active=True)
    selected = (request.POST.get("department") or request.GET.get("department") or "").strip()

    latest = (DeptPublicationsSubmission.objects
              .filter(department_id=selected)
              .order_by("-id").first()) if selected else None
    subs_qs = (DeptPublicationsSubmission.objects
               .filter(department_id=selected)
               .order_by("-id")) if selected else []

    if request.method == "POST":
        dept_id = (request.POST.get("department") or "").strip()
        ay = (request.POST.get("academic_year_range") or "").strip()
        if not dept_id or not ay:
            messages.error(request, "Department and Academic Year are required.")
            return redirect("add_deptpubs")

        with transaction.atomic():
            sub = DeptPublicationsSubmission.objects.create(
                department_id=dept_id, academic_year_range=ay
            )

            def save_bucket(bucket: str):
                titles  = request.POST.getlist(f"title_{bucket}[]")
                types   = request.POST.getlist(f"pub_type_{bucket}[]")
                editors = request.POST.getlist(f"editor_{bucket}[]")
                sems    = request.POST.getlist(f"studsem_{bucket}[]")
                issues  = request.POST.getlist(f"issues_{bucket}[]")
                copies  = request.POST.getlist(f"copy_{bucket}[]")
                links   = request.POST.getlist(f"weblink_{bucket}[]")

                n = max(
                    len(titles), len(types), len(editors),
                    len(sems), len(issues), len(copies), len(links)
                )
                for i in range(n):
                    title = (titles[i] if i < len(titles) else "").strip()
                    if not title:
                        continue
                    iss_val = None
                    if i < len(issues):
                        raw = (issues[i] or "").strip()
                        if raw:
                            try:
                                iss_val = int(raw)
                            except ValueError:
                                iss_val = None

                    DeptPublicationRow.objects.create(
                        submission=sub,
                        cay_bucket=bucket,
                        title=title,
                        pub_type=(types[i] if i < len(types) else None),
                        editor_name=(editors[i] if i < len(editors) else None),
                        student_semester=(sems[i] if i < len(sems) else None),
                        num_issues=iss_val,
                        copy_type=(copies[i] if i < len(copies) else None),
                        weblink=(links[i] if i < len(links) else None),
                    )

            save_bucket("CAYm1")
            save_bucket("CAYm2")
            save_bucket("CAYm3")

            # snapshot counters
            sub.caym1_count = sub.dept_publication_rows.filter(cay_bucket="CAYm1").count()
            sub.caym2_count = sub.dept_publication_rows.filter(cay_bucket="CAYm2").count()
            sub.caym3_count = sub.dept_publication_rows.filter(cay_bucket="CAYm3").count()
            sub.save()

        messages.success(request, "Department publications saved.")
        return redirect(f"{request.path}?department={dept_id}")

    context = {
        "departments": departments,
        "selected_dept_id": selected,
        "latest_entry": latest,
        "submissions_dropdown": [
            {
                "id": s.id,
                "ay": s.academic_year_range or "",
                "created_str": s.created_at.strftime("%d-%m-%Y") if s.created_at else "",
            } for s in subs_qs
        ],
    }
    return render(request, "nba_management/pa_473_dept_pubs.html", context)


def past_deptpubs(request):
    """Past 4.7.3 submissions (cards)"""
    dept_id = request.GET.get("department_id")
    if not dept_id:
        return JsonResponse({"ok": False, "error": "department_id is required"}, status=400)

    qs = DeptPublicationsSubmission.objects.filter(department_id=dept_id).order_by("-id")[:10]
    entries = []
    for s in qs:
        rows = [{
            "bucket": r.cay_bucket or "",
            "title": r.title or "",
            "pub_type": r.pub_type or "",
            "editor_name": r.editor_name or "",
            "student_semester": r.student_semester or "",
            "num_issues": r.num_issues if r.num_issues is not None else "",
            "copy_type": r.copy_type or "",
            "weblink": r.weblink or "",
        } for r in s.dept_publication_rows.all().order_by("cay_bucket", "id")]

        entries.append({
            "id": s.id,
            "academic_year_range": s.academic_year_range or "",
            "is_verified": bool(s.is_verified),
            "admin_remarks": s.admin_remarks or "",
            "created_at": s.created_at.strftime("%d-%m-%Y") if s.created_at else "",
            "caym1": getattr(s, "caym1_count", 0) or 0,
            "caym2": getattr(s, "caym2_count", 0) or 0,
            "caym3": getattr(s, "caym3_count", 0) or 0,
            "rows": rows,
        })
    return JsonResponse({"ok": True, "entries": entries})


# =====================================================================
# ------------------------------ 4.7.4 ------------------------------
# =====================================================================

@check_permission("nba_students_performance")
def add_studpubs(request):
    """
    4.7.4 — Student Publications
    Layout: CAYm1 / CAYm2 / CAYm3.
    Columns (per row): Student & Semester, Publisher, Journal/Conference, Volume/Issue, Award.
    Includes in-row 'Verify by RegNo' (fetches from StudentDetails via student_lookup) but DOES NOT store regno.
    """
    departments = Add_Department.objects.filter(is_active=True)
    selected = (request.POST.get("department") or request.GET.get("department") or "").strip()

    latest = (StudentPublicationsSubmission.objects
              .filter(department_id=selected)
              .order_by("-id").first()) if selected else None
    subs_qs = (StudentPublicationsSubmission.objects
               .filter(department_id=selected)
               .order_by("-id")) if selected else []

    if request.method == "POST":
        dept_id = (request.POST.get("department") or "").strip()
        ay = (request.POST.get("academic_year_range") or "").strip()
        if not dept_id or not ay:
            messages.error(request, "Department and Academic Year are required.")
            return redirect("add_studpubs")

        def save_bucket(sub, bucket):
            stu = request.POST.getlist(f"student_{bucket}[]")
            pub = request.POST.getlist(f"publisher_{bucket}[]")
            ven = request.POST.getlist(f"venue_{bucket}[]")
            vol = request.POST.getlist(f"volume_{bucket}[]")
            awd = request.POST.getlist(f"award_{bucket}[]")

            n = max(len(stu), len(pub), len(ven), len(vol), len(awd))
            for i in range(n):
                s = (stu[i] if i < len(stu) else "").strip()
                p = (pub[i] if i < len(pub) else "").strip()
                v = (ven[i] if i < len(ven) else "").strip()
                vi = (vol[i] if i < len(vol) else "").strip()
                a = (awd[i] if i < len(awd) else "").strip()
                if not (s or p or v or vi or a):
                    continue
                StudentPublicationRow.objects.create(
                    submission=sub,
                    cay_bucket=bucket,
                    student_and_semester=s,
                    publisher_name=p,
                    venue_title=v,
                    volume_issue=vi,
                    award_name=a,
                )

        with transaction.atomic():
            sub = StudentPublicationsSubmission.objects.create(
                department_id=dept_id, academic_year_range=ay
            )
            save_bucket(sub, "CAYm1")
            save_bucket(sub, "CAYm2")
            save_bucket(sub, "CAYm3")

            # snapshot counters + a simple scoring heuristic (0.2 per row, cap at 5)
            sub.caym1_count = sub.rows.filter(cay_bucket="CAYm1").count()
            sub.caym2_count = sub.rows.filter(cay_bucket="CAYm2").count()
            sub.caym3_count = sub.rows.filter(cay_bucket="CAYm3").count()
            total_rows = sub.rows.count()
            sub.marks_awarded = min(Decimal("0.20") * Decimal(total_rows), Decimal(str(sub.max_marks)))
            sub.save()

        messages.success(request, "Student publications saved.")
        return redirect(f"{request.path}?department={dept_id}")

    context = {
        "departments": departments,
        "selected_dept_id": selected,
        "latest_entry": latest,
        "submissions_dropdown": [
            {
                "id": s.id,
                "ay": s.academic_year_range or "",
                "created_str": s.created_at.strftime("%d-%m-%Y") if s.created_at else "",
            } for s in subs_qs
        ],
    }
    return render(request, "nba_management/pa_474_student_pubs.html", context)


def past_studpubs(request):
    """Past 4.7.4 submissions — compact card payload"""
    dept_id = request.GET.get("department_id")
    if not dept_id:
        return JsonResponse({"ok": False, "error": "department_id is required"}, status=400)

    qs = StudentPublicationsSubmission.objects.filter(department_id=dept_id).order_by("-id")[:10]
    entries = []
    for s in qs:
        entries.append({
            "id": s.id,
            "academic_year_range": s.academic_year_range or "",
            "is_verified": bool(s.is_verified),
            "admin_remarks": s.admin_remarks or "",
            "created_at": s.created_at.strftime("%d-%m-%Y") if s.created_at else "",
            "rows": s.rows.count(),
            "c1": getattr(s, "caym1_count", 0) or 0,
            "c2": getattr(s, "caym2_count", 0) or 0,
            "c3": getattr(s, "caym3_count", 0) or 0,
            "marks_awarded": str(s.marks_awarded),
            "max_marks": s.max_marks,
        })
    return JsonResponse({"ok": True, "entries": entries})
