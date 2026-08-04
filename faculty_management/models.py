from django.db import models
from django.conf import settings
from django.db import transaction
from jsonschema import ValidationError

from faculty_management.utils.upload_paths import *
from django.core.validators import FileExtensionValidator
from user_accounts.models import StudentDetails
from examination_management.models import InternalAssessment



from user_accounts.models import Role

class FacultyFunction(models.Model):
    role = models.ForeignKey(
        "user_accounts.Role",       # Role from external DB
        on_delete=models.DO_NOTHING, 
        db_constraint=False         # 🚨 disables DB-level FK
    )
    function = models.CharField(max_length=500)
    permission = models.BooleanField()



class DesignationMaster(models.Model):
    designation_name = models.CharField(max_length=100, unique=True)
    is_teaching = models.BooleanField(default=False)

    def __str__(self):
        return self.designation_name
 


class FacultyCategory(models.Model):
    category_name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category_name"]
        verbose_name = "Faculty Category"
        verbose_name_plural = "Faculty Categories"

    def __str__(self):
        return self.category_name


class StaffCategoryAssignment(models.Model):
    """Category pre-assigned to a staff member during pre-authorization.

    Recorded when an admin pre-authorizes an employee on the Add Employee
    page. Once set, the category is fixed and applied as read-only when the
    faculty member completes/updates their general information after signup.
    """
    employee_id = models.CharField(max_length=225, unique=True)
    category = models.ForeignKey(
        FacultyCategory,
        on_delete=models.CASCADE,
        related_name="staff_assignments",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Staff Category Assignment"
        verbose_name_plural = "Staff Category Assignments"

    def __str__(self):
        return f"{self.employee_id} -> {self.category.category_name}"
 

class general_information(models.Model):
    class GenderChoices(models.TextChoices):
        MALE = "Male", "Male"
        FEMALE = "Female", "Female"
        TRANSGENDER = "Transgender", "Transgender"
        OTHER = "Other", "Other"
    faculty_id = models.IntegerField(null=True, blank=True)
    name = models.CharField(max_length=225, null=True, blank=True)
    department = models.ForeignKey(
        "user_accounts.Add_Department",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    designation = models.ForeignKey(DesignationMaster, on_delete=models.CASCADE, null=True, blank=True)
    category = models.ForeignKey(
        FacultyCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="faculty_members",
    )
    gender = models.CharField(max_length=100,choices=GenderChoices.choices,null=True,blank=True)
    dob = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=225, null=True, blank=True)
    personal_email = models.CharField(max_length=225, null=True, blank=True)
    college_email = models.CharField(max_length=225, null=True, blank=True)
    phone = models.BigIntegerField(null=True, blank=True)
    blood_group = models.CharField(max_length=225, null=True, blank=True)
    community = models.CharField(max_length=225, null=True, blank=True)
    caste = models.CharField(max_length=225, null=True, blank=True)
    religion = models.CharField(max_length=225, null=True, blank=True)
    doj = models.DateField(null=True, blank=True)
    apaar_id = models.CharField(max_length=100, null=True, blank=True)
    anu_id = models.CharField(max_length=100, null=True, blank=True)
    aicte_id = models.CharField(max_length=100, null=True, blank=True)
    annauniversity_affiliation_id = models.CharField(max_length=100, null=True, blank=True)
    PAN_number = models.CharField(max_length=100, null=True, blank=True)
    Aadhar_number = models.CharField(max_length=100, null=True, blank=True)
    shift = models.ForeignKey('faculty_leave_management.ShiftMaster', on_delete=models.SET_NULL, null=True, blank=True)
    PAN_certificate = models.FileField(
        upload_to=PAN_certificate_upload_path,
        null=True,
        blank=True,
        verbose_name="Certificate (PDF only, max 1000KB)",
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        help_text="Upload PDF certificate (max 1000KB)"
    )
    Aadhar_certificate = models.FileField(
        upload_to=Aadhar_certificate_upload_path,
        null=True,
        blank=True,
        verbose_name="Certificate (PDF only, max 1000KB)",
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        help_text="Upload PDF certificate (max 1000KB)"
    )
    approval = models.CharField(
        max_length=10,
        choices=[('Pending', 'Pending'), ('Approved', 'Approved')],
        default='Pending',
        verbose_name="Approval Status"
    )
    APPOINTMENT_TYPE_CHOICES = [
        ("Regular", "Regular"),
        ("Contract", "Contract"),
        ("Adhoc", "Adhoc"),
    ]
    appointment_type = models.CharField(
        max_length=20,
        choices=APPOINTMENT_TYPE_CHOICES,
        null=True,
        blank=True,
        verbose_name="Type of Appointment"
    )

    # Pay details
    basic_pay = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Basic Pay"
    )
    agp = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="AGP"
    )
    allowances = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Allowances"
    )
    pay_scale_notes = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Scale of Pay (As per AICTE / 7th CPC)"
    )

    RECRUITMENT_MODE_CHOICES = [
        ("Selection Committee", "Through Selection Committee"),
        ("Direct", "Direct"),
        ("Deputation", "Deputation"),
    ]
    recruitment_mode = models.CharField(
        max_length=30,
        choices=RECRUITMENT_MODE_CHOICES,
        null=True,
        blank=True,
        verbose_name="Mode of Recruitment"
    )

    DUTIES_CHOICES = [
        ("Teaching", "Teaching"),
        ("Research", "Research"),
        ("Administration", "Administration"),
    ]
    nature_of_duties = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        choices=DUTIES_CHOICES,
        verbose_name="Nature of Duties"
    )

    confirmation_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Confirmation of Service Date"
    )

    probation_period_months = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Probation Period (in months)"
    )
    probation_confirmation_reference = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Probation Confirmation Order Reference"
    )
    probation_confirmation_document = models.FileField(
        upload_to=probation_confirmation_upload_path,
        null=True,
        blank=True,
        verbose_name="Probation Confirmation Document (PDF)"
    )

    profile_photo = models.ImageField(
    upload_to="upload_profile/",
    null=True,
    blank=True,
    verbose_name="Profile Photo"
)
    dor = models.DateField(null=True, blank=True)




    def save(self, *args, **kwargs):
        # Convert empty strings to None for numeric fields
        if self.faculty_id == '':
            self.faculty_id = None
        if self.phone == '':
            self.phone = None
        super().save(*args, **kwargs)
      
 

