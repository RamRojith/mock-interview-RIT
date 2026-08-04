"""
URL configuration for rit_academic_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static 

from user_accounts.urls import user_setting_urls

from user_accounts.views.dashboards import index
from user_accounts.views.dashboards import faculty_dashboard, home, student_dashboard, parent_dashboard
from course_management.cm_urls import cm_setting_urls
from examination_management.urls import em_setting_urls
from student_management.sm_urls import sm_setting_urls
from faculty_management.fm_urls import fm_setting_urls
from fee_management.urls import fee_setting_urls
from nba.urls import nba_setting_urls
from faculty_leave_management.urls import flm_setting_urls
from feedback_management.urls import feedback_setting_urls
from learning_management_system.urls import lms_setting_urls
from data_center_management.urls import dc_setting_urls
from library_management.urls import library_setting_urls
from stock_management.urls import stock_setting_urls

urlpatterns = [
    # path('admin/', admin.site.urls),
    path('', include(user_setting_urls)),
    path('course_management/', include(cm_setting_urls)),
    path("examination_management/", include(em_setting_urls)),
    path('student_management/', include(sm_setting_urls)),
    path('faculty_management/', include(fm_setting_urls)),
    path('fee_management/', include(fee_setting_urls)),
    path('nba_management/', include(nba_setting_urls)),
    
    path('faculty_leave_management/', include(flm_setting_urls)),
    path('feedback_management/', include(feedback_setting_urls)),
    path('learning_management_system/', include(lms_setting_urls)),
    path('data_center_management/', include(dc_setting_urls)),
    path('library_management/', include(library_setting_urls)),
    path('stock_management/', include(stock_setting_urls)),
    path('chatbot/', include('chatbot.urls')),
    path('mock-interview/', include('mock_interview.urls', namespace='mock_interview')),


    path('', index, name="index"),
    path('faculty_dashboard/',faculty_dashboard,name="faculty_dashboard"),
    path('student_dashboard/', student_dashboard, name="student_dashboard"),
    path('parent_dashboard/', parent_dashboard, name="parent_dashboard"),

    


    path('home/',home,name="home"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
