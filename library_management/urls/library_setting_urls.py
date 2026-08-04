from django.urls import path, include
from library_management.urls import library_admin_urls, library_control_urls
from library_management.views import library_admin_views

urlpatterns = [
    path("library_admin/", include(library_admin_urls)),
    path("library_control/", include(library_control_urls)),
    path("Home/",library_admin_views.library_home,name="library_home"),
]


