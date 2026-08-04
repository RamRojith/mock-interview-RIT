from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from student_management.views.admin_control_sm import (

    sm_assign_permission,
    student_details,
    edit_student_details,
    sync_student_reg_numbers,
    upload_student_details,
    sync_user_student_aadhar_to_reg_numbers,
    sync_user_to_admission_student_details,
    sync_student_to_user_details,
    sync_student_mode_from_admission,
    student_details_ajax, export_student_basic_excel,
    discontinue_student_ajax,

)
from student_management.views.sm_views import *
from student_management.views import sm_curd
urlpatterns = [

    
    
    path('sm_assign_permission/', sm_assign_permission, name='sm_assign_permission'),

     path('upload_calendar/',upload_calendar, name='upload_calendar'),
    path('delete_calendar/<int:calendar_id>/',delete_calendar, name='delete_calendar'),

    path('students/', student_details, name='student_details'),
    path("student-details/ajax/", student_details_ajax, name="student_details_ajax"),
    path("students/discontinue/", discontinue_student_ajax, name="discontinue_student_ajax"),
    path('students/edit/<int:id>/', edit_student_details, name='edit_student_details'),
    path("students/upload/", upload_student_details, name="upload_student_details"),
    path('sync_user_student_aadhar_to_reg_numbers/', sync_user_student_aadhar_to_reg_numbers, name='sync_user_student_aadhar_to_reg_numbers'),
    path('sync_user_to_admission_student_details/', sync_user_to_admission_student_details, name='sync_user_to_admission_student_details'),
    path('sync_student_to_user_details/', sync_student_to_user_details, name='sync_student_to_user_details'),
    path('sync_student_mode_from_admission/', sync_student_mode_from_admission, name='sync_student_mode_from_admission'),
    # urls.py
path(
    "sync-student-reg-numbers/",
    sync_student_reg_numbers,
    name="sync_student_reg_numbers"
),

path(
    "edit-our-student/<int:student_id>/",
    edit_our_student,
    name="edit_our_student"
),

 path(
        "our_students/data/",
        our_students_data,
        name="our_students_data"
    ),
    path(
    "students/export-excel-2/",
    export_student_basic_excel,
    name="export_student_basic_excel",
),


]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

