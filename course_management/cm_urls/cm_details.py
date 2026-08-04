from django.urls import path
from course_management.views.cm_details import *

from django.conf.urls.static import static
from django.conf import settings
urlpatterns = [    

    # path('fetch_student_marks/', fetch_student_marks, name='fetch_student_marks'),
    # path('generate_pdf/<int:semester>/', generate_pdf, name='generate_pdf'),

    # path('Student_Semester_Mark_Dashboard/', Student_Semester_Mark_Dashboard, name='Student_Semester_Mark_Dashboard'),
    # path('fetch_students_for_mark/', fetch_students_for_mark, name='fetch_students_for_mark'),
    # path('course_details/register_course/<str:course_code>/', register_course, name='register_course'),
    # path('get_student_details',get_student_details,name='get_student_details')
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)