class Academic_Background(models.Model):
    faculty = models.ForeignKey(general_information, on_delete=models.CASCADE, null=True, blank=True)
    # Add-on generalized degree info
    DEGREE_CHOICES = [
        ('SSLC', 'SSLC'),
        ('High School', 'High School / Sec. or Equivalent'),
        ('Graduation', 'Graduation'),
        ('Post-Graduation', 'Post-Graduation'),
        ('MPhil', 'M. Phil'),
        ('PhD', 'PhD'),
        ('PostDoc', 'Post Doc'),
    ]
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    degree = models.CharField(max_length=30, choices=DEGREE_CHOICES, null=True, blank=True)
    title = models.CharField(max_length=100, null=True, blank=True)
    board_university = models.CharField(max_length=100, null=True, blank=True)
    year_of_passing = models.PositiveIntegerField(null=True, blank=True)
    marks_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    sslc_certificate = models.FileField(
        upload_to=sslc_certificate_upload_path, 
        null=True, 
        blank=True, 
        verbose_name="Certificate (PDF only, max 1000KB)",
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        help_text="Upload PDF certificate (max 1000KB)"
    )

    hsc_certificate = models.FileField(
        upload_to=hsc_certificate_upload_path, 
        null=True, 
        blank=True, 
        verbose_name="Certificate (PDF only, max 1000KB)",
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        help_text="Upload PDF certificate (max 1000KB)"
    )
    ug_certificate = models.FileField(
        upload_to=ug_certificate_upload_path, 
        null=True, 
        blank=True, 
        verbose_name="Certificate (PDF only, max 1000KB)",
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        help_text="Upload PDF certificate (max 1000KB)"
    )
    pg_certificate = models.FileField(
        upload_to=pg_certificate_upload_path, 
        null=True, 
        blank=True, 
        verbose_name="Certificate (PDF only, max 1000KB)",
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        help_text="Upload PDF certificate (max 1000KB)"
    )
    phd_certificate = models.FileField(
        upload_to=phd_certificate_upload_path, 
        null=True, 
        blank=True, 
        verbose_name="Certificate (PDF only, max 1000KB)",
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        help_text="Upload PDF certificate (max 1000KB)"
    )
    postDoc_certificate = models.FileField(
        upload_to=postDoc_certificate_upload_path, 
        null=True, 
        blank=True, 
        verbose_name="Certificate (PDF only, max 1000KB)",
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        help_text="Upload PDF certificate (max 1000KB)"
    )
    mphil_certificate = models.FileField(
        upload_to=mphil_certificate_upload_path, 
        null=True, 
        blank=True, 
        verbose_name="Certificate (PDF only, max 1000KB)",
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        help_text="Upload PDF certificate (max 1000KB)"
    )

    def __str__(self):
        return f"Educational Qualification - {self.faculty.faculty_id }"

from datetime import date
from dateutil.relativedelta import relativedelta

class AcademicExperience(models.Model):
    # faculty_id = models.CharField(max_length=100)
    faculty = models.ForeignKey(general_information, on_delete=models.CASCADE, null=True, blank=True)
    institute_name = models.CharField(max_length=225, null=True, blank=True)
    designation = models.CharField(max_length=225, null=True, blank=True)
    from_date = models.DateField(null=True, blank=True)
    to_date = models.DateField(null=True, blank=True)
    certificate = models.FileField(upload_to=academic_experience_certificate_upload_path, null=True, blank=True, max_length=500, help_text="Upload certificate for academic experience (PDF only - Max 10MB)")
    # indexp_certificate = models.FileField(upload_to=industry_experience_certificate_upload_path, null=True, blank=True, max_length=500, help_text="Upload certificate for academic experience (PDF only - Max 10MB)")
    # reexp_certificate = models.FileField(upload_to=research_experience_certificate_upload_path, null=True, blank=True, max_length=500, help_text="Upload certificate for academic experience (PDF only - Max 10MB)")

    relieving_date = models.DateField(null=True, blank=True)


    # aca_relieving_certificate = models.FileField(upload_to=academic_experience_relieving_certificate_upload_path, null=True, blank=True, max_length=500, help_text="Upload certificate for academic experience (PDF only - Max 10MB)")
    # ind_relieving_certificate = models.FileField(upload_to=industry_experience_relieving_certificate_upload_path, null=True, blank=True, max_length=500, help_text="Upload certificate for academic experience (PDF only - Max 10MB)")
    # res_relieving_certificate = models.FileField(upload_to=research_experience_relieving_certificate_upload_path, null=True, blank=True, max_length=500, help_text="Upload certificate for academic experience (PDF only - Max 10MB)")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return f"{self.institute_name} - {self.designation} ({self.faculty_id})"

    def get_duration(self):
        """Returns duration between from_date and to_date (or today) in 'X years Y months Z days' format"""
        if not self.from_date:
            return ""

        start = self.from_date
        end = self.to_date or date.today()

        delta = relativedelta(end, start)

        years = delta.years
        months = delta.months
        days = delta.days

        parts = []
        if years > 0:
            parts.append(f"{years} year{'s' if years != 1 else ''}")
        if months > 0:
            parts.append(f"{months} month{'s' if months != 1 else ''}")
        if days > 0 or not parts:
            parts.append(f"{days} day{'s' if days != 1 else ''}")

        return " ".join(parts)

    def clean(self):
        """Validate certificate file"""
        from django.core.exceptions import ValidationError
        import os
        
        if self.certificate:
            # Check file size (10MB limit)
            if self.certificate.size > 10 * 1024 * 1024:
                raise ValidationError({'certificate': 'Certificate file size cannot exceed 10MB.'})
            
            # Check file extension
            allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png']
            file_extension = os.path.splitext(self.certificate.name)[1].lower()
            if file_extension not in allowed_extensions:
                raise ValidationError({'certificate': 'Only PDF, DOC, DOCX, JPG, and PNG files are allowed.'})

    class Meta:
        verbose_name = "Academic Experience"
        verbose_name_plural = "Academic Experiences"
        ordering = ['-from_date']


