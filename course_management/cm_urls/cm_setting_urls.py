from django.urls import path,include
from course_management.cm_urls import admin_cm,cm_details,cm_curd , course_examination_urls, ajax_urls
from course_management.views.faculty_control_cm import cm_home
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path("course_admin/",include(admin_cm)),
    path("course_details/",include(cm_details)),
    path("course_management/",include(cm_curd)),
    path("course_examination/",include(course_examination_urls) ),  
    path("ajax/",include(ajax_urls) ),  
    path("Home/",cm_home,name="cm_home"),

]
  