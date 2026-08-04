from django.urls import path

from library_management.views.library_admin_views import library_hello
from library_management.views.library_admin_views import *

urlpatterns = [
    path("library_hello/", library_hello, name="library_hello"),
        path("book-entry/", library_book_entry, name="library_book_entry"),
        path("student/request-book/", student_request_book, name="student_request_book"),
        path("hod/requests/", hod_library_requests, name="hod_library_requests"),
        path("incharge/requests/", library_incharge_requests, name="library_incharge_requests"),
        path("analytics-dashboard/", library_analytics_dashboard, name="library_analytics_dashboard"),
         

]