class Faculty_Academic_Experience(models.Model):
    faculty_id = models.CharField(max_length=100)
    institute_name = models.CharField(max_length=225, null=True, blank=True)
    designation = models.CharField(max_length=225, null=True, blank=True)
    from_date = models.DateField(null=True, blank=True)
    to_date = models.DateField(null=True, blank=True)
    certificate = models.FileField(upload_to=academic_experience_certificate_upload_path, null=True, blank=True, max_length=500, help_text="Upload certificate for academic experience (PDF only - Max 10MB)")
    indexp_certificate = models.FileField(upload_to=industry_experience_certificate_upload_path, null=True, blank=True, max_length=500, help_text="Upload certificate for academic experience (PDF only - Max 10MB)")
    reexp_certificate = models.FileField(upload_to=research_experience_certificate_upload_path, null=True, blank=True, max_length=500, help_text="Upload certificate for academic experience (PDF only - Max 10MB)")

    relieving_date = models.DateField(null=True, blank=True)


    aca_relieving_certificate = models.FileField(upload_to=academic_experience_relieving_certificate_upload_path, null=True, blank=True, max_length=500, help_text="Upload certificate for academic experience (PDF only - Max 10MB)")
    ind_relieving_certificate = models.FileField(upload_to=industry_experience_relieving_certificate_upload_path, null=True, blank=True, max_length=500, help_text="Upload certificate for academic experience (PDF only - Max 10MB)")
    res_relieving_certificate = models.FileField(upload_to=research_experience_relieving_certificate_upload_path, null=True, blank=True, max_length=500, help_text="Upload certificate for academic experience (PDF only - Max 10MB)")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return f"{self.institute_name} - {self.designation} ({self.faculty_id})"

    def get_duration(self):
        """Returns duration between from_date and to_date (or today) in 'X years Y months Z days' format"""
        if not self.from_date:
            return ""

        start = self.from_date
        end = self.to_date or date.today()

        delta = relativedelta(end, start)

        years = delta.years
        months = delta.months
        days = delta.days

        parts = []
        if years > 0:
            parts.append(f"{years} year{'s' if years != 1 else ''}")
        if months > 0:
            parts.append(f"{months} month{'s' if months != 1 else ''}")
        if days > 0 or not parts:
            parts.append(f"{days} day{'s' if days != 1 else ''}")

        return " ".join(parts)

    def clean(self):
        """Validate certificate file"""
        from django.core.exceptions import ValidationError
        import os
        
        if self.certificate:
            # Check file size (10MB limit)
            if self.certificate.size > 10 * 1024 * 1024:
                raise ValidationError({'certificate': 'Certificate file size cannot exceed 10MB.'})
            
            # Check file extension
            allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png']
            file_extension = os.path.splitext(self.certificate.name)[1].lower()
            if file_extension not in allowed_extensions:
                raise ValidationError({'certificate': 'Only PDF, DOC, DOCX, JPG, and PNG files are allowed.'})

    class Meta:
        verbose_name = "Academic Experience"
        verbose_name_plural = "Academic Experiences"
        ordering = ['-from_date']
        managed = False
        db_table = 'app_academicexperience'  # Custom table name to avoid conflicts with other apps



class IndustryExperience(models.Model):
    # faculty_id = models.CharField(max_length=100)
    faculty = models.ForeignKey(general_information, on_delete=models.CASCADE, null=True, blank=True)
    company_name = models.CharField(max_length=225, null=True, blank=True)
    designation = models.ForeignKey(DesignationMaster, on_delete=models.CASCADE, null=True, blank=True)
    from_date = models.DateField(null=True, blank=True)
    to_date = models.DateField(null=True, blank=True)
    certificate = models.FileField(upload_to=industry_experience_certificate_upload_path, null=True, blank=True, help_text="Upload certificate for industry experience (PDF, DOC, DOCX, JPG, PNG - Max 10MB)")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return f"{self.company_name} - {self.designation}"

    def get_duration(self):
        if not self.from_date:
            return ""
        end = self.to_date or date.today()
        delta = relativedelta(end, self.from_date)

        years = delta.years
        months = delta.months
        days = delta.days

        parts = []
        if years:
            parts.append(f"{years} year{'s' if years != 1 else ''}")
        if months:
            parts.append(f"{months} month{'s' if months != 1 else ''}")
        if days:
            parts.append(f"{days} day{'s' if days != 1 else ''}")

        return " ".join(parts) or "0 days"

    def clean(self):
        """Validate certificate file"""
        from django.core.exceptions import ValidationError
        import os
        
        if self.certificate:
            # Check file size (10MB limit)
            if self.certificate.size > 10 * 1024 * 1024:
                raise ValidationError({'certificate': 'Certificate file size cannot exceed 10MB.'})
            
            # Check file extension
            allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png']
            file_extension = os.path.splitext(self.certificate.name)[1].lower()
            if file_extension not in allowed_extensions:
                raise ValidationError({'certificate': 'Only PDF, DOC, DOCX, JPG, and PNG files are allowed.'})

    class Meta:
        verbose_name = "Industry Experience"
        verbose_name_plural = "Industry Experiences"
        ordering = ['-from_date']





class ResearchExperience(models.Model):
    faculty = models.ForeignKey(general_information, on_delete=models.CASCADE, null=True, blank=True)
    research_area = models.CharField(max_length=225, null=True, blank=True)
    institute = models.CharField(max_length=225, null=True, blank=True)
    from_date = models.DateField(null=True, blank=True)
    to_date = models.DateField(null=True, blank=True)
    certificate = models.FileField(upload_to=research_experience_certificate_upload_path, null=True, blank=True, help_text="Upload certificate for research experience (PDF, DOC, DOCX, JPG, PNG - Max 10MB)")
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def get_duration(self):
        if not self.from_date:
            return "N/A"
        end = self.to_date or date.today()
        delta = relativedelta(end, self.from_date)
        return f"{delta.years} years {delta.months} months {delta.days} days"

    def clean(self):
        """Validate certificate file"""
        from django.core.exceptions import ValidationError
        import os
        
        if self.certificate:
            # Check file size (10MB limit)
            if self.certificate.size > 10 * 1024 * 1024:
                raise ValidationError({'certificate': 'Certificate file size cannot exceed 10MB.'})
            
            # Check file extension
            allowed_extensions = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png']
            file_extension = os.path.splitext(self.certificate.name)[1].lower()
            if file_extension not in allowed_extensions:
                raise ValidationError({'certificate': 'Only PDF, DOC, DOCX, JPG, and PNG files are allowed.'})

    def __str__(self):
        return f"{self.research_area} - {self.institute} ({self.faculty_id})"

    class Meta:
        verbose_name = "Research Experience"
        verbose_name_plural = "Research Experiences"
        ordering = ['-from_date']


