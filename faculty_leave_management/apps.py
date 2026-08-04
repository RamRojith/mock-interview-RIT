from django.apps import AppConfig


class FacultyLeaveManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'faculty_leave_management'
    def ready(self):
        from faculty_leave_management import signals