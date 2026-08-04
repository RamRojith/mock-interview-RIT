from django.urls import path
from user_accounts.views import parent_auth_views

urlpatterns = [
    path('parent_check_aadhar/', parent_auth_views.parent_check_aadhar, name="parent_check_aadhar"),
    path('parent_sign_up/', parent_auth_views.parent_sign_up, name="parent_sign_up"),

    path('parent_login/', parent_auth_views.parent_login, name="parent_login"),
    path('parent_logout/', parent_auth_views.parent_logout, name="parent_logout"),

]


