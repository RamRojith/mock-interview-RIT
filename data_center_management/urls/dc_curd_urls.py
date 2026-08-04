from django.urls import path, include
from data_center_management.views import admin_dc_views, dc_curd_views

urlpatterns = [
    path("dc_assign_permission/", admin_dc_views.dc_assign_permission, name="dc_assign_permission"),
    path("get-student-by-reg-no/",dc_curd_views.get_student_by_reg_no,name="get_student_by_reg_no"),
]

