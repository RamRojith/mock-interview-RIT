from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from stock_management.decorators import stock_management
from user_accounts.decorators import check_permission
from stock_management.models import StockRegister, StockEntry, StockItem, Lab
from stock_management.views.stock_common import (
    get_logged_in_faculty, is_super, is_principal, is_hod, is_iso, is_incharge,
    generate_asset_tag, notify, audit,
)


# ------------------------------------------------------------------
# Scope helper: which entries can this user see
# ------------------------------------------------------------------
def _visible_entries(request, faculty):
    qs = StockEntry.objects.select_related("register", "register__lab", "register__lab__department", "entered_by")
    if is_super(request) or is_principal(request) or is_iso(request):
        return qs
    dept = getattr(faculty, "department", None) if faculty else None
    if is_hod(request) and dept:
        return qs.filter(register__lab__department=dept)
    if faculty:
        return qs.filter(register__lab__incharge=faculty) | qs.filter(entered_by=faculty)
    return qs.none()


# ------------------------------------------------------------------
# Stock Entry list (landing)
# ------------------------------------------------------------------
@stock_management
@check_permission("stock_entry")
def stock_entry(request):
    faculty = get_logged_in_faculty(request)
    entries = _visible_entries(request, faculty).distinct().order_by("-id")

    status = request.GET.get("status")
    if status:
        entries = entries.filter(entry_status=status)

    return render(request, "stock_management/procurement/stock_entry_list.html", {
        "entries": entries,
        "status_choices": StockEntry.Status.choices,
        "selected_status": status or "",
    })


# ------------------------------------------------------------------
# Create
# ------------------------------------------------------------------
@stock_management
@check_permission("stock_entry")
def stock_entry_create(request):
    faculty = get_logged_in_faculty(request)

    if is_super(request) or is_principal(request):
        registers = StockRegister.objects.select_related("lab")
    elif faculty:
        registers = StockRegister.objects.select_related("lab").filter(lab__incharge=faculty)
    else:
        registers = StockRegister.objects.none()

    if request.method == "POST":
        register_id = request.POST.get("register") or None
        data = request.POST
        errors = {}

        register = StockRegister.objects.filter(id=register_id).first() if register_id else None
        if not register:
            errors["register"] = "Please select a valid stock register."
        for f in ["bill_number", "bill_date", "vendor_name", "vendor_address", "item_description", "item_category", "quantity", "price_per_unit"]:
            if not data.get(f):
                errors[f] = "This field is required."

        if not errors:
            try:
                with transaction.atomic():
                    next_serial = (
                        StockEntry.objects.filter(register=register).aggregate(m=Max("serial_number"))["m"] or 0
                    ) + 1
                    entry = StockEntry(
                        register=register,
                        serial_number=next_serial,
                        bill_number=data.get("bill_number").strip(),
                        bill_date=data.get("bill_date"),
                        vendor_name=data.get("vendor_name").strip(),
                        vendor_address=data.get("vendor_address").strip(),
                        vendor_gstin=(data.get("vendor_gstin") or "").strip() or None,
                        item_description=data.get("item_description").strip(),
                        item_category=data.get("item_category"),
                        quantity=int(data.get("quantity") or 1),
                        unit=data.get("unit") or StockEntry.Unit.NOS,
                        price_per_unit=data.get("price_per_unit") or 0,
                        warranty_years=int(data.get("warranty_years") or 0),
                        page_number=(data.get("page_number") or None),
                        entry_status=StockEntry.Status.DRAFT,
                        entered_by=faculty,
                    )
                    if request.FILES.get("bill_scan"):
                        entry.bill_scan = request.FILES["bill_scan"]
                    entry.save()
                    audit(request, "CREATED", target=entry, new_status=entry.entry_status)
                messages.success(request, "Stock entry saved as draft.")
                return redirect("stock_entry_detail", pk=entry.id)
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
        else:
            for m in errors.values():
                messages.error(request, m)

    return render(request, "stock_management/procurement/stock_entry_form.html", {
        "registers": registers,
        "category_choices": StockEntry.ItemCategory.choices,
        "unit_choices": StockEntry.Unit.choices,
        "form_data": request.POST if request.method == "POST" else {},
        "is_edit": False,
    })


