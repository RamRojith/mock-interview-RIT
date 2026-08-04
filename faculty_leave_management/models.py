from django.db import models
from django.conf import settings
from django.db import transaction

from django.core.exceptions import ValidationError
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
from django.db.models import Q, F
from user_accounts.models import Department, Role, USER, Add_Department
from faculty_management.models import general_information,DesignationMaster
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from faculty_leave_management.utils import leave_allotment_update
import logging
logger = logging.getLogger(__name__)


class LeavePermissionFunction(models.Model):
    role = models.ForeignKey("user_accounts.Role", on_delete=models.DO_NOTHING,
        db_constraint=False, blank=True, null=True)
    function = models.CharField(max_length=255, blank=True, null=True)
    permission = models.BooleanField()




# ---------------------------------------
# LEAVE TYPE MODEL
# ---------------------------------------
class LeaveType(models.Model):
    RESTRICTION_CHOICES = [
        ('restricted', 'Restricted'),
        ('unrestricted', 'Not Restricted'),
    ]
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=10, unique=True)  # e.g., 'CL', 'CCL'
    is_leave = models.BooleanField(default=True)  # True for regular leaves, False for permissions
    is_active = models.BooleanField(default=True)
    # Restricted: cannot be applied once the available balance is 0 (CL/VL/CCL/ML).
    # Not Restricted: can be applied even at 0 and never shows negative remaining
    # (Loss of Pay / On Duty / Research On Duty).
    restriction = models.CharField(
        max_length=12, choices=RESTRICTION_CHOICES, default='restricted', blank=True, null=True
    )

    def __str__(self):
        return self.name

# ---------------------------------------
# LEAVE ALLOTMENT MODEL
# ---------------------------------------
class LeaveAllotment(models.Model):
    FREQUENCY_CHOICES = [
        ('yearly', 'Yearly'),
        ('monthly', 'Monthly'),
    ]
    academic_year = models.CharField(max_length=10, blank=True, null=True)
    role = models.ForeignKey("faculty_management.DesignationMaster", on_delete=models.PROTECT, blank=True, null=True)
    category = models.ForeignKey("faculty_management.FacultyCategory", on_delete=models.PROTECT, blank=True, null=True)
    start_date=models.DateField(blank=True, null=True)
    end_date=models.DateField(blank=True, null=True)
    leave_type = models.ForeignKey("LeaveType", on_delete=models.CASCADE, blank=True, null=True)
    default_allotment = models.IntegerField(default=0, blank=True, null=True)
    # Whether ``default_allotment`` is granted per year or per month. Monthly
    # allotments reset every calendar month on the leave/permission forms.
    frequency = models.CharField(
        max_length=10, choices=FREQUENCY_CHOICES, default='yearly', blank=True, null=True
    )
    active = models.BooleanField(default=True, blank=True, null=True)
    class Meta:
        unique_together = ('academic_year', 'role', 'category', 'leave_type')

    @property
    def target_name(self):
        """Human-readable target: the category (if set) else the designation/role."""
        if self.category_id:
            return self.category.category_name
        if self.role_id:
            return self.role.designation_name
        return "—"

    def __str__(self):
        return f"{self.leave_type.name} Allotment for {self.academic_year}"

# ---------------------------------------
# LEAVE BALANCE MODEL
# ---------------------------------------
class LeaveBalance(models.Model):

    faculty = models.ForeignKey("faculty_management.general_information", on_delete=models.CASCADE, blank=True, null=True)
    designation = models.ForeignKey("faculty_management.DesignationMaster", on_delete=models.CASCADE, related_name='leave_balance', blank=True, null=True)
    academic_year = models.CharField(max_length=10, blank=True, null=True)
    leave_type = models.ForeignKey("LeaveType", on_delete=models.CASCADE, blank=True, null=True)
    available = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, null=True)
    start_date=models.DateField(blank=True, null=True)
    end_date=models.DateField(blank=True, null=True)
    used = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, null=True)

    def __str__(self):
        emp = getattr(self.faculty, "faculty_id", "N/A")
        name = getattr(self.faculty, "username", "") or getattr(self.faculty, "name", "")
        lt = getattr(self.leave_type, "name", "Leave")
        return f"{emp} {name} - {self.academic_year} {lt} Balance"




