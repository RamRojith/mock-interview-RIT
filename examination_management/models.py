from django.db import models
import uuid
import random
import string
from user_accounts.models import Role
from course_management.models import AssignSubjectFaculty, Course,  Regulations
from user_accounts.models import Degree
from user_accounts.models import StudentDetails, Add_Department
from django.core.validators import MinValueValidator, MaxValueValidator

class ExaminationFunction(models.Model):
    role = models.ForeignKey(
        "user_accounts.Role",       # Role from external DB
        on_delete=models.DO_NOTHING, 
        db_constraint=False         # 🚨 disables DB-level FK
    )
    function = models.CharField(max_length=500)
    permission = models.BooleanField()


    
class GradeMaster(models.Model):
    
    degree = models.CharField(max_length=255, null=True, blank=True)
    regulation = models.CharField(max_length=255, null=True, blank=True)
    grade_from = models.FloatField(null=True, blank=True)
    grade_to = models.FloatField(null=True, blank=True)
    class_category = models.CharField(max_length=255, null=True, blank=True)
    mark_from = models.IntegerField(null=True, blank=True)
    mark_to = models.IntegerField(null=True, blank=True)
    grade = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.degree} : {self.mark_from}-{self.mark_to} -> {self.class_category}"
    
class InternalAssessment(models.Model):
    degree = models.ForeignKey(Degree, on_delete=models.CASCADE, null=True, blank=True)
    iat = models.CharField(max_length=50, null=True, blank=True, help_text="E.g. iat1, iat2 or IAT1")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["degree", "iat"], name="uniq_degree_iat")
        ]
        ordering = ["degree", "iat"]

    def __str__(self):
        deg = getattr(self.degree, "degree", None) or "-"
        return f"{deg} : {self.iat or 'Unspecified'}"
 

class Assessments(models.Model):
    degree = models.ForeignKey(Degree, on_delete=models.CASCADE, null=True, blank=True)
    assessment_name = models.CharField(max_length=255, null=True, blank=True)
    question_paper_required = models.BooleanField(default=False)

    # NEW: map this assessment to an InternalAssessment row (nullable)
    internal_assessment = models.ForeignKey(
        InternalAssessment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assessments",
    )

    def __str__(self):
        deg = getattr(self.degree, "degree", None) or str(self.degree) or "-"
        return f"{deg} : {self.assessment_name}"


class CourseOutcome(models.Model):
    regulation = models.CharField(max_length=50, null=True, blank=True)   
    co_code = models.CharField(max_length=20, null=True, blank=True)
    co_name = models.CharField(max_length=255, null=True, blank=True) 

    def __str__(self):
        return f"{self.co_code} - {self.co_name}"

class ProgrammeOutcome(models.Model):
    regulation = models.CharField(max_length=50, null=True, blank=True)   
    po_code = models.CharField(max_length=20, null=True, blank=True)
    po_name = models.CharField(max_length=255, null=True, blank=True) 

    def __str__(self):
        return f"{self.po_code} - {self.po_name}"

class BloomsLevel(models.Model):
    level_code = models.CharField(max_length=10, null=True, blank=True)  
    description = models.CharField(max_length=255, null=True, blank=True)              

    def __str__(self):
        return f"{self.level_code} - {self.description}"




# class QuestionMaster(models.Model):
#     question_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     question_text = models.TextField()
#     option_a = models.CharField(max_length=255, null=True, blank=True)
#     option_b = models.CharField(max_length=255, null=True, blank=True)
#     option_c = models.CharField(max_length=255, null=True, blank=True)
#     option_d = models.CharField(max_length=255, null=True, blank=True)
#     correct_option = models.CharField(max_length=1)  # Assuming options are labeled as A, B, C, D
#     marks = models.IntegerField()
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     def __str__(self):
#         return f"Question {self.question_id}: {self.question_text[:50]}..."  # Display first 50 chars


from course_management.models import Regulations

class ExamPattern(models.Model):
    regulation = models.ForeignKey(Regulations, on_delete=models.CASCADE, null=True, blank=True)
    year = models.CharField(max_length=10, null=True, blank=True)
    semester = models.CharField(max_length=10, null=True, blank=True)
    academic_year = models.CharField(max_length=9, null=True, blank=True)  # YYYY-YYYY
    pattern = models.CharField(max_length=50, null=True, blank=True)
    for_exam = models.CharField(max_length=50, null=True, blank=True)
    degree = models.ForeignKey(Degree, on_delete=models.CASCADE, null=True, blank=True)
    def __str__(self):
        return f"{self.regulation} - {self.year} {self.semester} ({self.pattern})"




class Part(models.Model):
    exam_pattern = models.ForeignKey(ExamPattern, on_delete=models.CASCADE, related_name="parts", null=True, blank=True)
    name = models.CharField(max_length=1)  # A, B, C
    total_questions = models.IntegerField()
    max_marks = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Part {self.name}"



