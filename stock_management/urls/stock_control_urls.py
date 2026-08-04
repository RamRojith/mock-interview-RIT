from django.urls import path
from stock_management.views import (
    admin_stock_views,
    procurement_views,
    transfer_views,
    verification_views,
    notification_views,
)

# These url NAMES are the permission functions (columns in the permission modal
# and items in the sidebar). One landing page per grantable function.
urlpatterns = [
    path("stock_hello/", admin_stock_views.stock_hello, name="stock_hello"),
    path("stock_dashboard/", admin_stock_views.stock_dashboard, name="stock_dashboard"),

    # Master data
    path("lab_management/", admin_stock_views.lab_management, name="lab_management"),
    path("stock_register/", admin_stock_views.stock_register, name="stock_register"),

    # Phase 1 - Procurement
    path("stock_entry/", procurement_views.stock_entry, name="stock_entry"),
    path("stock_entry_approvals/", procurement_views.stock_entry_approvals, name="stock_entry_approvals"),
    path("stock_item/", procurement_views.stock_item, name="stock_item"),

    # Phase 2 - Transfer
    path("transfer/", transfer_views.transfer, name="transfer"),
    path("transfer_approvals/", transfer_views.transfer_approvals, name="transfer_approvals"),

    # Phase 3 - Verification cycle / assignment
    path("verification_cycle/", verification_views.verification_cycle, name="verification_cycle"),
    path("verification_cycle_approvals/", verification_views.verification_cycle_approvals, name="verification_cycle_approvals"),
    path("verification_assignment/", verification_views.verification_assignment, name="verification_assignment"),

    # Phase 4 - Verification report
    path("my_verifications/", verification_views.my_verifications, name="my_verifications"),
    path("verification_report_approvals/", verification_views.verification_report_approvals, name="verification_report_approvals"),

    # Notifications
    path("notifications/", notification_views.notifications, name="notifications"),
]
