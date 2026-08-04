from django.urls import path
from learning_management_system.views.admin_lms_view import lms_assign_permission, lms_hello, lms_home

urlpatterns = [
    path('lms_assign_permission/', lms_assign_permission, name='lms_assign_permission'),
    
    
]
