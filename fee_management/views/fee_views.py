from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db import IntegrityError
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from decimal import Decimal, InvalidOperation
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


def _redirect_back(request, modal_name=None):
    """Redirect to the referring page, tagging which modal (if any) should
    auto-reopen there so unrelated modals on the same page don't pop up."""

    referer = request.META.get("HTTP_REFERER")

    if referer:
        parts = urlsplit(referer)
        query = dict(parse_qsl(parts.query))
        if modal_name:
            query["open_modal"] = modal_name
        else:
            query.pop("open_modal", None)
        url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
        return redirect(url)

    url = reverse("fee_management")
    if modal_name:
        url = f"{url}?open_modal={modal_name}"
    return redirect(url)

from fee_management.models import (
    FeeType,
    FeeEntry,
    ScholarshipType,
    ScholarshipDeduction,
    TransportStage,
    TransportFee
)

from course_management.models import Degree
from user_accounts.models import Add_Department , AdmissionRecords, StudentDetails , Scholarships
from faculty_management.models import general_information



# =====================================================
# MANAGE FEES PAGE
# =====================================================

def manage_fees(request):

    fee_types = FeeType.objects.all().order_by('name')
    scholarship_types = ScholarshipType.objects.all().order_by('name')

    scholarships = Scholarships.objects.using('admissionform1').all()

    departments = Add_Department.objects.all()

    quotas = (
        AdmissionRecords.objects.using('admissionform1')
        .exclude(Quota__isnull=True)
        .exclude(Quota='')
        .order_by('Quota')
        .values_list('Quota', flat=True)
        .distinct()
    )

    degrees = Degree.objects.all().only(
        "id", "degree_code", "degree", "duration"
    )

    stages = TransportStage.objects.all().order_by("stage_no")

    open_modal = request.GET.get("open_modal")

    return render(
        request,
        "fee_management/admin/manage_fees.html",
        {
            "fee_types": fee_types,
            "scholarships": scholarships,
            "departments": departments,
            "quotas": list(quotas),
            "degrees": degrees,
            "open_modal": open_modal,
            "stages": stages,
            "scholarship_types": scholarship_types,
        }
    )


# =====================================================
# ADD / UPDATE FEE TYPE
# =====================================================

def add_fee_type(request):

    if request.method != "POST":
        return _redirect_back(request)

    name = (request.POST.get("fee_type") or "").strip()
    fee_id = request.POST.get("fee_category_id")

    if not name:
        messages.error(request, "Fee type is required.")
        return _redirect_back(request, "add_fee_type")

    # ---------- UPDATE ----------
    if fee_id:

        obj = get_object_or_404(FeeType, pk=fee_id)

        if FeeType.objects.filter(name__iexact=name).exclude(pk=obj.pk).exists():
            messages.warning(request, f"'{name}' already exists.")
            return _redirect_back(request, "add_fee_type")

        obj.name = name
        obj.save(update_fields=["name"])

        messages.success(request, "Fee type updated successfully.")

        return _redirect_back(request, "add_fee_type")

    # ---------- CREATE ----------

    if FeeType.objects.filter(name__iexact=name).exists():
        messages.warning(request, f"'{name}' already exists.")
        return _redirect_back(request, "add_fee_type")

    try:

        FeeType.objects.create(name=name)

        messages.success(request, "Fee type added successfully.")

    except IntegrityError:

        messages.warning(request, f"'{name}' already exists.")

    return _redirect_back(request, "add_fee_type")


# =====================================================
# DELETE FEE TYPE
# =====================================================

def delete_fee_type(request, fee_category_id):

    fee_type = get_object_or_404(FeeType, id=fee_category_id)

    if request.method == "POST":

        fee_type.delete()

        messages.success(request, "Fee type deleted successfully.")

    return _redirect_back(request, "add_fee_type")


# =====================================================
# FEE ENTRY PAGE
# =====================================================