# ------------------------------------------------------------------
# Edit (DRAFT / REJECTED only)
# ------------------------------------------------------------------
@stock_management
@check_permission("stock_entry")
def stock_entry_edit(request, pk):
    entry = get_object_or_404(StockEntry, pk=pk)
    if entry.entry_status not in [StockEntry.Status.DRAFT, StockEntry.Status.REJECTED]:
        messages.error(request, "Only draft or rejected entries can be edited.")
        return redirect("stock_entry_detail", pk=pk)

    if request.method == "POST":
        data = request.POST
        entry.bill_number = data.get("bill_number", entry.bill_number).strip()
        entry.bill_date = data.get("bill_date") or entry.bill_date
        entry.vendor_name = data.get("vendor_name", entry.vendor_name).strip()
        entry.vendor_address = data.get("vendor_address", entry.vendor_address).strip()
        entry.vendor_gstin = (data.get("vendor_gstin") or "").strip() or None
        entry.item_description = data.get("item_description", entry.item_description).strip()
        entry.item_category = data.get("item_category") or entry.item_category
        entry.quantity = int(data.get("quantity") or entry.quantity)
        entry.unit = data.get("unit") or entry.unit
        entry.price_per_unit = data.get("price_per_unit") or entry.price_per_unit
        entry.warranty_years = int(data.get("warranty_years") or 0)
        entry.page_number = data.get("page_number") or entry.page_number
        if request.FILES.get("bill_scan"):
            entry.bill_scan = request.FILES["bill_scan"]
        if entry.entry_status == StockEntry.Status.REJECTED:
            entry.entry_status = StockEntry.Status.DRAFT
            entry.rejection_reason = None
        entry.save()
        audit(request, "UPDATED", target=entry, new_status=entry.entry_status)
        messages.success(request, "Stock entry updated.")
        return redirect("stock_entry_detail", pk=pk)

    return render(request, "stock_management/procurement/stock_entry_form.html", {
        "entry": entry,
        "registers": StockRegister.objects.select_related("lab"),
        "category_choices": StockEntry.ItemCategory.choices,
        "unit_choices": StockEntry.Unit.choices,
        "form_data": {},
        "is_edit": True,
    })


# ------------------------------------------------------------------
# Detail
# ------------------------------------------------------------------
@stock_management
@check_permission("stock_entry")
def stock_entry_detail(request, pk):
    entry = get_object_or_404(
        StockEntry.objects.select_related("register", "register__lab", "entered_by"), pk=pk
    )
    items = entry.items.select_related("current_lab").all()
    return render(request, "stock_management/procurement/stock_entry_detail.html", {
        "entry": entry,
        "items": items,
        "can_incharge": is_incharge(request),
        "can_hod": is_hod(request),
        "can_principal": is_principal(request),
    })


# ------------------------------------------------------------------
# Approvals queue
# ------------------------------------------------------------------
@stock_management
@check_permission("stock_entry_approvals")
def stock_entry_approvals(request):
    faculty = get_logged_in_faculty(request)
    qs = StockEntry.objects.select_related("register", "register__lab", "register__lab__department", "entered_by")

    role = "none"
    if is_principal(request):
        pending = qs.filter(entry_status=StockEntry.Status.APPROVED_HOD)
        role = "principal"
    elif is_hod(request):
        dept = getattr(faculty, "department", None)
        pending = qs.filter(entry_status=StockEntry.Status.APPROVED_INCHARGE)
        if dept:
            pending = pending.filter(register__lab__department=dept)
        role = "hod"
    elif is_incharge(request):
        pending = qs.filter(entry_status=StockEntry.Status.SUBMITTED)
        if faculty:
            pending = pending.filter(register__lab__incharge=faculty)
        role = "incharge"
    else:
        pending = qs.none()

    return render(request, "stock_management/procurement/stock_entry_approvals.html", {
        "pending": pending.order_by("-id"),
        "role": role,
    })


