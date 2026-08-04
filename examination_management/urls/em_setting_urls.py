from django.urls import path, include

from examination_management.views import admin_em
from examination_management.urls import admin_em_urls, em_control_urls, em_result_urls, em_ajax_urls


urlpatterns = [
   
   path('em_home/', admin_em.em_home, name="em_home"),

    path('', include(admin_em_urls)),
    path('', include(em_control_urls)),
    path('result/', include(em_result_urls)),
    path('ajax/', include(em_ajax_urls)),

]