def fee_entry(request):

    edit_obj = None

    edit_id = request.GET.get("edit")

    if edit_id:
        edit_obj = get_object_or_404(FeeEntry, pk=edit_id)

    # ================= DELETE =================

    if request.method == "POST" and request.POST.get("delete_id"):

        entry = get_object_or_404(FeeEntry, pk=request.POST.get("delete_id"))

        entry.delete()

        messages.success(request, "Fee entry deleted successfully.")

        return redirect(request.META.get("HTTP_REFERER", "fee_entry"))

    # ================= SAVE =================

    if request.method == "POST" and request.POST.get("save_fee"):

        entry_id = request.POST.get("entry_id")

        fee_entry_obj = None

        if entry_id:
            fee_entry_obj = get_object_or_404(FeeEntry, pk=entry_id)

        department = get_object_or_404(
            Add_Department,
            id=request.POST.get("department")
        )

        fee_category = get_object_or_404(
            FeeType,
            id=request.POST.get("fee_category")
        )

        degree = get_object_or_404(
            Degree,
            id=request.POST.get("degree_id")
        )

        quota = (request.POST.get("quota") or "").strip()

        batch = (request.POST.get("batch") or "").strip()

        def amt(v):
            try:
                return float(v)
            except:
                return 0.0

        years = [amt(request.POST.get(f"year_{i}")) for i in range(1, 5)]

        duplicate_qs = FeeEntry.objects.filter(
            fee_category=fee_category,
            department=department,
            batch=batch,
            quota=quota,
            degree=degree
        )

        if fee_entry_obj:
            duplicate_qs = duplicate_qs.exclude(pk=fee_entry_obj.pk)

        if duplicate_qs.exists():
            messages.error(request, "Fee entry already exists.")
            return redirect(request.META.get("HTTP_REFERER", "fee_entry"))

        if fee_entry_obj:

            fee_entry_obj.department = department
            fee_entry_obj.fee_category = fee_category
            fee_entry_obj.degree = degree
            fee_entry_obj.quota = quota
            fee_entry_obj.batch = batch

            fee_entry_obj.year_1 = years[0]
            fee_entry_obj.year_2 = years[1]
            fee_entry_obj.year_3 = years[2]
            fee_entry_obj.year_4 = years[3]

            fee_entry_obj.save()

            messages.success(request, "Updated successfully.")

        else:

            FeeEntry.objects.create(
                department=department,
                fee_category=fee_category,
                degree=degree,
                quota=quota,
                batch=batch,
                year_1=years[0],
                year_2=years[1],
                year_3=years[2],
                year_4=years[3],
            )

            messages.success(request, "Created successfully.")

        return redirect(request.META.get("HTTP_REFERER", "fee_entry"))

    # ================= LIST =================

    qs = FeeEntry.objects.select_related(
        "degree",
        "fee_category",
        "department"
    ).order_by("-created_at")

    paginator = Paginator(qs, 25)

    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "fee_entries": page_obj,
        "degrees": Degree.objects.all(),
        "fee_types": FeeType.objects.all(),
        "quotas": AdmissionRecords.objects.using("admissionform1")
                    .values_list("Quota", flat=True)
                    .distinct(),
        "batches": [
            str(datetime.now().year + i)
            for i in range(-3, 4)
        ],
        "edit_obj": edit_obj,
    }

    return render(
        request,
        "fee_management/admin/fee_entry.html",
        context
    )


# =====================================================
# GET DEPARTMENT BY DEGREE
# =====================================================

def get_departments_by_degree(request):

    degree_id = request.GET.get("degree_id")

    departments = Add_Department.objects.filter(
        degree_id=degree_id,
        is_active=True
    ).values(
        "id",
        "Department"
    )

    return JsonResponse({
        "departments": list(departments)
    })


# =====================================================
# ADD SCHOLARSHIP TYPE
# =====================================================

def add_scholarship_type(request):

    if request.method != "POST":
        return _redirect_back(request)

    name = (request.POST.get("scholarship_type") or "").strip()

    scholar_id = request.POST.get("scholarship_type_id")

    if not name:
        messages.error(request, "Scholarship type is required.")
        return _redirect_back(request, "add_scholarship")

    if scholar_id:

        obj = get_object_or_404(
            ScholarshipType,
            pk=scholar_id
        )

        if ScholarshipType.objects.filter(name__iexact=name).exclude(pk=obj.pk).exists():
            messages.warning(request, f"'{name}' already exists.")
            return _redirect_back(request, "add_scholarship")

        obj.name = name
        obj.save(update_fields=["name"])

        messages.success(request, "Scholarship type updated.")

        return _redirect_back(request, "add_scholarship")

    if ScholarshipType.objects.filter(name__iexact=name).exists():

        messages.warning(request, f"'{name}' already exists.")

        return _redirect_back(request, "add_scholarship")

    try:

        ScholarshipType.objects.create(name=name)

        messages.success(request, "Scholarship type added.")

    except IntegrityError:

        messages.warning(request, f"'{name}' already exists.")

    return _redirect_back(request, "add_scholarship")


# =====================================================
# DELETE SCHOLARSHIP TYPE
# =====================================================

