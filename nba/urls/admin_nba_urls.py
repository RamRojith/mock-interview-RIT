from django.urls import path
from nba.views.sanctioned_intake_details_views import *
from nba.views.module_4_views import *
from nba.views.admin_nba_views import *


urlpatterns = [

    path('nba_assign_permission', nba_assign_permission, name='nba_assign_permission'),
    
    path('add_sanctioned_intake', add_sanctioned_intake, name='add_sanctioned_intake'),
    path('edit-sanctioned-intake/<int:id>/', edit_sanctioned_intake, name='edit_sanctioned_intake'),
    path('delete-sanctioned-intake/<int:id>/',delete_sanctioned_intake, name='delete_sanctioned_intake'),
    path("nba/get-batches-by-department/", get_batches_by_department, name="get_batches_by_department"),
    path("nba/get-intake-snapshot/", get_intake_snapshot, name="get_intake_snapshot"),  # NEW

]