from user_accounts.models import Add_Department , Degree
from course_management.models import *
from examination_management.models import CourseOutcome , BloomsLevel


class Assessment_master(models.Model):
    degree = models.ForeignKey(Degree, on_delete=models.CASCADE,null=True,blank=True,) 
    department = models.ForeignKey(Add_Department, on_delete=models.CASCADE,null=True,blank=True,) 
    regulation = models.ForeignKey(Regulations, on_delete=models.CASCADE,null=True,blank=True,) 
    semester = models.CharField(max_length=100, null=True, blank=True) 
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="assignments_by_name") 
    module = models.CharField(max_length=100, null=True, blank=True) 
    internal_assessment = models.ForeignKey(InternalAssessment,on_delete=models.SET_NULL,null=True, blank=True,related_name="assessment_masters")

    # assessment_name = models.ForeignKey('examination_management.Assessments', on_delete=models.CASCADE, to_field='assessment_name', db_column='assessment_name', related_name='assessment_names')
    
    faculty_id = models.CharField(max_length=100, null=True, blank=True) 
    weightage = models.CharField(max_length=100, null=True, blank=True) 
    co_codes = models.ManyToManyField(CourseOutcome, blank=True, related_name="assessment_master_co")
    bloom_levels = models.ManyToManyField(BloomsLevel, blank=True, related_name="assessment_master_blooms")
    assessment = models.ForeignKey(
        "examination_management.Assessments",
        on_delete=models.CASCADE,
        null=True, blank=True,
         # keep DB constraint disabled if that’s your convention
        related_name="assessment_masters",
    )
    # Cached fields for display/reporting
    Assessmentname = models.CharField(max_length=255, null=True, blank=True)
    customAssessmentname = models.CharField(max_length=255, null=True, blank=True)
    Maxmarks = models.IntegerField(null=True, blank=True)
    # Stores per-CO max marks keyed by CourseOutcome id: {"12": 10, "13": 15}
    co_max_marks = models.JSONField(default=dict, blank=True)
    batch = models.CharField(max_length=255, null=True, blank=True)
    section = models.CharField(max_length=255, null=True, blank=True)
     
    
class Vision(models.Model):
    department = models.ForeignKey(
        Add_Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="visions"
    )
    year = models.PositiveIntegerField(null=True, blank=True)
    vision_statement = models.TextField(null=False, blank=False)
    
    # Optional improvements:
    is_active = models.BooleanField(default=True, help_text="Mark as active vision for the year")
    created_by = models.ForeignKey(
        "faculty_management.general_information",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_visions"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-year", "-created_at"]
        unique_together = ("department", "year")  # Prevent duplicate year entries per department
        verbose_name = "Vision Statement"
        verbose_name_plural = "Vision Statements"

    def __str__(self):
        return f"{self.department} - {self.year}"


class Mission(models.Model):
    department = models.ForeignKey(
        Add_Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="missions"
    )
    mission_statement = models.TextField(null=False, blank=False)
    created_by = models.ForeignKey(
        "faculty_management.general_information",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_missions"
    )
    year = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True, help_text="Mark as active vision for the year")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Mission Statement"
        verbose_name_plural = "Mission Statements"

    def __str__(self):
        return f"{self.department} - Mission"



class Program_Educational_Objective(models.Model):
    department = models.ForeignKey(
        Add_Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="peos"
    )
    peo_code = models.CharField(max_length=100, null=True, blank=True)
    peo_statement = models.TextField(null=False, blank=False)
    created_by = models.ForeignKey(
        "faculty_management.general_information",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_peos"
    )
    year = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True, help_text="Mark as active PEO for the year")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    batch = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        verbose_name = "Program Educational Objective"
        verbose_name_plural = "Program Educational Objectives"

    def __str__(self):
        return f"{self.department} - PEO"
    

class Program_specific_Outcomes(models.Model):
    batch = models.CharField(max_length=100, null=True, blank=True)
    department = models.ForeignKey(
        Add_Department,
        
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="psos"
    )
    pso_code = models.CharField(max_length=100, null=True, blank=True)
    pso_statement = models.TextField(null=False, blank=False)
    created_by = models.ForeignKey(
        "faculty_management.general_information",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_psos"
    )
    year = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True, help_text="Mark as active PSO for the year")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Program Specific Outcome"
        verbose_name_plural = "Program Specific Outcomes"

    def __str__(self):
        return f"{self.department} - PSO"





from decimal import Decimal
from django.db import models

class AssessmentMark(models.Model):
    assignment = models.ForeignKey(
        "course_management.AssignSubjectFaculty",
        on_delete=models.CASCADE,
        related_name="marks",
        null=True, blank=True
    )
    assessment = models.ForeignKey(
        "faculty_management.Assessment_master",
        on_delete=models.CASCADE,
        related_name="marks",
        null=True, blank=True
    )
    student = models.ForeignKey(
        "user_accounts.StudentDetails",
        on_delete=models.CASCADE,
        related_name="assessment_marks",
        null=True, blank=True
    )

    # teacher-entered raw mark (what they type into the form)
    marks_raw = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    # computed weighted contribution (same units as your weight system — e.g. out of 70)
    marks_weighted = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)

    # legacy / compatibility column (optional)
    marks = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    remarks = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("assignment", "assessment", "student")

    def __str__(self):
        return f"{self.assignment_id} | A:{self.assessment_id} | S:{self.student_id} -> {self.marks_raw or self.marks}"
 
  

















