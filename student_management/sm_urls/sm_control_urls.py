from django.urls import path,include
from student_management.sm_urls import admin_sm_urls

from student_management.views.sm_views import *
from student_management.views import sm_curd, sm_views
from student_management.views import admin_control_sm
from course_management.views import faculty_control_cm
from student_management.views import student_views
from student_management.views.sm_approve_views import bonafide_apply, bonafide_approve_view, update_umis_id # added import
from student_management.views import passout_students_views 
from faculty_leave_management.views import flm_admin

urlpatterns = [


    path('sm_hello/', admin_control_sm.sm_hello, name="sm_hello"),
    path('assign_mentor/', faculty_control_cm.assign_mentor, name="assign_mentor"),
    path('assign_class_advisor/', faculty_control_cm.assign_class_advisor, name="assign_class_advisor"),
    path('student/leave_od_request/', sm_curd.student_apply_leave_od, name="apply_leave_od"),
    path('bonafide/approve/', bonafide_approve_view, name='bonafide_approve_view'),

    path('umis_id/',update_umis_id, name='update_umis_id'),
    path('bonafide/apply/', bonafide_apply, name='bonafide_apply'),
    path('student/dashboard/', sm_curd.dashboard, name="dashboard"),
    path('student/profile/', sm_curd.profile, name="profile"),
    path('student/student_activity_upload/', sm_curd.student_activity_upload, name="student_activity_upload"),
    path('leave_od_applications/', faculty_control_cm.leave_od_applications, name="leave_od_applications"),
    path('student_attendance/', sm_curd.student_attendance, name="student_attendance"),
    path('student_graduation_details/', sm_curd.student_graduation_details, name="student_graduation_details"),
    path('student_timetable/', sm_curd.student_timetable, name="student_timetable"),
    # path('student_courses/', sm_curd.student_courses, name="student_courses"),
    path('hour_attendence/',sm_curd.hour_attendence,name='hour_attendence'),
    path('class_attendence/',sm_curd.class_attendence,name='class_attendence'),
    path('course_plan_completion_report/', sm_curd.course_plan_completion_report, name='course_plan_completion_report'),
    
   # urls.py
    # path('enter-marks/', sm_curd.enter_marks_page, name='enter_marks_page'),
    


    path('student_document_verification/',sm_curd.student_document_verification,name='student_document_verification'),
    
    
    path('our_students/',sm_views.our_students,name='our_students'),
        path('mentees/',sm_views.mentees,name='mentees'),

        path('generate_register_no/', generate_register_no, name='generate_register_no'),


    path('approve_leave_od/', faculty_control_cm.approve_leave_od, name="approve_leave_od"),
    
    path('student_analysis_dashboard/', passout_students_views.student_analysis_dashboard, name='student_analysis_dashboard'),
    path('retest_internalmark/', sm_curd.retest_internalmark, name='retest_internalmark'),
    path("faculty-course-students-attendance-datewise-pdf/<str:year>/<str:semester>/<int:course_id>/<str:batch>/<str:section>/<int:regulation_id>/",faculty_control_cm.faculty_course_students_attendance_datewise_pdf,name="faculty_course_students_attendance_datewise_pdf"),
    path("faculty-course-students-attendance-datewise-excel/<str:year>/<str:semester>/<int:course_id>/<str:batch>/<str:section>/<int:regulation_id>/",faculty_control_cm.faculty_course_students_attendance_datewise_excel,name="faculty_course_students_attendance_datewise_excel"),
    path("faculty-course-students-attendance-view/<str:year>/<str:semester>/<int:course_id>/<str:batch>/<str:section>/<int:regulation_id>/",faculty_control_cm.faculty_course_students_attendance_view,name="faculty_course_students_attendance_view"),
    path('conduct-certificate/', passout_students_views.conduct_certificate, name='conduct_certificate'),
    path('course-completion-certificate/', passout_students_views.course_completion_certificate, name='course_completion_certificate'),
    path('transfer_certificate/', passout_students_views.transfer_certificate, name='transfer_certificate'),
    path('transfer_certificate_office/', passout_students_views.transfer_certificate_office, name='transfer_certificate_office'),


    path('discontinue_transfer_certificate/', passout_students_views.discontinue_transfer_certificate, name='discontinue_transfer_certificate'),
    path('discontinue_transfer_certificate_office/', passout_students_views.discontinue_transfer_certificate_office, name='discontinue_transfer_certificate_office'),
    
]