class Question(models.Model):
    part = models.ForeignKey(Part, related_name='questions', on_delete=models.CASCADE)
    number = models.PositiveIntegerField()
    total_marks = models.PositiveIntegerField(default=0)
    # course_outcome = models.ForeignKey(CourseOutcome, on_delete=models.SET_NULL, null=True, blank=True)
    # blooms_level = models.ForeignKey(BloomsLevel, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Q{self.number} - Part {self.part.name} ({self.total_marks} marks)"


class OptionMarks(models.Model):
    question = models.ForeignKey(Question, related_name='options', on_delete=models.CASCADE)
    option_letter = models.CharField(max_length=2)
    marks_i = models.PositiveIntegerField(default=0)
    marks_ii = models.PositiveIntegerField(default=0)

    course_outcome_i = models.ForeignKey(
        CourseOutcome, related_name='option_i_co', on_delete=models.SET_NULL, null=True, blank=True
    )
    course_outcome_ii = models.ForeignKey(
        CourseOutcome, related_name='option_ii_co', on_delete=models.SET_NULL, null=True, blank=True
    )

    blooms_level_i = models.ForeignKey(
        BloomsLevel, related_name='option_i_level', on_delete=models.SET_NULL, null=True, blank=True
    )
    blooms_level_ii = models.ForeignKey(
        BloomsLevel, related_name='option_ii_level', on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return f"{self.question} - Option {self.option_letter}"



from faculty_management.models import general_information

from faculty_management.models import general_information

class SquadMember(models.Model):
    IAT_CHOICES = [
        ('I', 'I'),
        ('II', 'II'),
        ('III', 'III'),
    ]

    DURATION_CHOICES = [
        ('FN', 'FN'),
        ('AN', 'AN'),
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Reported', 'Reported'),
    ]

    
    SEMESTER_CHOICES = [('Odd', 'Odd'), ('Even', 'Even')]
    
    appointment_ref = models.CharField(max_length=100, unique=True, null=True, blank=True)
    faculty_id =  models.ForeignKey(general_information, on_delete=models.CASCADE, related_name='marks', blank=True, null=True)
    date = models.DateField(null=True, blank=True)
    # Removed 'session'; replaced by 'semester' constrained to 1-8
    
    semester = models.CharField(max_length=100, choices=SEMESTER_CHOICES, null=True, blank=True)
    iat = models.CharField(max_length=3, choices=IAT_CHOICES, null=True, blank=True)
    no_of_hall = models.PositiveIntegerField(null=True, blank=True)
    duration = models.CharField(max_length=2, choices=DURATION_CHOICES, null=True, blank=True)
    hall_numbers = models.CharField(max_length=200, null=True, blank=True)
    reported = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')

    def __str__(self):
        return f"{self.faculty_id.name} - {self.appointment_ref} ({self.reported})"
  

 




class SquadMemberReport(models.Model):
    squad_member = models.ForeignKey(SquadMember, related_name='reports', on_delete=models.CASCADE, null=True, blank=True)
    date_filled = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    # Observation fields
    seating_appropriate = models.BooleanField(null=True, blank=True)
    classrooms_clean = models.BooleanField(null=True, blank=True)
    class_room_board_clean =models.BooleanField(null=True, blank=True)
    seating_as_arrangement = models.BooleanField(null=True, blank=True)
    materials_distributed = models.BooleanField(null=True, blank=True)
    only_permitted_materials = models.BooleanField(null=True, blank=True)
    register_no_written = models.BooleanField(null=True, blank=True)
    no_markings_on_paper = models.BooleanField(null=True, blank=True)
    id_worn = models.BooleanField(null=True, blank=True)
    unruly_behaviour = models.BooleanField(null=True, blank=True)
    followed_rules = models.BooleanField(null=True, blank=True)
    faculty_present = models.BooleanField(null=True, blank=True)
    faculty_misconduct = models.BooleanField(null=True, blank=True)

    feedback = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Report for {self.squad_member.faculty_id.name} ({self.squad_member.appointment_ref})"




 



class ExamPatternSetting(models.Model):
    # Basic identifiers
    department_code = models.CharField(max_length=10)
    department_name = models.CharField(max_length=100)
    course_code = models.CharField(max_length=20)
    course_title = models.CharField(max_length=200)
    batch = models.CharField(max_length=20, blank=True, null=True)
    section = models.CharField(max_length=10, blank=True, null=True)
    iat = models.CharField(max_length=50, blank=True, null=True)  # e.g., IAT1, IAT2, Assignment
    
    # Selected pattern details
    regulation_year = models.CharField(max_length=10)
    year = models.CharField(max_length=10)
    semester = models.CharField(max_length=10)
    academic_year = models.CharField(max_length=20)
    pattern = models.CharField(max_length=50)
    
    # Track creation and update
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('department_code', 'course_code', 'batch', 'section', 'iat')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.department_code} - {self.course_code} - {self.batch or '-'} - {self.section or '-'} - {self.iat or '-'}"


