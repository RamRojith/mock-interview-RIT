from django.db import models

class NBAPerimissonFunction(models.Model):
    role = models.ForeignKey(
        "user_accounts.Role",       # Role from external DB
        on_delete=models.DO_NOTHING, 
        db_constraint=False         # 🚨 disables DB-level FK
    )
    function = models.CharField(max_length=500)
    permission = models.BooleanField()


class SanctionedIntake(models.Model):
    degree = models.ForeignKey("user_accounts.Degree", on_delete=models.CASCADE, null=True, blank=True)
    department = models.ForeignKey("user_accounts.Add_Department", on_delete=models.CASCADE, null=True, blank=True)
    year = models.CharField(max_length=20, null=True, blank=True)
    sanctioned_intake = models.PositiveIntegerField(null=True, blank=True)


class EnrolmentRatioFirstYear(models.Model):
    department = models.ForeignKey(
        "user_accounts.Add_Department",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="enrolment_ratio_first_years",
    )
    # Academic Year Range
    academic_year_range = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    is_verified   = models.BooleanField(default=False)
    admin_remarks = models.TextField(blank=True, null=True)

    # ---- Sanctioned Intake (N) ----
    sanctioned_intake_cay = models.PositiveIntegerField("N (CAY)", default=0, null=True, blank=True)
    sanctioned_intake_caym1 = models.PositiveIntegerField("N (CAYm1)", default=0, null=True, blank=True)
    sanctioned_intake_caym2 = models.PositiveIntegerField("N (CAYm2)", default=0, null=True, blank=True)

    # ---- Students Admitted (N1) ----
    admitted_cay = models.PositiveIntegerField("N1 (CAY)", default=0, null=True, blank=True)
    admitted_caym1 = models.PositiveIntegerField("N1 (CAYm1)", default=0, null=True, blank=True)
    admitted_caym2 = models.PositiveIntegerField("N1 (CAYm2)", default=0, null=True, blank=True)

    # ---- Supernumerary Admissions (N4) ----
    supernumerary_cay = models.PositiveIntegerField("N4 (CAY)", default=0, null=True, blank=True)
    supernumerary_caym1 = models.PositiveIntegerField("N4 (CAYm1)", default=0, null=True, blank=True)
    supernumerary_caym2 = models.PositiveIntegerField("N4 (CAYm2)", default=0, null=True, blank=True)

    # ---- Enrolment Ratios (ER) ----
    er_cay = models.DecimalField("ER₁ (CAY)", max_digits=6, decimal_places=2, default=0.00, null=True, blank=True)
    er_caym1 = models.DecimalField("ER₂ (CAYm1)", max_digits=6, decimal_places=2, default=0.00, null=True, blank=True)
    er_caym2 = models.DecimalField("ER₃ (CAYm2)", max_digits=6, decimal_places=2, default=0.00, null=True, blank=True)

    # ---- Averages and Points ----
    average_er = models.DecimalField("Average ER", max_digits=6, decimal_places=2, default=0.00, null=True, blank=True)
    er_points = models.DecimalField("ER Points", max_digits=6, decimal_places=2, default=0.00, null=True, blank=True)

    # ---- Marks Distribution ----
    max_marks = models.PositiveIntegerField(default=20, null=True, blank=True)
    marks_awarded = models.PositiveIntegerField(default=0, null=True, blank=True)




from django.db import models
from django.conf import settings
from user_accounts.models import Add_Department


