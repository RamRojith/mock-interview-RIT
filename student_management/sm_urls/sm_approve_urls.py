
from django.urls import path, include
from student_management.views import sm_approve_views

urlpatterns = [

    path('bonafide/delete/', sm_approve_views.delete_bonafide_request, name='delete_bonafide_request'),
    path('bonafide/view_pdf/<int:app_id>/', sm_approve_views.bonafide_view_pdf, name='bonafide_view_pdf'),
    path("students/bonafide/edit/", sm_approve_views.bonafide_edit, name="bonafide_edit"),




    # path("bonafide/approve/", sm_approve_views.bonafide_approve_view, name="bonafide_approve"),


    path("assign-approval/", sm_approve_views.assign_approval_management, name="assign_approval_management"),
    path("api/assign-roles/<int:creatorRoleId>/", sm_approve_views.api_assign_role_to_employees, name="api_assign_role_to_employees"),

    
]