class StudentExam(models.Model):
    reg_no = models.CharField(max_length=20)
    student_name = models.CharField(max_length=100)
    department_code = models.CharField(max_length=20)
    department_name = models.CharField(max_length=100)
    course_code = models.CharField(max_length=20)
    course_title = models.CharField(max_length=100)
    batch = models.CharField(max_length=20, blank=True, null=True)
    section = models.CharField(max_length=10, blank=True, null=True)
    exam_name = models.CharField(max_length=50, blank=True, null=True)
    
    pattern = models.ForeignKey(
        ExamPatternSetting,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_exams'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.reg_no} - {self.student_name} ({self.course_code})"



# Detail model: store marks including max marks for each question/option
class StudentMark(models.Model):
    student_exam = models.ForeignKey(StudentExam, on_delete=models.CASCADE, related_name='marks', blank=True, null=True)
    
    part_name = models.CharField(max_length=10, blank=True, null=True)      # Part A, B, etc.
    question_number = models.CharField(max_length=10, blank=True, null=True)  # e.g., 1, 12a
    sub_question = models.CharField(max_length=10, blank=True, null=True) # i, ii
    option_letter = models.CharField(max_length=5, blank=True, null=True) # a, b, c if multiple choice
    

    max_marks = models.PositiveIntegerField()
    marks_obtained = models.PositiveIntegerField()
    

    created_at = models.DateTimeField(auto_now_add=True)
    
    co_code = models.ForeignKey(CourseOutcome, on_delete=models.CASCADE, blank=True, null=True) 
    level_code = models.ForeignKey(BloomsLevel, on_delete=models.CASCADE, blank=True, null=True)

    

    def __str__(self):
        return f"{self.student_exam.reg_no} - {self.part_name}{self.question_number}{self.option_letter or ''}{self.sub_question or ''}: {self.marks_obtained}/{self.max_marks}"


class Final_Marks(models.Model):
    student = models.ForeignKey("user_accounts.StudentDetails", on_delete=models.CASCADE, blank=True, null=True)
    exam = models.ForeignKey(StudentExam, on_delete=models.CASCADE, blank=True, null=True)
    co_marks = models.FloatField(null=True, blank=True)
    total = models.FloatField(null=True, blank=True)
    co_code = models.ForeignKey(
        'examination_management.CourseOutcome', 
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    







class experiment_marks(models.Model):
    student = models.ForeignKey(
        'user_accounts.StudentDetails',
        on_delete=models.CASCADE,
        related_name='experiment_marks_marks'
    )
    courses = models.ForeignKey(
        'course_management.CourseEnrollment',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='experiment_marks_marks'
    )

    # NEW: store selected CO
    cos = models.ManyToManyField(
        'examination_management.CourseOutcome',
        blank=True,
        related_name='practical_marks'
    )

    # changed: multiple Bloom's levels
    blooms_levels = models.ManyToManyField(
        'examination_management.BloomsLevel',
        blank=True,
        related_name='practical_marks'
    )

    # NEW: link to InternalAssessment
    assessment = models.ForeignKey(
        'examination_management.InternalAssessment',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='experiment_marks'
    )

    work_program = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(40)]
    )
    observation = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(20)]
    )
    record = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(15)]
    )
    total = models.PositiveSmallIntegerField(editable=False)

    experiment_no = models.PositiveSmallIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['student'])]

    def clean(self):
        wp = max(0, min(int(self.work_program or 0), 40))
        ob = max(0, min(int(self.observation or 0), 20))
        rc = max(0, min(int(self.record or 0), 15))
        self.work_program, self.observation, self.record = wp, ob, rc
        self.total = min(wp + ob + rc, 75)

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        en = f" | Exp {self.experiment_no}" if self.experiment_no else ""
        return f"{getattr(self.student, 'reg_no', self.student_id)} -> {self.total}/75{en}"

    
    
    
class ModelLabMarks(models.Model):
    student = models.ForeignKey(
        'user_accounts.StudentDetails',
        on_delete=models.CASCADE,
        related_name='model_lab_marks'
    )
    courses = models.ForeignKey(
        'course_management.CourseEnrollment',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='model_lab_marks'
    )

    program = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(75)],
        null=True, blank=True
    )
    viva = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(25)],
        null=True, blank=True
    )
    total = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    only_total = models.BooleanField(default=False)

    model_lab = models.ForeignKey(
        'examination_management.ModelLab',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='marks'
    )

    internal_assessment = models.ForeignKey(
        'examination_management.InternalAssessment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='model_lab_marks'
    )

    batch = models.CharField(max_length=20, blank=True, null=True)
    section = models.CharField(max_length=10, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['student']),
            models.Index(fields=['model_lab']),
            models.Index(fields=['internal_assessment']),
        ]
        unique_together = ('student', 'courses', 'model_lab', 'internal_assessment', 'batch', 'section')
        verbose_name = "Model Lab Mark"
        verbose_name_plural = "Model Lab Marks"

    def clean(self):
        if self.only_total:
            self.program = None
            self.viva = None
            self.total = max(0, min(int(self.total or 0), 100))
        else:
            prog = max(0, min(int(self.program or 0), 75))
            viv = max(0, min(int(self.viva or 0), 25))
            self.program = prog
            self.viva = viv
            self.total = min(prog + viv, 100)

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        lab_name = getattr(self.model_lab, 'model_lab_name', None) or '-'
        iat_name = getattr(self.internal_assessment, 'iat', None) or '-'
        return f"{getattr(self.student, 'reg_no', self.student_id)} -> {self.total}/100 | {lab_name} | IAT:{iat_name}"