class Open_Elective_Offer(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, null=True, blank=True, related_name="open_elective_offers"
    )
    regulation = models.ForeignKey(
        Regulations, on_delete=models.CASCADE, null=True, blank=True, related_name="open_elective_offers"
    )
    faculty = models.ForeignKey(
        general_information, on_delete=models.CASCADE, null=True, blank=True, related_name="offered_courses"
    )
    slots = models.CharField(max_length=100, null=True, blank=True)
    academic_year = models.CharField(max_length=100, null=True, blank=True)
    batch = models.CharField(max_length=100, null=True, blank=True)

    department = models.ForeignKey(
        Add_Department, on_delete=models.CASCADE, null=True, blank=True, related_name="elective_offers"
    )
    offered_from_dept = models.ForeignKey(
        Add_Department, on_delete=models.CASCADE, null=True, blank=True, related_name="offered_from"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        general_information,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_open_electives"
    )
    updated_by = models.ForeignKey(
        general_information,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_open_electives"
    )

    class Meta:
        verbose_name = "Open Elective Offer"
        verbose_name_plural = "Open Elective Offers"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.course} ({self.academic_year})" if self.course else f"Offer {self.id}"


class Open_Elective_OfferToDept(models.Model):
    offer = models.ForeignKey(Open_Elective_Offer, on_delete=models.CASCADE, related_name="to_departments")
    offered_to_dept = models.ForeignKey(Add_Department, on_delete=models.CASCADE)





