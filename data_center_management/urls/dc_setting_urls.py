from django.urls import path, include
from data_center_management.views import admin_dc_views
from data_center_management.urls import dc_control_urls, dc_curd_urls

urlpatterns = [
    path('dc_settings/', include(dc_control_urls)),
    path('dc_home/', admin_dc_views.dc_home, name='dc_home'),
    path('dc_crud/', include(dc_curd_urls)),
]

