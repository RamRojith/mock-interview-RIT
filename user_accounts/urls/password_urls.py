from django.urls import path, include
from user_accounts.views import password_views

urlpatterns = [
    path('password/forget-password/', password_views.forgot_password, name='forgot_password'),
    path('password/verify-otp/', password_views.verify_otp, name='verify_otp'),
    path('password/reset/', password_views.reset_password, name='reset_password'),
    path('password/set-new/', password_views.set_new_password, name='set_new_password'),
    path('password/change/', password_views.change_logged_in_password, name='change_logged_in_password'),
]
