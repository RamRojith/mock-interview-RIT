from django.urls import path, include
from fee_management.urls import fee_controls_url, admin_fee_urls
from fee_management.views.admin_fee_views import fee_home


urlpatterns = [
    path('', include(admin_fee_urls)),
    path('controls/', include(fee_controls_url)),
    path("fee_home/", fee_home, name="fee_home"),
]
