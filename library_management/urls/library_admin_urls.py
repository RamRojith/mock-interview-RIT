# library_management/urls/library_admin_urls.py
from django.urls import path

from library_management.views.library_admin_views import (
    # BOOK TYPE
    book_type_page,
    edit_book_type,
    delete_book_type,

    # BOOK ENTRY
    library_book_entry,
    delete_library_book,
    delete_all_library_books,
    library_books_sample_excel,

    # PERMISSION
    library_assign_permission,

    # ANALYTICS
    library_analytics_dashboard,
    library_analytics_dashboard_pdf,

    # STUDENT
    student_request_book,\
    student_request_book_pdf,
    
    student_return_request,

    # HOD
    hod_library_requests,
    hod_approve_book_request,
    hod_reject_book_request,
    hod_confirm_return,

    # ✅ APPROVER MANAGEMENT
    library_request_approval_management,

    # ✅ INCHARGE (ADD THESE IMPORTS)
    library_incharge_requests,
    incharge_approve_book_request,
    incharge_reject_book_request,
    incharge_confirm_return,
    edit_library_book,
    
    
)

urlpatterns = [

    # ================= PERMISSION =================
    path("library_assign_permission/", library_assign_permission, name="library_assign_permission"),

    # ================= BOOK TYPE MASTER =================
    path("book-type/", book_type_page, name="book_type_page"),
    path("book-type/edit/<int:pk>/", edit_book_type, name="edit_book_type"),
    path("book-type/delete/<int:pk>/", delete_book_type, name="delete_book_type"),

    # ================= ANALYTICS DASHBOARD =================
    
    path("analytics-dashboard/pdf/", library_analytics_dashboard_pdf, name="library_analytics_dashboard_pdf"),

    # ================= BOOK ENTRY =================
    path("book-entry/", library_book_entry, name="library_book_entry"),
    path("book-entry/sample-excel/", library_books_sample_excel, name="library_books_sample_excel"),

    # ================= DELETE BOOK =================
    path("book-entry/delete/<int:pk>/", delete_library_book, name="delete_library_book"),
    path("delete-all-library-books/", delete_all_library_books, name="delete_all_library_books"),

    # ================= STUDENT =================
    path("student/request-book/", student_request_book, name="student_request_book"),
    path("student/request-book/pdf/<int:pk>/", student_request_book_pdf, name="student_request_book_pdf"),
    # path("student/my-requests/", student_my_requests, name="student_my_requests"),
    path("student/return/<int:pk>/", student_return_request, name="student_return_request"),

    # ================= HOD =================
    path("hod/requests/", hod_library_requests, name="hod_library_requests"),
    path("hod/requests/approve/<int:pk>/", hod_approve_book_request, name="hod_approve_book_request"),
    path("hod/requests/reject/<int:pk>/", hod_reject_book_request, name="hod_reject_book_request"),
    path("hod/requests/confirm-return/<int:pk>/", hod_confirm_return, name="hod_confirm_return"),

    # ================= APPROVER MANAGEMENT =================
    path("library-request-approval-management/", library_request_approval_management,
         name="library_request_approval_management"),

    # ================= LIBRARY INCHARGE (NEW URLS) =================
    
    path("incharge/requests/approve/<int:pk>/", incharge_approve_book_request, name="incharge_approve_book_request"),
    path("incharge/requests/reject/<int:pk>/", incharge_reject_book_request, name="incharge_reject_book_request"),
    path("incharge/requests/confirm-return/<int:pk>/", incharge_confirm_return, name="incharge_confirm_return"),
    # ================= EDIT BOOK =================
    # ================= EDIT BOOK =================
path("book-entry/edit/<int:pk>/", edit_library_book, name="edit_library_book"),
    
]