class StudentInternalMark(models.Model):
    # canonical foreign keys
    student = models.ForeignKey(
        StudentDetails, on_delete=models.CASCADE, related_name="internal_marks"
    )
    faculty_assignment = models.ForeignKey(AssignSubjectFaculty, on_delete=models.SET_NULL, null=True, blank=True, related_name="internal_marks")
    degree = models.ForeignKey(Degree, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey(Add_Department, on_delete=models.SET_NULL, null=True, blank=True)
    enrollment = models.ForeignKey(
        'course_management.CourseEnrollment', on_delete=models.PROTECT, related_name="internal_marks",
        null=True, blank=True
    )  # your "course" anchor as requested
    pattern = models.ForeignKey(
        ExamPattern,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internal_marks")

    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
    # exam/session meta
    exam_name = models.CharField(max_length=50, blank=True, null=True)
    semester = models.CharField(max_length=50, blank=True, null=True)

    # row granularity (one row per question/sub/option)
    part_name = models.CharField(max_length=10, blank=True, null=True)          # A, B, ...
    question_number = models.CharField(max_length=10, blank=True, null=True)    # 1, 2, 12a
    sub_question = models.CharField(max_length=10, blank=True, null=True)       # i, ii
    option_letter = models.CharField(max_length=5, blank=True, null=True)       # a, b

    max_marks = models.PositiveIntegerField(null=True, blank=True)
    marks_obtained = models.PositiveIntegerField(null=True, blank=True)

    co_code = models.ForeignKey(CourseOutcome, on_delete=models.SET_NULL, null=True, blank=True)
    level_code = models.ForeignKey(BloomsLevel, on_delete=models.SET_NULL, null=True, blank=True)

    # convenience denorms (optional — handy for display/search; safe to remove later)
    reg_no = models.CharField(max_length=20, blank=True, null=True)
    course_code = models.CharField(max_length=20, blank=True, null=True)
    absentee = models.PositiveSmallIntegerField(default=0) 
    retest_attempted = models.PositiveSmallIntegerField(default=0) 
    batch = models.CharField(max_length=20, blank=True, null=True)
    section = models.CharField(max_length=10, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    academic_year = models.CharField(max_length=20, null=True, blank=True)
    # faculty_assignment = models.ForeignKey(AssignSubjectFaculty, on_delete=models.SET_NULL, null=True, blank=True, related_name="student_marks")

    class Meta:
        indexes = [
            models.Index(fields=["student", "enrollment", "exam_name"]),
            models.Index(fields=["exam_name"]),
            models.Index(fields=["student", "exam_name", "part_name", "question_number"]),
        ]
        unique_together = (
            # unique per sitting for a given row (prevents duplicates)
            ("student", "enrollment", "exam_name", "part_name", "question_number", "sub_question", "option_letter"),
        )

    def __str__(self):
        who = self.reg_no or (self.student.reg_no if self.student_id else "-")
        course = self.course_code or (self.enrollment.course.course_code if (self.enrollment_id and self.enrollment.course_id) else "-")
        addr = f"{self.part_name}{self.question_number or ''}{self.option_letter or ''}{self.sub_question or ''}"
        return f"{who} {self.exam_name or ''} {course} :: {addr} = {self.marks_obtained}/{self.max_marks}"




class ModelLab(models.Model):
    degree = models.ForeignKey(Degree, on_delete=models.CASCADE, null=True, blank=True)
    model_lab_name = models.CharField(max_length=255)

    # NEW: map a modellab to an InternalAssessment (nullable)
    internal_assessment = models.ForeignKey(
        InternalAssessment, on_delete=models.SET_NULL, null=True, blank=True, related_name="modellabs"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["degree", "model_lab_name"], name="uniq_degree_modellab_name")
        ]
        ordering = ["model_lab_name"]

    def __str__(self):
        deg = getattr(self.degree, "degree", None) or "-"
        return f"{deg} : {self.model_lab_name}"




class AssessmentWeightage(models.Model):
    degree = models.ForeignKey(Degree, on_delete=models.CASCADE)
    regulation = models.ForeignKey(Regulations, on_delete=models.CASCADE)
    selected_assessment_percentage = models.FloatField()
    activity_percentage = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)



from django.db import models

class ConsolidatedAssessmentResult(models.Model):
    student = models.ForeignKey(
        StudentDetails, on_delete=models.CASCADE, related_name="consolidate_admin", null=True, blank=True
    )
    course = models.ForeignKey(
        'course_management.CourseEnrollment', on_delete=models.PROTECT, related_name="consolidate_course",
        null=True, blank=True
    )

    theory_assessment_name = models.CharField(max_length=255, null=True, blank=True)
    activity_assessment_name = models.CharField(max_length=255, null=True, blank=True)
    practical_assessment_name = models.CharField(max_length=255, null=True, blank=True)

    theory_max_mark = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )
    

    theory_actual_mark = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    
    theory_display_max_mark = models.CharField(max_length=255, null=True, blank=True)
    
    theory_display_actual_mark = models.CharField(max_length=255, null=True, blank=True)
    
    
    practical_max_mark = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )
    practical_actual_mark = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    
    practical_display_max_mark = models.CharField(max_length=255, null=True, blank=True)
    
    practical_display_actual_mark = models.CharField(max_length=255, null=True, blank=True)
    
    
    activity_max_mark = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )
    activity_actual_mark = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    activity_display_max_mark = models.CharField(max_length=255, null=True, blank=True)
    activity_display_actual_mark = models.CharField(max_length=255, null=True, blank=True)
    
    
    
    
    hour_config = models.ForeignKey(
        "examination_management.CourseHourConfig",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="consolidated_results"
    )

    # ⭐ SEPARATE TOTAL COLUMN
    

    generated_on = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    department = models.ForeignKey(
        Add_Department,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="consolidated_department"
    )
    degree = models.ForeignKey(
        Degree,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="consolidated_degree"
    )
    batch = models.CharField(max_length=50, null=True, blank=True)
    section = models.CharField(max_length=10, null=True, blank=True)
    current_semester = models.PositiveSmallIntegerField(null=True, blank=True)

    


    def __str__(self):
      return f"{self.student_id} - {self.course_id} - {self.generated_on.date()}"