class SuccessRateStipulated(models.Model):
    """
    NBA Table 4.2.1 — Success Rate in the stipulated period (LYG, LYGm1, LYGm2)

    A* = Admitted in 1st year + actual 2nd year lateral entry + multiple-entry adds
         (minus exits due to multiple entry if any) — as per note in the table.
    B  = Graduated in stipulated duration.

    SR_i = (B_i / A_i) * 100
    Average_SR = mean(SR_1, SR_2, SR_3)
    SR_Points = 1.5 * Average_SR / 10
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    department = models.ForeignKey(Add_Department, on_delete=models.CASCADE, related_name="success_rates")

    # Display labels kept for traceability (e.g., "2023-24" style strings)
    lyg_label   = models.CharField(max_length=16, null=True, blank=True)
    lygm1_label = models.CharField(max_length=16, null=True, blank=True)
    lygm2_label = models.CharField(max_length=16, null=True, blank=True)

    # Academic year range (header shown in reports)
    academic_year_range = models.CharField(max_length=128, null=True, blank=True)

    # A* and B for each batch (integers; store as positive small ints to be safe)
    a_lyg   = models.PositiveIntegerField(default=0, null=True, blank=True)
    a_lygm1 = models.PositiveIntegerField(default=0, null=True, blank=True)
    a_lygm2 = models.PositiveIntegerField(default=0, null=True, blank=True)

    b_lyg   = models.PositiveIntegerField(default=0, null=True, blank=True)
    b_lygm1 = models.PositiveIntegerField(default=0, null=True, blank=True)
    b_lygm2 = models.PositiveIntegerField(default=0, null=True, blank=True)

    # Computed Success Rates per batch
    sr_1 = models.DecimalField(max_digits=6, decimal_places=2, default=0, null=True, blank=True)  # LYG
    sr_2 = models.DecimalField(max_digits=6, decimal_places=2, default=0, null=True, blank=True)  # LYGm1
    sr_3 = models.DecimalField(max_digits=6, decimal_places=2, default=0, null=True, blank=True)  # LYGm2

    # Aggregates
    average_sr = models.DecimalField(max_digits=6, decimal_places=2, default=0, null=True, blank=True)
    sr_points  = models.DecimalField(max_digits=6, decimal_places=2, default=0, null=True, blank=True)

    # Keep parity with other tables (always final here)
    is_verified   = models.BooleanField(default=True)
    admin_remarks = models.TextField(blank=True, null=True)

    # ---- Marks Distribution ----
    max_marks = models.PositiveIntegerField(default=15, null=True, blank=True)
    marks_awarded = models.PositiveIntegerField(default=0, null=True, blank=True)







# nba/models.py
from django.db import models
from user_accounts.models import Add_Department

class AcademicPerformanceFirstYear(models.Model):
    """
    Table 4.3 — Academic Performance of the First-Year Students (weight 10).
    API_i = X_i * (Y_i / Z_i)
      X: Mean of 1st-year GPA of all successful students (10-point) OR mean%/10
      Y: Total number of successful students (proceeded to 2nd year)
      Z: Total number of students appeared in the examination
    Average_API = (API_1 + API_2 + API_3) / 3
    Marks awarded generally equals Average_API (out of 10).
    """
    department = models.ForeignKey(Add_Department, on_delete=models.CASCADE, related_name="api_first_year")

    # Labels like "2023-24"
    caym1_label = models.CharField(max_length=16, blank=True, null=True)
    caym2_label = models.CharField(max_length=16, blank=True, null=True)
    caym3_label = models.CharField(max_length=16, blank=True, null=True)

    academic_year_range = models.CharField(max_length=128, blank=True, null=True)

    # X values (0..10)
    x_caym1 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    x_caym2 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    x_caym3 = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Y counts
    y_caym1 = models.IntegerField(default=0)
    y_caym2 = models.IntegerField(default=0)
    y_caym3 = models.IntegerField(default=0)

    # Z counts
    z_caym1 = models.IntegerField(default=0)
    z_caym2 = models.IntegerField(default=0)
    z_caym3 = models.IntegerField(default=0)

    # Computed APIs
    api_1 = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # CAYm1
    api_2 = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # CAYm2
    api_3 = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # CAYm3

    average_api = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    # Marks (weight 10)
    max_marks = models.IntegerField(default=10)
    marks_awarded = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    # Workflow flags
    is_verified = models.BooleanField(default=False)
    admin_remarks = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)



# nba/models.py
from django.db import models
from user_accounts.models import Add_Department

class AcademicPerformanceSecondYear(models.Model):
    """
    Table 4.4 — Academic Performance of the Second-Year Students (weight 10).
    API_i = X_i * (Y_i / Z_i)
      X: Mean of 2nd-year GPA (10-point) OR mean%/10 of successful students
      Y: Successful students (proceeded to 3rd year)
      Z: Students appeared in the 2nd-year examination
    Average_API = (API_1 + API_2 + API_3) / 3
    """
    department = models.ForeignKey(Add_Department, on_delete=models.CASCADE, related_name="api_second_year")

    # Labels like "2023-24" for CAYm1..m3
    caym1_label = models.CharField(max_length=16, blank=True, null=True)
    caym2_label = models.CharField(max_length=16, blank=True, null=True)
    caym3_label = models.CharField(max_length=16, blank=True, null=True)

    academic_year_range = models.CharField(max_length=128, blank=True, null=True)

    # X values (0..10)
    x_caym1 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    x_caym2 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    x_caym3 = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Y counts
    y_caym1 = models.IntegerField(default=0)
    y_caym2 = models.IntegerField(default=0)
    y_caym3 = models.IntegerField(default=0)

    # Z counts
    z_caym1 = models.IntegerField(default=0)
    z_caym2 = models.IntegerField(default=0)
    z_caym3 = models.IntegerField(default=0)

    # Computed APIs
    api_1 = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # CAYm1
    api_2 = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # CAYm2
    api_3 = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # CAYm3

    average_api = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    # Marks (weight 10)
    max_marks = models.IntegerField(default=10)
    marks_awarded = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    # Workflow
    is_verified = models.BooleanField(default=False)
    admin_remarks = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

# nba/models.py
from django.db import models
from user_accounts.models import Add_Department

class AcademicPerformanceThirdYear(models.Model):
    """
    Table 4.5 — Academic Performance of the Third-Year Students (weight 10).
    API_i = X_i * (Y_i / Z_i)
      X: Mean of 3rd-year GPA of successful students (10-point) OR mean%/10
      Y: Total successful students (proceeded to 4th year)
      Z: Total students appeared in the 3rd-year examination
    Average_API = (API_1 + API_2 + API_3) / 3
    Marks awarded = Average_API (out of 10)
    """
    department = models.ForeignKey(Add_Department, on_delete=models.CASCADE, related_name="api_third_year")

    # Labels like "2023-24"
    caym1_label = models.CharField(max_length=16, blank=True, null=True)
    caym2_label = models.CharField(max_length=16, blank=True, null=True)
    caym3_label = models.CharField(max_length=16, blank=True, null=True)

    academic_year_range = models.CharField(max_length=128, blank=True, null=True)

    # X (0..10)
    x_caym1 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    x_caym2 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    x_caym3 = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Y counts
    y_caym1 = models.IntegerField(default=0)
    y_caym2 = models.IntegerField(default=0)
    y_caym3 = models.IntegerField(default=0)

    # Z counts
    z_caym1 = models.IntegerField(default=0)
    z_caym2 = models.IntegerField(default=0)
    z_caym3 = models.IntegerField(default=0)

    # Computed APIs
    api_1 = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    api_2 = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    api_3 = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    average_api = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    max_marks = models.IntegerField(default=10)
    marks_awarded = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    is_verified = models.BooleanField(default=False)
    admin_remarks = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)


# nba/models.py
from django.db import models
from user_accounts.models import Add_Department

class PlacementHigherStudiesEntrepreneurship(models.Model):
    """
    Table 4.6 — Placement, Higher Studies & Entrepreneurship.
    P_i = ((X_i + Y_i + Z_i) / FS_i) * 100
    Average_P = (P_1 + P_2 + P_3) / 3
    Points (out of 30) = 0.3 * Average_P
    """
    department = models.ForeignKey(Add_Department, on_delete=models.CASCADE, related_name="placements")

    # Labels like "2023-24" for LYG / LYGm1 / LYGm2
    lyg_label   = models.CharField(max_length=16, blank=True, null=True)
    lygm1_label = models.CharField(max_length=16, blank=True, null=True)
    lygm2_label = models.CharField(max_length=16, blank=True, null=True)

    academic_year_range = models.CharField(max_length=128, blank=True, null=True)

    # FS = total final-year students
    fs_lyg   = models.IntegerField(default=0)
    fs_lygm1 = models.IntegerField(default=0)
    fs_lygm2 = models.IntegerField(default=0)

    # X = placed, Y = higher studies, Z = entrepreneurship
    x_lyg = models.IntegerField(default=0); y_lyg = models.IntegerField(default=0); z_lyg = models.IntegerField(default=0)
    x_lygm1 = models.IntegerField(default=0); y_lygm1 = models.IntegerField(default=0); z_lygm1 = models.IntegerField(default=0)
    x_lygm2 = models.IntegerField(default=0); y_lygm2 = models.IntegerField(default=0); z_lygm2 = models.IntegerField(default=0)

    # Computed placement indices
    p_1 = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # LYG
    p_2 = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # LYGm1
    p_3 = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # LYGm2

    average_p = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    placement_points = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # 0.3 * average_p

    max_marks = models.IntegerField(default=30)
    is_verified = models.BooleanField(default=False)
    admin_remarks = models.TextField(blank=True, null=True)
    marks_awarded = models.PositiveIntegerField(default=0, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


from django.db import models
from user_accounts.models import Add_Department
from decimal import Decimal

# =========================================================
# 4.7.1 — Professional Societies / Chapters / Clubs
# =========================================================

CAY_BUCKET_CHOICES = [
    ("CAYm1", "CAYm1"),
    ("CAYm2", "CAYm2"),
    ("CAYm3", "CAYm3"),
]

LEVEL_CHOICES = [
    ("State", "State"),
    ("National", "National"),
    ("International", "International"),
]

TYPE_CHOICES = [
    ("Society", "Society"),
    ("Club", "Club"),
    ("Chapter", "Chapter"),
]

class SocietiesSubmission(models.Model):
    department = models.ForeignKey(
        Add_Department, on_delete=models.CASCADE,
        related_name="nba_471_societies_submissions",
        null=True, blank=True
    )
    academic_year_range = models.CharField(max_length=64, null=True, blank=True)

    # workflow/status
    is_verified = models.BooleanField(default=False, null=True, blank=True)
    admin_remarks = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    # marks snapshot
    max_marks = models.IntegerField(default=5, null=True, blank=True)
    marks_awarded = models.DecimalField(max_digits=6, decimal_places=2,
                                        default=Decimal("0.00"), null=True, blank=True)

    # counters snapshot (for quick display)
    state_events_count = models.IntegerField(default=0, null=True, blank=True)
    national_events_count = models.IntegerField(default=0, null=True, blank=True)
    international_events_count = models.IntegerField(default=0, null=True, blank=True)

    # per-bucket counters (optional)
    caym1_events_count = models.IntegerField(default=0, null=True, blank=True)
    caym2_events_count = models.IntegerField(default=0, null=True, blank=True)
    caym3_events_count = models.IntegerField(default=0, null=True, blank=True)

    def __str__(self):
        dep = getattr(self.department, "Department", str(self.department))
        return f"{dep} - {self.academic_year_range or 'AY'}"


class SocietyChapter(models.Model):
    submission = models.ForeignKey(
        SocietiesSubmission, on_delete=models.CASCADE,
        related_name="society_chapters", null=True, blank=True
    )
    department = models.ForeignKey(Add_Department, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=128, null=True, blank=True)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, default="Society")
    scope = models.CharField(max_length=32, choices=LEVEL_CHOICES, null=True, blank=True)  # optional descriptor
    inauguration_year = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.type})"


class SocietyEvent(models.Model):
    submission = models.ForeignKey(
        SocietiesSubmission, on_delete=models.CASCADE,
        related_name="events", null=True, blank=True
    )
    society = models.ForeignKey(
        SocietyChapter, on_delete=models.PROTECT,
        related_name="organized_events", null=True, blank=True
    )
    cay_bucket = models.CharField(max_length=8, choices=CAY_BUCKET_CHOICES, null=True, blank=True)

    # event details
    event_title = models.CharField(max_length=256, null=True, blank=True)
    body_name = models.CharField(max_length=256, null=True, blank=True)  # IEEE/ISTE/etc (optional)
    level = models.CharField(max_length=32, choices=LEVEL_CHOICES, null=True, blank=True)
    date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.event_title or 'Event'} [{self.cay_bucket or ''}]"



# =========================================================
# 4.7.2 — Student Events
# =========================================================

class StudentEventsSubmission(models.Model):
    department = models.ForeignKey(
        Add_Department,
        on_delete=models.CASCADE,
        related_name="student_event_submissions",
        null=True, blank=True
    )
    academic_year_range = models.CharField(max_length=64, null=True, blank=True)

    # workflow
    is_verified = models.BooleanField(default=False, null=True, blank=True)
    admin_remarks = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    # scoring
    max_marks = models.IntegerField(default=10)
    marks_awarded = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))

    # counters snapshot (auto by views)
    state_events_count = models.IntegerField(default=0, null=True, blank=True)
    national_events_count = models.IntegerField(default=0, null=True, blank=True)
    international_events_count = models.IntegerField(default=0, null=True, blank=True)

    caym1_count = models.IntegerField(default=0, null=True, blank=True)
    caym2_count = models.IntegerField(default=0, null=True, blank=True)
    caym3_count = models.IntegerField(default=0, null=True, blank=True)

    def __str__(self):
        return f"{self.department} - {self.academic_year_range}"


class StudentEventRow(models.Model):
    submission = models.ForeignKey(
        StudentEventsSubmission,
        on_delete=models.CASCADE,
        related_name="student_event_rows",
        null=True, blank=True
    )

    # CAY bucket
    CAY_CHOICES = (("CAYm1", "CAYm1"), ("CAYm2", "CAYm2"), ("CAYm3", "CAYm3"))
    cay_bucket = models.CharField(max_length=8, choices=CAY_CHOICES, null=True, blank=True)

    # row fields
    student = models.CharField(max_length=128, null=True, blank=True)
    event_title = models.CharField(max_length=256, null=True, blank=True)
    level = models.CharField(
        max_length=32,
        choices=(("State", "State"), ("National", "National"), ("International", "International")),
        null=True, blank=True
    )
    date = models.DateField(null=True, blank=True)
    award = models.CharField(max_length=128, null=True, blank=True)


    def __str__(self):
        return f"{self.student} – {self.event_title} ({self.cay_bucket})"    




# =========================================================
# 4.7.3 — Department Publications
# =========================================================

CAY_CHOICES = (
    ("CAYm1", "CAYm1"),
    ("CAYm2", "CAYm2"),
    ("CAYm3", "CAYm3"),
)

COPY_CHOICES = (
    ("Hard", "Hard"),
    ("Soft", "Soft"),
    ("Both", "Both"),
)

PUB_TYPE_CHOICES = (
    ("Journal", "Journal"),
    ("Magazine", "Magazine"),
    ("Newsletter", "Newsletter"),
)

class DeptPublicationsSubmission(models.Model):
    department = models.ForeignKey(
        Add_Department,
        on_delete=models.CASCADE,
        related_name="dept_publication_submissions",
        null=True, blank=True
    )
    academic_year_range = models.CharField(max_length=64, null=True, blank=True)

    # verification
    is_verified = models.BooleanField(default=False, null=True, blank=True)
    admin_remarks = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    # optional scoring snapshot (keep, even if unused)
    max_marks = models.IntegerField(default=5)
    marks_awarded = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))

    # simple counters
    caym1_count = models.IntegerField(default=0, blank=True)
    caym2_count = models.IntegerField(default=0, blank=True)
    caym3_count = models.IntegerField(default=0, blank=True)

    def __str__(self):
        dept = getattr(self.department, "Department", self.department_id)
        return f"{dept} - {self.academic_year_range or ''}"


class DeptPublicationRow(models.Model):
    submission = models.ForeignKey(
        DeptPublicationsSubmission,
        on_delete=models.CASCADE,
        related_name="dept_publication_rows",
        null=True, blank=True
    )
    cay_bucket = models.CharField(max_length=8, choices=CAY_CHOICES, null=True, blank=True)

    # Columns from the template
    title = models.CharField(max_length=256, null=True, blank=True)  # Journal/Magazine/Newsletter name
    pub_type = models.CharField(max_length=32, choices=PUB_TYPE_CHOICES, default="Newsletter", null=True, blank=True)
    editor_name = models.CharField(max_length=128, null=True, blank=True)
    student_semester = models.CharField(max_length=64, null=True, blank=True)  # "Name & Semester" or just "Semester"
    num_issues = models.IntegerField(null=True, blank=True)
    copy_type = models.CharField(max_length=16, choices=COPY_CHOICES, null=True, blank=True)  # Soft copy column
    weblink = models.URLField(null=True, blank=True)  # optional: for soft copy link



# =========================================================
# 4.7.4 — Student Publications
# =========================================================

CAY_CHOICES = (
    ("CAYm1", "CAYm1"),
    ("CAYm2", "CAYm2"),
    ("CAYm3", "CAYm3"),
)

class StudentPublicationsSubmission(models.Model):
    department = models.ForeignKey(
        Add_Department,
        on_delete=models.CASCADE,
        related_name="student_publication_submissions",
        null=True, blank=True
    )
    academic_year_range = models.CharField(max_length=64, null=True, blank=True)

    # verification snapshot
    is_verified = models.BooleanField(default=False, null=True, blank=True)
    admin_remarks = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    # optional scoring snapshot (cap at 5 as per (05) heading)
    max_marks = models.IntegerField(default=5)
    marks_awarded = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))

    # convenience counters
    caym1_count = models.IntegerField(default=0, blank=True)
    caym2_count = models.IntegerField(default=0, blank=True)
    caym3_count = models.IntegerField(default=0, blank=True)

    def __str__(self):
        dept = getattr(self.department, "Department", self.department_id)
        return f"{dept} — {self.academic_year_range or ''}"


class StudentPublicationRow(models.Model):
    submission = models.ForeignKey(
        StudentPublicationsSubmission,
        on_delete=models.CASCADE,
        related_name="rows",
        null=True, blank=True
    )
    cay_bucket = models.CharField(max_length=8, choices=CAY_CHOICES, null=True, blank=True)

    # EXACT columns from the NBA table screenshot
    student = models.CharField(max_length=256, null=True, blank=True)
    publisher_name = models.CharField(max_length=256, null=True, blank=True)
    venue_title = models.CharField(max_length=256, null=True, blank=True)   # Journal / Conference name
    volume_issue = models.CharField(max_length=128, null=True, blank=True)
    award_name = models.CharField(max_length=256, null=True, blank=True)

    # optional richer metadata (unused in UI but handy later)
    # title = models.CharField(max_length=256, null=True, blank=True)
    # authors = models.CharField(max_length=256, null=True, blank=True)
    venue_type = models.CharField(max_length=32, default="Journal", null=True, blank=True)
    # venue_or_publisher = models.CharField(max_length=256, null=True, blank=True)
    # year = models.IntegerField(null=True, blank=True)
    # link_or_doi = models.CharField(max_length=256, null=True, blank=True)
    # indexed_in = models.CharField(max_length=128, null=True, blank=True)

