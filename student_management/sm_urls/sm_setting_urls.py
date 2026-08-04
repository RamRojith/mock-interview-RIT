from django.urls import path,include
from student_management.sm_urls import admin_sm_urls, sm_approve_urls, sm_control_urls
from student_management.views.sm_curd import *

from student_management.sm_urls import sm_urls, passout_students_urls

from student_management.views import admin_control_sm

urlpatterns = [
    path("student_management_admin/",include(admin_sm_urls)),
    path("student_management/", include(sm_urls)),
    path("students/", include(sm_control_urls)),
    path("passout_students/",include(passout_students_urls)),
    path("student_management/", include(sm_approve_urls)),

    path('sm_home/', admin_control_sm.sm_home, name="sm_home")
   
    
]