class OverallConsolidateRecord(models.Model):
    faculty_id = models.CharField(max_length=50, blank=True, null=True)

    student = models.ForeignKey(
        StudentDetails,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="overall_consolidate_records"
    )

    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True)
    department = models.ForeignKey(Add_Department, on_delete=models.SET_NULL, null=True, blank=True)
    degree = models.ForeignKey(Degree, on_delete=models.SET_NULL, null=True, blank=True)

    batch = models.CharField(max_length=50, blank=True, null=True)
    section = models.CharField(max_length=50, blank=True, null=True)

    theory_assessment = models.TextField(blank=True, null=True)
    activity_assessment = models.TextField(blank=True, null=True)
    practical_assessment = models.TextField(blank=True, null=True)

    theory_max_mark = models.TextField(blank=True, null=True)
    activity_max_mark = models.TextField(blank=True, null=True)
    practical_max_mark = models.TextField(blank=True, null=True)

    theory_actual_mark = models.TextField(blank=True, null=True)
    activity_actual_mark = models.TextField(blank=True, null=True)
    practical_actual_mark = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        student_text = self.student.reg_no if self.student_id else "-"
        return f"{student_text} | {self.batch or '-'}-{self.section or '-'}"

class CourseHourConfig(models.Model):
    degree = models.ForeignKey(Degree, on_delete=models.CASCADE, null=True, blank=True)
    regulation = models.ForeignKey(Regulations, on_delete=models.CASCADE, null=True, blank=True)

    lecture_hours = models.IntegerField(default=0)
    tutorial_hours = models.IntegerField(default=0)
    laboratory_hours = models.IntegerField(default=0)
    theory_percentage = models.IntegerField(default=0)
    practical_percentage = models.IntegerField(default=0)
    activity_percentage = models.IntegerField(default=0)


class InternalAssessmentMasterTemplate(models.Model):
    COURSE_TYPE_CHOICES = [
        ("theory", "Theory Course"),
        ("practical", "Practical Course"),
        ("theory_lab", "Theory with Laboratory Course"),
    ]

    degree = models.ForeignKey(Degree, on_delete=models.CASCADE)
    regulation = models.ForeignKey(Regulations, on_delete=models.CASCADE)
    course_type = models.CharField(max_length=20, choices=COURSE_TYPE_CHOICES)

    assessment1_assignment = models.IntegerField(default=0)
    assessment1_test = models.IntegerField(default=0)
    assessment2_assignment = models.IntegerField(default=0)
    assessment2_test = models.IntegerField(default=0)
    total_internal = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("degree", "regulation", "course_type")

    def __str__(self):
        return f"{self.degree} - {self.regulation} - {self.course_type}"



class Class_Category(models.Model):
    degree = models.ForeignKey(Degree, on_delete=models.CASCADE, null=True, blank=True)
    department = models.ForeignKey(Add_Department, on_delete=models.CASCADE, null=True, blank=True)
    regulation = models.ForeignKey(Regulations, on_delete=models.CASCADE, null=True, blank=True)

    class_category = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    




