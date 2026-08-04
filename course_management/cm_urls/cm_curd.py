from django.urls import path
from course_management.views.admin_control_cm import *
from course_management.views.faculty_control_cm import *

from django.conf.urls.static import static
from django.conf import settings
urlpatterns = [     

        path(
        "faculty/course/<int:year>/<int:semester>/<int:course_id>/<str:batch>/<str:section>/<int:regulation_id>/students/",
        faculty_course_students,
        name="faculty_course_students",
    ),
        path("review-subject-willingness/", review_subject_willingness, name="review_subject_willingness"),

        path("assign-subject-faculty/pdf/", assign_subject_faculty_pdf, name="assign_subject_faculty_pdf"),


        path("download-all-requests/", download_subject_request_pdf, name="download_subject_request_pdf"),
        path("subject-request/get-years/", sr_get_years, name="sr_get_years"),
        path("subject-request/get-courses/", sr_get_courses, name="sr_get_courses"),

        path("hod/requests/download/", download_hod_subject_request_pdf, name="download_hod_subject_request_pdf"),
        path("course-plan/pdf/", course_plan_pdf, name="course_plan_pdf"),
        
    path('subject_willingness/pdf/', my_willingness_pdf, name='my_willingness_pdf'),
    path('co_po_mapping_manage/', co_po_mapping_manage, name='co_po_mapping_manage'),
    path("api/program-outcomes/", api_program_outcomes, name="api_program_outcomes"),
    path("api/program-specific-outcomes/", api_program_specific_outcomes, name="api_program_specific_outcomes"),
    path('export-filtered-courses-excel/', export_filtered_courses_excel, name='export_filtered_courses_excel'),

       path(
    "download-student-wise-excel/",
    download_student_wise_excel,
    name="download_student_wise_excel"
),

    path("course-enrollment-dashboard/pdf/", course_enrollment_dashboard_pdf, name="course_enrollment_dashboard_pdf"),
    path('course_enrollment_dashboard/api/degrees/', api_ce_degrees, name='api_ce_degrees'),
    path('course_enrollment_dashboard/api/departments/', api_ce_departments, name='api_ce_departments'),
    path('course_enrollment_dashboard/api/years/', api_ce_years, name='api_ce_years'),
    path('course_enrollment_dashboard/api/semesters/', api_ce_semesters, name='api_ce_semesters'),
    path('course_enrollment_dashboard/api/sections/', api_ce_sections, name='api_ce_sections'),

    path('attendance_lag_dashboard/api/degrees/', api_al_degrees, name='api_al_degrees'),
    path('attendance_lag_dashboard/api/departments/', api_al_departments, name='api_al_departments'),
    path('attendance_lag_dashboard/api/years/', api_al_years, name='api_al_years'),
    path('attendance_lag_dashboard/api/semesters/', api_al_semesters, name='api_al_semesters'),
    path('attendance_lag_dashboard/api/sections/', api_al_sections, name='api_al_sections'),
    path("attendance-lag-dashboard/pdf/", attendance_lag_dashboard_pdf, name="attendance_lag_dashboard_pdf"),

]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)