from django.urls import path,include

from faculty_management.views import faculty_data_views, fm_control_views, fm_views, admin_control_fm

urlpatterns = [
    path('faculty_general_information/', faculty_data_views.faculty_general_information, name='faculty_general_information'),
    path('faculty_academic_background/', faculty_data_views.faculty_academic_background, name='faculty_academic_background'),
    path('faculty_academic_experience/', faculty_data_views.faculty_academic_experience, name='faculty_academic_experience'),

    path('faculty_industry_experience/', faculty_data_views.faculty_industry_experience, name='faculty_industry_experience'),

    path('faculty_research_experience/', faculty_data_views.faculty_research_experience, name='faculty_research_experience'),
    path('employee-data-upload/', faculty_data_views.employee_date_upload, name='employee_date_upload'),
    path('employee-data-upload/template/', faculty_data_views.employee_data_upload_template, name='employee_data_upload_template'),

    
path("ajax/departments-for-degree/", fm_control_views.departments_for_degree, name="ajax_departments_for_degree"),
    path("ajax/semesters-for-degree/", fm_control_views.semesters_for_degree, name="ajax_semesters_for_degree"),

    path("get-offered-to-list/", fm_control_views.get_offered_to_list, name="get_offered_to_list"),
    path("get-courses-by-reg-sem/", fm_control_views.get_courses_by_reg_sem, name="get_courses_by_reg_sem"),

     path("ajax/departments-for-degree/", fm_control_views.departments_for_degree, name="ajax_departments_for_degree"),
    path("ajax/semesters-for-degree/", fm_control_views.semesters_for_degree, name="ajax_semesters_for_degree"),
    path("ajax/regulations-for-department/", fm_control_views.regulations_for_department, name="ajax_regulations_for_department"),
    path("ajax/courses-for-selection/", fm_control_views.courses_for_selection, name="ajax_courses_for_selection"),
    path("ajax/iats-for-degree/", fm_control_views.iats_for_degree, name="ajax_iats_for_degree"),
     path("faculty/ajax/assessments-for-degree-iat/", fm_control_views.assessments_for_degree_iat, name="ajax_assessments_for_degree_iat"),
      path('ajax/assessment-weight/', fm_control_views.ajax_assessment_weight, name='ajax_assessment_weight'),
      path("ajax/cos-for-regulation/", fm_control_views.ajax_cos_for_regulation, name="ajax_cos_for_regulation"),
path("ajax/blooms-levels/", fm_control_views.ajax_blooms_levels, name="ajax_blooms_levels"),



       path('professional-society/', fm_control_views.professional_society_view, name='professional_society'),
    path('type-of-program/', fm_control_views.type_of_program, name='type_of_program'),
    
    path("program-org-excel/", fm_control_views.program_org_excel_export, name="program_org_excel_export"),
    path("program-org-pdf/", fm_control_views.program_org_pdf, name="program_org_pdf"),
    path("program-org-permission/", fm_control_views.program_org_permission, name="program_org_permission"),
    path("program-org-permission-api/", fm_control_views.program_org_permission_api, name="program_org_permission_api"),

    path("faculty_data_permission/", fm_control_views.assign_faculty_data_permission, name="assign_faculty_data_permission"),
    path("api/faculty-data-permission/", fm_control_views.faculty_data_permission_api, name="faculty_data_permission_api"),
    path('sync-faculty-data/', admin_control_fm.sync_faculty_data, name='sync_faculty_data'),
    path("ajax/batch-sections-for-course/",fm_control_views. ajax_batch_sections_for_course, name="ajax_batch_sections_for_course"),

    
    
 ]

 
 
