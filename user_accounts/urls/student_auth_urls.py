from django.urls import path
from user_accounts.views import student_auth_views

urlpatterns = [
    path('check_aadhar/', student_auth_views.check_aadhar, name="check_aadhar"),
    path('student_sign_up/', student_auth_views.student_sign_up, name="student_sign_up"),

    path('student_login/', student_auth_views.student_login, name="student_login"),
    path('student_logout/', student_auth_views.student_logout, name="student_logout"),

]


