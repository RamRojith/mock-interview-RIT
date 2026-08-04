from django.shortcuts import render, redirect
from django.http import JsonResponse
from examination_management.views import admin_em, question_em, upload_excel_views
from django.urls import path, include


urlpatterns = [

    path('em_assign_permission/', admin_em.em_assign_permission, name='em_assign_permission'),
    # path('grade_master/', admin_em.grade_master, name='grade_master'),
    # path('grade_master_list/', admin_em.grade_master_list, name='grade_master_list'),
    path('class_category/', admin_em.class_category, name='class_category'),
    path("grades/edit/<int:grade_id>/", admin_em.edit_grade_master, name="edit_grade_master"),
    path("grades/delete/<int:grade_id>/", admin_em.delete_grade_master, name="delete_grade_master"),
    path('assessments/', admin_em.assessments, name='assessments'),
    path('assessments_list/', admin_em.assessments_list, name='assessments_list'),
    path('assessments/edit/<int:assessment_id>/', admin_em.edit_assessments, name='edit_assessments'),
    path('assessments/delete/<int:assessment_id>/', admin_em.delete_assessments, name='delete_assessments'),
    path("update_course_outcome/", admin_em.update_course_outcome, name="update_course_outcome"),
    path('update_blooms_level/', admin_em.update_blooms_level, name='update_blooms_level'),
    path('assessments_weightage/', admin_em.assessments_weightage, name='assessments_weightage'),
    path('ltp/', admin_em.ltp, name='ltp'),
    path('upload_student_results/', upload_excel_views.upload_student_results, name='upload_student_results'),

]
# examination_management/urls/admin_em_urls.py

from django.urls import path
from examination_management.views import admin_em, upload_excel_views

urlpatterns = [

    path('em_assign_permission/', admin_em.em_assign_permission, name='em_assign_permission'),

    path('class_category/', admin_em.class_category, name='class_category'),

    path("grades/edit/<int:grade_id>/", admin_em.edit_grade_master, name="edit_grade_master"),
    path("grades/delete/<int:grade_id>/", admin_em.delete_grade_master, name="delete_grade_master"),

    path('assessments/', admin_em.assessments, name='assessments'),
    path('assessments_list/', admin_em.assessments_list, name='assessments_list'),
    path('assessments/edit/<int:assessment_id>/', admin_em.edit_assessments, name='edit_assessments'),
    path('assessments/delete/<int:assessment_id>/', admin_em.delete_assessments, name='delete_assessments'),

    path("update_course_outcome/", admin_em.update_course_outcome, name="update_course_outcome"),
    path('update_blooms_level/', admin_em.update_blooms_level, name='update_blooms_level'),

    path('assessments_weightage/', admin_em.assessments_weightage, name='assessments_weightage'),
    path('ltp/', admin_em.ltp, name='ltp'),

    path('upload_student_results/', upload_excel_views.upload_student_results, name='upload_student_results'),

    # HALL ENTRY
    path('hall-entry_sem/', admin_em.hall_entry_sem, name='hall_entry_sem'),
    path('delete-hall/<int:id>/', admin_em.delete_hall, name='delete_hall'),

    # HALL ALLOTMENT
    path('hall-allotment/', admin_em.hall_allotment, name='hall_allotment'),
    path('hall-allotment/save/', admin_em.save_hall_allotment, name='save_hall_allotment'),
    path('hall-allotment/remove-allotments/', admin_em.remove_hall_allotments, name='remove_hall_allotments'),
    path("hall-allotment/pdf/", admin_em.seating_arrangement_pdf, name="seating_arrangement_pdf"),
    
    path('add_squad_questions/', admin_em.add_squad_questions, name='add_squad_questions'),

    path("hall-allotment/pdf/", admin_em.seating_arrangement_pdf, name="seating_arrangement_pdf"),
#     path("hall-arrangement-statement-pdf/", admin_em.hall_arrangement_statement_pdf, name="hall_arrangement_statement_pdf"),
#     path(
#     "hall-allotment/department-wise-attendance/pdf/",
#     admin_em.department_wise_attendance_pdf,
#     name="department_wise_attendance_pdf"
# ),



    path(
        "hall-allotment/absentees-statement/pdf/",
        admin_em.absentees_statement_summary_pdf,
        name="sem_absentees_statement_summary_pdf"
    ),
    path(
        "hall-allotment/absentees/pdf/",
        admin_em.absentees_statement_pdf,
        name="sem_absentees_statement_pdf"
    ),
]


    


    # # INTERNAL / SEMESTER EXAM
    # path('internal_admin/', admin_em.internal_admin, name='internal_admin'),
    # path('internal_exam_schedule/', admin_em.internal_exam_schedule, name='internal_exam_schedule'),
    # path('semester_exam_schedule/', admin_em.semester_exam_schedule, name='semester_exam_schedule'),

    # # HALL TICKET
    # path('generate_hallticket/', admin_em.generate_hallticket, name='generate_hallticket'),

    # # ADMIN CONSOLIDATE
    # path('admin_consolidate/', admin_em.admin_consolidate, name='admin_consolidate'),

    # # SQUAD MEMBER
    # path('assign_squad_member_list/', admin_em.assign_squad_member_list, name='assign_squad_member_list'),

    # # QUESTION
    # path('question/', admin_em.question, name='question'),

