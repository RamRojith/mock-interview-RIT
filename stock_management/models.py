from django.db import models
from django.utils import timezone
from django.utils.dateparse import parse_date
from datetime import timedelta, date
from decimal import Decimal, InvalidOperation

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from user_accounts.models import Add_Department, Role
from faculty_management.models import general_information


# ------------------------------------------------------------------
# Permission model (same mechanism as the other apps)
# ------------------------------------------------------------------
class Stock_Permission(models.Model):
    role = models.ForeignKey(
        "user_accounts.Role",
        on_delete=models.DO_NOTHING,
        db_constraint=False, null=True, blank=True
    )
    function = models.CharField(max_length=500, null=True, blank=True)
    permission = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = "stock_permission"


# ------------------------------------------------------------------
# Departments / Labs  (Department reuses user_accounts.Add_Department)
# ------------------------------------------------------------------
class Lab(models.Model):
    department = models.ForeignKey(
        Add_Department,
        on_delete=models.CASCADE,
        related_name="stock_labs",
    )
    name = models.CharField(max_length=150)
    lab_code = models.CharField(max_length=20, unique=True)
    incharge = models.ForeignKey(
        general_information,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="incharge_labs",
    )
    location = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "stock_lab"
        ordering = ["lab_code"]

    def __str__(self):
        return f"{self.lab_code} - {self.name}"


class StockRegister(models.Model):
    """One register per lab. Immutable once created."""
    lab = models.OneToOneField(
        Lab,
        on_delete=models.CASCADE,
        related_name="register",
    )
    register_number = models.CharField(max_length=30, unique=True)
    created_date = models.DateField(auto_now_add=True)
    financial_year = models.CharField(max_length=9)  # e.g. 2025-26

    class Meta:
        db_table = "stock_register"
        ordering = ["register_number"]

    def __str__(self):
        return f"{self.register_number} ({self.lab.lab_code})"


# ------------------------------------------------------------------
# Phase 1 - Procurement
# ------------------------------------------------------------------
class StockEntry(models.Model):
    class ItemCategory(models.TextChoices):
        EQUIPMENT = "EQUIPMENT", "Equipment"
        FURNITURE = "FURNITURE", "Furniture"
        CONSUMABLE = "CONSUMABLE", "Consumable"
        SOFTWARE = "SOFTWARE", "Software"
        OTHER = "OTHER", "Other"

    class Unit(models.TextChoices):
        NOS = "NOS", "Nos"
        SET = "SET", "Set"
        KG = "KG", "Kg"
        LTR = "LTR", "Litre"
        MTR = "MTR", "Metre"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        APPROVED_INCHARGE = "APPROVED_INCHARGE", "Approved by Incharge"
        APPROVED_HOD = "APPROVED_HOD", "Approved by HOD"
        APPROVED_PRINCIPAL = "APPROVED_PRINCIPAL", "Approved by Principal"
        REJECTED = "REJECTED", "Rejected"

    register = models.ForeignKey(
        StockRegister, on_delete=models.CASCADE, related_name="entries"
    )
    serial_number = models.PositiveIntegerField(null=True, blank=True)  # per register
    bill_number = models.CharField(max_length=50)
    bill_date = models.DateField()
    vendor_name = models.CharField(max_length=200)
    vendor_address = models.TextField()
    vendor_gstin = models.CharField(max_length=15, null=True, blank=True)
    item_description = models.TextField()
    item_category = models.CharField(max_length=20, choices=ItemCategory.choices)
    quantity = models.PositiveIntegerField(default=1)
    unit = models.CharField(max_length=20, choices=Unit.choices, default=Unit.NOS)
    price_per_unit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    warranty_years = models.PositiveSmallIntegerField(default=0)
    warranty_expiry_date = models.DateField(null=True, blank=True)
    bill_scan = models.FileField(upload_to="stock/bills/%Y/%m/", null=True, blank=True)
    page_number = models.PositiveSmallIntegerField(null=True, blank=True)

    entry_status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    rejection_reason = models.TextField(null=True, blank=True)

    entered_by = models.ForeignKey(
        general_information, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="entered_stock_entries",
    )
    incharge_verified_by = models.ForeignKey(
        general_information, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="incharge_verified_entries",
    )
    incharge_verified_at = models.DateTimeField(null=True, blank=True)
    hod_approved_by = models.ForeignKey(
        general_information, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="hod_approved_entries",
    )
    hod_approved_at = models.DateTimeField(null=True, blank=True)
    principal_approved_by = models.ForeignKey(
        general_information, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="principal_approved_entries",
    )
    principal_approved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "stock_entry"
        ordering = ["-id"]

    def __str__(self):
        return f"Entry #{self.id} - {self.bill_number}"

    def save(self, *args, **kwargs):
        # Values can arrive as strings straight from a form POST — normalize them
        # before doing arithmetic / date math so save() never crashes.
        if isinstance(self.bill_date, str):
            self.bill_date = parse_date(self.bill_date) or None

        try:
            qty = int(self.quantity or 0)
        except (TypeError, ValueError):
            qty = 0
        try:
            price = Decimal(str(self.price_per_unit or 0))
        except (InvalidOperation, TypeError, ValueError):
            price = Decimal("0")
        try:
            wy = int(self.warranty_years or 0)
        except (TypeError, ValueError):
            wy = 0

        # total_price = qty x price
        self.total_price = qty * price

        # warranty expiry = bill_date + warranty_years
        if isinstance(self.bill_date, date) and wy:
            try:
                self.warranty_expiry_date = self.bill_date.replace(
                    year=self.bill_date.year + wy
                )
            except ValueError:
                # handle Feb-29 etc.
                self.warranty_expiry_date = self.bill_date + timedelta(days=365 * wy)

        super().save(*args, **kwargs)


