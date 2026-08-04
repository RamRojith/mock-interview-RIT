from django.urls import path
from fee_management.views.admin_fee_views import fee_hello
from student_management.views import sm_curd , sm_views
from fee_management.views import fee_views


urlpatterns = [
    path("fee_hello/", fee_hello, name="fee_hello"),
    path('fee_receipt_upload/', sm_curd.fee_receipt_upload, name='fee_receipt_upload'),
    path('manual_fee_entry/', sm_curd.manual_fee_entry, name='manual_fee_entry'),
    path('student_fee_view/', sm_views.student_fee_view, name='student_fee_view'),
    # Combined Faculty page (replaces mentor and CA pages)
    path('fee_view/', sm_views.fee_view, name='fee_view'),
    # AJAX endpoints for fee details
    path('get_payment_history/<str:reg_no>/', sm_views.get_payment_history, name='get_payment_history'),
    path('get_fee_structure/<str:reg_no>/', sm_views.get_fee_structure, name='get_fee_structure'),
    
    path('ja_scholarship_entry/', fee_views.ja_scholarship_entry, name='ja_scholarship_entry'),
    
]
