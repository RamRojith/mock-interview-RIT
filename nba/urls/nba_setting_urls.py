from django.urls import path, include

from nba.urls import admin_nba_urls
from nba.urls import nba_controls_urls
from nba.urls import nba_ajax_urls
from nba.urls import nba_curd_urls

from nba.views.admin_nba_views import nba_home
urlpatterns = [
   path('admin_nba/', include(admin_nba_urls)),
   path('nba_controls/', include(nba_controls_urls)),
   path('nba_ajax/', include(nba_ajax_urls)),
   path('nba_curd/', include(nba_curd_urls)),
    path("nba_home/",nba_home,name="nba_home"),
]

