from django.urls import path
from faculty_leave_management.urls import flm_admin
from faculty_leave_management.views.flm_admin import *
from faculty_leave_management.views.flm_crud import *
urlpatterns = [

        path('punch_details/', flm_admin.emp_punch_details, name="employee_punch_details"),
        path('emp_mess_bills/', emp_mess_bills, name="employee_mess_bills"),
        path('sync_ccl_from_erp/', sync_ccl_from_erp, name='sync_ccl_from_erp'),
    # path('bulk_approve_all_ccl/', flm_admin.bulk_approve_all_ccl, name='bulk_approve_all_ccl'),
    # bulk_approve_ccl retired — approve_all now goes through ccl_approval_action (flm_control_urls.py)
    path('regenerate_ccl_approvers/', regenerate_ccl_approvers, name='regenerate_ccl_approvers'),
    path('debug_ccl_approvals/', debug_ccl_approvals, name='debug_ccl_approvals'),
    path('fix_approved_ccl_approvers/', fix_approved_ccl_approvers, name='fix_approved_ccl_approvers'),
    path('emp_attendance_export/', emp_attendance_export, name='emp_attendance_export'),
]
