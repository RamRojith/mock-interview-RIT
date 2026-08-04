from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone

from stock_management.decorators import stock_management
from user_accounts.decorators import check_permission
from stock_management.models import Lab, StockItem, TransferRequest, TransferItem
from stock_management.views.stock_common import (
    get_logged_in_faculty, is_super, is_principal, is_hod, is_incharge,
    notify, audit,
)

# Conditions eligible for transfer (spec 5.2: exclude CONDEMNED / MISSING;
# an idle or working asset can move, everything else stays put).
ELIGIBLE_CONDITIONS = [StockItem.Condition.WORKING, StockItem.Condition.IDLE]

# A transfer is "open" (still locks its items) until it is completed or rejected.
OPEN_EXCLUDE = [TransferRequest.Status.COMPLETED, TransferRequest.Status.REJECTED]


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _item_in_open_transfer(stock_item_id, exclude_request_id=None):
    """True if the asset is already committed to an in-flight transfer."""
    qs = TransferItem.objects.filter(stock_item_id=stock_item_id).exclude(
        transfer_request__status__in=OPEN_EXCLUDE
    )
    if exclude_request_id:
        qs = qs.exclude(transfer_request_id=exclude_request_id)
    return qs.exists()


def _detail_url(tr):
    return f"/stock_management/stock_crud/transfer_detail/{tr.id}/"


# ------------------------------------------------------------------
# Transfer list (landing)
# ------------------------------------------------------------------
@stock_management
@check_permission("transfer")
def transfer(request):
    faculty = get_logged_in_faculty(request)
    qs = TransferRequest.objects.select_related(
        "from_lab", "from_lab__department", "to_lab", "to_lab__department", "requested_by"
    )

    if is_super(request) or is_principal(request):
        transfers = qs
    elif is_hod(request):
        dept = getattr(faculty, "department", None) if faculty else None
        transfers = (
            qs.filter(Q(from_lab__department=dept) | Q(to_lab__department=dept))
            if dept else qs.none()
        )
    elif is_incharge(request):
        transfers = (
            qs.filter(
                Q(from_lab__incharge=faculty)
                | Q(to_lab__incharge=faculty)
                | Q(requested_by=faculty)
            )
            if faculty else qs.none()
        )
    else:
        transfers = qs.filter(requested_by=faculty) if faculty else qs.none()

    return render(request, "stock_management/transfer/transfer_list.html", {
        "transfers": transfers.distinct().order_by("-id"),
    })


# ------------------------------------------------------------------
# Approvals queue (url name: transfer_approvals)
# ------------------------------------------------------------------
@stock_management
@check_permission("transfer_approvals")
def transfer_approvals(request):
    faculty = get_logged_in_faculty(request)
    qs = TransferRequest.objects.select_related(
        "from_lab", "from_lab__department", "to_lab", "to_lab__department", "requested_by"
    )
    S = TransferRequest.Status

    if is_super(request) or is_principal(request):
        pending = qs.filter(status__in=[S.SUBMITTED, S.APPROVED_HOD_SENDER, S.APPROVED_HOD_RECEIVER])
    elif is_hod(request):
        dept = getattr(faculty, "department", None) if faculty else None
        pending = qs.filter(status__in=[S.SUBMITTED, S.APPROVED_HOD_SENDER])
        if dept:
            pending = pending.filter(Q(from_lab__department=dept) | Q(to_lab__department=dept))
    elif is_incharge(request):
        pending = qs.filter(status=S.APPROVED_HOD_RECEIVER)
        if faculty:
            pending = pending.filter(Q(from_lab__incharge=faculty) | Q(to_lab__incharge=faculty))
    else:
        pending = qs.none()

    return render(request, "stock_management/transfer/transfer_list.html", {
        "transfers": pending.distinct().order_by("-id"),
        "is_approvals": True,
    })


# ------------------------------------------------------------------
# Create
# ------------------------------------------------------------------
@stock_management
@check_permission("transfer")
def transfer_create(request):
    faculty = get_logged_in_faculty(request)

    if is_super(request) or is_principal(request):
        from_labs = Lab.objects.filter(is_active=True).select_related("department")
    elif faculty:
        from_labs = Lab.objects.filter(is_active=True, incharge=faculty).select_related("department")
    else:
        from_labs = Lab.objects.none()
    to_labs = Lab.objects.filter(is_active=True).select_related("department")

    if request.method == "POST":
        data = request.POST
        from_lab_id = data.get("from_lab") or None
        to_lab_id = data.get("to_lab") or None
        reason = (data.get("reason") or "").strip()
        errors = {}

        from_lab = Lab.objects.filter(id=from_lab_id).first() if from_lab_id else None
        to_lab = Lab.objects.filter(id=to_lab_id).first() if to_lab_id else None

        if not from_lab:
            errors["from_lab"] = "Please select a valid source lab."
        if not to_lab:
            errors["to_lab"] = "Please select a valid destination lab."
        if from_lab and to_lab and from_lab.id == to_lab.id:
            errors["to_lab"] = "Source and destination labs must be different."
        if len(reason) < 20:
            errors["reason"] = "Reason must be at least 20 characters."

        if not errors:
            try:
                with transaction.atomic():
                    obj = TransferRequest(
                        from_lab=from_lab,
                        to_lab=to_lab,
                        reason=reason,
                        status=TransferRequest.Status.DRAFT,
                        requested_by=faculty,
                    )
                    obj.save()  # transfer_number auto-generates in model.save()
                    audit(request, "CREATED", target=obj, new_status=obj.status)
                messages.success(request, f"Transfer request {obj.transfer_number} created as draft.")
                return redirect("transfer_detail", pk=obj.id)
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
        else:
            for m in errors.values():
                messages.error(request, m)

    return render(request, "stock_management/transfer/transfer_form.html", {
        "from_labs": from_labs,
        "to_labs": to_labs,
        "form_data": request.POST if request.method == "POST" else {},
    })


