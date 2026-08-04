from django.urls import path,include
from faculty_management.fm_urls import admin_fm,fm_curd, fm_control_urls

from faculty_management.views import admin_control_fm

urlpatterns = [
     path('fm_home/', admin_control_fm.fm_home, name="fm_home"),
    
    
    path("faculty/",include(fm_curd)),
    path("faculty_management_admin/",include(admin_fm)),
    path('', include(fm_control_urls)),
   
 ]
 