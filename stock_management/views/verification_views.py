"""
Phase 3 (Verification Cycle & Assignment) and Phase 4 (Verification Report).
Follows the same conventions as procurement_views.py:
    @stock_management -> @check_permission("...") -> transaction.atomic(), messages,
    get_object_or_404, notify(...), audit(...).
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from django.urls import reverse

from faculty_management.models import general_information
from stock_management.decorators import stock_management
from user_accounts.decorators import check_permission
from stock_management.models import (
    Lab, StockItem,
    VerificationCycle, VerificationAssignment,
    VerificationReport, VerificationReportLine,
)
from stock_management.views.stock_common import (
    get_logged_in_faculty, is_super, is_principal, is_iso,
    notify, audit, current_financial_year,
)


# ------------------------------------------------------------------
# Local helper: resolve principal recipients (general_information objects)
# ------------------------------------------------------------------
def _principals():
    return general_information.objects.filter(
        designation__designation_name__icontains="principal"
    )


# ==================================================================
# Phase 3 - Verification cycle
# ==================================================================
@stock_management
@check_permission("verification_cycle")
def verification_cycle(request):
    cycles = (
        VerificationCycle.objects.select_related("created_by", "principal_approved_by")
        .order_by("-id")
    )
    return render(request, "stock_management/verification/cycle_list.html", {
        "cycles": cycles,
    })


@stock_management
@check_permission("verification_cycle")
def verification_cycle_create(request):
    faculty = get_logged_in_faculty(request)

    if request.method == "POST":
        data = request.POST
        cycle_name = (data.get("cycle_name") or "").strip()
        financial_year = (data.get("financial_year") or "").strip()
        start_date = data.get("start_date") or None
        end_date = data.get("end_date") or None

        errors = {}
        if not cycle_name:
            errors["cycle_name"] = "Cycle name is required."
        if not financial_year:
            errors["financial_year"] = "Financial year is required."
        if not start_date:
            errors["start_date"] = "Start date is required."
        if not end_date:
            errors["end_date"] = "End date is required."
        if financial_year and VerificationCycle.objects.filter(financial_year=financial_year).exists():
            errors["financial_year"] = "A cycle already exists for this financial year."
        # ISO date strings (YYYY-MM-DD) compare lexicographically == chronologically
        if start_date and end_date and end_date <= start_date:
            errors["end_date"] = "End date must be after the start date."

        if not errors:
            try:
                with transaction.atomic():
                    cycle = VerificationCycle.objects.create(
                        cycle_name=cycle_name,
                        financial_year=financial_year,
                        start_date=start_date,
                        end_date=end_date,
                        status=VerificationCycle.Status.DRAFT,
                        created_by=faculty,
                    )
                    audit(request, "CREATED", target=cycle, new_status=cycle.status)
                messages.success(request, "Verification cycle created.")
                return redirect("verification_cycle_detail", pk=cycle.id)
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
        else:
            for m in errors.values():
                messages.error(request, m)

    return render(request, "stock_management/verification/cycle_form.html", {
        "default_fy": current_financial_year(),
        "form_data": request.POST if request.method == "POST" else {},
    })


@stock_management
@check_permission("verification_cycle")
def verification_cycle_detail(request, pk):
    cycle = get_object_or_404(
        VerificationCycle.objects.select_related("created_by", "principal_approved_by"),
        pk=pk,
    )
    assignments = (
        cycle.assignments
        .select_related("lab", "lab__department", "assigned_faculty")
        .all()
    )
    return render(request, "stock_management/verification/cycle_detail.html", {
        "cycle": cycle,
        "assignments": assignments,
        "is_principal": is_principal(request),
    })


@stock_management
@check_permission("verification_cycle")
def verification_cycle_action(request, pk):
    if request.method != "POST":
        return redirect("verification_cycle_detail", pk=pk)

    action = request.POST.get("action")
    reason = (request.POST.get("reason") or "").strip()
    faculty = get_logged_in_faculty(request)

    with transaction.atomic():
        cycle = (
            VerificationCycle.objects.select_for_update()
            .select_related("created_by").get(pk=pk)
        )
        prev = cycle.status
        S = VerificationCycle.Status

        if action == "submit" and cycle.status == S.DRAFT:
            # Status stays DRAFT; it now appears in the principal approvals queue.
            audit(request, "SUBMITTED", target=cycle, previous_status=prev, new_status=cycle.status)
            for p in _principals():
                notify(
                    p, "VERIFICATION_CYCLE_SUBMITTED",
                    "Verification cycle awaiting approval",
                    f"Cycle '{cycle.cycle_name}' ({cycle.financial_year}) is awaiting your approval.",
                    action_url=reverse("verification_cycle_approvals"), target=cycle,
                )
            messages.success(request, "Submitted to Principal for approval.")

        elif action == "approve" and cycle.status == S.DRAFT and is_principal(request):
            cycle.status = S.ACTIVE
            cycle.principal_approved_by = faculty
            cycle.principal_approved_at = timezone.now()
            cycle.save()
            for a in cycle.assignments.select_related("assigned_faculty", "lab").all():
                a.status = VerificationAssignment.Status.ASSIGNED
                a.principal_approved = True
                a.principal_approved_at = timezone.now()
                a.save()
                notify(
                    a.assigned_faculty, "VERIFICATION_ASSIGNED",
                    "Verification assigned",
                    f"You have been assigned verification of {a.lab} (due {a.due_date}).",
                    action_url=reverse("my_verifications"), target=a,
                )
            audit(request, "APPROVED", target=cycle, previous_status=prev, new_status=cycle.status)
            messages.success(request, "Cycle approved and activated. Faculty notified.")

        elif action == "reject" and is_principal(request):
            # Status stays DRAFT; creator revises.
            notify(
                cycle.created_by, "VERIFICATION_CYCLE_REJECTED",
                "Verification cycle rejected",
                f"Cycle '{cycle.cycle_name}' was rejected: {reason or 'Please revise.'}",
                action_url=reverse("verification_cycle_detail", args=[cycle.id]), target=cycle,
            )
            audit(request, "REJECTED", target=cycle, previous_status=prev,
                  new_status=cycle.status, remarks=reason)
            messages.warning(request, "Cycle sent back to the creator for revision.")

        else:
            messages.warning(request, "Action not allowed at the current stage, or insufficient role.")

    return redirect(request.POST.get("next") or reverse("verification_cycle_detail", args=[pk]))


@stock_management
@check_permission("verification_cycle_approvals")
def verification_cycle_approvals(request):
    cycles = (
        VerificationCycle.objects
        .filter(status=VerificationCycle.Status.DRAFT, assignments__isnull=False)
        .select_related("created_by")
        .distinct()
        .order_by("-id")
    )
    return render(request, "stock_management/verification/cycle_approvals.html", {
        "cycles": cycles,
    })


# ==================================================================
# Phase 3 - Verification assignment
# ==================================================================
@stock_management
@check_permission("verification_assignment")
def verification_assignment(request):
    assignments = (
        VerificationAssignment.objects
        .select_related("cycle", "lab", "lab__department", "assigned_faculty", "assigned_by")
        .order_by("-id")
    )
    cycles = (
        VerificationCycle.objects
        .filter(status=VerificationCycle.Status.DRAFT)
        .order_by("-id")
    )
    labs = Lab.objects.filter(is_active=True).select_related("department")
    faculties = general_information.objects.select_related("department").all()[:500]

    return render(request, "stock_management/verification/assignment_list.html", {
        "assignments": assignments,
        "cycles": cycles,
        "labs": labs,
        "faculties": faculties,
    })


@stock_management
@check_permission("verification_assignment")
def verification_assignment_create(request):
    if request.method != "POST":
        return redirect("verification_assignment")

    faculty = get_logged_in_faculty(request)
    data = request.POST
    cycle_id = data.get("cycle") or None
    lab_id = data.get("lab") or None
    faculty_id = data.get("assigned_faculty") or None
    due_date = data.get("due_date") or None

    cycle = VerificationCycle.objects.filter(id=cycle_id).first() if cycle_id else None
    lab = Lab.objects.filter(id=lab_id).first() if lab_id else None
    assigned_faculty = (
        general_information.objects.filter(id=faculty_id).first() if faculty_id else None
    )

    if not (cycle and lab and assigned_faculty and due_date):
        messages.error(request, "Cycle, lab, faculty and due date are all required.")
        return redirect("verification_assignment")

    # Respect unique_together = (cycle, lab)
    if VerificationAssignment.objects.filter(cycle=cycle, lab=lab).exists():
        messages.error(request, "An assignment for this lab already exists in the selected cycle.")
        return redirect("verification_assignment")

    try:
        with transaction.atomic():
            assignment = VerificationAssignment.objects.create(
                cycle=cycle,
                lab=lab,
                assigned_faculty=assigned_faculty,
                due_date=due_date,
                assigned_by=faculty,
                status=VerificationAssignment.Status.ASSIGNED,
            )
            audit(request, "CREATED", target=assignment, new_status=assignment.status)
        messages.success(request, "Assignment created.")
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")

    return redirect("verification_assignment")


# ==================================================================
# Phase 4 - Verification report
# ==================================================================
@stock_management
@check_permission("my_verifications")
def my_verifications(request):
    faculty = get_logged_in_faculty(request)
    if faculty:
        assignments = (
            VerificationAssignment.objects
            .filter(assigned_faculty=faculty, cycle__status=VerificationCycle.Status.ACTIVE)
            .select_related("cycle", "lab", "lab__department")
            .order_by("-id")
        )
    else:
        assignments = VerificationAssignment.objects.none()

    return render(request, "stock_management/verification/my_verifications.html", {
        "assignments": assignments,
    })


@stock_management
@check_permission("my_verifications")
def verification_report(request, assignment_id):
    assignment = get_object_or_404(
        VerificationAssignment.objects.select_related(
            "cycle", "cycle__created_by", "lab", "lab__department", "assigned_faculty"
        ),
        pk=assignment_id,
    )
    faculty = get_logged_in_faculty(request)
    report, _created = VerificationReport.objects.get_or_create(assignment=assignment)

    # Ensure one line per StockItem currently sitting in the assignment's lab.
    today = timezone.localdate()
    existing_item_ids = set(report.lines.values_list("stock_item_id", flat=True))
    items = (
        StockItem.objects.filter(current_lab=assignment.lab)
        .select_related("entry").order_by("asset_tag")
    )
    next_sl = report.lines.aggregate(m=Max("sl_no"))["m"] or 0
    for item in items:
        if item.id in existing_item_ids:
            continue
        next_sl += 1
        expiry = getattr(item.entry, "warranty_expiry_date", None)
        within = bool(expiry and today <= expiry)
        VerificationReportLine.objects.create(
            report=report,
            stock_item=item,
            sl_no=next_sl,
            qty_as_per_register=1,
            within_warranty=within,
            physical_condition=item.condition,
        )

    lines = report.lines.select_related("stock_item", "stock_item__entry").all()

    if request.method == "POST":
        action = request.POST.get("action")
        C = StockItem.Condition
        errors = []

        # Apply POSTed values to the (cached) line objects in memory.
        for line in lines:
            line.physical_condition = (
                request.POST.get(f"physical_condition_{line.id}") or line.physical_condition
            )
            line.qty_idle = int(request.POST.get(f"qty_idle_{line.id}") or 0)
            line.defect_details = (request.POST.get(f"defect_details_{line.id}") or "").strip() or None
            line.condemnation_reason = (request.POST.get(f"condemnation_reason_{line.id}") or "").strip() or None
            line.missing_details = (request.POST.get(f"missing_details_{line.id}") or "").strip() or None
            line.faculty_remarks = (request.POST.get(f"faculty_remarks_{line.id}") or "").strip() or None

            if action == "submit":
                if line.physical_condition == C.UNDER_REPAIR and not line.defect_details:
                    errors.append(f"SL {line.sl_no}: defect details required for 'Under Repair'.")
                if line.physical_condition == C.CONDEMNED and not line.condemnation_reason:
                    errors.append(f"SL {line.sl_no}: condemnation reason required for 'Condemned'.")
                if line.physical_condition == C.MISSING and not line.missing_details:
                    errors.append(f"SL {line.sl_no}: missing details required for 'Missing'.")

        report.overall_remarks = (request.POST.get("overall_remarks") or "").strip() or None

        if action == "submit" and errors:
            for e in errors:
                messages.error(request, e)
            # fall through to re-render with the in-memory (unsaved) values shown
        else:
            with transaction.atomic():
                for line in lines:
                    line.save()

                if action == "submit":
                    report.status = VerificationReport.Status.SUBMITTED
                    report.submitted_by = faculty
                    report.submitted_at = timezone.now()
                    report.save()
                    assignment.status = VerificationAssignment.Status.SUBMITTED
                    assignment.save()
                    notify(
                        assignment.cycle.created_by, "VERIFICATION_REPORT_SUBMITTED",
                        "Verification report submitted",
                        f"Report for {assignment.lab} ({assignment.cycle.financial_year}) "
                        f"is ready for ISO review.",
                        action_url=reverse("verification_report_approvals"), target=report,
                    )
                    audit(request, "SUBMITTED", target=report, new_status=report.status)
                    messages.success(request, "Verification report submitted.")
                    return redirect("my_verifications")
                else:
                    report.status = VerificationReport.Status.DRAFT
                    report.save()
                    assignment.status = VerificationAssignment.Status.IN_PROGRESS
                    assignment.save()
                    audit(request, "UPDATED", target=report, new_status=report.status)
                    messages.success(request, "Draft saved.")
                    return redirect("verification_report", assignment_id=assignment.id)

    return render(request, "stock_management/verification/verification_report_form.html", {
        "assignment": assignment,
        "report": report,
        "lines": lines,
        "condition_choices": StockItem.Condition.choices,
    })


@stock_management
@check_permission("verification_report_approvals")
def verification_report_approvals(request):
    base = VerificationReport.objects.select_related(
        "assignment", "assignment__cycle", "assignment__lab", "submitted_by"
    )
    iso_reports = base.filter(
        status=VerificationReport.Status.SUBMITTED, iso_approved_by__isnull=True
    ).order_by("-id")
    principal_reports = base.filter(
        status=VerificationReport.Status.SUBMITTED, iso_approved_by__isnull=False
    ).order_by("-id")

    return render(request, "stock_management/verification/report_approvals.html", {
        "iso_reports": iso_reports,
        "principal_reports": principal_reports,
        "is_iso": is_iso(request),
        "is_principal": is_principal(request),
    })


@stock_management
@check_permission("verification_report_approvals")
def verification_report_action(request, pk):
    if request.method != "POST":
        return redirect("verification_report_approvals")

    action = request.POST.get("action")
    reason = (request.POST.get("reason") or "").strip()
    faculty = get_logged_in_faculty(request)

    with transaction.atomic():
        report = (
            VerificationReport.objects.select_for_update()
            .select_related("assignment", "assignment__cycle", "assignment__lab", "submitted_by")
            .get(pk=pk)
        )
        assignment = report.assignment
        prev = report.status
        S = VerificationReport.Status

        if (action == "iso_approve" and report.status == S.SUBMITTED
                and report.iso_approved_by is None and is_iso(request)):
            report.iso_approved_by = faculty
            report.iso_approved_at = timezone.now()
            report.save()
            for p in _principals():
                notify(
                    p, "VERIFICATION_REPORT_ISO_APPROVED",
                    "Report awaiting Principal approval",
                    f"ISO approved the verification report for {assignment.lab}. "
                    f"Awaiting your approval.",
                    action_url=reverse("verification_report_approvals"), target=report,
                )
            audit(request, "APPROVED", target=report, previous_status=prev,
                  new_status=report.status, remarks="ISO approved")
            messages.success(request, "ISO approval recorded. Forwarded to Principal.")

        elif (action == "principal_approve" and report.status == S.SUBMITTED
                and report.iso_approved_by is not None and is_principal(request)):
            report.status = S.APPROVED
            report.principal_approved_by = faculty
            report.principal_approved_at = timezone.now()
            report.save()
            assignment.status = VerificationAssignment.Status.APPROVED
            assignment.save()
            today = timezone.localdate()
            for line in report.lines.select_related("stock_item").all():
                item = line.stock_item
                item.condition = line.physical_condition
                if line.physical_condition == StockItem.Condition.CONDEMNED:
                    item.condemned_date = today
                    item.condemned_reason = line.condemnation_reason or "Condemned during verification."
                item.save()
            notify(
                report.submitted_by, "VERIFICATION_REPORT_APPROVED",
                "Verification report approved",
                f"Your verification report for {assignment.lab} has been approved.",
                action_url=reverse("my_verifications"), target=report,
            )
            audit(request, "APPROVED", target=report, previous_status=prev, new_status=report.status)
            messages.success(request, "Report approved. Asset conditions updated.")

        elif (action == "reject" and report.status == S.SUBMITTED
                and (is_iso(request) or is_principal(request))):
            report.status = S.REJECTED
            report.save()
            assignment.status = VerificationAssignment.Status.IN_PROGRESS
            assignment.save()
            notify(
                report.submitted_by, "VERIFICATION_REPORT_REJECTED",
                "Verification report rejected",
                f"Your report for {assignment.lab} was rejected: {reason or 'Please revise.'}",
                action_url=reverse("verification_report", args=[assignment.id]), target=report,
            )
            audit(request, "REJECTED", target=report, previous_status=prev,
                  new_status=report.status, remarks=reason)
            messages.warning(request, "Report rejected and sent back for revision.")

        else:
            messages.warning(request, "Action not allowed at the current stage, or insufficient role.")

    return redirect(request.POST.get("next") or reverse("verification_report_approvals"))


@stock_management
@check_permission("verification_report_approvals")
def verification_report_pdf(request, pk):
    report = get_object_or_404(
        VerificationReport.objects.select_related(
            "assignment", "assignment__cycle", "assignment__lab", "assignment__lab__department",
            "submitted_by", "iso_approved_by", "principal_approved_by",
        ),
        pk=pk,
    )
    lines = report.lines.select_related("stock_item", "stock_item__entry").all()
    return render(request, "stock_management/verification/report_pdf.html", {
        "report": report,
        "assignment": report.assignment,
        "cycle": report.assignment.cycle,
        "lab": report.assignment.lab,
        "lines": lines,
        "today": timezone.localdate(),
    })