def delete_scholarship_type(request, pk):

    obj = get_object_or_404(
        ScholarshipType,
        id=pk
    )

    if request.method == "POST":

        obj.delete()

        messages.success(
            request,
            "Scholarship type deleted successfully."
        )

    return _redirect_back(request, "add_scholarship")


# =====================================================
# ADMIN DASHBOARD
# =====================================================

def admin_dashboard_view(request):

    stages = TransportStage.objects.all().order_by("stage_no")

    return render(
        request,
        "fee_management/admin/dashboard.html",
        {"stages": stages},
    )



from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.urls import reverse
from datetime import datetime

def scholarship_fee_entry(request):

    edit_obj = None

    # ================= EDIT LOAD =================
    edit_id = request.GET.get("edit")
    if edit_id:
        edit_obj = get_object_or_404(ScholarshipDeduction, pk=edit_id)

    # ================= POST =================
    if request.method == "POST":

        entry_id = request.POST.get("entry_id")
        scholarship = get_object_or_404(ScholarshipType, pk=request.POST.get("scholarship_id"))
        degree = get_object_or_404(Degree, pk=request.POST.get("degree_id"))
        department = get_object_or_404(Add_Department, pk=request.POST.get("department_id"))

        quota = request.POST.get("quota")
        batch = request.POST.get("batch")

        try:
            amount = Decimal(request.POST.get("scholarship_amount"))
        except:
            messages.error(request, "Invalid amount.")
            return redirect("scholarship_fee_entry")

        # Duplicate check
        duplicate = ScholarshipDeduction.objects.filter(
            scholarship=scholarship,
            degree=degree,
            department=department,
            quota=quota,
            batch=batch
        )

        if entry_id:
            duplicate = duplicate.exclude(pk=entry_id)

        if duplicate.exists():
            messages.error(request, "Entry already exists.")
            return redirect("scholarship_fee_entry")

        # -------- UPDATE --------
        if entry_id:
            obj = get_object_or_404(ScholarshipDeduction, pk=entry_id)
            obj.scholarship = scholarship
            obj.degree = degree
            obj.department = department
            obj.quota = quota
            obj.batch = batch
            obj.scholarship_amount = amount
            obj.save()
            messages.success(request, "Updated successfully.")
        else:
            # -------- CREATE --------
            ScholarshipDeduction.objects.create(
                scholarship=scholarship,
                degree=degree,
                department=department,
                quota=quota,
                batch=batch,
                scholarship_amount=amount,
            )
            messages.success(request, "Created successfully.")

        return redirect("scholarship_fee_entry")

    # ================= LIST =================
    queryset = ScholarshipDeduction.objects.select_related(
        "scholarship", "degree", "department"
    ).order_by("-created_at")

    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "scholarship_fees": page_obj,
        "degrees": Degree.objects.all(),
        "scholarship_types": ScholarshipType.objects.all(),
        "quotas": AdmissionRecords.objects.using("admissionform1")
            .values_list("Quota", flat=True).distinct(),
        "batches": [str(datetime.now().year + i) for i in range(-3, 4)],
        "edit_obj": edit_obj,
    }

    return render(
        request,
        "fee_management/admin/scholarship_fee/scholarship_fee_entry.html",
        context,
    )
 
 
 
def admin_dashboard_view(request):
    stages = TransportStage.objects.all().order_by("stage_no")
    return render(request, "fee_management/admin/dashboard.html", {"stages": stages})

from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from fee_management.models import TransportStage