# ------------------------------------------------------------------
# Detail
# ------------------------------------------------------------------
@stock_management
@check_permission("transfer")
def transfer_detail(request, pk):
    obj = get_object_or_404(
        TransferRequest.objects.select_related(
            "from_lab", "from_lab__department", "from_lab__incharge",
            "to_lab", "to_lab__department", "to_lab__incharge",
            "requested_by", "sender_hod_approved_by", "receiver_hod_approved_by",
        ),
        pk=pk,
    )
    items = obj.items.select_related("stock_item", "stock_item__entry").all()
    faculty = get_logged_in_faculty(request)
    is_requester = bool(faculty and obj.requested_by_id and obj.requested_by_id == faculty.id)

    return render(request, "stock_management/transfer/transfer_detail.html", {
        "tr": obj,
        "items": items,
        "can_hod": is_hod(request),
        "can_incharge": is_incharge(request),
        "is_requester": is_requester,
        "condition_choices": StockItem.Condition.choices,
    })


# ------------------------------------------------------------------
# Action (state machine) - POST only
# ------------------------------------------------------------------
@stock_management
@check_permission("transfer")
def transfer_action(request, pk):
    if request.method != "POST":
        return redirect("transfer_detail", pk=pk)

    action = request.POST.get("action")
    reason = (request.POST.get("reason") or "").strip()
    faculty = get_logged_in_faculty(request)
    S = TransferRequest.Status
    valid_conditions = {c for c, _ in StockItem.Condition.choices}

    with transaction.atomic():
        tr = TransferRequest.objects.select_for_update().select_related(
            "from_lab", "from_lab__department", "from_lab__incharge",
            "to_lab", "to_lab__department", "to_lab__incharge", "requested_by",
        ).get(pk=pk)
        prev = tr.status

        # ---- add items (DRAFT only) ------------------------------
        if action == "add_item" and tr.status == S.DRAFT:
            ids = request.POST.getlist("stock_items")
            existing_ids = set(tr.items.values_list("stock_item_id", flat=True))
            added, skipped = 0, 0
            for raw in ids:
                try:
                    sid = int(raw)
                except (TypeError, ValueError):
                    continue
                if sid in existing_ids:
                    continue  # skip dupes already on this request
                item = StockItem.objects.filter(id=sid).first()
                if (
                    not item
                    or item.current_lab_id != tr.from_lab_id
                    or item.condition not in ELIGIBLE_CONDITIONS
                    or _item_in_open_transfer(item.id, exclude_request_id=tr.id)
                ):
                    skipped += 1
                    continue
                TransferItem.objects.create(transfer_request=tr, stock_item=item)
                existing_ids.add(sid)
                added += 1
            if added:
                audit(request, "UPDATED", target=tr, remarks=f"Added {added} item(s).")
                messages.success(request, f"Added {added} item(s) to the transfer.")
            if skipped:
                messages.warning(request, f"Skipped {skipped} ineligible item(s).")
            if not added and not skipped:
                messages.info(request, "No items were selected.")

        # ---- submit (DRAFT -> SUBMITTED) -------------------------
        elif action == "submit" and tr.status == S.DRAFT:
            if not tr.items.exists():
                messages.error(request, "Add at least one item before submitting.")
            else:
                tr.status = S.SUBMITTED
                tr.save(update_fields=["status"])
                audit(request, "SUBMITTED", target=tr, previous_status=prev, new_status=tr.status)
                notify(tr.from_lab.incharge, "TRANSFER_APPROVAL_NEEDED",
                       "Transfer submitted",
                       f"Transfer {tr.transfer_number} awaits sender HOD approval.",
                       action_url=_detail_url(tr), target=tr)
                messages.success(request, "Transfer submitted for approval.")

        # ---- sender HOD approve (SUBMITTED -> APPROVED_HOD_SENDER)
        elif action == "approve_sender" and tr.status == S.SUBMITTED and is_hod(request):
            tr.status = S.APPROVED_HOD_SENDER
            tr.sender_hod_approved_by = faculty
            tr.sender_hod_approved_at = timezone.now()
            tr.save(update_fields=["status", "sender_hod_approved_by", "sender_hod_approved_at"])
            audit(request, "APPROVED", target=tr, previous_status=prev, new_status=tr.status)
            notify(tr.to_lab.incharge, "TRANSFER_APPROVAL_NEEDED",
                   "Transfer needs receiver HOD approval",
                   f"Transfer {tr.transfer_number} approved by sender HOD.",
                   action_url=_detail_url(tr), target=tr)
            messages.success(request, "Approved as sender HOD. Forwarded to receiver HOD.")

        # ---- receiver HOD approve (-> APPROVED_HOD_RECEIVER) -----
        elif action == "approve_receiver" and tr.status == S.APPROVED_HOD_SENDER and is_hod(request):
            tr.status = S.APPROVED_HOD_RECEIVER
            tr.receiver_hod_approved_by = faculty
            tr.receiver_hod_approved_at = timezone.now()
            tr.save(update_fields=["status", "receiver_hod_approved_by", "receiver_hod_approved_at"])
            audit(request, "APPROVED", target=tr, previous_status=prev, new_status=tr.status)
            notify(tr.from_lab.incharge, "TRANSFER_APPROVED", "Transfer approved",
                   f"Transfer {tr.transfer_number} approved by receiver HOD.",
                   action_url=_detail_url(tr), target=tr)
            notify(tr.to_lab.incharge, "TRANSFER_APPROVED", "Transfer approved",
                   f"Transfer {tr.transfer_number} approved. Ready to complete.",
                   action_url=_detail_url(tr), target=tr)
            messages.success(request, "Approved as receiver HOD. Ready for completion.")

        # ---- reject (SUBMITTED / APPROVED_HOD_SENDER -> DRAFT) ---
        elif action == "reject" and tr.status in [S.SUBMITTED, S.APPROVED_HOD_SENDER]:
            tr.status = S.DRAFT
            tr.save(update_fields=["status"])
            audit(request, "REJECTED", target=tr, previous_status=prev, new_status=tr.status, remarks=reason)
            notify(tr.requested_by, "TRANSFER_REJECTED", "Transfer rejected",
                   f"Transfer {tr.transfer_number} was returned to draft: {reason or 'No reason provided.'}",
                   action_url=_detail_url(tr), target=tr)
            messages.warning(request, "Transfer rejected and returned to draft.")

        # ---- complete (APPROVED_HOD_RECEIVER -> COMPLETED) -------
        elif action == "complete" and tr.status == S.APPROVED_HOD_RECEIVER and is_incharge(request):
            tr.status = S.COMPLETED
            tr.completed_at = timezone.now()
            tr.save(update_fields=["status", "completed_at"])
            for ti in tr.items.select_related("stock_item").all():
                rc = request.POST.get(f"received_condition_{ti.id}") or StockItem.Condition.WORKING
                if rc not in valid_conditions:
                    rc = StockItem.Condition.WORKING
                ti.received_condition = rc
                ti.save(update_fields=["received_condition"])
                si = ti.stock_item
                si.current_lab = tr.to_lab
                si.condition = rc
                si.save(update_fields=["current_lab", "condition", "updated_at"])
            audit(request, "COMPLETED", target=tr, previous_status=prev, new_status=tr.status)
            notify(tr.from_lab.incharge, "TRANSFER_COMPLETED", "Transfer completed",
                   f"Transfer {tr.transfer_number} completed. Items moved out of {tr.from_lab.lab_code}.",
                   action_url=_detail_url(tr), target=tr)
            notify(tr.to_lab.incharge, "TRANSFER_COMPLETED", "Transfer completed",
                   f"Transfer {tr.transfer_number} completed. Items received at {tr.to_lab.lab_code}.",
                   action_url=_detail_url(tr), target=tr)
            messages.success(request, "Transfer completed. Assets moved to the destination lab.")

        else:
            messages.warning(request, "Action not allowed at the current stage, or insufficient role.")

    next_url = request.POST.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("transfer_detail", pk=pk)


# ------------------------------------------------------------------
# AJAX: eligible items for a lab
# ------------------------------------------------------------------
@stock_management
def get_lab_items(request):
    lab_id = request.GET.get("lab_id")
    data = []
    if lab_id:
        items = (
            StockItem.objects
            .filter(current_lab_id=lab_id, condition__in=ELIGIBLE_CONDITIONS)
            .select_related("entry")
            .order_by("asset_tag")
        )
        for it in items:
            if _item_in_open_transfer(it.id):
                continue
            desc = (it.entry.item_description or "")[:80] if it.entry_id else ""
            data.append({
                "id": it.id,
                "asset_tag": it.asset_tag,
                "description": desc,
                "condition": it.condition,
            })
    return JsonResponse({"items": data})
