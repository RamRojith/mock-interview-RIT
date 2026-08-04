from django.urls import path
from course_management.views.admin_control_cm import *

from django.conf.urls.static import static
from django.conf import settings
from examination_management.views.admin_em import *
from course_management.views.admin_control_cm import hall_students,hall_students_pdf
from course_management.views.faculty_control_cm import *
urlpatterns = [    
    
#     path('admin_course_management/', admin_course_management, name='admin_course_management'),
    path('add_regulation/', add_regulation, name='add_regulation'),
    
    path('admin_update_course/', admin_update_course, name='admin_update_course'),
#     path('admin_update_course/<int:course_id>/<str:action>/', admin_update_course, name='admin_update_course'),
    path('get_courses/', get_courses, name='get_courses'),
    # path('add_period_allocation/', add_period_allocation, name='add_period_allocation'),
    path('get_courses_only/', get_courses_only, name='get_courses_only'),
#     path('add_regulation/', add_regulation, name='add_regulation'),
    path('hall_entry/', hall_entry, name='hall_entry'),
    path('edit_hall/<int:id>/', edit_hall, name='edit_hall'),
    path('delete_hall/<int:id>/', delete_hall, name='delete_hall'),
    path("course_admin/hall_allotment_detail/", hall_allotment_detail, name="hall_allotment_detail"),
    path("course_admin/hall/<int:hall_id>/students/", hall_students, name="hall_students"),
    path("course_admin/hall/<int:hall_id>/students/pdf/", hall_students_pdf, name="hall_students_pdf"),
    path("course_admin/hall/<int:hall_id>/hall_all_departments/signature-pdf/", hall_all_departments_signature_pdf, name="hall_all_departments_signature_pdf"),
    path("course_admin/hall/<int:hall_id>/dept/<int:dept_id>/students/pdf/", hall_dept_students_pdf, name="hall_dept_students_pdf"),








    
    
    path('course_category/', course_category, name='course_category'),
    path("export-course-category-excel/", export_course_category_excel, name="export_course_category_excel"),

    # ---- Honours Course Master (Regulation -> Degree -> Dept -> Year -> Sem -> Academic Year) ----
    
    path('honours_course_master/api/degrees/', api_honours_degrees, name='api_honours_degrees'),
    path('honours_course_master/api/departments/', api_honours_departments, name='api_honours_departments'),
    path('honours_course_master/api/years/', api_honours_years, name='api_honours_years'),
    path('honours_course_master/api/semesters/', api_honours_semesters, name='api_honours_semesters'),
#     # path('course_dashboard/', course_dashboard, name='course_dashboard'),
#     # path('add_period_allocation/', add_period_allocation, name='add_period_allocation'),
#     # path('get_courses_only/', get_courses_only, name='get_courses_only'),
#     # path("update-semester/", update_semester, name="update_semester"),
#     # path("add-exam/", add_exam, name="add_exam"),
#     # path("fetch_exams/", fetch_exams, name="fetch_exams"),
#     # path("semester-update/", semester_update_page, name="semester_update_page"),
#     # path('exam-fee-form/', exam_fee_form, name='exam_fee_form'),
#     # path('add-exam-fee/', add_exam_fee, name='add_exam_fee'),
#     # path("update-exam-fees/", update_exam_fees, name="update_exam_fees"),
#     # path('dummy_numbers/', dummy_number_page, name='dummy_number_page'),  # Load HTML page
#     # path('generate-dummy-numbers/', generate_dummy_numbers, name='generate_dummy_numbers'),
#     # path('save-dummy-numbers/', save_dummy_numbers, name='save_dummy_numbers'),
#     # path('exam_page/', exam_page, name='exam_page'),
       path('cm_assign_permission/', cm_assign_permission, name='cm_assign_permission'),
        path('update_semester/', semester_upgrade, name="semester_upgrade"),
        path('api_degrees/', api_degrees, name='api_degrees'),
        path('api_regulations/', api_regulations, name='api_regulations'),
        path('api_assessments/', api_assessments, name='api_assessments'),
        path('semester_cooldown_period/',semester_cooldown_period, name='semester_cooldown_period'),
    path("all-course-enrollments/", all_course_enrollments, name="all_course_enrollments"),
    path("all-course-enrollments/ajax/", all_course_enrollments_ajax, name="all_course_enrollments_ajax"),
    path("all-course-enrollments/export/", export_course_enrollments_excel, name="export_course_enrollments_excel"),
    path("all-course-enrollments/bulk-enroll/", bulk_enroll_course_enrollments, name="bulk_enroll_course_enrollments"),
    path("get-courses-by-department-ajax/", get_courses_by_department_ajax, name="get_courses_by_department_ajax"),
    path('sync_course_enrollments/', sync_course_enrollments, name='sync_course_enrollments'),
        

        
    path('program_outcome/', program_outcome, name='program_outcome'),
            path('student_leave_approval_management/',student_leave_approval_management, name='student_leave_approval_management'),
    
        
    path('attendance_percentage/', attendance_percentage, name='attendance_percentage'),
    # Course Enrollment CRUD URLs
    
    

#     # path('add_course_fee/', add_course_fee, name='add_course_fee'),
#     # path("fee_structure_list/", fee_structure_list, name="fee_structure_list"),
#     # path('update_fee_structure/<int:pk>/', update_fee_structure, name='update_fee_structure'),
#     # path('delete_fee_structure/<int:pk>/', delete_fee_structure, name='delete_fee_structure'),
#     # path('load-programs/', load_programs, name='ajax_load_programs'),
#     # path('load-courses/', load_courses, name='ajax_load_courses'),
#     # path('generate_exam/', generate_exam, name='generate_exam'),
    
    




    
#     # path('exam_date_entry/', exam_date_entry, name='exam_date_entry'),
#     # path('get_semesters/', get_semesters, name='get_semesters'),
#     # path('get_courses_1/', get_courses_1, name='get_courses_1'),
#     # path('get_failed_courses/', get_failed_courses, name='get_failed_courses'),
#     # path('exam_dashboard/', exam_dashboard, name='exam_dashboard'),
#     # path('delete_exam/', delete_exam, name='delete_exam'),
#     # path('clear_all_exams/', clear_all_exams, name='clear_all_exams'),
#     # path('get_semesters_for_exam/', get_semesters_for_exam, name='get_semesters_for_exam'),
#     # path('get_exam_schedule/', get_exam_schedule, name='get_exam_schedule'),
#     # path('header_footer/', header_footer, name='header_footer'),
#     # path('download_exam_schedule/', download_exam_schedule, name='download_exam_schedule'),
#     # path('generate_hall_ticket/', generate_hall_ticket, name='generate_hall_ticket'),
#     # path('fetch_students1/', fetch_students1, name='fetch_students1'),
#     # path('draw_wrapped_text/', draw_wrapped_text, name='draw_wrapped_text'),
#     # path('download_hall_ticket_pdf/', download_hall_ticket_pdf, name='download_hall_ticket_pdf'),
#     # path('get_programs1/', get_programs1, name='get_programs1'),
    

]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)








    
