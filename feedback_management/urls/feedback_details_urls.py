from django.urls import path
from examination_management import views
from feedback_management.views import academic_activity_views, admin_feedback_views, course_end_survey_views, course_exit_survey_views, course_feedback_views, program_exit_survey_views


urlpatterns = [
        path('course_exit_survey/', course_exit_survey_views.course_exit_survey_entry, name='course_exit_survey_entry'),
        path('course_feedback/', course_feedback_views.course_feedback_entry, name='course_feedback_entry'),
        path('program_exit_survey/', program_exit_survey_views.program_exit_survey_entry, name='program_exit_survey_entry'),
        path('delete_feedback_question/<int:pk>/', course_feedback_views.delete_feedback_question, name='delete_feedback_question'),
        path("student/feedback/<int:enrollment_id>/", course_feedback_views.student_feedback_form, name="student_feedback_form"),
        path("course-feedbacks/pdf/", course_feedback_views.course_feedbacks_pdf, name="course_feedbacks_pdf"),
        path("subject-feedback/pdf/", course_feedback_views.subject_feedback_pdf, name="subject_feedback_pdf"),
        path("view-feedbacks/pdf/", course_feedback_views.view_feedbacks_pdf, name="view_feedbacks_pdf"),
        path("view-feedbacks/bulk-pdf/", course_feedback_views.view_feedbacks_bulk_pdf, name="view_feedbacks_bulk_pdf"),
        path("course-feedbacks/bulk-pdf/",course_feedback_views.course_feedbacks_bulk_pdf,name="course_feedbacks_bulk_pdf"),
        path("course-feedbacks/bulk-excel/",course_feedback_views.course_feedbacks_bulk_excel_download,name="course_feedbacks_bulk_excel_download"),
        path("view-feedbacks/bulk-excel-download/",course_feedback_views.view_feedbacks_bulk_excel_download,name="view_feedbacks_bulk_excel_download"),
        path("control/view-feedbacks-summary-pdf/",course_feedback_views.view_feedbacks_summary_pdf,name="view_feedbacks_summary_pdf"),
        path("subject-feedback-bulk-pdf/", course_feedback_views.subject_feedback_bulk_pdf, name="subject_feedback_bulk_pdf"),



        path("course_end_survey_form/", course_end_survey_views.course_end_survey_form, name="course_end_survey_form"),
        path("end_survey/pdf/", course_end_survey_views.end_survey_pdf, name="end_survey_pdf"),
        
        path("view_end_survey_bulk_pdf/", course_end_survey_views.view_end_survey_bulk_pdf, name="view_end_survey_bulk_pdf"),
        path('delete_program_exit_question/<int:pk>/', program_exit_survey_views.delete_program_exit_question, name='delete_program_exit_question'),
        path("view-program-exit-survey-bulk-pdf/",program_exit_survey_views.view_program_exit_survey_bulk_pdf,name="view_program_exit_survey_bulk_pdf"),

        path("course-exit-survey-entry/",course_exit_survey_views.course_exit_survey_entry,name="course_exit_survey_entry"),
        path("delete-exit-survey-question/<int:pk>/",course_exit_survey_views.delete_exit_survey_question,name="delete_exit_survey_question"),

        path("view-course-exit-survey/bulk-pdf/",course_exit_survey_views.view_course_exit_survey_bulk_pdf,name="view_course_exit_survey_bulk_pdf"),


        path("academic-activity-submission-pdf/<int:pk>/",academic_activity_views.academic_activity_submission_pdf,name="academic_activity_submission_pdf"),
        path("view-academic-activity-survey-bulk-pdf/",academic_activity_views.view_academic_activity_survey_bulk_pdf,name="view_academic_activity_survey_bulk_pdf"),
        path("academic-activity-question-delete/<int:pk>/",academic_activity_views.delete_academic_activity_question,name="delete_academic_activity_question"),


]