# ------------------------------------------------------------------
# Action (state machine)  POST only
# ------------------------------------------------------------------
@stock_management
@check_permission("stock_entry")
def stock_entry_action(request, pk):
    if request.method != "POST":
        return redirect("stock_entry_detail", pk=pk)

    action = request.POST.get("action")
    reason = (request.POST.get("reason") or "").strip()
    faculty = get_logged_in_faculty(request)

    with transaction.atomic():
        entry = StockEntry.objects.select_for_update().select_related(
            "register", "register__lab", "register__lab__department", "entered_by"
        ).get(pk=pk)
        prev = entry.entry_status
        S = StockEntry.Status

        if action == "submit" and entry.entry_status == S.DRAFT:
            entry.entry_status = S.SUBMITTED
            entry.save(update_fields=["entry_status", "updated_at"])
            audit(request, "SUBMITTED", target=entry, previous_status=prev, new_status=entry.entry_status)
            notify(entry.register.lab.incharge, "STOCK_APPROVAL_NEEDED",
                   "Stock entry submitted", f"Entry {entry.bill_number} awaits verification.",
                   action_url=f"/stock_management/stock_crud/stock_entry_detail/{entry.id}/", target=entry)
            messages.success(request, "Submitted for approval.")

        elif action == "verify" and entry.entry_status == S.SUBMITTED and is_incharge(request):
            entry.entry_status = S.APPROVED_INCHARGE
            entry.incharge_verified_by = faculty
            entry.incharge_verified_at = timezone.now()
            entry.save()
            audit(request, "APPROVED", target=entry, previous_status=prev, new_status=entry.entry_status)
            messages.success(request, "Verified. Forwarded to HOD.")

        elif action == "approve_hod" and entry.entry_status == S.APPROVED_INCHARGE and is_hod(request):
            entry.entry_status = S.APPROVED_HOD
            entry.hod_approved_by = faculty
            entry.hod_approved_at = timezone.now()
            entry.save()
            audit(request, "APPROVED", target=entry, previous_status=prev, new_status=entry.entry_status)
            messages.success(request, "Approved. Forwarded to Principal.")

        elif action == "approve_principal" and entry.entry_status == S.APPROVED_HOD and is_principal(request):
            entry.entry_status = S.APPROVED_PRINCIPAL
            entry.principal_approved_by = faculty
            entry.principal_approved_at = timezone.now()
            entry.save()
            # Generate one StockItem per unit with an asset tag
            for i in range(1, (entry.quantity or 0) + 1):
                StockItem.objects.create(
                    entry=entry,
                    asset_tag=generate_asset_tag(entry, i),
                    current_lab=entry.register.lab,
                    condition=StockItem.Condition.WORKING,
                )
            audit(request, "APPROVED", target=entry, previous_status=prev, new_status=entry.entry_status)
            notify(entry.entered_by, "STOCK_APPROVED", "Stock entry approved",
                   f"Entry {entry.bill_number} is now live. Asset tags generated.", target=entry)
            messages.success(request, "Approved. Asset items generated.")

        elif action == "reject" and entry.entry_status not in [S.DRAFT, S.APPROVED_PRINCIPAL, S.REJECTED]:
            entry.entry_status = S.REJECTED
            entry.rejection_reason = reason or "No reason provided."
            entry.save()
            audit(request, "REJECTED", target=entry, previous_status=prev, new_status=entry.entry_status, remarks=reason)
            notify(entry.entered_by, "STOCK_REJECTED", "Stock entry rejected",
                   f"Entry {entry.bill_number} was rejected: {entry.rejection_reason}", target=entry)
            messages.error(request, "Entry rejected.")
        else:
            messages.warning(request, "Action not allowed at the current stage, or insufficient role.")

    return redirect(request.POST.get("next") or "stock_entry_approvals")


# ------------------------------------------------------------------
# Stock items (assets)
# ------------------------------------------------------------------
@stock_management
@check_permission("stock_item")
def stock_item(request):
    items = StockItem.objects.select_related("entry", "current_lab", "current_lab__department").order_by("-id")
    lab_id = request.GET.get("lab")
    cond = request.GET.get("condition")
    if lab_id:
        items = items.filter(current_lab_id=lab_id)
    if cond:
        items = items.filter(condition=cond)
    return render(request, "stock_management/procurement/stock_item_list.html", {
        "items": items[:500],
        "labs": Lab.objects.all(),
        "condition_choices": StockItem.Condition.choices,
        "selected_lab": lab_id or "",
        "selected_condition": cond or "",
    })


@stock_management
@check_permission("stock_item")
def stock_item_detail(request, pk):
    item = get_object_or_404(
        StockItem.objects.select_related("entry", "entry__register", "current_lab"), pk=pk
    )
    return render(request, "stock_management/procurement/stock_item_detail.html", {
        "item": item,
        "transfer_items": item.transfer_items.select_related("transfer_request").all(),
    })
