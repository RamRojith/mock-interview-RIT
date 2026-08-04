from django.urls import path, include
from feedback_management.urls import feedback_control_urls, admin_feedback_urls, feedback_details_urls
from feedback_management.views import admin_feedback_views

urlpatterns = [
    path('admin/', include(admin_feedback_urls)),
    path('control/', include(feedback_control_urls)),
    path('details/', include(feedback_details_urls)),
    path('feedback_home/', admin_feedback_views.feedback_home, name="feedback_home"),
]

