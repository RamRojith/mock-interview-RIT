from django.urls import path
from user_accounts.views.auth_views import *
from user_accounts.views import admin_views
from user_accounts.views import audit_views

urlpatterns = [
    path('login/', login_view, name="login_view"),
    path("faculty/sign-up/", faculty_sign_up, name="faculty_sign_up"),
    path('logout/', logout_view, name='logout'),


    path('users/staff-accounts/', admin_views.staff_user_accounts, name="staff_user_accounts"),
    path("curd/staff_accounts/data/", admin_views.staff_user_accounts_data, name="staff_user_accounts_data"),  # ✅ AJAX
    path("users/staff-accounts/<int:id>/reset-password/", admin_views.reset_staff_user_password, name="reset_staff_user_password"),
    path('user-accounts/staff-accounts/edit/<int:id>/', admin_views.edit_staff_user_accounts, name='edit_staff_user_accounts'),

    path('users/student-accounts/', admin_views.student_user_accounts, name="student_user_accounts"),
    path("admin/student_accounts/data/", admin_views.student_user_accounts_data, name="student_user_accounts_data"),
    path("users/student-accounts/<int:id>/reset-password/", admin_views.reset_student_user_password, name="reset_student_user_password"),
    path('user-accounts/student-accounts/edit/<int:id>/', admin_views.edit_student_user_accounts, name='edit_student_user_accounts'),


    path('users/parent-accounts/', admin_views.parent_user_accounts, name="parent_user_accounts"),
    path("admin/parents/data/", admin_views.parent_user_accounts_data, name="parent_user_accounts_data"),
    path("users/parent-accounts/<int:id>/reset-password/", admin_views.reset_parent_user_password, name="reset_parent_user_password"),
    path('user-accounts/parent-accounts/edit/<int:id>/', admin_views.edit_parent_user_accounts, name='edit_parent_user_accounts'),
    path('switch_user',admin_views.switch_user,name="switch_user"),



    path('degree_departments',admin_views.degree_departments,name="degree_departments"),

     path('add_degree',admin_views.add_degree,name="add_degree"),
     path("admin/degree/data/", admin_views.add_degree_data, name="add_degree_data"),
     path("export_degree_excel/", admin_views.export_degree_excel, name="export_degree_excel"),

      path('add_department',admin_views.add_department,name="add_department"),
       path("admin/programs/data/", admin_views.add_department_data, name="add_department_data"),
       path("export_department_excel/", admin_views.export_department_excel, name="export_department_excel"),
    


path("curd_approvals/", admin_views.curd_approvals, name="curd_approvals"),

    path('create_global_users/', admin_views.create_global_users, name='create_global_users'),


    path("role_view/", admin_views.role_view, name="role_view"),
    path("roles_views_data/", admin_views.role_view_data, name="role_view_data"),
    path("export_role_excel/", admin_views.export_role_excel, name="export_role_excel"),

    path("admin/system-logs/", audit_views.system_audit_logs, name="system_audit_logs"),
    path("admin/system-logs/data/", audit_views.system_audit_logs_data, name="system_audit_logs_data"),
]


