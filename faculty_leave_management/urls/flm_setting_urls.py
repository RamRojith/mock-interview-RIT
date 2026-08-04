from django.urls import path,include
from faculty_leave_management.views.authorizer import leave_management
from faculty_leave_management.urls import flm_admin,flm_application, flm_control_urls
from faculty_leave_management.views.flm_admin import flm_hello, flm_home
urlpatterns = [

 path('flm_admin/', include(flm_admin)), 
 path('faculty_leave/',include(flm_application)),
 path('faculty/leave/',include(flm_control_urls)),
 path('faculty_leave',leave_management,name='leave_management'),



 path("flm_home/", flm_home, name='flm_home'),

]

