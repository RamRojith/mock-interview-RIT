from django.urls import path
from nba.views.sanctioned_intake_details_views import *
from nba.views.module_4_views import *

urlpatterns = [
    path('add-sanctioned-intake/', add_sanctioned_intake, name='add_sanctioned_intake'),
    path('ajax/departments/', get_departments_by_degree, name='ajax_get_departments'),
    path("pa/472/lookup/", student_lookup, name="student_lookup"),
    
    
]