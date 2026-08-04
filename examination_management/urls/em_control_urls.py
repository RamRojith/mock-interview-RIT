from django.urls import path
from examination_management.views.admin_em import *
from examination_management.views.result_views import results
from faculty_management.views import fm_control_views
from examination_management.views import admin_em, question_em
from student_management.views import sm_curd, student_views
from course_management.views import admin_control_cm, faculty_control_cm

urlpatterns = [

    # ================= BASIC =================
    path("em_hello/", em_hello, name="em_hello"),

    # ================= ASSESSMENTS =================
    path('add_assessments/', fm_control_views.add_assessments, name="add_assessments"),
    path("exams/add-assessment-marks/", fm_control_views.add_assessment_marks, name="add_assessment_marks"),
    path("exams/assign-assessment-students/", fm_control_views.assign_assessment_student, name="assign_assessment_student"),

    # ================= SQUAD MEMBER REPORT =================
    path("exams/squad-member-report/", squad_member_report, name="squad_member_report"),
    path('exams/squad-member-report-view/', squad_member_report_view, name='squad_member_report_view'),
    path('assign_squad_member_list/', assign_squad_member_list, name='assign_squad_member_list'),

    # ================= QUESTION =================
    path('question/', question_em.question, name='question'),

    # ================= CONSOLIDATE / INTERNAL =================
    path('overall_consolidate/', sm_curd.overall_consolidate, name='overall_consolidate'),
    path('internalmarks/', sm_curd.internalmarks, name='Internalmarks'),
    path('faculty_internal_timetable/', sm_curd.faculty_internal_timetable, name='faculty_internal_timetable'),

    # ================= GRADE MASTER =================
    path('regular_course_grade_master/', admin_em.regular_course_grade_master, name='regular_course_grade_master'),
    path('self_learning_course_grade_master/', admin_em.self_learning_course_grade_master, name='self_learning_course_grade_master'),

    # ================= RESULTS =================
    path('results/', results, name='results'),

    # ==========================================================
    # ✅ HALL ENTRY + HALL ALLOTMENT (USE admin_em ONLY)
    # ==========================================================
    path('hall-entry_sem/', admin_em.hall_entry_sem, name='hall_entry_sem'),
    path('delete-hall/<int:id>/', admin_em.delete_hall, name='delete_hall'),

    # ✅ This is the page that should open after Proceed (GET params)
    path('hall-allotment/', admin_em.hall_allotment, name='hall_allotment'),

    # ✅ This is the POST submit after selecting students + hall

    # ==========================================================
    # ⚠️ If you still need old course_admin routes, keep with different names
    # (otherwise hall_allotment name conflicts)
    # ==========================================================
    path('hall_entry_old/', admin_control_cm.hall_entry, name='hall_entry_old'),
    path("course_admin/hall_allotment_old/", admin_control_cm.hall_allotment, name="hall_allotment_old"),
    path("result_analysis/", sm_curd.result_analysis, name="result_analysis"),
   path("admin_iat_result_analysis/", admin_control_cm.admin_iat_result_analysis, name="admin_iat_result_analysis"),



       path('Student_Semester_Mark_Dashboard/', student_views.Student_Semester_Mark_Dashboard, name='Student_Semester_Mark_Dashboard'),
    path('Student_Internal_Exam_timetable/', faculty_control_cm.Student_Internal_Exam_timetable, name="Student_Internal_Exam_timetable"),
    path('Student_Semester_Exam_timetable/', faculty_control_cm.Student_Semester_Exam_timetable, name="Student_Semester_Exam_timetable"),
path('student_mark/', sm_curd.student_mark, name="student_mark"),
]







