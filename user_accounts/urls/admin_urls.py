from django.urls import path
from user_accounts.views.dashboards import *

# ✅ ADD THIS IMPORT



urlpatterns = [
    path('admin_management', admin_management, name="admin_management"),
    path('faculty_management', faculty_management, name="faculty_management"),
    path('student_management', student_management, name="student_management"),
    path('faculty_leave_management', faculty_leave_management, name="faculty_leave_management"),
    path('course_management', course_management, name="course_management"),
    path('examination_management', examination_management, name="examination_management"),
    path('fee_management', fee_management, name='fee_management'),
    path('nba_management', nba_management, name='nba_management'),
    path('feedback_management', feedback_management, name="feedback_management"),
    path('lms_management', lms_management, name="lms_management"),
    path('data_center_management', data_center_management, name="data_center_management"),
    path('library_management', library_management, name="library_management"),
    path('stock_management', stock_management, name="stock_management"),


]

