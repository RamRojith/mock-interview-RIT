from django.urls import path, include
from user_accounts.urls import auth_urls, admin_urls, student_auth_urls, parent_auth_urls, password_urls


urlpatterns = [
    path('user-accounts/', include(auth_urls)),
    path('students/user-accounts/', include(student_auth_urls)),
    path('parents/user-accounts/', include(parent_auth_urls)),
    path('user-accounts/passwords/', include(password_urls)),

    path('', include(admin_urls))
]
