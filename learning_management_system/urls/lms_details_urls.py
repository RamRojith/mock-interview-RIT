from django.urls import path,include
from learning_management_system.views.admin_lms_view import lms_assign_permission, lms_home

from learning_management_system.urls import lms_control_urls as canva_urls

from learning_management_system.views.lms_create_folder import *
from learning_management_system.views.student_view import view_uploaded_documents, view_folders_and_files
from learning_management_system.views.ai_chat_view import ai_chat_view
# from learning_management_system.views.canva_upload_assignments import canva_upload_assignments, assignment_folders, canva_view_submissions
# from learning_management_system.views.canva_assignment_student_view import view_assignment_documents , view_uploaded_assignment_documents, submit_canva_assignment


urlpatterns = [
    
    # path('canva_management/', include(canva_urls)),  # Include all URLs from canva.urls
    
    
    
    # # path('canva_management/', canva_management, name = "canva_management"),
    # path('lms_assign_permission/', lms_assign_permission, name='lms_assign_permission'),
    # path('canva_home/', canva_home, name='canva_home'),
    path(
        "faculty/course/<int:course_id>/batch/<str:batch>/folders/<str:academic_year>/section/<str:section>/",course_folders,name="course_folders"
    ),
    path('learning_management_system/course_folders/<int:course_id>/upload/<int:folder_id>/', upload_to_folder, name='upload_to_folder'),

    # path('course/<int:course_id>/folder/<int:folder_id>/videos/', upload_video_to_folder, name='upload_video_to_folder'),

    
    # path('canva_management/view_assignment_documents/', view_assignment_documents, name='view_assignment_documents'),  # URL for viewing assignment documents
    # path('canva_management/view_uploaded_assignment_documents/<str:course_code>/', view_uploaded_assignment_documents, name='view_uploaded_assignment_documents'),
    # path('canva_management/submit_assignment/<int:assignment_id>/', submit_canva_assignment, name='submit_canva_assignment'),


    


    
    
    path('canva_management/view_uploaded_documents/', view_uploaded_documents, name='view_uploaded_documents'),  # URL for viewing uploaded documents
    path('canva_management/view_folders_and_files/<str:course_id>/', view_folders_and_files, name='view_folders_and_files'),
    path('ai-chat/<int:course_id>/', ai_chat_view, name='ai_chat_view'),
    # # path('folder_documents/<int:folder_id>/', folder_documents, name='folder_documents'),  # URL for viewing documents in a specific folder

    
    # path('canva_management/assignment_folders/<str:course_code>/', assignment_folders, name='assignment_folders'),
    # path('canva_management/canva_upload_assignments/<str:course_code>/<int:folder_id>/', canva_upload_assignments, name='canva_upload_assignments'),
    # path('canva_management/canva_view_submissions/<str:course_code>/<int:assignment_id>/submissions/', canva_view_submissions, name='canva_view_submissions'),
    






]