# class Result(models.Model):
#     degree = models.ForeignKey(Degree, on_delete=models.CASCADE, null=True, blank=True)
#     department = models.ForeignKey(Add_Department, on_delete=models.CASCADE, null=True, blank=True)
#     student = models.ForeignKey(StudentDetails, on_delete=models.CASCADE, null=True, blank=True)
#     regulation = models.ForeignKey(Regulations, on_delete=models.CASCADE, null=True, blank=True)
#     course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
#     credit = models.CharField(max_length=10, null=True, blank=True)
#     grade = models.CharField(max_length=10, null=True, blank=True)
#     grade_total = models.FloatField(null=True, blank=True)
#     year = models.CharField(max_length=100, null=True, blank=True)
#     semester = models.CharField(max_length=100, null=True, blank=True)
#     batch = models.CharField(max_length=500, null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     academic_year = models.CharField(max_length=100, null=True, blank=True)


from django.db import models
from django.utils import timezone


class Result(models.Model):
    degree = models.ForeignKey(Degree, on_delete=models.CASCADE, null=True, blank=True)
    department = models.ForeignKey(Add_Department, on_delete=models.CASCADE, null=True, blank=True)
    student = models.ForeignKey(StudentDetails, on_delete=models.CASCADE, null=True, blank=True)
    regulation = models.ForeignKey(Regulations, on_delete=models.CASCADE, null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
    credit = models.CharField(max_length=10, null=True, blank=True)
    grade = models.CharField(max_length=10, null=True, blank=True)
    grade_total = models.FloatField(null=True, blank=True)
    year = models.CharField(max_length=100, null=True, blank=True)
    semester = models.CharField(max_length=100, null=True, blank=True)
    batch = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    academic_year = models.CharField(max_length=100, null=True, blank=True)





class GPA(models.Model):
    student = models.ForeignKey(StudentDetails, on_delete=models.CASCADE, null=True, blank=True)
    semester = models.CharField(max_length=10, null=True, blank=True)
    gpa = models.FloatField(null=True, blank=True)
    cgpa = models.FloatField(null=True, blank=True)
    academic_year = models.CharField(max_length=100, null=True, blank=True)


class CourseGrade(models.Model):
    letter_grade = models.CharField(max_length=10, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    mark_range = models.CharField(max_length=10, null=True, blank=True)  # NEW
    grade_points = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True,null=True,blank=True)

    def __str__(self):
        return f"{self.letter_grade} ({self.mark_range}) - {self.grade_points}"   
    



class Regular_Course_Grade_Master(models.Model):
    degree = models.ForeignKey(Degree, on_delete=models.CASCADE, null=True, blank=True)
    regulation = models.ForeignKey(
        Regulations,
        on_delete=models.CASCADE, null=True, blank=True
    )
    letter_grade = models.CharField(max_length=10, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    grade_points = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    mark_from = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    mark_to = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_fail_grade = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.letter_grade} - {self.grade_points}"    
    

class Self_Learning_Course_Grade_Master(models.Model):
    degree = models.ForeignKey(
        Degree,
        on_delete=models.CASCADE,
        null=True, blank=True
        
    )
    regulation = models.ForeignKey(
        Regulations,
        on_delete=models.CASCADE, null=True, blank=True
    )
    letter_grade = models.CharField(max_length=10, null=True, blank=True)

    mark_from = models.PositiveIntegerField(null=True, blank=True)
    mark_to = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True,null=True,blank=True)



    def __str__(self):
        return f"{self.degree} - {self.regulation}"

 



class Result_Permission(models.Model):
    role_id = models.PositiveIntegerField( null=True, blank=True)
    
    can_view_all_results = models.BooleanField(default=False, null=True, blank=True)
    can_view_department_results = models.BooleanField(default=False, null=True, blank=True)



