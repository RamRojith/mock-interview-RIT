from django.urls import path,include
from student_management.sm_urls import admin_sm_urls
from course_management.views.faculty_control_cm import *
from student_management.views import sm_curd
from student_management.views.sm_curd import *
from student_management.views.sm_views import *
from student_management.views.student_document_verification_views import *
from student_management.views.student_views import *

urlpatterns = [
   path('course-detail/', course_attendance_detail, name='course_attendance_detail'),
   path('course-plan-completion-report/pdf/', course_plan_completion_report_pdf, name='course_plan_completion_report_pdf'),

    path('student_achievements_view/', student_achievements_view, name="student_achievements_view"),
    path('student_co_ex_curricular_view/', student_co_ex_curricular_view, name="student_co_ex_curricular_view"),
    path('student_professional_view/', student_professional_view, name="student_professional_view"),
    path('student_projects_view/', student_projects_view, name="student_projects_view"),
    path('student_publications_view/', student_publications_view, name="student_publications_view"),
    path('student_activity_upload/', student_activity_upload, name="student_activity_upload"),
    path('student_co_ex_curricular_upload/', student_co_ex_curricular_upload, name="student_co_ex_curricular_upload"),
    path('student_achievements_upload/', student_achievements_upload, name="student_achievements_upload"),
    path('student_professional_body_upload/', student_professional_body_upload, name="student_professional_body_upload"),
    path('student_project_upload/', student_project_upload, name="student_project_upload"),
    path('student_publications_upload/', student_publications_upload, name="student_publications_upload"),
    path('student_admission_details/', student_admission_details, name="student_admission_details"),
    path("student_management/edit_address/", edit_address, name="edit_address"),
    # path("student_co_ex_curricular_approve/", student_co_ex_curricular_approve, name="student_co_ex_curricular_approve"),
    # path("approve/co_ex_curricular/", student_activity_approve, {"model_name": "co_ex_curricular"}, name="student_co_ex_curricular_approve"),
    # path("approve/publication/", student_activity_approve, {"model_name": "publication"}, name="student_publication_approve"),
    # path("approve/achievement/", student_activity_approve, {"model_name": "achievement"}, name="student_achievement_approve"),
    # path("approve/professional/", student_activity_approve, {"model_name": "professional"}, name="student_professional_approve"),
    # path("approve/project/", student_activity_approve, {"model_name": "project"}, name="student_project_approve"),
    path("mentor_publications_approval/", mentor_publications_approval, name="mentor_publications_approval"),
    path("mentor_projects_approval/", mentor_projects_approval, name="mentor_projects_approval"),
    path("mentor_achievements_approval/", mentor_achievements_approval, name="mentor_achievements_approval"),
    path("mentor_professional_approval/", mentor_professional_approval, name="mentor_professional_approval"),
    path("mentor_coex_approval/", mentor_coex_approval, name="mentor_coex_approval"),

    path('student_academic_calendar/', student_academic_calendar, name='student_academic_calendar'),

    path("student/timetable/pdf/", student_timetable_pdf, name="student_timetable_pdf"),


    path('enter-marks/', enter_marks_page, name='enter_marks_page'),
    path('ajax/load_years/', load_years, name='ajax_load_years'),
    path('ajax/load_semesters/', load_semesters, name='ajax_load_semesters'),
    path('ajax/load_academic_years/', load_academic_years, name='ajax_load_academic_years'),
    path('ajax/load_patterns/', load_patterns, name='ajax_load_patterns'),
    path('save-marks/', save_student_marks, name='save_student_marks'),

     path('marks/pdf/', student_mark_pdf, name='student_mark_pdf'),
    path('marks/pdf/all/', student_mark_pdf_all, name='student_mark_pdf_all'),



     path(
        "student_management/students/practical",
        enter_practical_page,
        name="enter_practical_page",
    ),
    path("reports/practical-statement/", practical_statement_pdf, name="practical_statement_pdf"),
    path("model-lab/", model_lab_entry_page, name="model_lab_entry_page"),
    path(
        "model-lab/statement.pdf",
        model_lab_statement_pdf,
        name="model_lab_statement_pdf",
    ),
    
    path("overall-consolidate/pdf/", overall_consolidate_pdf, name="overall_consolidate_pdf"),

    path("api/map-experiment-iat/", map_experiment_iat, name="map_experiment_iat"),
    path("api/get-experiment-iat-mapping/", get_experiment_iat_mapping, name="get_experiment_iat_mapping"),

    path("consolidated-assessment/pdf/", consolidated_assessment_pdf, name="consolidated_assessment_pdf"),
   
    path('semester/<int:semester_number>/grade-pdf/', semester_grade_pdf, name='semester_grade_pdf'),
    path("faculty-timetable/batches/", fit_batches, name="fit_batches"),
    path("faculty-timetable/semesters/", fit_semesters, name="fit_semesters"),
    path("faculty-timetable/iats/", fit_iats, name="fit_iats"),
    path("faculty/internal-timetable/pdf/",faculty_internal_timetable_pdf,name="faculty_internal_timetable_pdf"),
    path("download_fee_summary_pdf/",download_fee_summary_pdf,name="download_fee_summary_pdf"),
    path("api_fee_summary/", api_fee_summary, name="api_fee_summary"),
    path("api_fee_students/", api_fee_students, name="api_fee_students"),
    path("api_degree_departments/", api_degree_departments, name="api_degree_departments"),
    
    path('student_attendance_pdf/', student_attendance_pdf, name='student_attendance_pdf'),
    path('faculty/course/<str:year>/<str:semester>/<int:course_id>/<str:batch>/<str:section>/<int:regulation_id>/attendance/pdf/',faculty_course_students_attendance_pdf,name="faculty_course_students_attendance_pdf",),
    
     path('result-analysis-pdf/', result_analysis_pdf, name='result_analysis_pdf'),


    path("attendance/download-pdf/", class_attendance_pdf, name="class_attendance_pdf"),
    # path("attendance/download-excel/", class_attendance_datewise_excel, name="class_attendance_excel"),
    
    
    path("retest-enter-mark-page/", sm_curd.retest_enter_mark_page, name="retest_enter_mark_page"),
    path("save-retest-marks/",  save_retest_marks, name="save_retest_marks"),
    path(
    "save-overall-consolidate-record/",save_overall_consolidate_record,name="save_overall_consolidate_record"
),
    path(
    'class_attendance_datewise_excel/<str:year>/<str:semester>/<int:course_id>/<str:batch>/<str:section>/<int:regulation_id>/',
    sm_curd.class_attendance_datewise_excel,
    name='class_attendance_datewise_excel'
),
path(
    'class_attendance_datewise_pdf/<str:year>/<str:semester>/<int:course_id>/<str:batch>/<str:section>/<int:regulation_id>/',
    sm_curd.class_attendance_datewise_pdf,
    name='class_attendance_datewise_pdf'
),
path(
    'class_attendance_datewise_view/<str:year>/<str:semester>/<int:course_id>/<str:batch>/<str:section>/<int:regulation_id>/',
    sm_curd.class_attendance_detail_view,
    name='class_attendance_view'
),
path(
    'class_attendance_pdf/<str:year>/<str:semester>/<int:course_id>/<str:batch>/<str:section>/<int:regulation_id>/',
    sm_curd.class_attendance_pdf,
    name='class_attendance_pdf'
),

]
