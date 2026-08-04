from django.urls import path,include
from learning_management_system.urls import lms_control_urls, lms_details_urls, admin_lms_urls
from learning_management_system.views.admin_lms_view import lms_assign_permission, lms_home

urlpatterns = [
    path('lms/', include(lms_control_urls)),  # Include all URLs from lms_control_urls
    path('lms/', include(lms_details_urls)),  # Include all URLs from lms_details_urls
    path('admin/lms/', include(admin_lms_urls)),  # Include all URLs from admin_lms_urls
    path('lms_home/', lms_home, name='lms_home'),

]