class InternalExamSchedule(models.Model):
    SESSION_CHOICES = (
        ("FN", "Forenoon (FN)"),
        ("AN", "Afternoon (AN)"),
    )

    degree = models.ForeignKey(Degree, on_delete=models.PROTECT, related_name="internal_exam_schedules", null=True, blank=True)
    department = models.ForeignKey(Add_Department, on_delete=models.PROTECT, related_name="internal_exam_schedules", null=True, blank=True)
    regulation = models.ForeignKey(Regulations, on_delete=models.PROTECT, related_name="internal_exam_schedules", null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="internal_exam_schedules", null=True, blank=True)
    semester = models.CharField(max_length=10, null=True, blank=True)
    exam_date = models.DateField(null=True, blank=True)
    batch = models.CharField(max_length=20, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    session = models.CharField(max_length=2, choices=SESSION_CHOICES, default="FN")
    internal_assessment = models.ForeignKey(InternalAssessment, on_delete=models.PROTECT,related_name="internal_exam_schedules",null=True,blank=True )


   

    def __str__(self):
        return f"{self.degree} | {self.department} | {self.regulation}"




class InternalTimeTable(models.Model):
    SESSION_CHOICES = (
        ("FN", "Forenoon (FN)"),
        ("AN", "Afternoon (AN)"),
    )

    degree = models.ForeignKey(
        Degree, on_delete=models.PROTECT,
        related_name="internal_timetables",
        null=True, blank=True
    )
    department = models.ForeignKey(
        Add_Department, on_delete=models.PROTECT,
        related_name="internal_timetables",
        null=True, blank=True
    )
    regulation = models.ForeignKey(
        Regulations, on_delete=models.PROTECT,
        related_name="internal_timetables",
        null=True, blank=True
    )
    course = models.ForeignKey(
        Course, on_delete=models.PROTECT,
        related_name="internal_timetables",
        null=True, blank=True
    )
    internal_assessment= models.ForeignKey(InternalAssessment, on_delete=models.PROTECT, related_name="internal_timetables", null=True, blank=True)
    batch = models.CharField(max_length=20, null=True, blank=True)

    semester = models.CharField(max_length=10, null=True, blank=True)
    exam_date = models.DateField(null=True, blank=True)

    
    published_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    session = models.CharField(max_length=2, choices=SESSION_CHOICES, default="FN")

  
    def __str__(self):
        return f"{self.degree} | {self.department} | {self.regulation}"


 







class SemesterExamSchedule(models.Model):
    SESSION_CHOICES = (
        ("FN", "Forenoon (FN)"),
        ("AN", "Afternoon (AN)"),
    )

    degree = models.ForeignKey(Degree, on_delete=models.PROTECT, related_name="semester_exam_schedules", null=True, blank=True)
    department = models.ForeignKey(Add_Department, on_delete=models.PROTECT, related_name="semester_exam_schedules", null=True, blank=True)
    regulation = models.ForeignKey(Regulations, on_delete=models.PROTECT, related_name="semester_exam_schedules", null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="semester_exam_schedules", null=True, blank=True)
    semester = models.CharField(max_length=10, null=True, blank=True)
    exam_date = models.DateField(null=True, blank=True)
    batch = models.CharField(max_length=20, null=True, blank=True)
    
    is_failed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)
    session = models.CharField(max_length=2, choices=SESSION_CHOICES, default="FN")
  


   

    def __str__(self):
        return f"{self.degree} | {self.department} | {self.regulation}"
    



class SemesterExamScheduletimetable(models.Model):
    SESSION_CHOICES = (
        ("FN", "Forenoon (FN)"),
        ("AN", "Afternoon (AN)"),
    )

    degree = models.ForeignKey(Degree, on_delete=models.PROTECT, related_name="semester_timetable_exam_schedules", null=True, blank=True)
    department = models.ForeignKey(Add_Department, on_delete=models.PROTECT, related_name="semester_timetable_exam_schedules", null=True, blank=True)
    regulation = models.ForeignKey(Regulations, on_delete=models.PROTECT, related_name="semester_timetable_exam_schedules", null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="semester_timetable_exam_schedules", null=True, blank=True)
    semester = models.CharField(max_length=10, null=True, blank=True)
    exam_date = models.DateField(null=True, blank=True)
    batch = models.CharField(max_length=20, null=True, blank=True)
    published_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    session = models.CharField(max_length=2, choices=SESSION_CHOICES, default="FN")
    examsession = models.CharField(max_length=30, null=True, blank=True)
    is_failed = models.BooleanField(default=False)
  


   

    def __str__(self):
        return f"{self.degree} | {self.department} | {self.regulation}"
    



class HallticketStudent(models.Model):
    degree = models.ForeignKey(Degree, on_delete=models.CASCADE, related_name="hallticket_students")
    department = models.ForeignKey(Add_Department, on_delete=models.CASCADE, related_name="hallticket_students")
    student = models.ForeignKey(StudentDetails, on_delete=models.CASCADE, related_name="hallticket_records")

    batch = models.CharField(max_length=20)
    semester = models.CharField(max_length=10, blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)




class HallticketStudentCourse(models.Model):
    hallticket_student = models.ForeignKey(
        "HallticketStudent",
        on_delete=models.CASCADE,
        related_name="hallticket_courses"
    )

    exam_timetable = models.ForeignKey(
        "SemesterExamScheduletimetable",
        on_delete=models.CASCADE,
        related_name="hallticket_students"
    )

    semester = models.CharField(max_length=10)

    created_at = models.DateTimeField(auto_now_add=True)





from django.db import models
from django.core.exceptions import ValidationError


# ==========================================================
# HALL MASTER TABLE (HALL ENTRY)
# ==========================================================
class Hall(models.Model):
    hall_name = models.CharField(max_length=100, unique=True)
    benches = models.PositiveIntegerField(default=25)

    def clean(self):
        # enforce exactly 25 benches
        if self.benches != 25:
            raise ValidationError({"benches": "Benches must be exactly 25."})

    def save(self, *args, **kwargs):
        self.full_clean()  # ensure validation runs
        super().save(*args, **kwargs)

    def __str__(self):
        return self.hall_name


