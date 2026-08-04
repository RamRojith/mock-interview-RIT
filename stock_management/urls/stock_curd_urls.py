from django.urls import path
from stock_management.views import (
    admin_stock_views,
    procurement_views,
    transfer_views,
    verification_views,
    notification_views,
)

# Actions / detail / ajax endpoints. Gated by check_permission of the related
# landing function, but NOT listed as permission columns (not in stock_control_urls).
urlpatterns = [
    path("stock_assign_permission/", admin_stock_views.stock_assign_permission, name="stock_assign_permission"),

    # Master data actions
    path("lab_create/", admin_stock_views.lab_create, name="lab_create"),
    path("lab_edit/<int:pk>/", admin_stock_views.lab_edit, name="lab_edit"),
    path("lab_delete/<int:pk>/", admin_stock_views.lab_delete, name="lab_delete"),
    path("register_create/", admin_stock_views.register_create, name="register_create"),

    # Phase 1 - Procurement
    path("stock_entry_create/", procurement_views.stock_entry_create, name="stock_entry_create"),
    path("stock_entry_detail/<int:pk>/", procurement_views.stock_entry_detail, name="stock_entry_detail"),
    path("stock_entry_edit/<int:pk>/", procurement_views.stock_entry_edit, name="stock_entry_edit"),
    path("stock_entry_action/<int:pk>/", procurement_views.stock_entry_action, name="stock_entry_action"),
    path("stock_item_detail/<int:pk>/", procurement_views.stock_item_detail, name="stock_item_detail"),

    # Phase 2 - Transfer
    path("transfer_create/", transfer_views.transfer_create, name="transfer_create"),
    path("transfer_detail/<int:pk>/", transfer_views.transfer_detail, name="transfer_detail"),
    path("transfer_action/<int:pk>/", transfer_views.transfer_action, name="transfer_action"),
    path("get_lab_items/", transfer_views.get_lab_items, name="get_lab_items"),

    # Phase 3 - Verification cycle / assignment
    path("verification_cycle_create/", verification_views.verification_cycle_create, name="verification_cycle_create"),
    path("verification_cycle_detail/<int:pk>/", verification_views.verification_cycle_detail, name="verification_cycle_detail"),
    path("verification_cycle_action/<int:pk>/", verification_views.verification_cycle_action, name="verification_cycle_action"),
    path("verification_assignment_create/", verification_views.verification_assignment_create, name="verification_assignment_create"),

    # Phase 4 - Verification report
    path("verification_report/<int:assignment_id>/", verification_views.verification_report, name="verification_report"),
    path("verification_report_action/<int:pk>/", verification_views.verification_report_action, name="verification_report_action"),
    path("verification_report_pdf/<int:pk>/", verification_views.verification_report_pdf, name="verification_report_pdf"),

    # Notifications
    path("notifications_mark_read/", notification_views.notifications_mark_read, name="notifications_mark_read"),
]
