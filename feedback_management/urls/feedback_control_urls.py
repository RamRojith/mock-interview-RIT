from django.urls import path
from examination_management import views
from feedback_management.views import admin_feedback_views, course_end_survey_views, course_feedback_views, feedback_details_views, program_exit_survey_views,course_exit_survey_views , academic_activity_views

urlpatterns = [
    path("feedback_hello/", admin_feedback_views.feedback_hello, name="feedback_hello"),
    path("course_survey_entry/", feedback_details_views.course_survey_entry, name="course_survey_entry"),
    path("course_feedback/", course_feedback_views.course_feedback, name="course_feedback"),
     path("course_feedbacks/",course_feedback_views.course_feedbacks, name="course_feedbacks"),
    path("subject_feedback/",course_feedback_views.subject_feedback, name="subject_feedback"),
    path("view-feedbacks/", course_feedback_views.view_feedbacks, name="view_feedbacks"),





    path('view_end_survey/', course_end_survey_views.view_end_survey, name='view_end_survey'),
    path('course_end_survey_entry/', course_end_survey_views.course_end_survey_entry, name='course_end_survey_entry'),
    path('course_end_survey/', course_end_survey_views.course_end_survey, name='course_end_survey'),
    path("end_survey/", course_end_survey_views.end_survey, name="end_survey"),
    path("program_exit_survey/", program_exit_survey_views.program_exit_survey, name="program_exit_survey"),
    path("view-program-exit-survey/", program_exit_survey_views.view_program_exit_survey, name="view_program_exit_survey"),
    path("course-exit-survey/", course_exit_survey_views.course_exit_survey,name="course_exit_survey"),
    path("view-course-exit-survey/",course_exit_survey_views.view_course_exit_survey,name="view_course_exit_survey"),
    
    
    
    
    path("academic-activity-question-entry/",academic_activity_views.academic_activity_question_entry,name="academic_activity_question_entry"),
    path("academic-activity-survey/",academic_activity_views.academic_activity_survey,name="academic_activity_survey"),
    path("view-academic-activity-survey/",academic_activity_views.view_academic_activity_survey,name="view_academic_activity_survey"),

    
    
    
    
    ]