# ---------------------------------------
# LEAVE APPLICATION MODEL
# ---------------------------------------



from django.db import models


class PermissionTimingMaster(models.Model):
    session_name = models.CharField(max_length=100, blank=True, null=True)
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True, blank=True, null=True)
    value = models.DecimalField(
        max_digits=3,       # total digits (e.g., 1.5, 10.5)
        decimal_places=1, blank=True, null=True    # allows 1.0, 1.5
    )

    class Meta:
        db_table = "permission_timing_master"
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.session_name} ({self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')})"


# ---------------------------------------------------------------------------
# Session-aware leave-day calculation
# ---------------------------------------------------------------------------
from datetime import time as _dt_time


def session_day_bounds(session):
    """Return the (start_fraction, end_fraction) of a single day that a session
    covers, as fractions in [0.0, 1.0].

    FN / forenoon / morning  -> first half  [0.0, 0.5]
    AN / afternoon           -> second half [0.5, 1.0]
    Full day / unknown       -> whole day   [0.0, 1.0]
    """
    if not session:
        return (0.0, 1.0)

    name = (getattr(session, "session_name", "") or "").strip().upper()
    if name in ("FN", "MORNING", "FORENOON"):
        return (0.0, 0.5)
    if name in ("AN", "AFTERNOON"):
        return (0.5, 1.0)
    if name in ("FULL DAY", "FULL", "BOTH"):
        return (0.0, 1.0)

    # Fallback: decide by start time (before noon => forenoon half).
    start_time = getattr(session, "start_time", None)
    if start_time is not None:
        return (0.0, 0.5) if start_time < _dt_time(12, 0) else (0.5, 1.0)
    return (0.0, 1.0)


def compute_leave_days(from_date, to_date, from_session, to_session):
    """Total leave days for a date range, honouring a half-day session on the
    first day (``from_session``) and the last day (``to_session``).

    Example: 06-Jul (AN) to 07-Jul (AN) -> 0.5 (afternoon of day 1) + 1.0
    (full day 2) = 1.5 days.

    Legacy records that only carry a single session (``to_session`` is None)
    keep their original whole-range behaviour: session value x calendar days.
    """
    if not from_date or not to_date or to_date < from_date:
        return 0.0

    span_days = (to_date - from_date).days + 1

    # Legacy single-session records — preserve the old multiply behaviour.
    if to_session is None:
        value = float(from_session.value) if from_session and from_session.value else 1.0
        if value <= 0:
            value = 1.0
        return span_days * value

    start_frac, _ = session_day_bounds(from_session)
    _, end_frac = session_day_bounds(to_session)

    if from_date == to_date:
        return max(0.0, end_frac - start_frac)

    first_day = 1.0 - start_frac      # remainder of the first day
    last_day = end_frac               # portion of the last day
    middle_days = span_days - 2       # full days in between
    return first_day + middle_days + last_day


def leave_day_fraction(day, from_date, to_date, from_session, to_session):
    """Fraction (0.0/0.5/1.0) of a single ``day`` covered by a leave, honouring
    the boundary sessions. Used by attendance reports that iterate day by day."""
    if not from_date or not to_date or day < from_date or day > to_date:
        return 0.0

    if to_session is None:
        value = float(from_session.value) if from_session and from_session.value else 1.0
        if value <= 0:
            value = 1.0
        return min(1.0, value)

    start_frac, _ = session_day_bounds(from_session)
    _, end_frac = session_day_bounds(to_session)

    if from_date == to_date:
        return max(0.0, end_frac - start_frac)
    if day == from_date:
        return 1.0 - start_frac
    if day == to_date:
        return end_frac
    return 1.0


class LeaveApplication(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Pre-approved', 'Pre-approved'),
    ]

    user = models.ForeignKey(
       "user_accounts.USER",
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        blank=True,
        null=True,
    )
    faculty = models.ForeignKey(
        "faculty_management.general_information",
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    designation = models.ForeignKey(  # role_id to designation
        "faculty_management.DesignationMaster",
        on_delete=models.CASCADE,
        related_name='leave_application',
        blank=True,
        null=True
    )
    academic_year = models.CharField(max_length=10, blank=True, null=True)
    from_date = models.DateField(blank=True, null=True)
    to_date = models.DateField(blank=True, null=True)
    # Time window — used by "permission" type applications (is_leave=False),
    # applied on the dedicated Permission page with a date range plus a
    # from-time / to-time. Null for regular leaves.
    from_time = models.TimeField(blank=True, null=True)
    to_time = models.TimeField(blank=True, null=True)
    leave_type = models.ForeignKey("LeaveType", on_delete=models.CASCADE, blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending', blank=True, null=True
    )
    requested_date = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    session = models.ForeignKey(
    PermissionTimingMaster,
    on_delete=models.SET_NULL,
    null=True,
    blank=True
        )
    # Session on the last day of the range. Together with ``session`` (the first
    # day's session) this allows half-day starts/ends, e.g. AN -> AN = 1.5 days.
    to_session = models.ForeignKey(
        PermissionTimingMaster,
        on_delete=models.SET_NULL,
        related_name="leave_application_to_session",
        null=True,
        blank=True,
    )
    # Supporting PDF proof — required for On Duty / Research On Duty applications.
    proof_file = models.FileField(
        upload_to="faculty_leave_od_proofs/",
        null=True,
        blank=True,
    )
    class Meta:
        ordering = ['-requested_date']
        verbose_name = "Leave Application"
        verbose_name_plural = "Leave Applications"

    def __str__(self):
        emp = getattr(self.faculty, "faculty_id", "N/A")
        uname = getattr(self.faculty, "username", "") or getattr(self.faculty, "name", "")
        lt = getattr(self.leave_type, "name", "Leave")
        return f"{emp} {uname} - {lt} ({self.from_date} to {self.to_date})"

    @property
    def days(self):
        return compute_leave_days(
            self.from_date, self.to_date, self.session, self.to_session
        )




# ---------------------------------------
# PERMISSION REQUEST MODEL
# ---------------------------------------
class PermissionRequest(models.Model):
    user = models.ForeignKey("user_accounts.USER",  on_delete=models.DO_NOTHING,
        db_constraint=False, blank=True, null=True)
    faculty = models.ForeignKey("faculty_management.general_information", on_delete=models.CASCADE, related_name='permission_request', blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    from_time = models.TimeField(blank=True, null=True)
    to_time = models.TimeField(blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=[
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected')
    ], default='Pending', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} Permission on {self.date}"

# ---------------------------------------
# ALTERATION MODEL (FOR CLASS SWAPS)
# ---------------------------------------
class Alteration(models.Model):
    leave_application = models.ForeignKey("LeaveApplication", on_delete=models.CASCADE, blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    class_name = models.CharField(max_length=50, blank=True, null=True)
    hour = models.IntegerField(blank=True, null=True)
    faculty_altered_to = models.ForeignKey("faculty_management.general_information",on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return f"Alteration for {self.leave_application.user.name} on {self.date}"

# ---------------------------------------
# SIGNALS TO UPDATE LEAVE BALANCE
# ---------------------------------------




# class LeaveApprovers(models.Model):
#     class DefaultApprover(models.TextChoices):
#         YES = "YES", "Yes"
#         NO = "NO", "No"

#     creator_role = models.ForeignKey(
#         "user_accounts.Role",
#         on_delete=models.DO_NOTHING,
#         db_constraint=False,
#         related_name="leave_creator",
#         blank=True,
#         null=True
#     )

#     approver_role = models.ForeignKey(
#         "user_accounts.Role",
#         on_delete=models.DO_NOTHING,
#         db_constraint=False,
#         related_name="leave_approvers_role",
#         blank=True,
#         null=True
#     )

#     approver_level = models.PositiveIntegerField()

#     is_cross_department_approver = models.CharField(
#         max_length=3,
#         choices=DefaultApprover.choices,
#         default=DefaultApprover.NO,
#         blank=True,
#         null=True
#     )

#     approver_department = models.ForeignKey(
#         "user_accounts.Department",
#         db_constraint=False,
#         on_delete=models.DO_NOTHING,
#         blank=True,
#         null=True,
#     )

#     def __str__(self):
#         creator = self.creator_role.role_name if self.creator_role else "Unknown"
#         approver = self.approver_role.role_name if self.approver_role else "Unknown"
#         return f"Approver Level {self.approver_level}: {approver} for {creator}"


# class LeaveApproversData(models.Model):
#     class Status(models.TextChoices):
#         APPROVED = "APPROVED", "Approved"
#         PENDING = "PENDING", "Pending"
#         REJECTED = "REJECTED", "Rejected"

#     leave_application = models.ForeignKey(
#         "LeaveApplication",
#         on_delete=models.CASCADE,
#         related_name="leave_application_details",
#         blank=True,
#         null=True
#     )

#     approver_id = models.ForeignKey(
#         "user_accounts.USER",
#         on_delete=models.DO_NOTHING,
#         db_constraint=False,
#         blank=True,
#         null=True,
#         related_name="leave_approver_entries"
#     )

#     creator_id = models.ForeignKey(
#         "user_accounts.USER",
#         on_delete=models.DO_NOTHING,
#         db_constraint=False,
#         blank=True,
#         null=True,
#         related_name="leave_creator_entries"
#     )

#     reason = models.CharField(max_length=225, null=True, blank=True)

#     status = models.CharField(
#         max_length=16,
#         choices=Status.choices,
#         default=Status.PENDING,
#         blank=True,
#         null=True
#     )

#     approver_level = models.PositiveIntegerField(blank=True, null=True)
#     approved_date = models.DateTimeField(default=timezone.now, blank=True, null=True)

#     def __str__(self):
#         approver = self.approver_id.username if self.approver_id else "N/A"
#         leave_id = self.leave_application.id if self.leave_application else "N/A"
#         return f"Leave #{leave_id} - {approver} ({self.status})"


class LeaveApprovers(models.Model):

    class DefaultApprover(models.TextChoices):
        YES = "YES", "Yes"
        NO = "NO", "No"

    creator_role_id = models.IntegerField(null=True, blank=True)
    approver_role_id = models.IntegerField(null=True, blank=True)

    approver_level = models.PositiveIntegerField()

    is_cross_department_approver = models.CharField(
        max_length=3,
        choices=DefaultApprover.choices,
        default=DefaultApprover.NO,
        blank=True,
        null=True
    )

    approver_department = models.ForeignKey(
        Add_Department,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )

    def __str__(self):
        return f"Approver Level {self.approver_level} (Creator ID: {self.creator_role_id})"


class LeaveApproversData(models.Model):
    class Status(models.TextChoices):
        APPROVED = "APPROVED", "Approved"
        PENDING = "PENDING", "Pending"
        REJECTED = "REJECTED", "Rejected"

    leave_application = models.ForeignKey(
        "LeaveApplication",
        on_delete=models.CASCADE,
        related_name="leave_application_details",
        blank=True,
        null=True
    )

    approver_id = models.ForeignKey(
        general_information,
       on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="leave_approver_entries"
    )

    creator_id = models.ForeignKey(
        general_information,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="leave_creator_entries"
    )

    # Roles captured from the approval hierarchy at chain-creation time:
    # the role this approver acts as, and the applicant's (creator's) role.
    approver_role_id = models.IntegerField(blank=True, null=True)
    creator_role_id = models.IntegerField(blank=True, null=True)

    reason = models.CharField(max_length=225, null=True, blank=True)

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        blank=True,
        null=True
    )

    approver_level = models.PositiveIntegerField(blank=True, null=True)
    approved_date = models.DateTimeField(default=timezone.now, blank=True, null=True)

    def __str__(self):
        approver = getattr(self.approver_id, "name", None) or getattr(self.approver_id, "username", None) or "N/A"
        leave_id = self.leave_application.id if self.leave_application else "N/A"
        return f"Leave #{leave_id} - {approver} ({self.status})"



from django.db import models


class DeviceLog(models.Model):
    devicelogid = models.BigIntegerField(db_column='DeviceLogId', primary_key=True)
    deviceid = models.IntegerField(db_column='DeviceId', null=True, blank=True)
    userid = models.IntegerField(db_column='UserId', null=True, blank=True)
    logdate = models.DateTimeField(db_column='LogDate', null=True, blank=True)
    direction = models.CharField(db_column='Direction', max_length=50, null=True, blank=True)

    class Meta:
        managed = False


class DeviceLogLocal(models.Model):
    """Local MySQL mirror of DeviceLog records synced from MSSQL attendance_db."""
    devicelogid = models.BigIntegerField(null=True, blank=True)
    deviceid = models.IntegerField(null=True, blank=True)
    userid = models.IntegerField(null=True, blank=True)
    logdate = models.DateTimeField(null=True, blank=True)
    direction = models.CharField(max_length=50, null=True, blank=True)
    synced_at = models.DateTimeField(auto_now_add=True)
    month = models.CharField(max_length=50, null=True, blank=True)
    year = models.CharField(max_length=50, null=True, blank=True)




class DeviceInfo(models.Model):
    deviceid = models.CharField(max_length=255, null=True, blank=True)
    devicelocation = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_attendance = models.BooleanField(default=False)
    is_mess = models.BooleanField(default=False)




class ShiftMaster(models.Model):
    shift_name = models.CharField(max_length=150)
    no_of_shifts = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.shift_name} ({self.no_of_shifts} Shift(s))"


class ShiftDetail(models.Model):
    shift_master = models.ForeignKey(
        ShiftMaster,
        on_delete=models.CASCADE,
        related_name="shift_details"
    )
    shift_no = models.PositiveIntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_next_day = models.BooleanField(default=False)

    class Meta:
        ordering = ["shift_no"]

    def __str__(self):
        return f"{self.shift_master.shift_name} - Shift {self.shift_no}"





class AttendancePolicy(models.Model):
    PUNCH_MODE_CHOICES = [
        ("FIRST_LAST", "First punch in / last punch out"),
        ("PAIR", "Pair punches"),
    ]
    ODD_PUNCH_CHOICES = [
        ("MISSING_OUT", "Mark as Missing OUT"),
        ("IGNORE_LAST", "Ignore last open punch"),
    ]

    policy_name = models.CharField(max_length=150, unique=True)
    punch_mode = models.CharField(max_length=20, choices=PUNCH_MODE_CHOICES, default="FIRST_LAST")
    minimum_punches_required = models.PositiveSmallIntegerField(default=2)
    minimum_working_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    late_early_check = models.BooleanField(default=True)
    shift_required = models.BooleanField(default=True)
    odd_punch_handling = models.CharField(max_length=20, choices=ODD_PUNCH_CHOICES, default="MISSING_OUT")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["policy_name"]

    def __str__(self):
        return self.policy_name


class AttendancePolicyAssignment(models.Model):
    policy = models.ForeignKey(
        AttendancePolicy,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    employee = models.ForeignKey(
        "faculty_management.general_information",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="attendance_policy_assignments",
    )
    designation = models.ForeignKey(
        "faculty_management.DesignationMaster",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="attendance_policy_assignments",
    )
    category = models.ForeignKey(
        "faculty_management.FacultyCategory",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="attendance_policy_assignments",
    )
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    notes = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "employee_id", "designation_id", "category_id"]

    def clean(self):
        selected = [
            bool(self.employee_id),
            bool(self.designation_id),
            bool(self.category_id),
            bool(self.is_default),
        ]
        if sum(selected) != 1:
            raise ValidationError("Choose exactly one assignment scope.")

    @property
    def scope_label(self):
        if self.employee_id:
            emp_id = getattr(self.employee, "faculty_id", "")
            emp_name = getattr(self.employee, "name", "") or ""
            return f"Employee: {emp_id} {emp_name}".strip()
        if self.designation_id:
            return f"Designation: {self.designation}"
        if self.category_id:
            return f"Category: {self.category}"
        return "Default"

    def __str__(self):
        return f"{self.scope_label} -> {self.policy.policy_name}"

from django.db import models


# class PermissionTimingMaster(models.Model):
#     session_name = models.CharField(max_length=100)
#     start_time = models.TimeField()
#     end_time = models.TimeField()
#     is_active = models.BooleanField(default=True)

#     class Meta:
#         db_table = "permission_timing_master"
#         ordering = ["start_time"]

#     def __str__(self):
#         return f"{self.session_name} ({self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')})"


class Employee_Holidays(models.Model):
    SESSION_CHOICES = [
        ("F", "Full Day"),
        ("FN", "Forenoon"),
        ("AN", "Afternoon"),
    ]

    holiday_date = models.DateField()
    role_id = models.IntegerField()
    category = models.ForeignKey(
        "faculty_management.FacultyCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="holiday_by_role_entries",
    )
    session_type = models.CharField(max_length=5, choices=SESSION_CHOICES, default="F")
    reason = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        category_name = self.category.category_name if self.category else "All Categories"
        return f"{self.holiday_date} - {self.role_id} - {category_name} - {self.session_type}"


class CCL_Application(models.Model):

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),

    ]
    user = models.ForeignKey(
       "user_accounts.USER",
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        blank=True,
        null=True,
    )
    faculty = models.ForeignKey(
        "faculty_management.general_information",
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    designation = models.ForeignKey(  # role_id to designation
        "faculty_management.DesignationMaster",
        on_delete=models.CASCADE,
        related_name='ccl_application',
        blank=True,
        null=True
    )
    academic_year = models.CharField(max_length=10, blank=True, null=True)
    date = models.DateField(blank=True, null=True)

    reason = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending', blank=True, null=True
    )
    requested_date = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    days = models.DecimalField(max_digits=4, decimal_places=1, default=1)
    from_time = models.TimeField(blank=True, null=True)
    to_time = models.TimeField(blank=True, null=True)
    worked_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    session = models.CharField(max_length=20, blank=True, null=True)
    is_claimed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-requested_date']
        verbose_name = "CCL Application"
        verbose_name_plural = "CCL Applications"
        indexes = [
            models.Index(fields=["faculty", "status"], name="ccl_app_faculty_status_idx"),
            models.Index(fields=["faculty", "date"], name="ccl_app_faculty_date_idx"),
            models.Index(fields=["faculty", "academic_year"], name="ccl_app_faculty_ay_idx"),
        ]

    def __str__(self):
        emp = getattr(self.faculty, "faculty_id", "N/A")
        uname = getattr(self.faculty, "username", "") or getattr(self.faculty, "name", "")
        return f"{emp} {uname} - CCL ({self.date})"


class CCLTimingMaster(models.Model):
    session_name = models.CharField(max_length=100)
    min_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    max_hours = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    ccl_days = models.DecimalField(max_digits=3, decimal_places=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["min_hours", "max_hours", "session_name"]
        verbose_name = "CCL Timing Master"
        verbose_name_plural = "CCL Timing Masters"

    def __str__(self):
        max_label = self.max_hours if self.max_hours is not None else "above"
        return f"{self.session_name}: > {self.min_hours} to {max_label} hours = {self.ccl_days} day(s)"


class CCL_Approvers_Data(models.Model):
    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        APPROVED = "Approved", "Approved"
        REJECTED = "Rejected", "Rejected"

    ccl_application = models.ForeignKey(
        "faculty_leave_management.CCL_Application",
        on_delete=models.CASCADE,
        related_name="approver_rows"
    )
    approver_id = models.ForeignKey(
        "faculty_management.general_information",
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    approver_level = models.PositiveIntegerField(default=1)
    # Roles captured from the approval hierarchy at chain-creation time:
    # the role this approver acts as, and the applicant's (creator's) role.
    approver_role_id = models.IntegerField(blank=True, null=True)
    creator_role_id = models.IntegerField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    action_date = models.DateTimeField(blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ["approver_level", "id"]
        indexes = [
            models.Index(fields=["approver_id", "status"], name="ccl_appr_approver_status_idx"),
            models.Index(fields=["ccl_application", "approver_level"], name="ccl_appr_app_level_idx"),
        ]

    def __str__(self):
        return f"CCL {self.ccl_application_id} - Level {self.approver_level} - {self.status}"



from django.core.exceptions import ValidationError
from django.db import models

class CCL_Claim(models.Model):

    faculty = models.ForeignKey(
        "faculty_management.general_information",
        on_delete=models.CASCADE,
        related_name="ccl_balances", blank=True,
        null=True
    )

    designation = models.ForeignKey(
        "faculty_management.DesignationMaster",
        on_delete=models.CASCADE,
        related_name="ccl_claims",
        blank=True,
        null=True
    )


    academic_year = models.CharField(max_length=9, blank=True,
        null=True)  # e.g., 2024-2025

    claimed = models.DecimalField(max_digits=5, decimal_places=1, default=0)   # current academic year claimed
    used = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    total_claimed = models.DecimalField(max_digits=6, decimal_places=1, default=0)  # cumulative across all years

    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)


    def clean(self):
        if self.used > self.claimed:
            raise ValidationError("Used CCL cannot exceed claimed CCL.")

        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValidationError("Start date cannot be after end date.")

    @property
    def remaining(self):
        return self.claimed - self.used

    def __str__(self):
        faculty_name = getattr(self.faculty, "name", "Unknown")
        faculty_id = getattr(self.faculty, "faculty_id", "N/A")

        return f"{faculty_id} - {faculty_name} ({self.academic_year}) [CCL]"



from django.db import models

class MessDetails(models.Model):
    """Mess timing + pricing entries (e.g. Breakfast 07:00-09:00, Rs. 40)."""
    name = models.CharField(max_length=100, blank=True, null=True)
    from_time = models.TimeField(blank=True, null=True)
    to_time = models.TimeField(blank=True, null=True)
    rupees = models.DecimalField(max_digits=8, decimal_places=2, default=0, blank=True, null=True)
    academic_year = models.CharField(max_length=10, blank=True, null=True)
    is_active = models.BooleanField(default=True, blank=True, null=True)

    class Meta:
        db_table = "messdetails"
        ordering = ["from_time"]
        verbose_name = "Mess Detail"
        verbose_name_plural = "Mess Details"

    def __str__(self):
        return f"{self.name} ({self.from_time} - {self.to_time}) - Rs.{self.rupees}"


class Faculty_Leave_Page_Permission(models.Model):
 
    user_id = models.IntegerField(unique=True, blank=True, null=True)

    is_hidden = models.BooleanField(default=True, blank=True, null=True)

    class Meta:
        verbose_name = "Faculty Leave Page Permission"
        verbose_name_plural = "Faculty Leave Page Permissions"

    def __str__(self):
        return f"Leave Page Permission (User ID: {self.user_id})"



