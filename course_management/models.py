from django.db import models
from decimal import Decimal, ROUND_HALF_UP
from django.core.validators import MinValueValidator
from user_accounts.models import Degree, Role, Department, USER
from user_accounts.models import Role, Department, USER, Degree


# from faculty_management.models import Faculty

import uuid
import random
import string

from user_accounts.models import USER

class CourseandexaminationFunction(models.Model):
    role = models.ForeignKey(
        "user_accounts.Role",       # Role from external DB
        on_delete=models.DO_NOTHING, 
        db_constraint=False         # 🚨 disables DB-level FK
    )
    function = models.CharField(max_length=500)
    permission = models.BooleanField()


from user_accounts.models import Department
from user_accounts.models import Department, Add_Department



class Regulations(models.Model):
    year = models.CharField(max_length=6, unique=True, null=True, blank=True)  # 2021, 2025
    regulation_number = models.PositiveIntegerField(null=True, blank=True)  # 1, 4, 5

    class Meta:
        ordering = ["year"]

    def __str__(self):
        return f"R{self.regulation_number} ({self.year})"
  


class Course_category(models.Model):
    Course_category_name = models.CharField(max_length=25, null=True)
    category_code = models.CharField(max_length=10, unique=True, null=True, blank=True)
    category_description = models.TextField(blank=True, null=True)
    regulation = models.ForeignKey(Regulations, on_delete=models.SET_NULL, null=True) 


    def __str__(self):
        return f"{self.Course_category_name} - {self.regulation} - {self.category_code} - {self.category_description}"


