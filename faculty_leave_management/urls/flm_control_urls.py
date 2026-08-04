from django.urls import path,include
from faculty_leave_management.views import flm_admin
from faculty_leave_management.views.flm_admin import *
from faculty_leave_management.views.flm_crud import *


urlpatterns = [
    path('flm_hello/', flm_admin.flm_hello, name='flm_hello'),
    # path('apply_form/',LeaveApplicationCreateView.as_view(),name="apply_leave"),
    path('permission_form/', permission_form, name='permission_form'),
    path("leave_application_form/", leave_application_form, name="leave_application_form"),
    path('leave_approvals/', leave_approvals, name="leave_approvals"),
    #  path('pending_leave_applications/', pending_leave_applications, name="pending_leave_applications"),
    #  path('approved_leave_applications/', approved_leave_applications, name="approved_leave_applications"),
    #       path('rejected_leave_applications/', rejected_leave_applications, name="rejected_leave_applications"),
    path('punch_attendance/', flm_admin.punch_attendance , name="punch_attendance"),
    path('mess_bills/', flm_admin.mess_bills, name="mess_bills"),
    path('add_ccl_claim/', ccl_application_form, name='add_ccl_claim'),
    path('add_ccl_claim/data/', ccl_application_data, name='ccl_application_data'),
    path('add_ccl_claim/save/', ccl_application_save, name='ccl_application_save'),
    path('add_ccl_claim/delete/', ccl_application_delete, name='ccl_application_delete'),
    path("ccl_approval/", ccl_approval, name="ccl_approval"),
    path("ccl_approval/data/", ccl_approval_data, name="ccl_approval_data"),
    path("ccl_approval/action/", ccl_approval_action, name="ccl_approval_action"),
    path("ccl_approval/export/", ccl_approval_export, name="ccl_approval_export"),

    path('emp_attandance_report/', flm_admin.emp_attandance_report, name="employee_attandance_report"),

    path('award_ccl_admin/', flm_admin.award_ccl_admin, name="award_ccl_to_employee"),
    path('punch-entry/', flm_admin.punch_entry, name='punch_entry'),
    path("Employee_holidays/", Employee_holidays, name="Employee_holidays"),
    path("employee_leave_dashboard/", employee_leave_dashboard, name="employee_leave_dashboard"),
    path("college_data/", college_data, name="college_data"),
    path("releaving_order/", releaving_order, name="releaving_order"),
    path("relieve_faculty/<int:faculty_id>/", relieve_faculty, name="relieve_faculty"),
    path("releaving_order/<int:faculty_id>/pdf/", relieving_order_pdf, name="relieving_order_pdf"),
    path("punch_dashboard/", punch_dashboard, name="punch_dashboard"),

   
]




