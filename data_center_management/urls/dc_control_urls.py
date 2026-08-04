from django.urls import path, include
from data_center_management.views import admin_dc_views , dc_curd_views

urlpatterns = [
    path("dc_hello/", admin_dc_views.dc_hello, name="dc_hello"),
    path("dc_approval_system/", admin_dc_views.dc_approval_system, name="dc_approval_system"),
    path("wifi_application/", dc_curd_views.wifi_application, name="wifi_application"),
    path("query_application/", dc_curd_views.query_application, name="query_application"),
    path("wifi_application_approval/", dc_curd_views.wifi_application_approval, name="wifi_application_approval"),
    path("queries_approval/", dc_curd_views.queries_approval, name="queries_approval"),
    # path("wifi_application_status/", dc_curd_views.wifi_application_status, name="wifi_application_status"),
    path("queries_resolve/", dc_curd_views.queries_resolve, name="queries_resolve"),
    path("wifi_approved_credentials/", dc_curd_views.wifi_approved_credentials, name="wifi_approved_credentials"),
    path("user_wifi_credentials/", dc_curd_views.user_wifi_credentials, name="user_wifi_credentials"),
    path("guest_wifi_application/", dc_curd_views.guest_wifi_application, name="guest_wifi_application"),
    path("guest_wifi_approval/", dc_curd_views.guest_wifi_approval, name="guest_wifi_approval"),
    # path("guest_wifi_credentials/", dc_curd_views.guest_wifi_credentials, name="guest_wifi_credentials"),
    path("system_support_approval/", dc_curd_views.system_support_approval, name="system_support_approval"),
    path("system_support_application/", dc_curd_views.system_support_application, name="system_support_application"),
    path("system_support_resolve/", dc_curd_views.system_support_resolve, name="system_support_resolve"),
    
    path("email_relogin_apllication/", dc_curd_views.email_relogin_apllication, name="email_relogin_apllication"),
    path("email_relogin_approval/", dc_curd_views.email_relogin_approval, name="email_relogin_approval"),
    path("email_relogin_dashboard/", dc_curd_views.email_relogin_dashboard, name="email_relogin_dashboard"),
    

    path("application_dashboard/", dc_curd_views.application_dashboard, name="application_dashboard"),


]