@require_http_methods(["GET", "POST"])
def transport_stage_entry(request):

    edit_obj = None

    # ================= EDIT LOAD =================
    edit_id = request.GET.get("edit")
    if edit_id:
        edit_obj = get_object_or_404(TransportStage, pk=edit_id)

    # ================= DELETE =================
    if request.method == "POST" and request.POST.get("delete_id"):
        obj = get_object_or_404(TransportStage, pk=request.POST.get("delete_id"))
        obj.delete()
        messages.success(request, "Transport stage deleted successfully.")
        return redirect("transport_stage_entry")

    # ================= CREATE / UPDATE =================
    if request.method == "POST" and request.POST.get("save_stage"):

        entry_id = request.POST.get("entry_id")

        stage_no = request.POST.get("stage_no")
        d_from = request.POST.get("distance_from")
        d_to = request.POST.get("distance_to")
        try:
            stage_no_int = int(stage_no)
            df = Decimal(str(d_from))
            dt = Decimal(str(d_to))
        except (TypeError, ValueError, InvalidOperation):
            messages.error(request, "Enter valid numbers.")
            return redirect("transport_stage_entry")

        if dt < df:
            messages.error(request, "Distance 'To' must be greater than or equal to 'From'.")
            return redirect("transport_stage_entry")

        # Duplicate check
        duplicate = TransportStage.objects.filter(stage_no=stage_no_int)
        if entry_id:
            duplicate = duplicate.exclude(pk=entry_id)

        if duplicate.exists():
            messages.error(request, f"Stage number {stage_no_int} already exists.")
            return redirect("transport_stage_entry")

        if entry_id:
            obj = get_object_or_404(TransportStage, pk=entry_id)
            obj.stage_no = stage_no_int
            obj.distance_from = df
            obj.distance_to = dt
            obj.save()
            messages.success(request, "Transport stage updated successfully.")
        else:
            TransportStage.objects.create(
                stage_no=stage_no_int,
                distance_from=df,
                distance_to=dt,
            )
            messages.success(request, "Transport stage created successfully.")

        return redirect("transport_stage_entry")

    # ================= LIST =================
    qs = TransportStage.objects.all().order_by("stage_no")

    q = (request.GET.get("q") or "").strip()
    if q:
        try:
            qs = qs.filter(stage_no=int(q))
        except ValueError:
            qs = qs.none()

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "stages": page_obj,
        "edit_obj": edit_obj,
        "query": q,
    }

    return render(
        request,
        "fee_management/admin/transport_stage/transport_stage_entry.html",
        context,
    )
    
    


from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from fee_management.models import TransportStage, TransportFee


@require_http_methods(["GET", "POST"])
def transport_fee_entry(request):

    edit_obj = None

    # ================= EDIT LOAD =================
    edit_id = request.GET.get("edit")
    if edit_id:
        edit_obj = get_object_or_404(TransportFee, pk=edit_id)

    # ================= DELETE =================
    if request.method == "POST" and request.POST.get("delete_id"):
        obj = get_object_or_404(TransportFee, pk=request.POST.get("delete_id"))
        obj.delete()
        messages.success(request, "Transport fee deleted successfully.")
        return redirect("transport_fee_entry")

    # ================= CREATE / UPDATE =================
    if request.method == "POST" and request.POST.get("save_fee"):

        entry_id = request.POST.get("entry_id")
        stage_id = request.POST.get("stage")
        bus_stop = (request.POST.get("bus_stop") or "").strip() or None
        aps = request.POST.get("amount_per_semester")
        apy = request.POST.get("amount_per_year")

        try:
            stage = TransportStage.objects.get(pk=int(stage_id))
            aps_val = Decimal(str(aps))
            apy_val = Decimal(str(apy))

            if aps_val < 0 or apy_val < 0:
                raise InvalidOperation

        except (TransportStage.DoesNotExist, TypeError, ValueError):
            messages.error(request, "Select a valid transport stage.")
            return redirect("transport_fee_entry")
        except InvalidOperation:
            messages.error(request, "Enter valid non-negative amounts.")
            return redirect("transport_fee_entry")

        # Duplicate check (only one fee per stage)
        duplicate = TransportFee.objects.filter(stage=stage)
        if entry_id:
            duplicate = duplicate.exclude(pk=entry_id)

        if duplicate.exists():
            messages.error(request, f"Fee for Stage {stage.stage_no} already exists.")
            return redirect("transport_fee_entry")

        if entry_id:
            obj = get_object_or_404(TransportFee, pk=entry_id)
            obj.stage = stage
            obj.bus_stop = bus_stop
            obj.amount_per_semester = aps_val
            obj.amount_per_year = apy_val
            obj.save()
            messages.success(request, "Transport fee updated successfully.")
        else:
            TransportFee.objects.create(
                stage=stage,
                bus_stop=bus_stop,
                amount_per_semester=aps_val,
                amount_per_year=apy_val,
            )
            messages.success(request, "Transport fee created successfully.")

        return redirect("transport_fee_entry")

    # ================= LIST =================
    qs = TransportFee.objects.select_related("stage").all().order_by("stage__stage_no")

    q = (request.GET.get("q") or "").strip()
    if q:
        try:
            qs = qs.filter(stage__stage_no=int(q))
        except ValueError:
            qs = qs.filter(bus_stop__icontains=q)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "fees": page_obj,
        "stages": TransportStage.objects.all().order_by("stage_no"),
        "edit_obj": edit_obj,
        "query": q,
    }

    return render(
        request,
        "fee_management/admin/transport_fee/transport_fee_entry.html",
        context,
    )
 



