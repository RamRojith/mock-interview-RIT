from django.urls import path
from course_management import views
from faculty_management.views import admin_control_fm, fm_control_views, fm_views
from course_management.views import faculty_control_cm
from nba.views import module_4_views



urlpatterns = [
    path("fm_hello/", admin_control_fm.fm_hello, name="fm_hello"),
    path('assign_subject_faculty/', faculty_control_cm.assign_subject_faculty, name="assign_subject_faculty"),
    path("approval-resources/staff/", admin_control_fm.approval_add_staff_page, name="add_employee"),
    path("approval-resources/roles/", admin_control_fm.approval_roles_page, name="add_role"),
    path("approval-resources/assign/", admin_control_fm.approval_assign_role_to_employee_page, name="assign_role_to_employee"),
    
    path('faculty_timetable/', fm_control_views.faculty_timetable, name="faculty_timetable"),
    path('seminar_hall_booking/', fm_control_views.seminar_hall_booking, name="seminar_hall_booking"),
    path('shb_my_approvals/', fm_control_views.shb_my_approvals, name="shb_my_approvals"),
    path('shb_all_applications/', fm_control_views.shb_all_applications, name="shb_all_applications"),
    path('assign_section/', fm_control_views.assign_section, name="assign_section"),

    # Lab Management System (faculty side) — permission: "lab_management"
    path('lab_management/', fm_control_views.lab_management, name="lab_management"),

    
        path("vision_statement/", fm_views.vision_statement, name="vision_statement"),
        path("mission_statement/", fm_views.mission_statement, name="mission_statement"),
        path("program_educational_objectives/", fm_views.program_educational_objectives, name="program_educational_objectives"),
        path("program_specific_outcomes/", fm_views.program_specific_outcomes, name="program_specific_outcomes"),

     path("open_elective_offer/", fm_control_views.open_elective_offer, name="open_elective_offer"),
     path("open-elective-assignments/", fm_control_views.open_elective_assignments_view, name="open_elective_assignments"),

    

    path("upload_announcement/", fm_views.upload_announcement, name="upload_announcement"),
    path("program-org-view/", fm_control_views.program_org_view, name="program_org_view"),
    path("program-org-dashboard/", fm_control_views.program_org_dashboard, name="program_org_dashboard"),
    



    path("admin/faculty/", admin_control_fm.admin_faculty_details, name="employee_details"),
    path("faculty_analysis_dashboard/", fm_views.faculty_analysis_dashboard, name="faculty_analysis_dashboard"),
    
    path('ticket_raise/', fm_control_views.ticket_raise, name='ticket_raise'),
    path("ticket_raise/<int:ticket_id>/",fm_control_views.ticket_raise,name="ticket_raise_update"),
    path("inventory/categories/", fm_control_views.inventory_category_entry, name="inventory_category_entry"),
    path("inventory/items/", fm_control_views.inventory_item_entry, name="inventory_item_entry"),
    path("inventory/item-types/", fm_control_views.inventory_item_type_entry, name="inventory_item_type_entry"),
    path("material/request/", fm_control_views.material_request_entry, name="material_request_entry"),
    path("material/approval/", fm_control_views.material_request_approval, name="material_request_approval"),
    path("material/issue/",fm_control_views.material_issue,name="material_issue"),
    path("material/issue/<int:request_id>/",fm_control_views.material_issue,name="material_issue_detail"),
    path("inventory/low-stock/", fm_control_views.low_stock_dashboard, name="low_stock_dashboard"),
    path("inventory/stock-ledger/", fm_control_views.stock_ledger, name="stock_ledger"),
    path('material_proof_upload/', fm_control_views.material_proof_upload, name='material_proof_upload'),
    path('material_proof_approval/', fm_control_views.material_proof_approval, name='material_proof_approval'),
    
]


