
from django.urls import path
from faculty_management.views import admin_control_fm, fm_control_views, admin_fm_views

urlpatterns = [
    path("fm_assign_permission/", admin_control_fm.fm_assign_permission, name="fm_assign_permission"),
    path("designation_master/", admin_control_fm.designation_master, name="designation_master"),
    path("faculty_category_master/", admin_control_fm.faculty_category_master, name="faculty_category_master"),
    path("approval-resources/add-user/", admin_control_fm.add_approval_user, name="add_approval_user"),
    path("approval-resources/add-role/", admin_control_fm.add_approval_role, name="add_approval_role"),
    path("approval-resources/assign-role/", admin_control_fm.assign_approval_role, name="assign_approval_role"),

    path("export_designation_excel/", admin_control_fm.export_designation_excel, name="export_designation_excel"),

    
    path("admin/faculty/<int:faculty_id>/edit/", admin_control_fm.admin_edit_faculty_details, name="admin_edit_faculty_details"),
    path("admin/faculty/<int:faculty_id>/view/", admin_control_fm.admin_view_faculty_detail, name="admin_view_faculty_detail"),
    path("admin/faculty/<int:faculty_id>/popup/", admin_control_fm.faculty_popup_detail, name="faculty_popup_detail"),
    
    
    path("reports/marks-pdf/", fm_control_views.marks_pdf, name="marks_pdf"),
    
    # Seminar Hall Management
    path("seminar-halls/", admin_fm_views.manage_seminar_halls, name="manage_seminar_halls"),
    path("seminar-halls/approval-hierarchy/", admin_fm_views.shb_approval_hierarchy, name="shb_approval_hierarchy"),
    path("seminar-halls/applications/", admin_fm_views.shb_applications, name="shb_applications"),
    path("seminar-halls/applications/<str:booking_id>/", admin_fm_views.shb_application_detail, name="shb_application_detail"),
    path("seminar-halls/approve/<str:booking_id>/", admin_fm_views.approve_shb_application, name="approve_shb_application"),
    
    # Seminar Hall Booking Workflow API
    path("api/shb-workflow-roles/<int:creator_role_id>/", admin_fm_views.get_shb_workflow_roles, name="get_shb_workflow_roles"),
    path("api/shb-save-workflow/", admin_fm_views.save_shb_workflow, name="save_shb_workflow"),
    
#     path('designation/',DesignationCreateView.as_view(),name="designation_create"),  
#     path('designation/list',DesignationListView.as_view(),name="designations"),  
#     path('designation/update/<int:pk>/', DesignationUpdateView.as_view(), name='designation_update'),
#     path('designation/delete/<int:pk>/', DesignationDeleteView.as_view(), name='designation_delete'),
#     path('pdf/<int:faculty_id>/', generate_faculty_pdf, name='generate_faculty_pdf'),
#     path('faculty_filter/', faculty_filter, name='faculty_filter'),
#     path('export_faculty_excel/', export_faculty_excel, name='export_faculty_excel'),

    path("material/approval-system/", fm_control_views.material_approval_system, name="material_approval_system")

]   