class StockItem(models.Model):
    """Individual asset unit (one per physical unit of a StockEntry)."""
    class Condition(models.TextChoices):
        WORKING = "WORKING", "Working"
        IDLE = "IDLE", "Idle"
        UNDER_REPAIR = "UNDER_REPAIR", "Under Repair"
        CONDEMNED = "CONDEMNED", "Condemned"
        MISSING = "MISSING", "Missing"

    entry = models.ForeignKey(
        StockEntry, on_delete=models.CASCADE, related_name="items"
    )
    asset_tag = models.CharField(max_length=30, unique=True)
    serial_no_manufacturer = models.CharField(max_length=100, null=True, blank=True)
    current_lab = models.ForeignKey(
        Lab, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="current_items",
    )
    condition = models.CharField(
        max_length=20, choices=Condition.choices, default=Condition.WORKING
    )
    condemned_date = models.DateField(null=True, blank=True)
    condemned_reason = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "stock_item"
        ordering = ["asset_tag"]

    def __str__(self):
        return self.asset_tag


# ------------------------------------------------------------------
# Phase 2 - Inter-departmental transfer
# ------------------------------------------------------------------
class TransferRequest(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        APPROVED_HOD_SENDER = "APPROVED_HOD_SENDER", "Approved by Sender HOD"
        APPROVED_HOD_RECEIVER = "APPROVED_HOD_RECEIVER", "Approved by Receiver HOD"
        COMPLETED = "COMPLETED", "Completed"
        REJECTED = "REJECTED", "Rejected"

    transfer_number = models.CharField(max_length=30, unique=True, blank=True)
    from_lab = models.ForeignKey(
        Lab, on_delete=models.PROTECT, related_name="outgoing_transfers"
    )
    to_lab = models.ForeignKey(
        Lab, on_delete=models.PROTECT, related_name="incoming_transfers"
    )
    reason = models.TextField()
    status = models.CharField(
        max_length=25, choices=Status.choices, default=Status.DRAFT
    )
    requested_by = models.ForeignKey(
        general_information, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="requested_transfers",
    )
    sender_hod_approved_by = models.ForeignKey(
        general_information, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="sender_hod_transfers",
    )
    sender_hod_approved_at = models.DateTimeField(null=True, blank=True)
    receiver_hod_approved_by = models.ForeignKey(
        general_information, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="receiver_hod_transfers",
    )
    receiver_hod_approved_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        db_table = "stock_transfer_request"
        ordering = ["-id"]

    def __str__(self):
        return self.transfer_number or f"Transfer #{self.id}"

    def save(self, *args, **kwargs):
        if not self.transfer_number:
            year = timezone.localdate().year
            prefix = f"TFR-{year}-"
            last = (
                TransferRequest.objects.filter(transfer_number__startswith=prefix)
                .order_by("-id").first()
            )
            if last and last.transfer_number.split("-")[-1].isdigit():
                nxt = int(last.transfer_number.split("-")[-1]) + 1
            else:
                nxt = 1
            self.transfer_number = f"{prefix}{nxt:03d}"
        super().save(*args, **kwargs)


class TransferItem(models.Model):
    transfer_request = models.ForeignKey(
        TransferRequest, on_delete=models.CASCADE, related_name="items"
    )
    stock_item = models.ForeignKey(
        StockItem, on_delete=models.PROTECT, related_name="transfer_items"
    )
    received_condition = models.CharField(
        max_length=20, choices=StockItem.Condition.choices, null=True, blank=True
    )
    receiver_notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "stock_transfer_item"

    def __str__(self):
        return f"{self.transfer_request_id} - {self.stock_item.asset_tag}"


# ------------------------------------------------------------------
# Phase 3 - Verification cycle & assignment
# ------------------------------------------------------------------
class VerificationCycle(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ACTIVE = "ACTIVE", "Active"
        CLOSED = "CLOSED", "Closed"

    cycle_name = models.CharField(max_length=100)
    financial_year = models.CharField(max_length=9, unique=True)  # e.g. 2025-26
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    created_by = models.ForeignKey(
        general_information, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_verification_cycles",
    )
    principal_approved_by = models.ForeignKey(
        general_information, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="approved_verification_cycles",
    )
    principal_approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        db_table = "stock_verification_cycle"
        ordering = ["-id"]

    def __str__(self):
        return self.cycle_name


class VerificationAssignment(models.Model):
    class Status(models.TextChoices):
        ASSIGNED = "ASSIGNED", "Assigned"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        SUBMITTED = "SUBMITTED", "Submitted"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    cycle = models.ForeignKey(
        VerificationCycle, on_delete=models.CASCADE, related_name="assignments"
    )
    lab = models.ForeignKey(
        Lab, on_delete=models.PROTECT, related_name="verification_assignments"
    )
    assigned_faculty = models.ForeignKey(
        general_information, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="verification_assignments",
    )
    due_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ASSIGNED
    )
    assigned_by = models.ForeignKey(
        general_information, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_verifications",
    )
    principal_approved = models.BooleanField(default=False)
    principal_approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        db_table = "stock_verification_assignment"
        ordering = ["-id"]
        unique_together = ("cycle", "lab")

    def __str__(self):
        return f"{self.cycle.financial_year} - {self.lab.lab_code}"


# ------------------------------------------------------------------
# Phase 4 - Verification report
# ------------------------------------------------------------------
class VerificationReport(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    assignment = models.OneToOneField(
        VerificationAssignment, on_delete=models.CASCADE, related_name="report"
    )
    submitted_by = models.ForeignKey(
        general_information, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="submitted_reports",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    overall_remarks = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    iso_approved_by = models.ForeignKey(
        general_information, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="iso_approved_reports",
    )
    iso_approved_at = models.DateTimeField(null=True, blank=True)
    principal_approved_by = models.ForeignKey(
        general_information, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="principal_approved_reports",
    )
    principal_approved_at = models.DateTimeField(null=True, blank=True)
    pdf_file = models.FileField(upload_to="stock/reports/%Y/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "stock_verification_report"
        ordering = ["-id"]

    def __str__(self):
        return f"Report #{self.id} ({self.assignment})"


class VerificationReportLine(models.Model):
    report = models.ForeignKey(
        VerificationReport, on_delete=models.CASCADE, related_name="lines"
    )
    stock_item = models.ForeignKey(
        StockItem, on_delete=models.PROTECT, related_name="verification_lines"
    )
    sl_no = models.PositiveSmallIntegerField(null=True, blank=True)
    qty_as_per_register = models.PositiveIntegerField(default=1)
    within_warranty = models.BooleanField(default=False)
    physical_condition = models.CharField(
        max_length=20, choices=StockItem.Condition.choices,
        default=StockItem.Condition.WORKING,
    )
    qty_idle = models.PositiveIntegerField(default=0)
    defect_details = models.TextField(null=True, blank=True)
    condemnation_reason = models.TextField(null=True, blank=True)
    missing_details = models.TextField(null=True, blank=True)
    faculty_remarks = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "stock_verification_report_line"
        ordering = ["sl_no", "id"]

    def __str__(self):
        return f"Line {self.sl_no} - {self.stock_item.asset_tag}"


# ------------------------------------------------------------------
# Notifications (in-app) & Audit log
# ------------------------------------------------------------------
class Notification(models.Model):
    recipient = models.ForeignKey(
        general_information, on_delete=models.CASCADE, related_name="stock_notifications"
    )
    notification_type = models.CharField(max_length=40)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    action_url = models.CharField(max_length=300, null=True, blank=True)
    content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    target = GenericForeignKey("content_type", "object_id")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        db_table = "stock_notification"
        ordering = ["-id"]

    def __str__(self):
        return f"{self.notification_type} -> {self.recipient_id}"


class StockAuditLog(models.Model):
    actor = models.ForeignKey(
        general_information, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="stock_audit_logs",
    )
    action = models.CharField(max_length=50)
    content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    target = GenericForeignKey("content_type", "object_id")
    previous_status = models.CharField(max_length=30, null=True, blank=True)
    new_status = models.CharField(max_length=30, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        db_table = "stock_audit_log"
        ordering = ["-id"]

    def __str__(self):
        return f"{self.action} by {self.actor_id}"