class Course(models.Model):
    department = models.ForeignKey(
        Add_Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="courses"
    )
    course_code = models.CharField(max_length=50, null=True, blank=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    regulation = models.ForeignKey(Regulations, on_delete=models.CASCADE, null=True, blank=True) 
    year = models.CharField(max_length=10, null=True, blank=True)
    semester = models.CharField(max_length=10, null=True, blank=True)
    elective = models.ForeignKey(Course_category, on_delete=models.CASCADE, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "course_management_course"
        verbose_name = "Course" 
        verbose_name_plural = "Courses"
        ordering = ['course_code']

    def __str__(self):
        dept_name = self.department.Department if self.department else "No Dept"
        return f"{self.course_code or 'N/A'} - {self.title or 'No Title'} ({dept_name})"
 



class CourseHours(models.Model):
    hour_config = models.ForeignKey("examination_management.CourseHourConfig", on_delete=models.SET_NULL, null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="semesters")
    
    leture_npwk = models.CharField(max_length=15, null=True)
    
    tutorial_npwk = models.CharField(max_length=15, null=True)
    
    laboratory_npwk = models.CharField(max_length=15, null=True)
    total_hours = models.CharField(max_length=15, null=True)
    credits = models.CharField(max_length=15, null=True)

    def __str__(self):
        return f"{self.course}"
    
    
    
class PeriodAllocation(models.Model):
    

    department = models.ForeignKey(Add_Department, on_delete=models.DO_NOTHING, db_constraint=False ,null=True, blank=True)
    section = models.CharField(max_length=1,null=True, blank=True)  
    year = models.CharField(max_length=10)
    semester = models.CharField(max_length=10)
    day = models.CharField(max_length=30)
    first_period = models.CharField(max_length=200, null=True)
    second_period = models.CharField(max_length=200, null=True)
    third_period = models.CharField(max_length=200, null=True)
    fourth_period = models.CharField(max_length=200, null=True)
    fifth_period = models.CharField(max_length=200, null=True)
    sixth_period = models.CharField(max_length=200, null=True)
    seventh_period = models.CharField(max_length=200, null=True)
    eighth_period = models.CharField(max_length=200, null=True)
    nineth_period = models.CharField(max_length=200, null=True)
    tenth_period = models.CharField(max_length=200, null=True)

    def __str__(self):
        return f"{self.department} - Year {self.year} - Sem {self.semester} - Section {self.section} - {self.day}"

from django.db import models
from datetime import date


# class PeriodSubstitution(models.Model):
#     original_allocation = models.ForeignKey(
#         'PeriodAllocation',
#         on_delete=models.CASCADE,
#         related_name='substitutions'
#     )
#     substitution_date = models.DateField(default=date.today)
#     period_field = models.CharField(max_length=20)

#     original_faculty = models.ForeignKey(
#         'faculty_management.general_information',
#         on_delete=models.SET_NULL,
#         null=True,
#         related_name='substitutions_given'
#     )
#     substitute_faculty = models.ForeignKey(
#         'faculty_management.general_information',
#         on_delete=models.SET_NULL,
#         null=True,
#         related_name='substitutions_taken'
#     )

#     reason = models.CharField(
#         max_length=50,
#         choices=[
#             ('absent', 'Absent / Leave'),
#             ('official_duty', 'Official Duty / Meeting'),
#             ('medical', 'Medical'),
#             ('other', 'Other'),
#         ],
#         default='absent'
#     )
#     remarks = models.TextField(blank=True, null=True)

#     created_at = models.DateTimeField(auto_now_add=True)
#     created_by = models.ForeignKey(
#         'faculty_management.general_information',
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         related_name='created_substitutions'
#     )


class SectionMaster(models.Model):
    section = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.section
 

class PassOutStudents(models.Model):

    student = models.ForeignKey("user_accounts.StudentDetails", on_delete=models.CASCADE,null=True, blank=True)

    department = models.ForeignKey(Add_Department, on_delete=models.CASCADE, null=True, blank=True)
    year_of_passing = models.IntegerField()
    certificate_number = models.CharField(max_length=100, null=True, blank=True)
    qualified_higher_class = models.CharField(max_length=3, choices=[('Yes', 'Yes'), ('No', 'No')], null=True, blank=True)
    tc_requested_date = models.DateField(null=True, blank=True)
    last_date_of_attendance = models.DateField(null=True, blank=True)
    reason_for_tc = models.CharField(max_length=255, null=True, blank=True)
    conduct = models.CharField(max_length=20, choices=[('Good', 'Good'), ('Average', 'Average'), ('Bad', 'Bad')], null=True, blank=True)


    def __str__(self):



        return f"{self.student} - {self.year_of_passing}"



class Discontinued_Student(models.Model):
    student = models.ForeignKey(
        "user_accounts.StudentDetails",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    department = models.ForeignKey(
        Add_Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    discontinued_date = models.DateField()
    year_of_discontinuation = models.IntegerField()
    certificate_number = models.CharField(max_length=100, null=True, blank=True)

    reason_for_discontinuation = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )

    tc_requested_date = models.DateField(
        null=True,
        blank=True
    )

    tc_issued = models.CharField(
        max_length=3,
        choices=[("Yes", "Yes"), ("No", "No")],
        default="No"
    )

    conduct = models.CharField(
        max_length=20,
        choices=[
            ("Good", "Good"),
            ("Average", "Average"),
            ("Bad", "Bad"),
        ],
        null=True,
        blank=True,
    )

    remarks = models.TextField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    duration_of_study = models.CharField(max_length=50, null=True, blank=True)
    last_date_of_attendance = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.student} - {self.year_of_discontinuation}"





class StudentLeaveOdApplication(models.Model):
    class ApplicationType(models.TextChoices):
        LEAVE = 'LEAVE', 'Leave'
        OD = 'OD', 'On Duty'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        MENTOR_APPROVED = 'MENTOR_APPROVED', 'Mentor Approved'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    student = models.ForeignKey(
        "user_accounts.StudentDetails",
        on_delete=models.CASCADE,
         null=True,
        blank=True,
    )

    mentor = models.ForeignKey(
        "user_accounts.USER",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        db_constraint=False,
        related_name="mentor_leave_od_applications"
    )

    ca = models.ForeignKey(
        "user_accounts.USER",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        db_constraint=False,
        related_name="ca_leave_od_applications"
    )

    application_type = models.CharField(
        max_length=10,
        choices=ApplicationType.choices,
        default=ApplicationType.LEAVE
    )

    from_date = models.DateTimeField()
    to_date = models.DateTimeField()
    total_days = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    reason = models.TextField()
    proof_file = models.FileField(upload_to='student_leave_od_proofs/', null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    department = models.ForeignKey(Add_Department,on_delete=models.SET_NULL,
         null=True,
        blank=True,)
    study_year = models.CharField(
        max_length=50,
        choices=[(1, "I (First Year)"), (2, "II (Second Year)"), (3, "III (Third Year)"), (4, "IV (Fourth Year)")],
        blank=True, null=True
    )

    remarks = models.TextField(null=True, blank=True, help_text="Remarks or actions taken by approvers")


    @property
    def calculated_days(self):
        if not self.from_date or not self.to_date or self.to_date <= self.from_date:
            return None

        delta = self.to_date - self.from_date
        seconds = (
            Decimal(delta.days * 86400 + delta.seconds)
            + (Decimal(delta.microseconds) / Decimal("1000000"))
        )
        days = (seconds / Decimal("86400")).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        return days if days > 0 else Decimal("0.01")

    @property
    def display_total_days(self):
        return self.total_days if self.total_days is not None else self.calculated_days

    @property
    def display_duration(self):
        if not self.from_date or not self.to_date or self.to_date <= self.from_date:
            return "-"

        total_minutes = max(1, int(round((self.to_date - self.from_date).total_seconds() / 60)))
        days, day_remainder = divmod(total_minutes, 24 * 60)
        hours, minutes = divmod(day_remainder, 60)

        parts = []
        if days:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes or not parts:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

        return " ".join(parts)


    def mentor_approve(self, mentor_user=None):
        if self.status != self.Status.PENDING:
            return
        self.status = self.Status.MENTOR_APPROVED
        if mentor_user:
            self.mentor_id = mentor_user
        self.save()

    def ca_approve(self, ca_user=None):
        if self.status != self.Status.MENTOR_APPROVED:
            return
        self.status = self.Status.APPROVED
        if ca_user:
            self.ca_id = ca_user
        self.save()




class AssignSubjectFaculty(models.Model):
    REASON_CHOICES = [
        "Preference from the faculty members",
        "Consideration of specialization of the faculty members",
        "Analyzing the efficiency of the faculty member in handling same subject in previous semesters/ similar subjects.",
        "Feedback from the students",
        "If a Particular subject is not chosen by any one, the HOD allocates it to the senior faculty member with the corresponding specialization or to someone he thinks can do honest effort in handling the subject by undergoing any FDP in that area.",
        "Other",  # UI trigger for custom text
    ]

    department = models.ForeignKey(Add_Department, on_delete=models.SET_NULL, null=True, blank=True)
    faculty = models.ForeignKey("faculty_management.general_information", on_delete=models.SET_NULL, null=True, blank=True)
    skilled_faculty = models.ForeignKey(
        "faculty_management.general_information",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="skilled_subject_assignments",
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True, related_name="course_assign")
    regulation = models.ForeignKey(Regulations, on_delete=models.CASCADE, null=True, blank=True)
    batch = models.CharField(max_length=200, null=True, blank=True)
    section = models.CharField(max_length=100, null=True, blank=True)
    reason = models.CharField(max_length=500, null=True, blank=True)
    academic_year = models.CharField(max_length=9, null=True, blank=True)  # e.g., 2024-2025
    is_active = models.BooleanField(default=True)



class CourseEnrollment(models.Model):
    department = models.ForeignKey(Add_Department,on_delete=models.SET_NULL,
         null=True,
        blank=True,)
    # faculty_id = models.IntegerField(null=True, blank=True)
    # student_id = models.IntegerField(null=True, blank=True)
    faculty = models.ForeignKey("faculty_management.general_information", on_delete=models.CASCADE, null=True, blank=True)
    student = models.ForeignKey("user_accounts.StudentDetails", on_delete=models.CASCADE, null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
    batch = models.CharField(max_length=200, null=True, blank=True)
    section = models.CharField(max_length=100, null=True, blank=True)
    enrollment_date = models.DateField(null=True, blank=True)
    regulation = models.ForeignKey(Regulations, on_delete=models.CASCADE, null=True, blank=True)
    enroll = models.BooleanField(default=False)  # False = Unenrolled, True = Enrolled
    is_open_elective = models.BooleanField(default=False, null=True, blank=True)
    academic_year = models.CharField(max_length=9, null=True, blank=True)  # e.g., 2024-2025
    year = models.CharField(max_length=10, null=True, blank=True)
    semester = models.CharField(max_length=10, null=True, blank=True)



class HonoursCourse(models.Model):
    """
    Marks a Course as an Honours offering for a given department/regulation/
    year/semester in a specific academic year — kept as its own table (not a
    flag on Course) since the same course can be Honours in one academic
    year and not another.
    """
    department = models.ForeignKey(Add_Department, on_delete=models.CASCADE, null=True, blank=True)
    regulation = models.ForeignKey(Regulations, on_delete=models.CASCADE, null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="honours_selections")
    year = models.CharField(max_length=10, null=True, blank=True)
    semester = models.CharField(max_length=10, null=True, blank=True)
    academic_year = models.CharField(max_length=9, null=True, blank=True)  # e.g., 2024-2025
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("course", "academic_year")

    def __str__(self):
        return f"{self.course} - Honours ({self.academic_year})"


class FacultySubjectWillingness(models.Model):
    faculty = models.ForeignKey("faculty_management.general_information", on_delete=models.CASCADE, null=True, blank=True)
    degree = models.ForeignKey("user_accounts.Degree", on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey(Add_Department, on_delete=models.SET_NULL, null=True, blank=True)
    regulation = models.ForeignKey(Regulations, on_delete=models.SET_NULL, null=True, blank=True)
    year = models.CharField(max_length=10, null=True, blank=True)
    semester = models.CharField(max_length=10, null=True, blank=True)
    academic_year = models.CharField(max_length=9, null=True, blank=True)  # e.g., 2024-2025
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
    reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')], default='Pending')
    section = models.CharField(max_length=100, null=True, blank=True)
    batch = models.CharField(max_length=200, null=True, blank=True)
    No_of_time_handled = models.CharField(max_length=200, null=True, blank=True)
    No_of_time_handled_in_RIT = models.CharField(max_length=200, null=True, blank=True)
    pass_percentage_obtained = models.CharField(max_length=200, null=True, blank=True)


    def __str__(self):
        return f"{getattr(self.faculty, 'faculty_id', 'N/A')} -> {getattr(self.course, 'course_code', 'N/A')} ({self.academic_year})"


class CoursePlan(models.Model):
    faculty = models.ForeignKey("faculty_management.general_information", on_delete=models.CASCADE, null=True, blank=True)
    faculty_department = models.ForeignKey(Add_Department, on_delete=models.SET_NULL, null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
    academic_year = models.CharField(max_length=9, null=True, blank=True)
    unit_module_no = models.CharField(max_length=50, null=True, blank=True)
    co_no = models.CharField(max_length=50, null=True, blank=True)
    delivery_method = models.CharField(max_length=100, null=True, blank=True)
    topic = models.TextField(null=True, blank=True)
    content_beyond_syllabus = models.TextField(null=True, blank=True)
    period_no = models.CharField(max_length=50, null=True, blank=True)
    innovative_practice = models.TextField(null=True, blank=True)
    justify = models.TextField(null=True, blank=True)   # <-- NEW FIELD
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{getattr(self.faculty, 'faculty_id', '')} - {getattr(self.course, 'course_code', '')} ({self.academic_year})"



class SubjectRequest(models.Model):
    faculty = models.ForeignKey(
        "faculty_management.general_information",
        on_delete=models.SET_NULL, null=True, blank=True
    )

    # Department where the faculty currently belongs
    faculty_department = models.ForeignKey(
        Add_Department,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="subject_request_faculty_department"
    )

    # Department offering the course (target department)
    requested_department = models.ForeignKey(
        Add_Department,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="subject_request_requested_department"
    )

    requested_to_department = models.ForeignKey(
        Add_Department,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="subject_request_requested_to_department"
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="subject_request_courses"
    )

    regulation = models.ForeignKey(
        Regulations,
        on_delete=models.SET_NULL, null=True, blank=True
    )

    semester = models.CharField(max_length=10, null=True, blank=True)
    batch = models.CharField(max_length=200, null=True, blank=True)
    academic_year = models.CharField(max_length=9, null=True, blank=True)   # e.g., 2024-2025
    section = models.CharField(max_length=100, null=True, blank=True)
    reason = models.CharField(max_length=500, null=True, blank=True)  # same as AssignSubjectFaculty

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )

    requested_on = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        f = self.faculty or "Unknown Faculty"
        c = self.course or "No Course"
        return f"{f} requested {c} for {self.academic_year}"


class Program_outcomes(models.Model):
    program_number = models.CharField(max_length=100, null=True, blank=True)
    program_name = models.CharField(max_length=200, null=True, blank=True)
    program_description = models.TextField(null=True, blank=True)
    is_revised = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Program Outcome for {self.program_name}: {self.program_description}"
 
 




class Hall(models.Model):
    hall_name = models.CharField(max_length=100, unique=True, null=True, blank=True)
    benches = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.hall_name
    
    
    
    
class Co_Po_Mapping(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
    mapping = models.BooleanField(default=False, null=True, blank=True)
    co_number = models.ForeignKey("examination_management.CourseOutcome", on_delete=models.CASCADE, null=True, blank=True)
    co_description = models.CharField(max_length=500, null=True, blank=True)

    # ✅ These will store "1" or "2" or "3" or "" (empty)
    po_number_1 = models.CharField(max_length=500, null=True, blank=True)
    po_number_2 = models.CharField(max_length=500, null=True, blank=True)
    po_number_3 = models.CharField(max_length=500, null=True, blank=True)
    po_number_4 = models.CharField(max_length=500, null=True, blank=True)
    po_number_5 = models.CharField(max_length=500, null=True, blank=True)
    po_number_6 = models.CharField(max_length=500, null=True, blank=True)
    po_number_7 = models.CharField(max_length=500, null=True, blank=True)
    po_number_8 = models.CharField(max_length=500, null=True, blank=True)
    po_number_9 = models.CharField(max_length=500, null=True, blank=True)
    po_number_10 = models.CharField(max_length=500, null=True, blank=True)
    po_number_11 = models.CharField(max_length=500, null=True, blank=True)
    po_number_12 = models.CharField(max_length=500, null=True, blank=True)
    po_number_13 = models.CharField(max_length=500, null=True, blank=True)
    
    pso_number_1 = models.CharField(max_length=500, null=True, blank=True)
    pso_number_2 = models.CharField(max_length=500, null=True, blank=True)
    pso_number_3 = models.CharField(max_length=500, null=True, blank=True)
    pso_number_4 = models.CharField(max_length=500, null=True, blank=True)
    pso_number_5 = models.CharField(max_length=500, null=True, blank=True)


    assigned_faculty = models.ForeignKey(AssignSubjectFaculty, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        co_txt = getattr(self.co_number, "co_code", None) or getattr(self.co_number, "co_number", None) or str(self.co_number_id)
        return f"CO-PO Mapping: {co_txt} ({getattr(self.course, 'course_code', 'N/A')})"
 



class Semester_Cooldown_Period(models.Model):
    degree = models.ForeignKey(Degree, on_delete=models.CASCADE)

    no_of_months = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.degree.degree} - {self.no_of_months} months"


class SubjectAllocationSchedule(models.Model):
    academic_year = models.CharField(max_length=9, null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        ay = self.academic_year or "N/A"
        return f"AY {ay}: {self.start_date} to {self.end_date}"

from django.db import models
from user_accounts.models import StudentDetails


class Hall_Allotment(models.Model):
    SESSION_CHOICES = (
        ("FN", "Forenoon (FN)"),
        ("AN", "Afternoon (AN)"),
    )

    hall = models.ForeignKey(
        Hall,
        on_delete=models.CASCADE,
        related_name="allotments"
    )

    student = models.ForeignKey(
        StudentDetails,
        on_delete=models.CASCADE
    )

    seat_no = models.PositiveIntegerField(null=True, blank=True)

    # newly added fields
    exam_date = models.DateField(null=True, blank=True)
    session = models.CharField(max_length=2, choices=SESSION_CHOICES, null=True, blank=True)

    allotted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            ("hall", "seat_no"),
            ("hall", "student"),
        )
        ordering = ["seat_no"]
        indexes = [
            models.Index(fields=["hall"]),
            models.Index(fields=["seat_no"]),
            models.Index(fields=["exam_date"]),
            models.Index(fields=["session"]),
        ]

    def __str__(self):
        exam_part = ""
        if self.exam_date or self.session:
            exam_part = f" [{self.exam_date or '-'} / {self.session or '-'}]"
        return f"{self.student.reg_no} → {self.hall.hall_name} (Seat {self.seat_no}){exam_part}"







# ==================================================================
# Lab Timetable, Lab Assignment & Lab Utilization
# (Lab management inside Course & Examination)
# ==================================================================
class Lab(models.Model):
    department = models.ForeignKey(
        Add_Department, on_delete=models.CASCADE, null=True, blank=True,
        related_name="cm_labs",
    )
    lab_name = models.CharField(max_length=200)
    lab_code = models.CharField(max_length=50, unique=True)
    # Technician is a staff member of the same department (general_information).
    technician = models.ForeignKey(
        "faculty_management.general_information", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="cm_lab_technician",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        db_table = "course_management_lab"
        ordering = ["lab_code"]

    def __str__(self):
        return f"{self.lab_code} - {self.lab_name}"


class LabTimetable(models.Model):
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE, related_name="timetables")
    department = models.ForeignKey(Add_Department, on_delete=models.SET_NULL, null=True, blank=True)
    regulation = models.ForeignKey(Regulations, on_delete=models.SET_NULL, null=True, blank=True)
    year = models.CharField(max_length=10, null=True, blank=True)
    semester = models.CharField(max_length=10, null=True, blank=True)
    section = models.CharField(max_length=5, null=True, blank=True)
    created_by = models.ForeignKey(
        "faculty_management.general_information", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="created_lab_timetables",
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "course_management_lab_timetable"
        unique_together = ("lab", "semester", "section")
        ordering = ["-id"]

    def __str__(self):
        return f"{self.lab} - Sem {self.semester}"


class LabTimetableSlot(models.Model):
    DAY_CHOICES = [
        ("MON", "Monday"), ("TUE", "Tuesday"), ("WED", "Wednesday"),
        ("THU", "Thursday"), ("FRI", "Friday"),
    ]
    timetable = models.ForeignKey(LabTimetable, on_delete=models.CASCADE, related_name="slots")
    day = models.CharField(max_length=3, choices=DAY_CHOICES)
    period = models.PositiveSmallIntegerField()  # 1..8
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "course_management_lab_timetable_slot"
        unique_together = ("timetable", "day", "period")
        ordering = ["day", "period"]

    def __str__(self):
        return f"{self.timetable_id} {self.day} P{self.period}"


class LabUtilityLog(models.Model):
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE, related_name="utility_logs")
    log_date = models.DateField()
    is_utilized = models.BooleanField(default=False)
    remarks = models.CharField(max_length=255, null=True, blank=True)
    marked_by = models.ForeignKey(
        "faculty_management.general_information", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="lab_utility_marks",
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "course_management_lab_utility_log"
        unique_together = ("lab", "log_date")
        ordering = ["-log_date"]

    def __str__(self):
        return f"{self.lab} {self.log_date} {'Used' if self.is_utilized else 'Not used'}"
