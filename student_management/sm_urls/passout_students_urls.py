from django.urls import path, include
from student_management.views import passout_students_views


urlpatterns = [

    path('conduct-certificate/', passout_students_views.conduct_certificate, name='conduct_certificate'),
    path('generate_conduct_certificate/<int:student_id>/', passout_students_views.generate_conduct_certificate, name='generate_conduct_certificate'),
    path('generate-bulk-conduct-certificate/', passout_students_views.generate_bulk_conduct_certificate, name='generate_bulk_conduct_certificate'),


    path('course-completion-certificate/', passout_students_views.course_completion_certificate, name='course_completion_certificate'),
    path('generate_course_completion_certificate/<int:student_id>/', passout_students_views.generate_course_completion_certificate, name='generate_course_completion_certificate'),
    path('generate-bulk-course-completion-certificate/', passout_students_views.generate_bulk_course_completion_certificate, name='generate_bulk_course_completion_certificate'),


    path('transfer_certificate/', passout_students_views.transfer_certificate, name='transfer_certificate'),
    path('transfer_certificate/upload/', passout_students_views.transfer_certificate_upload_excel, name='transfer_certificate_upload_excel'),
    path('transfer_certificate/upload/template/', passout_students_views.transfer_certificate_template_excel, name='transfer_certificate_template_excel'),
    path('transfer_certificate/<int:student_id>/', passout_students_views.generate_transfer_certificate_pdf, name='generate_transfer_certificate_pdf'),
    path('transfer_certificate/bulk/', passout_students_views.generate_bulk_transfer_certificate, name='generate_bulk_transfer_certificate'),

    path('transfer_certificate_office/', passout_students_views.transfer_certificate_office, name='transfer_certificate_office'),
    path('transfer_certificate_office/<int:student_id>/', passout_students_views.generate_transfer_certificate_office_pdf, name='generate_transfer_certificate_office_pdf'),
    path('transfer_certificate_office/bulk/', passout_students_views.generate_bulk_transfer_certificate_office, name='generate_bulk_transfer_certificate_office'),
    path('save_tc_details/<int:student_id>/', passout_students_views.save_tc_details, name='save_tc_details'),
    path('student_analysis_dashboard/pdf/', passout_students_views.student_analysis_dashboard_pdf, name='student_analysis_dashboard_pdf'),

    path("discontinue-tc/save/<int:student_id>/",passout_students_views.save_discontinue_tc_details,name="save_discontinue_tc_details"),

    path("discontinue-tc/pdf/<int:student_id>/",passout_students_views.generate_discontinue_transfer_certificate_pdf,name="generate_discontinue_transfer_certificate_pdf"),

    path("discontinue-transfer-certificate-office/pdf/<int:student_id>/",passout_students_views.generate_discontinue_transfer_certificate_office_pdf,name="generate_discontinue_transfer_certificate_office_pdf"),

    path("discontinue-transfer-certificate-office/bulk-pdf/",passout_students_views.generate_bulk_discontinue_transfer_certificate_office,name="generate_bulk_discontinue_transfer_certificate_office"),

]

