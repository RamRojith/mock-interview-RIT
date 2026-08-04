from django.urls import path
from learning_management_system.views.lms_create_folder import lms_subjects
from learning_management_system.views.student_view import student_lms_dashboard
# from learning_management_system.views.canva_upload_assignments import canva_assignments, canva_upload_assignments
from learning_management_system.views.admin_lms_view import lms_assign_permission, lms_hello, lms_home


urlpatterns = [
   path('student_lms_dashboard/', student_lms_dashboard, name='student_lms_dashboard'),
   path('lms_subjects/', lms_subjects, name='lms_subjects'),
   # path('canva_assignments/', canva_assignments, name='canva_assignments'),
   path('lms_hello/', lms_hello, name='lms_hello'),
]
