from django.db import models
from user_accounts.models import USER, Role
from course_management.models import CourseEnrollment, Regulations
from user_accounts.models import StudentDetails
from faculty_management.models import general_information
from course_management.models import Course, AssignSubjectFaculty

from learning_management_system.utils.lms_folder_path_utils import faculty_document_path


# LMS Permissions Model
class LMS_Permissions(models.Model):
    role = models.ForeignKey(
        "user_accounts.Role",       # Role from external DB
        on_delete=models.DO_NOTHING, 
        db_constraint=False         # 🚨 disables DB-level FK
    )
    function = models.CharField(max_length=500)
    permission = models.BooleanField()

# Folder for storing documents and assignments
FOLDER_TYPE_CHOICES = (
    ('subject', 'Subject Folder'),
    ('assignment', 'Assignment Folder'),
)

class Folder(models.Model):
    folder_name = models.CharField(max_length=255, null=True, blank=True)
    regulation = models.ForeignKey(Regulations, on_delete=models.CASCADE, null=True, blank=True)
    faculty = models.ForeignKey(general_information, on_delete=models.CASCADE)
    academic_year = models.CharField(max_length=100, null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
    year = models.CharField(max_length=50, null=True, blank=True)
    semester = models.CharField(max_length=50, null=True, blank=True)
    section = models.CharField(max_length=50, null=True, blank=True)
    batch = models.CharField(max_length=50, null=True, blank=True)
    folder_type = models.CharField(
        max_length=20,
        choices=FOLDER_TYPE_CHOICES,
        default='subject'
    )
    # created_by = models.ForeignKey(general_information, on_delete=models.CASCADE, null=True, blank=True)
    def __str__(self):
        return f"{self.get_folder_type_display()}: {self.folder_name} - {self.course} - {self.academic_year}"

    class Meta:
        db_table = 'lms_create_folder'


# # Faculty Document Model
class FacultyDocument(models.Model):
    folder = models.ForeignKey(Folder, related_name='lms_documents', on_delete=models.CASCADE, null=True, blank=True)
    document_title = models.CharField(max_length=255, null=True, blank=True)
    academic_year = models.CharField(max_length=100, null=True, blank=True)
    # assigned_course = models.ForeignKey(AssignSubjectFaculty, on_delete=models.CASCADE, null=True, blank=True)
    year = models.CharField(max_length=50, null=True, blank=True)
    semester = models.CharField(max_length=50, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to=faculty_document_path, null=True, blank=True, max_length=255)
    uploaded_by = models.ForeignKey(general_information, on_delete=models.CASCADE, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document_title} by {self.uploaded_by.name}"

    class Meta:
        db_table = 'lms_faculty_document'
        ordering = ['-uploaded_at']

import re
from django.core.exceptions import ValidationError
from django.db import models

class FacultyVideo(models.Model):
    folder = models.ForeignKey(
        Folder,
        related_name='lms_videos',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    title = models.CharField(max_length=255)
    youtube_url = models.URLField(max_length=500)
    youtube_video_id = models.CharField(
        max_length=11,
        blank=True,
        null=True,
        editable=False,           # important: prevent manual editing
        help_text="Automatically extracted YouTube video ID"
    )
    description = models.TextField(blank=True, null=True)
    academic_year = models.CharField(max_length=50, null=True, blank=True)
    year = models.CharField(max_length=50, null=True, blank=True)
    semester = models.CharField(max_length=50, null=True, blank=True)
    uploaded_by = models.ForeignKey(general_information, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lms_faculty_video'
        ordering = ['-uploaded_at']

    def clean(self):
        if not self.youtube_url:
            raise ValidationError({"youtube_url": "YouTube URL is required."})

        # Very reliable regex that handles almost all real YouTube URLs
        pattern = r'(?:youtube(?:-nocookie)?\.com/(?:[^/\n\s]+/\S+/|(?:v|e(?:mbed)?|shorts?|live)/|.*[?&]v=)|youtu\.be/)([^"&?/\s]{11})'

        match = re.search(pattern, self.youtube_url, re.IGNORECASE)

        if match:
            self.youtube_video_id = match.group(1)
        else:
            raise ValidationError(
                {
                    "youtube_url": (
                        "Could not extract a valid 11-character YouTube video ID.\n\n"
                        "Supported formats include:\n"
                        " • https://www.youtube.com/watch?v=VIDEO_ID\n"
                        " • https://youtu.be/VIDEO_ID\n"
                        " • https://youtu.be/VIDEO_ID?si=...\n"
                        " • https://www.youtube.com/shorts/VIDEO_ID\n"
                        " • https://www.youtube.com/embed/VIDEO_ID\n"
                        " • https://youtube.com/live/VIDEO_ID\n"
                    )
                }
            )

    def save(self, *args, **kwargs):
        # Always validate and extract ID before saving
        self.full_clean()   # calls clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} by {self.uploaded_by.name}"


# # Canva Assignment Model
# class CanvaAssignment(models.Model):
#     folder = models.ForeignKey(Folder, related_name='canva_assignments', on_delete=models.CASCADE, null=True)  # Temporarily allow null

#     title = models.CharField(max_length=255, blank=True, null=True)
#     description = models.TextField(blank=True, null=True)
#     course_code = models.CharField(max_length=100)
#     faculty = models.ForeignKey(general_information, on_delete=models.CASCADE)
#     created_at = models.DateTimeField(auto_now_add=True)
#     due_date = models.DateTimeField()

#     intake = models.CharField(max_length=100)
#     batch = models.CharField(max_length=100)

#     assignment_file = models.FileField(upload_to='faculty_canva_assignments/')  # Faculty-uploaded file

#     total_marks = models.DecimalField(max_digits=5, decimal_places=2, default=100)

#     def __str__(self):
#         return f"{self.title} - {self.course_code}"

#     class Meta:
#         db_table = 'canva_upload_assignment'
#         ordering = ['-created_at']


# # Student Submission for Canva Assignment Model
# class StudentCanvaAssignmentSubmission(models.Model):
#     STATUS_CHOICES = [
#         ('not_completed', 'Not Completed'),
#         ('pending', 'Pending'),
#         ('completed', 'Completed'),
#         ('marked', 'Marked'),
#     ]

#     assignment = models.ForeignKey(CanvaAssignment, related_name='submissions', on_delete=models.CASCADE)
#     student = models.ForeignKey(StudentDetails, on_delete=models.CASCADE)
#     submitted_file = models.FileField(upload_to='student_submitted_canva_assignments/')
#     submitted_at = models.DateTimeField(auto_now_add=True)

#     marks_obtained = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
#     # feedback = models.TextField(null=True, blank=True)

#     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_completed')

#     def __str__(self):
#         return f"{self.student.first_name} - {self.assignment.title} ({self.get_status_display()})"

#     class Meta:
#         db_table = 'canva_student_assignment_submission'
#         unique_together = ('assignment', 'student')
#         ordering = ['-submitted_at']









