from django.urls import path
# # from faculty_leave_management.views import flm_admin
from faculty_leave_management.views import flm_admin
from faculty_leave_management.views.flm_admin import *
from faculty_leave_management.views.flm_crud import *



urlpatterns = [
#     path('leave_types/list/',LeaveTypeListView.as_view(), name='leave_types_list'),
#     path('leave_types/create/',LeaveTypeCreateView.as_view(), name='leave_types_create'),
      path('faculty_leave_types/create/',faculty_leave_types, name='faculty_leave_types'),
      path('faculty_leave_allotments/list/',faculty_leave_allotments_list, name='faculty_leave_allotments_list'),
#     path('leave_types/delete/<int:pk>/', LeaveTypesDeleteView.as_view(), name='leave_types_delete'),
#     path('leave_allotment/list/', LeaveAllotmentListView.as_view(), name='leave_allotment_list'),
#     path('leave_allotment/create/', LeaveAllotmentCreateView.as_view(), name='leave_allotment_create'),
#     path('leave_allotment/update/<int:pk>/', LeaveAllotmentUpdateView.as_view(), name='leave_allotment_update'),
#     path('delete/<int:pk>/', LeaveAllotmentDeleteView.as_view(), name='leave_allotment_delete'),
        path('flm_assign_permission/',flm_assign_permission,name="flm_assign_permission"),
#     path('leave_application/update/<int:pk>/', LeaveApplicationUpdateView.as_view(), name='leave_application_update'),
#     path('leave_application/list/', LeaveApplicationListView.as_view(), name='leave_application_list'),
#     path('leave_application/delete/<int:pk>/', LeaveApplicationDeleteView.as_view(), name='leave_application_delete'),
    path('api/leave_roles/<int:creatorRoleId>/', api_leave_roles, name='api_leave_roles'),
    path("ccl-timing-master/", ccl_timing_master, name="ccl_timing_master"),
    path("attendance-policy-master/", attendance_policy_master, name="attendance_policy_master"),
    
    path('leave-management/',leave_approval_management, name='leave_approval_management'),
        path("shift-entry/", shift_entry, name="shift_entry"),
    path("permission_timing_master", permission_timing_master, name="permission_timing_master"),
    path("mess_details/", mess_details, name="mess_details"),

    path("device-entry/", device_entry, name="device_entry"),
    path("edit_leave/", edit_leave, name="edit_leave"),
    path("upload_carry_forward/", upload_carry_forward, name="upload_carry_forward"),
    path("faculty_leave_page_permission/", faculty_leave_page_permission, name="faculty_leave_page_permission"),
    



]