from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

from user_accounts.models import StudentDetails
from faculty_management.models import general_information
from fee_management.models import ScholarshipType, JaScholarshipEntry
from django.db.models import OuterRef, Exists
from django.template.loader import render_to_string
from django.http import JsonResponse
from user_accounts.decorators import check_permission

@check_permission("ja_scholarship_entry")
@require_http_methods(["GET", "POST"])
def ja_scholarship_entry(request):
    faculty_id = request.user.Employee_id
    faculty = general_information.objects.get(faculty_id=faculty_id)

    # -----------------------------
    # TOP FILTERS (unassigned)
    # -----------------------------
    selected_batch = (request.GET.get("batch") or "").strip()
    selected_section = (request.GET.get("section") or "").strip()

    top_students = StudentDetails.objects.filter(department=faculty.department)
    if selected_batch:
        top_students = top_students.filter(batch=selected_batch)
    if selected_section:
        top_students = top_students.filter(section=selected_section)

    # -----------------------------
    # BOTTOM FILTERS (assigned)
    # -----------------------------
    assigned_batch = (request.GET.get("abatch") or "").strip()
    assigned_section = (request.GET.get("asection") or "").strip()

    bottom_students = StudentDetails.objects.filter(department=faculty.department)
    if assigned_batch:
        bottom_students = bottom_students.filter(batch=assigned_batch)
    if assigned_section:
        bottom_students = bottom_students.filter(section=assigned_section)

    # Dropdown options
    batches = (
        StudentDetails.objects.filter(department=faculty.department)
        .exclude(batch__isnull=True).exclude(batch__exact="")
        .values_list("batch", flat=True).distinct().order_by("batch")
    )
    sections = (
        StudentDetails.objects.filter(department=faculty.department)
        .exclude(section__isnull=True).exclude(section__exact="")
        .values_list("section", flat=True).distinct().order_by("section")
    )
    scholarships = ScholarshipType.objects.all().order_by("name")

    # Helper back url (keeps all params)
    qs = request.META.get("QUERY_STRING", "")
    back_url = request.path + (("?" + qs) if qs else "")

    has_any_entry = JaScholarshipEntry.objects.filter(student=OuterRef("pk"))

    # ✅ Unassigned students (top table)
    unassigned_students = (
        top_students.annotate(is_assigned=Exists(has_any_entry))
        .filter(is_assigned=False)
        .select_related("department")
        .order_by("reg_no")
    )

    # ✅ Assigned list (bottom table)
    assigned_entries = (
        JaScholarshipEntry.objects.filter(student__in=bottom_students)
        .select_related("student", "student__department", "scholarship", "created_by")
        .order_by("student__reg_no")
    )

    # -----------------------------
    # POST Assign (only from unassigned list)
    # -----------------------------
    if request.method == "POST":
        scholarship_type_id = (request.POST.get("scholarship_type_id") or "").strip()
        selected_student_ids = request.POST.getlist("student_ids") or []

        if not scholarship_type_id:
            messages.error(request, "Please select a scholarship.")
            return redirect(back_url)

        if not selected_student_ids:
            messages.error(request, "Please select at least one student.")
            return redirect(back_url)

        sch_type = ScholarshipType.objects.filter(id=scholarship_type_id).first()
        if not sch_type:
            messages.error(request, "Selected scholarship not found.")
            return redirect(back_url)

        # only assign from the filtered unassigned list
        selected_students = unassigned_students.filter(id__in=selected_student_ids)

        created = 0
        skipped = 0

        with transaction.atomic():
            for st in selected_students:
                obj, is_created = JaScholarshipEntry.objects.get_or_create(
                    student=st,
                    defaults={"created_by": faculty, "scholarship": sch_type},
                )
                if is_created:
                    created += 1
                else:
                    skipped += 1

        skipped += (len(selected_student_ids) - selected_students.count())
        messages.success(request, f"Assigned to {created} student(s). Skipped: {skipped}.")
        return redirect(back_url)

    context = {
        "faculty": faculty,

        "batches": batches,
        "sections": sections,
        "scholarships": scholarships,

        "selected_batch": selected_batch,
        "selected_section": selected_section,
        "assigned_batch": assigned_batch,
        "assigned_section": assigned_section,

        "unassigned_students": unassigned_students,
        "assigned_entries": assigned_entries,
    }
    return render(request, "fee_management/admin/scholarship_fee/ja_scholarship_entry.html", context)