class Announcement(models.Model):
    faculty = models.ForeignKey(
        general_information,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="faculty_announcements"
    )

    academic_year = models.CharField(max_length=100, null=True, blank=True)

    # ✅ Change these from ForeignKey to ManyToManyField
    roles = models.ManyToManyField(
        Role,
        blank=True,
        related_name="announcement_roles",
        db_constraint=False  # keep DB constraint disabled if that’s your convention
    )
    departments = models.ManyToManyField(
        Add_Department,
        blank=True,
        related_name="announcement_departments"
    )
    users = models.ManyToManyField(
        general_information,
        blank=True,
        related_name="announcement_users"
    )
    venue = models.CharField(max_length=255, null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    notify_from = models.DateTimeField(null=True, blank=True)
    notify_to = models.DateTimeField(null=True, blank=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    attachment = models.FileField(
        upload_to="announcements/files/",
        null=True,
        blank=True
    )

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        general_information,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_announcements"
    )
    updated_by = models.ForeignKey(
        general_information,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_announcements"
    )
    is_active = models.BooleanField(default=True)
    file = models.FileField(upload_to="announcements/files/", null=True, blank=True)

    def __str__(self):
        return self.title or "Untitled Announcement"

    class Meta:
        ordering = ["-created_at"]





class ProgramOrganizationRecord(models.Model):
    id = models.AutoField(primary_key=True)

    program_id = models.IntegerField(null=True, blank=True, help_text="Program identifier")

    faculty = models.ForeignKey(
        'general_information',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='program_organization_records',
          
        help_text="Faculty who created this program"
    )
    department = models.ForeignKey(
    'user_accounts.Add_Department',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    db_constraint=False,
    related_name='program_organization_records',
    help_text="Department for which this program is organized"
)
    program_name = models.CharField(max_length=500, null=True, blank=True, help_text="Name of the program")
    resource_person = models.CharField(max_length=255, null=True, blank=True, help_text="Resource person for the program")
    address = models.TextField(null=True, blank=True, help_text="Address/Venue of the program")
    from_date = models.DateField(null=True, blank=True, help_text="Program start date")
    to_date = models.DateField(null=True, blank=True, help_text="Program end date")
    no_of_days = models.IntegerField(null=True, blank=True, help_text="Number of days for the program")
    
    # Professional Society field
    professional_society = models.ForeignKey(
        'ProfessionalSociety',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_constraint=False,
        help_text="Professional society associated with this program"
    )
    
    # Type of Program field
    program_type = models.ForeignKey(
        'ProgramType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_constraint=False,
        help_text="Type of program"
    )
    
    # Mode of Program field
    MODE_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
    ]
    mode_of_program = models.CharField(
        max_length=20, 
        choices=MODE_CHOICES, 
        null=True, 
        blank=True,
        help_text="Mode of program delivery"
    )

    APPROVAL_CHOICES = [
        ('Pending', 'Pending'),
        ('HOD_Approved', 'HOD Approved'),
        ('Principal_Approved', 'Principal Approved'),
        ('Approved', 'Approved'),  # Final approval
        ('Rejected', 'Rejected'),
    ]
    approval = models.CharField(max_length=20, choices=APPROVAL_CHOICES, default='Pending', help_text="Approval status")
    hod_remarks = models.TextField(null=True, blank=True, help_text="Remarks/comments from HOD regarding approval/rejection")
    principal_remarks = models.TextField(null=True, blank=True, help_text="Remarks/comments from Principal regarding approval/rejection")
    hod_approved_at = models.DateTimeField(null=True, blank=True, help_text="Date and time when HOD approved")
    principal_approved_at = models.DateTimeField(null=True, blank=True, help_text="Date and time when Principal approved")
    hod_approved_by = models.ForeignKey(
        'general_information',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hod_approved_programs',
        help_text="HOD who approved this program"
    )
    principal_approved_by = models.ForeignKey(
        'general_information',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='principal_approved_programs',
        help_text="Principal who approved this program"
    )
    
    report = models.FileField(
        upload_to='program_organization/reports/',
        null=True,
        blank=True,
        help_text="Upload program report (PDF, DOC, DOCX - Max 10MB)",
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx'])]
    )

    regulation = models.ForeignKey('course_management.Regulations', on_delete=models.SET_NULL, null=True, blank=True)
    year = models.CharField(max_length=10, null=True, blank=True)
    section = models.CharField(max_length=10, null=True, blank=True)
    semester = models.CharField(max_length=10, null=True, blank=True)
    
    # Student selection options
    STUDENT_SELECTION_CHOICES = [
        ('both', 'Both (Boys & Girls)'),
        ('boys_only', 'Only Boys'),
        ('girls_only', 'Only Girls'),
        ('specific_students', 'Specific Students'),
    ]
    student_selection_type = models.CharField(
        max_length=20, 
        choices=STUDENT_SELECTION_CHOICES, 
        default='both',
        help_text="Type of student selection for this program"
    )
    specific_student_reg_numbers = models.TextField(
        null=True, 
        blank=True,
        help_text="Comma-separated register numbers for specific students (only used when selection type is 'specific_students')"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['id']


class ProgramOrganizationStudentMark(models.Model):

    id = models.AutoField(primary_key=True)

    program = models.ForeignKey(
        'ProgramOrganizationRecord',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='student_marks',
        help_text="Reference to ProgramOrganizationRecord"
    )
    
    department = models.ForeignKey(Add_Department, on_delete=models.DO_NOTHING, db_constraint=False ,null=True, blank=True)
    student = models.ForeignKey(
        "user_accounts.StudentDetails",
        on_delete=models.SET_NULL,
         null=True,
        blank=True,
    )

    regulation = models.ForeignKey('course_management.Regulations', on_delete=models.SET_NULL, null=True, blank=True)
    year = models.CharField(max_length=10, null=True, blank=True)
    section = models.CharField(max_length=10, null=True, blank=True)
    semester = models.CharField(max_length=10, null=True, blank=True)
    marks = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    program_outcome_mapping = models.ForeignKey(
        'ProgramOutcomeMapping',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='student_marks',
        help_text="Reference to ProgramOutcomeMapping for separate PO rows"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        program_id_value = self.program.program_id if self.program else 'None'
        return f"{program_id_value}"
    
    class Meta:
        ordering = ['id']
        verbose_name = "Program Organization Student Mark"
        verbose_name_plural = "Program Organization Student Marks"
 
 
from django.db import models


class ProgramOutcomeMapping(models.Model):
    program_organization = models.ForeignKey(
        'faculty_management.ProgramOrganizationRecord',
        on_delete=models.CASCADE,
        related_name='program_outcome_mappings'
    )

    revised_po = models.ForeignKey(
        'course_management.Program_outcomes',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='revised_program_mappings'
    )

    non_revised_po = models.ForeignKey(
        'course_management.Program_outcomes',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='non_revised_program_mappings'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"PO Mapping - ProgramOrg ID {self.program_organization.program_id}"


# ============================================================================
# SEMINAR HALL BOOKING SYSTEM MODELS
# ============================================================================

class SeminarHallBooking(models.Model):
    """Model for Seminar Hall Booking requests"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    EVENT_TYPE_CHOICES = [
        ('seminar', 'Seminar'),
        ('workshop', 'Workshop'),
        ('conference', 'Conference'),
        ('meeting', 'Meeting'),
        ('guest_lecture', 'Guest Lecture'),
        ('training', 'Training Program'),
        ('cultural', 'Cultural Event'),
        ('FDP', 'FDP'),
        ('STTP', 'STTP'),
        ('international_conference', 'International Conference'),
        ('national_conference', 'National Conference'),
        ('faculty_meeting', 'Faculty Meeting'),
        ('grievance_cell_meeting', 'Grievance Cell Meeting'),
        ('class_committee_meeting', 'Class Committee Meeting'),
        ('other', 'Other'),
    ]
    
    # Booking Identification
    booking_id = models.CharField(max_length=50, unique=True, editable=False)
    
    # Faculty Information
    faculty = models.ForeignKey(
        'general_information',
        on_delete=models.CASCADE,
        related_name='seminar_bookings'
    )
    faculty_name = models.CharField(max_length=255)
    faculty_email = models.EmailField()
    faculty_phone = models.CharField(max_length=20)
    department = models.ForeignKey(
        'user_accounts.Add_Department',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    
    # Event Details
    event_name = models.CharField(max_length=255, verbose_name="Event Name")
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES, verbose_name="Event Type")
    event_description = models.TextField(verbose_name="Event Description/Purpose")
    
    # Guest Speaker Information
    has_guest_speaker = models.BooleanField(default=False, verbose_name="Guest Speaker/Chief Guest")
    guest_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="Guest Name")
    guest_designation = models.CharField(max_length=255, null=True, blank=True, verbose_name="Guest Designation")
    guest_organization = models.CharField(max_length=255, null=True, blank=True, verbose_name="Guest Organization")
    guest_email = models.EmailField(null=True, blank=True, verbose_name="Guest Email")
    guest_phone = models.CharField(max_length=20, null=True, blank=True, verbose_name="Guest Phone")
    
    # Booking Schedule
    booking_date = models.DateField(verbose_name="Event Date")
    start_time = models.TimeField(verbose_name="Start Time")
    end_time = models.TimeField(verbose_name="End Time")
    
    # Hall and Capacity
    preferred_hall = models.CharField(max_length=50, verbose_name="Preferred Hall")
    expected_attendees = models.IntegerField(verbose_name="Expected Number of Attendees")
    
    # Requirements
    special_requirements = models.TextField(
        null=True,
        blank=True,
        verbose_name="Special Requirements",
        help_text="e.g., Projector, Microphone, Seating arrangement, Refreshments"
    )
    
    # Technical Requirements
    needs_projector = models.BooleanField(default=False, verbose_name="Projector Required")
    needs_microphone = models.BooleanField(default=False, verbose_name="Microphone Required")
    needs_sound_system = models.BooleanField(default=False, verbose_name="Sound System Required")
    needs_video_conferencing = models.BooleanField(default=False, verbose_name="Video Conferencing Required")
    
    # Refreshments
    needs_refreshments = models.BooleanField(default=False, verbose_name="Refreshments Required")
    refreshment_details = models.TextField(
        null=True,
        blank=True,
        verbose_name="Refreshment Details",
        help_text="Specify type and quantity"
    )
    
    # Additional Information
    target_audience = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Target Audience",
        help_text="e.g., Students, Faculty, Staff, External participants"
    )
    
    # Status and Approval
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey(
        'user_accounts.USER',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_bookings',
        db_constraint=False
    )
    approval_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Seminar Hall Booking'
        verbose_name_plural = 'Seminar Hall Bookings'
    
    def __str__(self):
        return f"{self.booking_id} - {self.event_name}"
    
    def save(self, *args, **kwargs):
        if not self.booking_id:
            # Generate booking ID
            import datetime
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            self.booking_id = f"SHB{timestamp}"
        super().save(*args, **kwargs)
    
    def get_hall_name(self):
        """Get the hall name from SeminarHall model"""
        try:
            hall = SeminarHall.objects.get(id=self.preferred_hall)
            return f"{hall.hall_name} ({hall.hall_number})"
        except (SeminarHall.DoesNotExist, ValueError):
            return self.preferred_hall


class SeminarHall(models.Model):
    """Model for Seminar Hall Master Data"""
    hall_name = models.CharField(max_length=255, verbose_name="Hall Name")
    hall_number = models.CharField(max_length=50, verbose_name="Hall Number", unique=True)
    capacity = models.IntegerField(verbose_name="Seating Capacity")
    has_projector = models.BooleanField(default=False, verbose_name="Has Projector")
    has_sound_system = models.BooleanField(default=False, verbose_name="Has Sound System")
    has_ac = models.BooleanField(default=False, verbose_name="Has AC")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['hall_number']
        verbose_name = 'Seminar Hall'
        verbose_name_plural = 'Seminar Halls'
    
    def __str__(self):
        return f"{self.hall_name} ({self.hall_number})"


class SHBApprovalWorkflow(models.Model):
    """
    Seminar Hall Booking Approval Workflow based on creator role
    Each faculty role can have its own approval hierarchy
    """
    # Creator role ID from external database (rit_approval_system)
    creator_role_id = models.IntegerField(
        unique=True,
        verbose_name="Creator Role ID",
        help_text="Role ID from rit_approval_system database"
    )
    
    workflow_name = models.CharField(max_length=255, verbose_name="Workflow Name")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'user_accounts.USER',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_constraint=False
    )
    
    class Meta:
        verbose_name = 'SHB Approval Workflow'
        verbose_name_plural = 'SHB Approval Workflows'
    
    def __str__(self):
        return f"{self.workflow_name} (Creator Role: {self.creator_role_id})"


class SHBApprovalStep(models.Model):
    """
    Individual approval steps in the workflow
    Each step represents one approval level
    """
    workflow = models.ForeignKey(
        SHBApprovalWorkflow,
        on_delete=models.CASCADE,
        related_name='steps'
    )
    approval_level = models.IntegerField(verbose_name="Approval Level")
    
    # Approver role ID from external database (rit_approval_system)
    approver_role_id = models.IntegerField(
        verbose_name="Approver Role ID",
        help_text="Role ID from rit_approval_system database"
    )
    
    # Department matching
    is_cross_department = models.BooleanField(
        default=False,
        verbose_name="Cross Department Approver",
        help_text="If true, this approver can approve applications from any department"
    )
    
    approver_department_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Approver Department ID",
        help_text="Department ID for department-specific approvers"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    
    class Meta:
        ordering = ['workflow', 'approval_level']
        unique_together = [['workflow', 'approval_level']]
        verbose_name = 'SHB Approval Step'
        verbose_name_plural = 'SHB Approval Steps'
    
    def __str__(self):
        return f"{self.workflow.workflow_name} - Level {self.approval_level}"
    
    def get_approver_role_name(self):
        """Get role name from external database"""
        try:
            from user_accounts.models import Role
            role = Role.objects.using('rit_approval_system').get(id=self.approver_role_id)
            return role.role
        except:
            return f"Role ID {self.approver_role_id}"


class SHBApplicationApproval(models.Model):
    """
    Track approval progress for each application
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    application = models.ForeignKey(
        SeminarHallBooking,
        on_delete=models.CASCADE,
        related_name='approvals'
    )
    approval_step = models.ForeignKey(
        SHBApprovalStep,
        on_delete=models.CASCADE
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Store approver ID instead of object to avoid cross-database issues
    approver_id = models.IntegerField(null=True, blank=True, verbose_name="Approver User ID")
    
    comments = models.TextField(null=True, blank=True, verbose_name="Comments")
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Department ID for filtering (copied from application)
    approver_department_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Approver Department ID"
    )
    
    class Meta:
        ordering = ['approval_step__approval_level']
        verbose_name = 'SHB Application Approval'
        verbose_name_plural = 'SHB Application Approvals'
    
    def __str__(self):
        return f"{self.application.booking_id} - Level {self.approval_step.approval_level} - {self.status}"
    
    def get_approver_name(self):
        """Get approver name from external database"""
        if not self.approver_id:
            return "Pending"
        try:
            from user_accounts.models import USER
            user = USER.objects.using('rit_approval_system').get(id=self.approver_id)
            return user.username
        except:
            return f"User ID {self.approver_id}"



class Faculty_Data_Permission(models.Model):
    role_id = models.PositiveIntegerField( null=True, blank=True)   
    
    can_view_all_faculty_data = models.BooleanField(default=False, null=True, blank=True)
    can_view_department_faculty_data = models.BooleanField(default=False, null=True, blank=True)


from django.db import models
from django.utils import timezone

from faculty_management.models import general_information
from user_accounts.models import Add_Department



class Ticket(models.Model):
    
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Progressing", "Progressing"),
        ("Solved", "Solved"),
        ("Accomplished", "Accomplished"),
    ]

    student = models.ForeignKey(
        StudentDetails,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_tickets"
    )

    faculty = models.ForeignKey(
        general_information,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="faculty_tickets"
    )

    issue = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    description = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending"
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if not self.student and not self.faculty:
            raise ValidationError("Please select either Student or Faculty.")

        if self.student and self.faculty:
            raise ValidationError("Please select only one user.")

    def __str__(self):
        if self.student:
            return f"{self.student.name} - {self.issue}"

        if self.faculty:
            return f"{self.faculty.name} - {self.issue}"

        return self.issue
 


class InventoryItemType(models.Model):
    type_name = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["type_name"]

    def __str__(self):
        return self.type_name


class InventoryCategory(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class InventoryItem(models.Model):
    item_code = models.CharField(max_length=100, unique=True)
    item_name = models.CharField(max_length=255)

    item_type = models.ForeignKey(
        InventoryItemType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    category = models.ForeignKey(
        InventoryCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    unit = models.CharField(max_length=50)

    stock_qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    minimum_qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    unit_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    # vendor_name = models.CharField(max_length=255, null=True, blank=True)

    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["item_name"]

    def is_low_stock(self):
        return self.stock_qty <= self.minimum_qty

    def __str__(self):
        return f"{self.item_code} - {self.item_name}"




class MaterialRequest(models.Model):
    
    STATUS = (
        ("PENDING", "Pending Approval"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("ISSUED", "Issued"),
    )

    request_no = models.CharField(max_length=100, unique=True, blank=True)

    creator_role_id = models.CharField(max_length=100, null=True, blank=True)

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="material_requests"
    )

    department = models.ForeignKey(
        Add_Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    purpose = models.TextField()
    location = models.CharField(max_length=255, null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="PENDING"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.request_no:
            count = MaterialRequest.objects.count() + 1
            self.request_no = f"MAT-{timezone.now().year}-{count:04d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.request_no


class MaterialRequestItem(models.Model):

    request = models.ForeignKey(
        MaterialRequest,
        related_name="request_items",
        on_delete=models.CASCADE
    )

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE
    )

    requested_qty = models.DecimalField(max_digits=10, decimal_places=2)
    issued_qty = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.request.request_no} - {self.item.item_name}"
 


class MaterialRequestApprovers(models.Model):
    """
    Master table for defining dynamic approval hierarchy.

    Example:
    Creator Role: Faculty
    Level 1: HOD
    Level 2: Admin
    Level 3: Principal
    """

    class CrossDepartment(models.TextChoices):
        YES = "YES", "Yes"
        NO = "NO", "No"

    # Role IDs are stored as CharField because Role is from rit_approval_system DB
    creator_role_id = models.CharField(max_length=100, null=True, blank=True)
    approver_role_id = models.CharField(max_length=100, null=True, blank=True)

    approver_level = models.PositiveIntegerField()

    is_cross_department_approver = models.CharField(
        max_length=3,
        choices=CrossDepartment.choices,
        default=CrossDepartment.NO,
        null=True,
        blank=True
    )

    approver_department = models.ForeignKey(
        Add_Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["creator_role_id", "approver_level"]

    def __str__(self):
        return f"Creator Role {self.creator_role_id} - Level {self.approver_level} - Approver Role {self.approver_role_id}"


class MaterialRequestApproversData(models.Model):
    """
    Runtime approval entries created for each request
    based on MaterialRequestApprovers hierarchy.
    """

    class Status(models.TextChoices):
        APPROVED = "APPROVED", "Approved"
        PENDING = "PENDING", "Pending"
        REJECTED = "REJECTED", "Rejected"

    request = models.ForeignKey(
        MaterialRequest,
        on_delete=models.CASCADE,
        related_name="approval_entries"
    )

    # Actual approver faculty who acts on the request
    approver = models.ForeignKey(
        general_information,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_constraint=False,
        related_name="material_approval_entries"
    )

    # Role IDs stored as CharField
    creator_role_id = models.CharField(max_length=100, null=True, blank=True)
    approver_role_id = models.CharField(max_length=100, null=True, blank=True)

    approver_level = models.PositiveIntegerField()

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING
    )

    reason = models.CharField(max_length=225, null=True, blank=True)
    acted_on = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["approver_level", "id"]

    def __str__(self):
        return f"{self.request.request_no} - Level {self.approver_level} - {self.status}"
 

class StockLedger(models.Model):
    TRANSACTION_TYPE = (
        ("OPENING", "Opening Stock"),
        ("RECEIPT", "Receipt"),
        ("ISSUE", "Issue"),
        ("ADJUSTMENT", "Adjustment"),
    )

    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPE)

    qty_in = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    qty_out = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance_qty = models.DecimalField(max_digits=10, decimal_places=2)

    reference_no = models.CharField(max_length=100, null=True, blank=True)

    handled_by_employee_id = models.CharField(max_length=100, null=True, blank=True)
    handled_by_name = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.item.item_name} - {self.transaction_type} - {self.balance_qty}"


class MaterialIssueProof(models.Model):
    STATUS = (
        ("PENDING", "Pending Verification"),
        ("VERIFIED", "Verified"),
        ("REJECTED", "Rejected"),
    )

    material_request = models.ForeignKey(
        MaterialRequest,
        on_delete=models.CASCADE,
        related_name="issue_proof"
    )

    proof_file = models.FileField(upload_to="material_issue_proofs/")

    description = models.TextField(null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="PENDING"
    )

    uploaded_by = models.ForeignKey(
        general_information,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_material_proofs",
        db_constraint=False
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    verified_by = models.ForeignKey(
        general_information,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_material_proofs",
        db_constraint=False
    )

    verified_remarks = models.TextField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    stock_updated = models.BooleanField(default=False)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.material_request.request_no} - {self.status}"
  

class MaterialScrapItem(models.Model):
    proof = models.ForeignKey(
        MaterialIssueProof,
        on_delete=models.CASCADE,
        related_name="scrap_items"
    )

    scrap_type = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.scrap_type} - {self.name} - {self.count}"


class MaterialIssueProofApprovalData(models.Model):
    class Status(models.TextChoices):
        APPROVED = "APPROVED", "Approved"
        PENDING = "PENDING", "Pending"
        REJECTED = "REJECTED", "Rejected"

    proof = models.ForeignKey(
        MaterialIssueProof,
        on_delete=models.CASCADE,
        related_name="approval_entries"
    )

    approver = models.ForeignKey(
        general_information,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_constraint=False,
        related_name="material_proof_approval_entries"
    )

    creator_role_id = models.CharField(max_length=100, null=True, blank=True)
    approver_role_id = models.CharField(max_length=100, null=True, blank=True)
    approver_level = models.PositiveIntegerField()

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING
    )

    reason = models.CharField(max_length=225, null=True, blank=True)
    acted_on = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["approver_level", "id"]

    def __str__(self):
        return f"{self.proof.material_request.request_no} - Level {self.approver_level} - {self.status}"
    
    
class program_org_data_Permission(models.Model):
    role_id = models.PositiveIntegerField(null=True, blank=True)
    can_view_all_program_org_data = models.BooleanField(default=False, null=True, blank=True)
    can_view_department_program_org_data = models.BooleanField(default=False, null=True, blank=True)
    
    class Meta:
        ordering = ["id"]
    
    def __str__(self):
        return f"Role ID: {self.role_id}"



   

class ProfessionalSociety(models.Model):
    society_name = models.CharField(max_length=255)
    department = models.ForeignKey(Add_Department, on_delete=models.CASCADE, db_constraint=False, null=True, blank=True)

    class Meta:
        db_table = "professional_society"
        unique_together = ['society_name', 'department']

    def __str__(self):
        return self.society_name
    
class ProgramType(models.Model):
    program_type_name = models.CharField(max_length=255)
    department = models.ForeignKey(Add_Department, on_delete=models.CASCADE, db_constraint=False, null=True, blank=True)

    class Meta:
        db_table = "program_type"
        unique_together = ['program_type_name', 'department']

    def __str__(self):
        return self.program_type_name




    

