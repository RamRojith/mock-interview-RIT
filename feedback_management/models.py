from django.db import models
from course_management.views.faculty_control_cm import get_academic_year
from user_accounts.models import  Role
from course_management.models import Co_Po_Mapping, Course, CourseEnrollment, Regulations
from django.core.validators import MinValueValidator, MaxValueValidator
from examination_management.models import CourseOutcome, BloomsLevel, ProgrammeOutcome
from user_accounts.models import StudentDetails
from course_management.models import CourseEnrollment, AssignSubjectFaculty
from examination_management.models import Regulations


class feedback_data_Permission(models.Model):
    role_id = models.PositiveIntegerField(null=True, blank=True)

    can_view_all_feedback_data = models.BooleanField(default=False, null=True, blank=True)
    can_view_department_feedback_data = models.BooleanField(default=False, null=True, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"Role ID: {self.role_id}"




from django.db import models


class end_survey_data_Permission(models.Model):
    role_id = models.PositiveIntegerField(null=True, blank=True)

    can_view_all_end_survey_data = models.BooleanField(default=False, null=True, blank=True)
    can_view_department_end_survey_data = models.BooleanField(default=False, null=True, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"Role ID: {self.role_id}"


class program_exit_Permission(models.Model):
    role_id = models.PositiveIntegerField(null=True, blank=True)

    can_view_all_program_exit_data = models.BooleanField(default=False, null=True, blank=True)
    can_view_department_program_exit_data = models.BooleanField(default=False, null=True, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"Role ID: {self.role_id}"



class course_exit_Permission(models.Model):
    role_id = models.PositiveIntegerField(null=True, blank=True)

    can_view_all_course_exit_data = models.BooleanField(default=False, null=True, blank=True)
    can_view_department_course_exit_data = models.BooleanField(default=False, null=True, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"Role ID: {self.role_id}"






class FeedbackPermission(models.Model):
    role = models.ForeignKey(
        "user_accounts.Role",      
        on_delete=models.DO_NOTHING, 
        db_constraint=False     
    )
    function = models.CharField(max_length=500)
    permission = models.BooleanField()





class gradeupload(models.Model):
    grade = models.CharField(max_length=100, null=True, blank=True)
    marks = models.IntegerField(default=0, null=True, blank=True)

    def __str__(self):
        return self.grade


from django.db import models
from django.utils import timezone


class FeedbackQuestion(models.Model):
    question_text = models.CharField(max_length=255, null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    department = models.ForeignKey(
        'user_accounts.Add_Department',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.question_text or ""







from django.db import models
from django.utils import timezone

from django.db import models
from django.utils import timezone


class FeedbackSubmission(models.Model):
    """
    One submission per student per enrolled course (per survey window).
    """
    student = models.ForeignKey("user_accounts.StudentDetails", on_delete=models.CASCADE)
    enrollment = models.ForeignKey("course_management.CourseEnrollment", on_delete=models.CASCADE)

    department = models.ForeignKey(
        "user_accounts.Add_Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    course = models.ForeignKey(
        "course_management.Course",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    faculty = models.ForeignKey(
        "faculty_management.general_information",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    submitted_at = models.DateTimeField(default=timezone.now)
    total_score = models.IntegerField(default=0)

    window_start = models.DateField(null=True, blank=True)
    window_end = models.DateField(null=True, blank=True)

    # OLD

    # NEW EXTRA 4 FIELDS
    overall_effectiveness_percentage = models.PositiveIntegerField(null=True, blank=True)
    student_satisfaction = models.BooleanField(null=True, blank=True)
    recommendation_to_continue_improve = models.TextField(null=True, blank=True)
    open_comments_for_improvement = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = ("student", "enrollment")

    def __str__(self):
        return f"{self.student} - {self.course} ({self.submitted_at.date()})"




class FeedbackAnswer(models.Model):
    submission = models.ForeignKey(
        FeedbackSubmission,
        on_delete=models.CASCADE,
        related_name="answers"
    )
    question = models.ForeignKey(FeedbackQuestion, on_delete=models.CASCADE, null=True, blank=True)
    selected_grade = models.CharField(max_length=10, null=True, blank=True)
    score = models.IntegerField(default=0)

    class Meta:
        unique_together = ("submission", "question")

    def __str__(self):
        return f"{self.question} = {self.selected_grade} ({self.score})"







class CourseFeedbackRemark(models.Model):
    faculty = models.ForeignKey(
        "faculty_management.general_information",on_delete=models.CASCADE,related_name="course_feedback_remarks",null=True,blank=True, )
    department = models.ForeignKey(
        "user_accounts.Add_Department",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="course_feedback_remarks",
    )
    course = models.ForeignKey(
        "course_management.Course",
        on_delete=models.CASCADE,
        related_name="feedback_remarks",
    )
    remarks = models.TextField(null=True, blank=True)
    action_taken = models.TextField(null=True, blank=True)

    # NEW FIELD
    report_file = models.FileField(
        upload_to="feedback_reports/",
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["faculty", "department", "course"],
                name="unique_course_feedback_remark_per_faculty_course"
            )
        ]

    def __str__(self):
        return f"{self.course} - {self.faculty}"
    




class CourseOutcomeDescription(models.Model):
    co_description = models.CharField(max_length=500, null=True, blank=True)
    start_datetime = models.DateTimeField(null=True, blank=True)
    end_datetime = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    co_po_mapping = models.ForeignKey(
        Co_Po_Mapping,
        on_delete=models.CASCADE,
        related_name='courseoutcomedescription',
        null=True,
        blank=True
    )

    def __str__(self):
        return f"CO Description for {self.co_po_mapping.co_number.co_code} ({self.co_po_mapping.course.course_code})"








from django.db import models
from user_accounts.models import StudentDetails
from course_management.models import CourseEnrollment, Course, Co_Po_Mapping
from faculty_management.models import general_information
from feedback_management.models import gradeupload


class CourseOutcomeSubmission(models.Model):
    student = models.ForeignKey(
        StudentDetails,
        on_delete=models.CASCADE,
        related_name="course_outcome_submissions"
    )
    enrollment = models.ForeignKey(
        CourseEnrollment,
        on_delete=models.CASCADE,
        related_name="course_outcome_submissions"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="course_outcome_submissions"
    )
    faculty = models.ForeignKey(
        general_information,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="course_outcome_submissions"
    )
    co_po_mapping = models.ForeignKey(
        Co_Po_Mapping,
        on_delete=models.CASCADE,
        related_name="student_submissions",null=True, blank=True
    )
    selected_grade = models.ForeignKey(
        gradeupload,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="course_outcome_grade_submissions"
    )
    score = models.IntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "enrollment", "co_po_mapping")
        ordering = ["co_po_mapping_id"]

    def __str__(self):
        return f"{self.student} - {self.course} - {self.co_po_mapping}"







from course_management.models import Program_outcomes


class ProgramExitQuestion(models.Model):
    question_text = models.CharField(max_length=255, null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    department = models.ForeignKey(
        'user_accounts.Add_Department',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    po_type = models.CharField(
        max_length=20,
        choices=(
            ("revised", "Revised"),
            ("non_revised", "Non Revised"),
        ),
        null=True,
        blank=True
    )

    program_outcomes = models.JSONField(default=list, blank=True, null=True)


    def __str__(self):
        return self.question_text or ""




class ProgramExitSubmission(models.Model):
    student = models.ForeignKey("user_accounts.StudentDetails", on_delete=models.CASCADE)

    enrollment = models.ForeignKey(
        "course_management.CourseEnrollment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    department = models.ForeignKey(
        "user_accounts.Add_Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    course = models.ForeignKey(
        "course_management.Course",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    faculty = models.ForeignKey(
        "faculty_management.general_information",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    submitted_at = models.DateTimeField(default=timezone.now)
    total_score = models.IntegerField(default=0)

    window_start = models.DateField(null=True, blank=True)
    window_end = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student"],
                name="unique_program_exit_submission_per_student"
            )
        ]

    def __str__(self):
        return f"{self.student} - Program Exit ({self.submitted_at.date()})"


class ProgramExitAnswer(models.Model):
    submission = models.ForeignKey(
        ProgramExitSubmission,
        on_delete=models.CASCADE,
        related_name="answers"
    )
    question = models.ForeignKey(
        ProgramExitQuestion,
        on_delete=models.CASCADE
    )
    score = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.submission_id} - {self.question_id} - {self.score}"






class ExitSurveyQuestion(models.Model):
    question_text = models.CharField(max_length=255, null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)
    department = models.ForeignKey(
        'user_accounts.Add_Department',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.question_text or ""




class ExitSurveySubmission(models.Model):
    student = models.ForeignKey("user_accounts.StudentDetails", on_delete=models.CASCADE)
    enrollment = models.ForeignKey("course_management.CourseEnrollment", on_delete=models.CASCADE)

    department = models.ForeignKey(
        "user_accounts.Add_Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    course = models.ForeignKey(
        "course_management.Course",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    faculty = models.ForeignKey(
        "faculty_management.general_information",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    submitted_at = models.DateTimeField(default=timezone.now)
    total_score = models.IntegerField(default=0)

    window_start = models.DateField(null=True, blank=True)
    window_end = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ("student", "enrollment")

    def __str__(self):
        return f"{self.student} - {self.course} ({self.submitted_at.date()})"


class ExitSurveyAnswer(models.Model):
    submission = models.ForeignKey(
        ExitSurveySubmission,
        on_delete=models.CASCADE,
        related_name="answers"
    )
    question = models.ForeignKey(ExitSurveyQuestion, on_delete=models.CASCADE, null=True, blank=True)
    selected_grade = models.CharField(max_length=10, null=True, blank=True)
    score = models.IntegerField(default=0)

    class Meta:
        unique_together = ("submission", "question")

    def __str__(self):
        return f"{self.question} = {self.selected_grade} ({self.score})"
 
 
 
class academic_activity_Permission(models.Model):
    role_id = models.IntegerField(unique=True)

    can_view_all_academic_activity_data = models.BooleanField(default=False)
    can_view_department_academic_activity_data = models.BooleanField(default=False)

    def __str__(self):
        return f"Academic Activity Permission - Role ID {self.role_id}"


from django.db import models
from django.utils import timezone




class AcademicActivityQuestion(models.Model):
    question_text = models.CharField(max_length=255, null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True)

    regulation = models.ForeignKey(
        Regulations,
        on_delete=models.CASCADE
    )

    is_revised = models.BooleanField(default=False)

    po1 = models.BooleanField(default=False)
    po2 = models.BooleanField(default=False)
    po3 = models.BooleanField(default=False)
    po4 = models.BooleanField(default=False)
    po5 = models.BooleanField(default=False)
    po6 = models.BooleanField(default=False)
    po7 = models.BooleanField(default=False)
    po8 = models.BooleanField(default=False)
    po9 = models.BooleanField(default=False)
    po10 = models.BooleanField(default=False)
    po11 = models.BooleanField(default=False)
    po12 = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        "faculty_management.general_information",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["regulation", "category", "id"]

    def __str__(self):
        return self.question_text or ""

class AcademicActivitySubmission(models.Model):
    student = models.ForeignKey(
        "user_accounts.StudentDetails",
        on_delete=models.CASCADE
    )

    regulation = models.ForeignKey(
        Regulations,
        on_delete=models.CASCADE
    )

    department = models.ForeignKey(
        "user_accounts.Add_Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    academic_year = models.CharField(max_length=9, null=True, blank=True)

    submitted_at = models.DateTimeField(default=timezone.now)
    total_score = models.IntegerField(default=0)

    window_start = models.DateField(null=True, blank=True)
    window_end = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ("student", "regulation")

    def __str__(self):
        return f"{self.student} - {self.regulation} ({self.submitted_at.date()})"



class AcademicActivityAnswer(models.Model):
    submission = models.ForeignKey(
        AcademicActivitySubmission,
        on_delete=models.CASCADE,
        related_name="answers"
    )

    question = models.ForeignKey(
        AcademicActivityQuestion,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    selected_grade = models.CharField(
        max_length=10,
        null=True,
        blank=True
    )

    score = models.IntegerField(default=0)

    class Meta:
        unique_together = ("submission", "question")

    def __str__(self):
        return f"{self.question} = {self.selected_grade} ({self.score})"