# ==========================================================
# HALL ALLOTMENT TABLE
# IMPORTANT:
# We DO NOT use ForeignKey to StudentDetails
# because StudentDetails may be in another DB alias.
# That causes cross-database relation error.
# ==========================================================
# class HallAllotment(models.Model):

#     # Hall reference (same DB)
#     hall = models.ForeignKey(
#         Hall,
#         on_delete=models.CASCADE,
#         related_name="allotments"
#     )

#     # ==============================
#     # Student snapshot fields
#     # ==============================

#     student_id = models.PositiveIntegerField(
#         null=True,
#         blank=True
#     )

#     reg_no = models.CharField(
#         max_length=50,
#         null=True,
#         blank=True
#     )

#     student_name = models.CharField(
#         max_length=255,
#         null=True,
#         blank=True
#     )

#     degree = models.CharField(
#         max_length=100,
#         null=True,
#         blank=True
#     )

#     department_id = models.PositiveIntegerField(
#         null=True,
#         blank=True
#     )

#     department_name = models.CharField(
#         max_length=200,
#         null=True,
#         blank=True
#     )

#     regulation = models.CharField(
#         max_length=50,
#         null=True,
#         blank=True
#     )

#     batch = models.CharField(
#         max_length=50,
#         null=True,
#         blank=True
#     )

#     year = models.CharField(
#         max_length=50,
#         null=True,
#         blank=True
#     )

#     semester = models.CharField(
#         max_length=50,
#         null=True,
#         blank=True
#     )

#     exam_type = models.CharField(
#         max_length=50,
#         null=True,
#         blank=True
#     )

#     # ==============================
#     # Seating Arrangement Fields
#     # ==============================

#     seat_no = models.PositiveIntegerField(
#         null=True,
#         blank=True
#     )

#     row_no = models.PositiveIntegerField(
#         null=True,
#         blank=True
#     )

#     col_no = models.PositiveIntegerField(
#         null=True,
#         blank=True
#     )

#     created_at = models.DateTimeField(auto_now_add=True)

   



class PracticalExamStudent(models.Model):
    # Student context (Model 1)
    student = models.ForeignKey(StudentDetails, on_delete=models.CASCADE, related_name="prac_exam_rows")
    degree = models.ForeignKey(Degree, on_delete=models.CASCADE)
    department = models.ForeignKey(Add_Department, on_delete=models.CASCADE)
    batch = models.CharField(max_length=50)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    semester = models.PositiveIntegerField(null=True, blank=True)



class PracticalExamStudentSchedule(models.Model):
    # Student schedule (Model 2)
    prac_student = models.ForeignKey(PracticalExamStudent, on_delete=models.CASCADE, related_name="schedules")

    batch_no = models.PositiveIntegerField()  # 1,2,3...
    exam_date = models.DateField()
    session = models.CharField(max_length=10)  # FN / AN
    exam_time = models.CharField(max_length=100)  # "09:30 AM - 12:30 PM"

    hall = models.ForeignKey("course_management.Hall", on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

   

    def __str__(self):
        return f"{self.reg_no} -> {self.hall.hall_name}"
    





class PassValue(models.Model):
    degree = models.ForeignKey(Degree, on_delete=models.CASCADE)
    regulation = models.ForeignKey(Regulations, on_delete=models.CASCADE)
    iat_pass_value = models.IntegerField(null=True, blank=True)
    university_iat_pass_value = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('degree', 'regulation')

    def __str__(self):
        return f"{self.degree} - {self.regulation}"



from django.db import models
import datetime


from course_management.models import Regulations

class SquadQuestions(models.Model): 

    academic_year = models.CharField(
        max_length=225 , null=True, blank=True
    )

    regulation = models.ForeignKey(Regulations, on_delete=models.DO_NOTHING, null=True, blank=True)

    question = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True , null=True, blank=True)
    
    is_active = models.BooleanField(default=True , null=True, blank=True)

    def __str__(self):
        return f"{self.question[:50]} - {self.academic_year}"  
     
# class SquadMemberReport(models.Model):
    
#     squad_member = models.ForeignKey(
#         SquadMember,
#         on_delete=models.CASCADE,
#         related_name="reports" , null=True, blank=True
#     )

#     feedback = models.TextField(null=True, blank=True)

#     created_at = models.DateTimeField(auto_now_add=True , null=True, blank=True)

#     def __str__(self):
#         return f"Report - {self.squad_member.appointment_ref}"
    
    
class SquadQuestionAnswer(models.Model):
    
    report = models.ForeignKey(
        SquadMemberReport,
        on_delete=models.CASCADE,
        related_name="answers" , null=True, blank=True
    )

    question = models.ForeignKey(
        SquadQuestions,
        on_delete=models.CASCADE ,  null=True, blank=True
    )

    answer = models.BooleanField(null=True, blank=True)

    remark = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.question} - {self.answer}"
    
