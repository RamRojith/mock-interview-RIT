from django.urls import path
from examination_management import views
from feedback_management.views import academic_activity_views, admin_feedback_views

urlpatterns = [
   
    path('feedback/assign-permission/', admin_feedback_views.feedback_assign_permission, name='feedback_assign_permission'),
    path('grade-upload/', admin_feedback_views.grade_upload, name='grade_upload'),
    path('grade-upload/edit/<int:pk>/', admin_feedback_views.grade_upload_edit, name='grade_upload_edit'),
    path('grade-upload/delete/<int:pk>/', admin_feedback_views.grade_upload_delete, name='grade_upload_delete'),
    path("feedback-permission/", admin_feedback_views.feedback_permission, name="feedback_permission"),
    path("feedback-permission-api/", admin_feedback_views.feedback_permission_api, name="feedback_permission_api"),

path("end_survey_permission/", admin_feedback_views.end_survey_permission, name="end_survey_permission"),
path("end_survey_permission_api/", admin_feedback_views.end_survey_permission_api, name="end_survey_permission_api"),

path("program_exit_permission/", admin_feedback_views.program_exit_permission, name="program_exit_permission"),
path("program_exit_permission_api/", admin_feedback_views.program_exit_permission_api, name="program_exit_permission_api"),

path("course-exit-permission/", admin_feedback_views.course_exit_permission, name="course_exit_permission"),
path("course-exit-permission-api/", admin_feedback_views.course_exit_permission_api, name="course_exit_permission_api"),

path("academic-activity-permission/", academic_activity_views.academic_activity_permission, name="academic_activity_permission"),
path("academic-activity-permission-api/", academic_activity_views.academic_activity_permission_api, name="academic_activity_permission_api"),

]

