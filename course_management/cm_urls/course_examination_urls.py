from django.urls import path
from course_management.views.cm_details import *
from course_management.views.faculty_control_cm import *
from django.conf.urls.static import static
from django.conf import settings
from course_management.views import cm_details, admin_control_cm, parent_views, faculty_control_cm
from student_management.views import sm_curd, sm_views
from course_management.views.admin_control_cm import *
from course_management.views.faculty_control_cm import *

urlpatterns = [

    path('hello/', hello, name="hello"),
    

     path('daily_attendance_report/', parent_views.daily_attendance_report, name="daily_attendance_report"),
        path('hour_attendance_report/', parent_views.hour_attendance_report, name="hour_attendance_report"),

   
    path('student_courses/', sm_views.student_courses, name="courses"),

    path('faculty_courses/', faculty_control_cm.faculty_courses, name="faculty_courses"),

    path('subject_willingness/', faculty_control_cm.subject_willingness, name='subject_willingness'),

    path('course_plan/', faculty_control_cm.course_plan, name='course_plan'),
    path('create_subject_request/', create_subject_request, name='create_subject_request'),
    path("approve-subject-requests/", approve_subject_requests, name="approve_subject_requests"),


    path('add-period-allocation/', add_period_allocation, name='add_period_allocation'),
        path('update_semester/', semester_upgrade, name="semester_upgrade"),
    path('add_hours/', add_hours, name='add_hours'),
    path('hour_allocation/', hour_allocation, name='hour_allocation'),
    path('workload_dashboard/', workload_dashboard, name='workload_dashboard'),

    path('add_new_course/', add_new_course, name='add_new_course'),
    path('course_analysis_dashboard/',course_analysis_dashboard, name='course_analysis_dashboard'),
    path('subject_allocation_schedule/',subject_allocation_schedule, name='subject_allocation_schedule'),
    path('honours_course_master/', honours_course_master, name='honours_course_master'),
    # ---- Course Enrollment Dashboard (Regulation -> Degree -> Dept -> Year -> Sem) ----
    path('course_enrollment_dashboard/', course_enrollment_dashboard, name='course_enrollment_dashboard'),

    # ---- Attendance Lag Dashboard (Regulation -> Degree -> Dept -> Year -> Sem -> Academic Year) ----
    path('attendance_lag_dashboard/', attendance_lag_dashboard, name='attendance_lag_dashboard'),


    # ---- Lab timetable / assignment / utilization (grantable permissions) ----
    path('lab_timetable_view/', lab_timetable_view, name='lab_timetable_view'),
    path('lab_timetable_create/', lab_timetable_create, name='lab_timetable_create'),
    path('lab_timetable_edit/<int:pk>/', lab_timetable_edit, name='lab_timetable_edit'),
    path('lab_timetable_assign/', lab_timetable_assign, name='lab_timetable_assign'),
    path('lab_utility_log/', lab_utility_log, name='lab_utility_log'),

    # ---- Lab utilization dashboards (grantable permissions; no role is hard-coded —
    #      access is controlled purely by which permission a role is granted) ----
    path('principal_lab_dashboard/', principal_lab_dashboard, name='principal_lab_dashboard'),
    path('hod_lab_dashboard/', hod_lab_dashboard, name='hod_lab_dashboard'),

    
    
]