from django.contrib import admin
from faculty_management.models import FacultyCategory, SeminarHallBooking


@admin.register(FacultyCategory)
class FacultyCategoryAdmin(admin.ModelAdmin):
    list_display = ("category_name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("category_name",)

# Register your models here.

# @admin.register(SeminarHallBooking)
# class SeminarHallBookingAdmin(admin.ModelAdmin):
#     list_display = ['booking_id', 'faculty_name', 'event_name', 'booking_date', 'preferred_hall', 'status', 'created_at']
#     list_filter = ['status', 'event_type', 'preferred_hall', 'booking_date']
#     search_fields = ['booking_id', 'faculty_name', 'event_name', 'guest_name']
#     readonly_fields = ['booking_id', 'created_at', 'updated_at']
#     date_hierarchy = 'booking_date'
    
#     fieldsets = (
#         ('Booking Information', {
#             'fields': ('booking_id', 'status', 'created_at', 'updated_at')
#         }),
#         ('Faculty Information', {
#             'fields': ('faculty', 'faculty_name', 'faculty_email', 'faculty_phone', 'department')
#         }),
#         ('Event Details', {
#             'fields': ('event_name', 'event_type', 'event_description', 'target_audience')
#         }),
#         ('Guest Information', {
#             'fields': ('has_guest_speaker', 'guest_name', 'guest_designation', 'guest_organization', 'guest_email', 'guest_phone')
#         }),
#         ('Schedule', {
#             'fields': ('booking_date', 'start_time', 'end_time', 'preferred_hall', 'expected_attendees')
#         }),
#         ('Requirements', {
#             'fields': ('needs_projector', 'needs_microphone', 'needs_sound_system', 'needs_video_conferencing', 'needs_refreshments', 'refreshment_details', 'special_requirements')
#         }),
#         ('Approval', {
#             'fields': ('approved_by', 'approval_date', 'rejection_reason')
#         }),
#     )
