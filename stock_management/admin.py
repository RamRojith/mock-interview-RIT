from django.contrib import admin

from stock_management.models import (
    Stock_Permission,
    Lab,
    StockRegister,
    StockEntry,
    StockItem,
    TransferRequest,
    TransferItem,
    VerificationCycle,
    VerificationAssignment,
    VerificationReport,
    VerificationReportLine,
    Notification,
    StockAuditLog,
)


@admin.register(Lab)
class LabAdmin(admin.ModelAdmin):
    list_display = ("id", "lab_code", "name", "department", "incharge", "is_active")
    search_fields = ("lab_code", "name")
    list_filter = ("is_active", "department")


@admin.register(StockRegister)
class StockRegisterAdmin(admin.ModelAdmin):
    list_display = ("id", "register_number", "lab", "financial_year", "created_date")
    search_fields = ("register_number",)


@admin.register(StockEntry)
class StockEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "bill_number", "item_category", "quantity", "entry_status", "register", "created_at")
    search_fields = ("bill_number", "vendor_name", "item_description")
    list_filter = ("entry_status", "item_category")


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ("id", "asset_tag", "entry", "current_lab", "condition")
    search_fields = ("asset_tag", "serial_no_manufacturer")
    list_filter = ("condition",)


@admin.register(TransferRequest)
class TransferRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "transfer_number", "from_lab", "to_lab", "status", "created_at")
    search_fields = ("transfer_number",)
    list_filter = ("status",)


@admin.register(VerificationCycle)
class VerificationCycleAdmin(admin.ModelAdmin):
    list_display = ("id", "cycle_name", "financial_year", "status", "start_date", "end_date")
    list_filter = ("status",)


@admin.register(VerificationAssignment)
class VerificationAssignmentAdmin(admin.ModelAdmin):
    list_display = ("id", "cycle", "lab", "assigned_faculty", "due_date", "status")
    list_filter = ("status",)


@admin.register(VerificationReport)
class VerificationReportAdmin(admin.ModelAdmin):
    list_display = ("id", "assignment", "submitted_by", "status", "submitted_at")
    list_filter = ("status",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "recipient", "notification_type", "title", "is_read", "created_at")
    list_filter = ("is_read", "notification_type")


@admin.register(StockAuditLog)
class StockAuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "actor", "action", "previous_status", "new_status", "timestamp")
    list_filter = ("action",)


admin.site.register(Stock_Permission)
admin.site.register(TransferItem)
admin.site.register(VerificationReportLine)
