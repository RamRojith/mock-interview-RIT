from django.urls import path, include
from fee_management.views.admin_fee_views import fee_assign_permission
from fee_management.views import fee_views as views
from fee_management.views import admin_fee_views as admin_fee_views

urlpatterns = [
    
    path("fee_assign_permission/", fee_assign_permission, name="fee_assign_permission"),
    path('add_fee_type/', views.add_fee_type, name='add_fee_type'),
    path('manage_fees/', views.manage_fees, name='manage_fees'),
    path('fee_entry/', views.fee_entry, name='fee_entry'),
    # path('edit_fee_type/', views.edit_fee_type, name='edit_fee_type'),
    path('fee/delete-fee-type/<int:fee_category_id>/', views.delete_fee_type, name='delete_fee_type'),
    # path("scholarship-fee/add/", views.add_scholarship_fee, name="add_scholarship_fee"),
    # path("scholarship-fee/<int:pk>/edit/", views.edit_scholarship_fee, name="edit_scholarship_fee"),
    # path("scholarship-fees/", views.view_scholarship_fees, name="view_scholarship_fees"),
    # path("scholarship-fee/<int:pk>/delete/", views.delete_scholarship_fee, name="delete_scholarship_fee"),

    # New scholarship fee routes
    path('add_scholarship_type/', views.add_scholarship_type, name='add_scholarship_type'),
    # path('add-scholarship-type/', views.add_scholarship_type, name='add_scholarship_type'),
    path('delete-scholarship-type/<int:pk>/', views.delete_scholarship_type, name='delete_scholarship_type'),
    path('scholarship_fee_entry/', views.scholarship_fee_entry, name='scholarship_fee_entry'),
    path("transport_stage_entry/", views.transport_stage_entry, name="transport_stage_entry"),
    path("transport_fee_entry/", views.transport_fee_entry, name="transport_fee_entry"),
    path("assign_fee_view_permission/", admin_fee_views.assign_fee_view_permission, name="assign_fee_view_permission"),
    path("fee_view_permission_api/", admin_fee_views.fee_view_permission_api, name="fee_view_permission_api"),
    path("ajax/get-departments/", views.get_departments_by_degree, name="get_departments_by_degree"),

]