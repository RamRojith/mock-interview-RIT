from django.urls import path
from course_management.views.admin_control_cm import *
from course_management.views.faculty_control_cm import *

from django.conf.urls.static import static
from django.conf import settings
from django.utils import timezone



urlpatterns = [
    # path('ajax/get-departments/', get_departments, name='ajax_get_departments'),
    path('ajax/get-sections/', get_sections, name='get_sections'),
    path('ajax/get-course-categories/', get_course_categories, name='get_course_categories'),
    path('ajax/get-courses/', get_courses_only, name='get_courses_only'),
    # path('add-period-allocation/', add_period_allocation, name='add_period_allocation'),



    path('cp/get_departments/', cp_get_departments, name='cp_get_departments'),
    path('cp/get_years_semesters/', cp_get_years_semesters, name='cp_get_years_semesters'),
    path('cp/get_courses/', cp_get_courses, name='cp_get_courses'),

    # Subject Willingness
    path('sw/get_departments/', sw_get_departments, name='sw_get_departments'),
    path('sw/get_years_semesters/', sw_get_years_semesters, name='sw_get_years_semesters'),
    path('sw/get_courses/', sw_get_courses, name='sw_get_courses'),
    path("get_ltp_config/", get_ltp_config, name="get_ltp_config"),
    path("hour_allocation/save/", hour_allocation_save, name="hour_allocation_save"),
    path("consolidate_admin/", admin_consolidate, name="admin_consolidate"),
     path("admin/consolidate/api/departments/", api_consolidate_departments, name="api_consolidate_departments"),
    path("admin/consolidate/api/batches/", api_consolidate_batches, name="api_consolidate_batches"),
    path("admin/consolidate/api/sections/", api_consolidate_sections, name="api_consolidate_sections"),
    path("ajax/consolidate_admin/semesters/", api_consolidate_semesters, name="api_consolidate_semesters"),
path("admin/consolidate/api/courses/", api_consolidate_courses, name="api_consolidate_courses"),
 path("consolidate/download-pdf/", download_consolidated_pdf, name="download_consolidated_pdf"),
 path("internal_admin/", internal_admin, name="internal_admin"),
 path("api/internal/departments/", api_internal_departments, name="api_internal_departments"),
    path("api/internal/batches/", api_internal_batches, name="api_internal_batches"),
    path("api/internal/sections/",api_internal_sections, name="api_internal_sections"),
    path("api/internal/semesters/", api_internal_semesters, name="api_internal_semesters"),
    path("api/internal/courses/", api_internal_courses, name="api_internal_courses"),
    path("internal-admin/download-pdf/", internal_admin_download_pdf, name="internal_admin_download_pdf"),
    path("ajax/internal_exam_schedule/", internal_exam_schedule, name="internal_exam_schedule"),
    
    path("ajax/departments-by-degree/", departments_by_degree, name="departments_by_degree"),
    path("internal-exam-schedule/view/", view_internal_exam_schedule, name="view_internal_exam_schedule"),
      path("internal-exam-schedule/filter/degrees/", ies_degrees, name="ies_degrees"),
    path("internal-exam-schedule/filter/departments/", ies_departments, name="ies_departments"),
    path("internal-exam-schedule/filter/regulations/", ies_regulations, name="ies_regulations"),
    path("internal-exam-schedule/filter/semesters/", ies_semesters, name="ies_semesters"),
    path("internal-exam-schedule/filter/courses/", ies_courses, name="ies_courses"),
    path("internal-exam-schedule/filter/dates/", ies_dates, name="ies_dates"),
     path("internal-exam-schedule/update/", ies_update, name="ies_update"),
    path("internal-exam-schedule/delete/<int:pk>/", ies_delete, name="ies_delete"),
    path("internal-exam-schedule/delete-all/", ies_delete_all, name="ies_delete_all"),
    path("ajax/internal-assessments/", internal_assessments_by_degree, name="internal_assessments_by_degree"),
    path("internal-exam-schedule/publish/",ies_publish, name="ies_publish"),
    path(
    "internal-exam-schedule/bulk-session-update/",
    ies_bulk_session_update,
    name="ies_bulk_session_update"),
    path(
    "internal-exam-schedule/semesters-by-department/",
ies_semesters_by_department,
    name="ies_semesters_by_department"
),
path(
    "internal-exam/published/",
   published_internal_exam_schedule,
    name="published_internal_exam_schedule"
),
   path("ajax/degrees/", load_adi_degrees, name="load_degrees"),
    path("ajax/departments/", load_adi_departments, name="load_departments"),
    path("ajax/batches/", load_adi_batches, name="load_batches"),
    path("ajax/semesters/", load_adi_semesters, name="load_semesters"),
    path("ajax/iats/", load_adi_iats, name="load_iats"),
    path("ajax/timetable/", load_adi_timetable, name="load_timetable"),
    # urls.py
path("admin_internal_timetable_pdf/", admin_internal_timetable_pdf, name="admin_internal_timetable_pdf"),

    path('ajax/get-departments/', get_departments, name='get_departments'),

    # path('ajax/get-programmes/', get_programmes, name='get_programmes'),
    path('ajax/get-departments/', get_departments, name='get_departments'),
    # path('ajax/filter-courses/', filter_courses, name='filter_courses'),
    

path("semester_exam_schedule", semester_exam_schedule, name="semester_exam_schedule"),
    path("semester_departments_by_degree/", semester_departments_by_degree, name="semester_departments_by_degree"),
    path('view_semester_exam_schedule/', view_semester_exam_schedule, name='view_semester_exam_schedule'),



path("ses_update/update/", ses_update, name="ses_update"),
    path("ses_delete/delete/<int:pk>/", ses_delete, name="ses_delete"),
    path("ses_delete_all/delete-all/", ses_delete_all, name="ses_delete_all"),
    path("ses/semesters-by-department/", ses_semesters_by_department, name="ses_semesters_by_department"),

   path(
    "ses_bulk_session_update/bulk-session-update/",
    ses_bulk_session_update,
    name="ses_bulk_session_update"),


 path("ses/degrees/", ses_degrees, name="ses_degrees"),
    path("ses/departments/", ses_departments, name="ses_departments"),
    path("ses/regulations/", ses_regulations, name="ses_regulations"),
    path("ses/semesters/", ses_semesters, name="ses_semesters"),

path("semester-exam-schedule/publish/", ses_publish, name="ses_publish"),
path("semester-exam-schedule/published/", published_semester_exam_schedule, name="published_semester_exam_schedule"),



path("load_sem_adi_degrees/", load_sem_adi_degrees, name="load_sem_adi_degrees"),
    path("load_sem_adi_departments/", load_sem_adi_departments, name="load_sem_adi_departments"),
    path("load_sem_adi_batches/", load_sem_adi_batches, name="load_sem_adi_batches"),
    path("load_sem_adi_semesters/", load_sem_adi_semesters, name="load_sem_adi_semesters"),
    path("load_sem_adi_timetable/", load_sem_adi_timetable, name="load_sem_adi_timetable"),
    path("ajax/semester-timetable/regulations/",load_sem_adi_regulations, name="load_sem_adi_regulations"),
    path("ajax/semester-timetable/monthyears/", load_sem_adi_monthyears, name="load_sem_adi_monthyears"),

    path('admin_semester_timetable_pdf/', admin_semester_timetable_pdf, name='admin_semester_timetable_pdf'),
       path('hall_degree/', hall_degree, name='hall_degree'),

    # AJAX URLs
    path('hall_departments/', hall_departments, name='hall_departments'),
    path('hall_batches/', hall_batches, name='hall_batches'),
    path('generate_hallticket/', generate_hallticket, name='generate_hallticket'),
    path("hallticket-courses/", hallticket_courses, name="hallticket_courses"),
    path('fetch_semesters/', fetch_semesters, name='fetch_semesters'),
    path('view_generated_halltickets/', view_generated_halltickets, name='view_generated_halltickets'),
    path("generated/departments/", hall_generated_departments, name="hall_generated_departments"),
path("generated/batches/", hall_generated_batches, name="hall_generated_batches"),
path("generated/semesters/", hall_generated_semesters, name="hall_generated_semesters"),
path("ajax/hallticket_saved_courses/", hallticket_saved_courses, name="hallticket_saved_courses"),
 path("hallticket/bulk-pdf/", hallticket_bulk_pdf, name="hallticket_bulk_pdf"),



    path("ajax/ajax_load_prac_departments/",ajax_load_prac_departments, name="ajax_load_prac_departments"),
    path("ajax/ajax_load_prac_batches/",  ajax_load_prac_batches, name="ajax_load_prac_batches"),
 path("practicalexamschedule/", practicalexamschedule, name="practicalexamschedule"),
path("ajax/practical/courses/", ajax_load_prac_courses, name="ajax_load_prac_courses"),
path("ajax/practical/students/", ajax_load_prac_students, name="ajax_load_prac_students"),
 path("ajax/load-halls/", ajax_load_halls, name="ajax_load_halls"),
 path("ajax/save_prac_schedule/", ajax_save_prac_schedule, name="ajax_save_prac_schedule"),
path("ajax/get-prac-saved-schedule/", ajax_get_prac_saved_schedule, name="ajax_get_prac_saved_schedule"),
path("passvalue/", passvalue, name="passvalue"),
path("admin_iat_result_analysis/", admin_iat_result_analysis, name="admin_iat_result_analysis"),
path("load-departments/",load_departments,name="load_departments"),
path("load-filter-values/", load_filter_values, name="load_filter_values"),
path("download-pass-percentage-pdf/", download_pass_percentage_pdf, name="download_pass_percentage_pdf"),
path('load_admin_iat_result_departments/', load_admin_iat_result_departments, name='load_admin_iat_result_departments'),
   path("ajax/get-pass-percentage-table/", get_pass_percentage_table,name="get_pass_percentage_table"),
   path("get-course-wise-details/", get_course_wise_details, name="get_course_wise_details"),
   path("download-course-wise-pdf/", download_course_wise_pdf, name="download_course_wise_pdf"),
   path("download-student-wise-pdf/",download_student_wise_pdf, name="download_student_wise_pdf"),

   path('api/student-leave-roles/<int:creatorRoleId>/', student_api_leave_roles, name='student_api_leave_roles'),

    # ---- Lab timetable AJAX ----
    path('lab/get_technicians/', lab_get_technicians, name='lab_get_technicians'),
    path('lab/get_labs/', lab_get_labs, name='lab_get_labs'),
    path('lab/get_sections/', lab_get_sections, name='lab_get_sections'),
    path('lab_timetable_pdf/<int:pk>/', lab_timetable_pdf, name='lab_timetable_pdf'),
    path('lab_utility_log_pdf/', lab_utility_log_pdf, name='lab_utility_log_pdf'),
    path('principal_lab_dashboard_pdf/', principal_lab_dashboard_pdf, name='principal_lab_dashboard_pdf'),
    path('hod_lab_dashboard_pdf/', hod_lab_dashboard_pdf, name='hod_lab_dashboard_pdf'),
    path('lab_timetable_delete/<int:pk>/', lab_timetable_delete, name='lab_timetable_delete'),



    
    


]


    


