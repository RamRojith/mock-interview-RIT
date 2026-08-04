from django.db import models
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from user_accounts.models import Role
from faculty_management.models import general_information
from user_accounts.models import Add_Department , StudentDetails


# #  Create your models here.
class Data_Center_Permission(models.Model):
    role = models.ForeignKey(
        "user_accounts.Role",       
        on_delete=models.DO_NOTHING, 
        db_constraint=False, null=True, blank=True         
    )
    function = models.CharField(max_length=500, null=True, blank=True)
    permission = models.BooleanField(null=True, blank=True)

from django.db import models


class DataCenterRequest(models.Model):
    DEVICE_TYPE_CHOICES = (
        ("LAPTOP", "Laptop"),
        ("MOBILE", "Mobile"),
    )

    creator_role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="data_center_requests",
        db_constraint=False
    )

    student = models.ForeignKey(
        StudentDetails,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="data_center_requests"
    )

    faculty = models.ForeignKey(
        general_information,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="data_center_requests"
    )

    admission_mode = models.CharField(max_length=100, null=True, blank=True)

    # hostel details
    cluster = models.CharField(max_length=100, null=True, blank=True)
    room_no = models.CharField(max_length=50, null=True, blank=True)

    # device/network
    ethernet_cable_required = models.BooleanField(default=False , null=True, blank=True)
    ethernet_mac_address = models.CharField(max_length=100, null=True, blank=True)
    device_type = models.CharField(
        max_length=20,
        choices=DEVICE_TYPE_CHOICES,
        null=True,
        blank=True
    )
    device_mac_address = models.CharField(max_length=100, null=True, blank=True)

    wifi_for_mobile_required = models.BooleanField(default=False, null=True, blank=True)
    mobile_no = models.CharField(max_length=20, null=True, blank=True)
    mobile_static_mac_address = models.CharField(max_length=100, null=True, blank=True)

    # event
    is_for_event = models.BooleanField(default=False, null=True, blank=True)
    purpose = models.TextField(null=True, blank=True)
    event_name = models.CharField(max_length=255, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    time_period = models.CharField(max_length=255, null=True, blank=True)

    # agreement
    agreement = models.BooleanField(default=False , null=True, blank=True)

    status = models.CharField(max_length=30, default="PENDING", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
 
 



class DataCenterRequestApprovers(models.Model):
    """
    Defines APPROVAL ROUTE for DataCenterRequest based on creator role.
    """
    class DefaultApprover(models.TextChoices):
        YES = "YES", "Yes"
        NO = "NO", "No"

    creator_role = models.ForeignKey(
        "user_accounts.Role",
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        related_name="data_center_request_creator",
        blank=True,
        null=True
    )

    approver_role = models.ForeignKey(
        "user_accounts.Role",
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        related_name="data_center_request_approver_role",
        blank=True,
        null=True
    )

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
        null=True
    )

    class Meta:
        db_table = "data_center_request_approvers"
        ordering = ["creator_role_id", "approver_level"]

    def _role_name(self, role_id):
        # Role lives in the external "rit_approval_system" DB. Resolve the name
        # there explicitly so stringifying this row never queries the (missing)
        # control_room_role table on the default database.
        if not role_id:
            return "Unknown"
        try:
            name = (
                Role.objects.using("rit_approval_system")
                .filter(id=role_id)
                .values_list("role", flat=True)
                .first()
            )
            return name or f"Role#{role_id}"
        except Exception:
            return f"Role#{role_id}"

    def __str__(self):
        return (
            f"[Data Center] Level {self.approver_level}: "
            f"{self._role_name(self.approver_role_id)} for {self._role_name(self.creator_role_id)}"
        )


class DataCenterRequestApproversData(models.Model):
    
    class Status(models.TextChoices):
        APPROVED = "APPROVED", "Approved"
        PENDING = "PENDING", "Pending"
        REJECTED = "REJECTED", "Rejected"

    request = models.ForeignKey(
        DataCenterRequest,
        on_delete=models.CASCADE,
        related_name="approval_entries",
        null=True,
        blank=True
    )

    approver = models.ForeignKey(
        general_information,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="data_center_request_approver_entries"
    )

    creator = models.ForeignKey(
        general_information,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_constraint=False,
        related_name="data_center_request_creator_entries"
    )

    # ✅ OPTIONAL (GOOD PRACTICE)
    approver_role = models.ForeignKey(
        Role,
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        related_name="data_center_request_approver_role_entries",
        db_constraint=False
    )

    creator_role = models.ForeignKey(
        Role,
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        related_name="data_center_request_creator_role_entries",
        db_constraint=False
    )

    reason = models.CharField(max_length=225, null=True, blank=True)

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING
    )

    approver_level = models.PositiveIntegerField(null=True, blank=True)

    acted_on = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"[Req #{self.request.id}] {self.status}"
    
    
from django.db import models
from django.utils import timezone
from django.core.validators import MinLengthValidator

# existing imports...
# from user_accounts.models import Role
# from student_management.models import StudentDetails
# from faculty_management.models import general_information


class WifiCredential(models.Model):
    request = models.ForeignKey(
        DataCenterRequest,
        on_delete=models.CASCADE,
        related_name="wifi_credential",
        null=True,
        blank=True
    )
    wifi_user_id = models.CharField(max_length=150, null=True, blank=True)
    wifi_password = models.CharField(max_length=150, null=True, blank=True)

    sent_to_user = models.BooleanField(default=False, null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    created_by_name = models.CharField(max_length=150, null=True, blank=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"WifiCredential(Request #{self.request_id})"  
    
    
    
    
from django.db import models
from django.utils import timezone

from student_management.models import StudentDetails
from faculty_management.models import general_information


class NetworkQuery(models.Model):
    class UserType(models.TextChoices):
        STUDENT = "student", "Student"
        FACULTY = "faculty", "Faculty"

    class StudentType(models.TextChoices):
        HOSTEL = "hostel", "Hostel"
        DAYSCHOLAR = "dayscholar", "Day Scholar"

    class ConnectionType(models.TextChoices):
        WIFI = "wifi", "WiFi"
        ETHERNET = "ethernet", "Ethernet"
        LAN = "lan", "LAN"
        OTHER = "other", "Other"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"
        REJECTED = "rejected", "Rejected"

    class QueryType(models.TextChoices):
        HOSTEL_WIFI_SLOW = "hostel_wifi_slow", "Hostel WiFi Slow Speed"
        HOSTEL_WIFI_DISCONNECTION = "hostel_wifi_disconnection", "Hostel WiFi Frequent Disconnections"
        HOSTEL_WIFI_NO_ACCESS = "hostel_wifi_no_access", "Cannot Connect to Hostel WiFi"
        HOSTEL_ETHERNET_NOT_WORKING = "hostel_ethernet_not_working", "Hostel Ethernet Cable Not Working"
        HOSTEL_ETHERNET_SLOW = "hostel_ethernet_slow", "Hostel Ethernet Slow Speed"
        HOSTEL_OTHERS = "hostel_others", "Other Hostel Network Issue"

        DAYSCHOLAR_CAMPUS_WIFI_SLOW = "dayscholar_campus_wifi_slow", "Campus WiFi Slow Speed"
        DAYSCHOLAR_CAMPUS_WIFI_DISCONNECTION = "dayscholar_campus_wifi_disconnection", "Campus WiFi Frequent Disconnections"
        DAYSCHOLAR_CAMPUS_WIFI_NO_ACCESS = "dayscholar_campus_wifi_no_access", "Cannot Connect to Campus WiFi"
        DAYSCHOLAR_LAB_NETWORK_ISSUES = "dayscholar_lab_network_issues", "Lab Network Problems"
        DAYSCHOLAR_LIBRARY_WIFI_ISSUES = "dayscholar_library_wifi_issues", "Library WiFi Issues"
        DAYSCHOLAR_OTHERS = "dayscholar_others", "Other Student Network Issue"

        FACULTY_WIFI_SLOW = "faculty_wifi_slow", "Faculty WiFi Slow Speed"
        FACULTY_WIFI_DISCONNECTION = "faculty_wifi_disconnection", "Faculty WiFi Frequent Disconnections"
        FACULTY_WIFI_NO_ACCESS = "faculty_wifi_no_access", "Cannot Connect to Faculty WiFi"
        FACULTY_LAN_ISSUE = "faculty_lan_issue", "Faculty LAN / Ethernet Issue"
        FACULTY_LAB_NETWORK_ISSUE = "faculty_lab_network_issue", "Faculty Lab / Department Network Issue"
        FACULTY_OTHERS = "faculty_others", "Other Faculty Network Issue"

    query_id = models.CharField(max_length=30, unique=True, blank=True)
    creator_role_id = models.IntegerField(null=True, blank=True)

    student = models.ForeignKey(
        StudentDetails,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="network_queries",
    )
    faculty = models.ForeignKey(
        general_information,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="network_queries",
    )

    user_type = models.CharField(max_length=20, choices=UserType.choices)
    student_type = models.CharField(
        max_length=20,
        choices=StudentType.choices,
        null=True,
        blank=True,
    )

    query_type = models.CharField(max_length=60, choices=QueryType.choices)
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )

    subject = models.CharField(max_length=255)
    description = models.TextField()

    device_type = models.CharField(max_length=50, default="mobile")
    location_details = models.CharField(max_length=255, default="Not specified")
    connection_type = models.CharField(
        max_length=20,
        choices=ConnectionType.choices,
        default=ConnectionType.WIFI,
    )

    # workflow
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    assigned_approver = models.ForeignKey(
        general_information,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_query_approvals",
    )
    approver_remarks = models.TextField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    # solving stage
    solved_by = models.ForeignKey(
        general_information,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solved_network_queries",
    )
    solved_at = models.DateTimeField(null=True, blank=True)
    solution_notes = models.TextField(null=True, blank=True)

    # closing stage
    closed_by = models.ForeignKey(
        general_information,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="closed_network_queries",
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    closing_notes = models.TextField(null=True, blank=True)

    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.query_id} - {self.subject}"

    def save(self, *args, **kwargs):
        if not self.query_id:
            today = timezone.localdate()
            prefix = f"NQ{today.strftime('%Y%m%d')}"
            last_query = (
                NetworkQuery.objects.filter(query_id__startswith=prefix)
                .order_by("-id")
                .first()
            )
            if last_query and last_query.query_id[-4:].isdigit():
                next_number = int(last_query.query_id[-4:]) + 1
            else:
                next_number = 1
            self.query_id = f"{prefix}{next_number:04d}"

        super().save(*args, **kwargs)
        
        
        
        
        
class GuestWifiRequest(models.Model):
    class VisitPurpose(models.TextChoices):
        OFFICIAL = "OFFICIAL", "Official"
        MEETING = "MEETING", "Meeting"
        EVENT = "EVENT", "Event"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    creator_role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guest_wifi_requests",
        db_constraint=False,
    )

    faculty = models.ForeignKey(
        general_information,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="guest_wifi_requests",
    )

    guest_name = models.CharField(max_length=255, null=True, blank=True)
    guest_mobile_no = models.CharField(max_length=20, null=True, blank=True)
    guest_email = models.EmailField(null=True, blank=True)
    guest_organization = models.CharField(max_length=255, null=True, blank=True)

    purpose_of_visit = models.CharField(
        max_length=20,
        choices=VisitPurpose.choices,
        null=True,
        blank=True,
    )
    reason = models.TextField(null=True, blank=True)
    visit_date = models.DateField(null=True, blank=True)
    access_from = models.DateTimeField(null=True, blank=True)
    access_to = models.DateTimeField(null=True, blank=True)

    device_type = models.CharField(max_length=100, null=True, blank=True)
    device_mac_address = models.CharField(max_length=100, null=True, blank=True)
    mobile_static_mac_address = models.CharField(max_length=100, null=True, blank=True)

    agreement = models.BooleanField(default=False, null=True, blank=True)

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.guest_name or 'Guest'} - {self.status}"
    
    
class GuestWifiRequestApproversData(models.Model):
    class Status(models.TextChoices):
        APPROVED = "APPROVED", "Approved"
        PENDING = "PENDING", "Pending"
        REJECTED = "REJECTED", "Rejected"

    request = models.ForeignKey(
        GuestWifiRequest,
        on_delete=models.CASCADE,
        related_name="approval_entries",
        null=True,
        blank=True
    )

    approver = models.ForeignKey(
        general_information,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="guest_wifi_request_approver_entries"
    )

    creator = models.ForeignKey(
        general_information,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_constraint=False,
        related_name="guest_wifi_request_creator_entries"
    )

    # IMPORTANT: use IntegerField, not ForeignKey(Role)
    approver_role_id = models.IntegerField(null=True, blank=True)
    creator_role_id = models.IntegerField(null=True, blank=True)

    reason = models.CharField(max_length=225, null=True, blank=True)

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING
    )

    approver_level = models.PositiveIntegerField(null=True, blank=True)
    acted_on = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["request_id", "approver_level", "id"]

    def __str__(self):
        req_id = self.request.id if self.request else "-"
        return f"[Guest Req #{req_id}] {self.status}"
   
   
from django.db import models
from django.utils import timezone

from student_management.models import StudentDetails
from faculty_management.models import general_information
from user_accounts.models import Role





from django.db import models
from django.utils import timezone

from student_management.models import StudentDetails


class SystemSupportRequest(models.Model):
    class UserType(models.TextChoices):
        STUDENT = "student", "Student"
        FACULTY = "faculty", "Faculty"

    class IssueType(models.TextChoices):
        EMAIL_FORGOT_PASSWORD = "email_forgot_password", "College Email - Forgot Password"
        EMAIL_ACCOUNT_LOCKED = "email_account_locked", "College Email - Account Locked"
        EMAIL_QUOTA_EXCEEDED = "email_quota_exceeded", "College Email - Storage Quota Exceeded"
        SYSTEM_FORGOT_PASSWORD = "system_forgot_password", "System Login - Forgot Password"
        SYSTEM_ACCOUNT_LOCKED = "system_account_locked", "System Login - Account Locked"
        SYSTEM_QUOTA_EXCEEDED = "system_quota_exceeded", "System Login - Storage Quota Exceeded"

    class PreferredContactMethod(models.TextChoices):
        EMAIL = "email", "Email"
        PHONE = "phone", "Phone"
        IN_PERSON = "in_person", "In Person"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"
        REJECTED = "rejected", "Rejected"

    application_id = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        db_index=True,
    )

    creator_role_id = models.BigIntegerField(null=True, blank=True)
    creator_role_name = models.CharField(max_length=150, null=True, blank=True, default="")

    created_by_user_id = models.BigIntegerField(null=True, blank=True)
    created_by_user_name = models.CharField(max_length=150, null=True, blank=True, default="")

    student = models.ForeignKey(
        StudentDetails,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="system_support_requests",
    )

    faculty_id = models.BigIntegerField(null=True, blank=True)
    faculty_name = models.CharField(max_length=150, null=True, blank=True, default="")
    faculty_email = models.EmailField(null=True, blank=True, default="")
    faculty_department = models.CharField(max_length=150, null=True, blank=True, default="")
    faculty_designation = models.CharField(max_length=150, null=True, blank=True, default="")

    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
    )

    issue_type = models.CharField(
        max_length=50,
        choices=IssueType.choices,
    )

    subject = models.CharField(
        max_length=255,
        default="System Support Request",
    )

    description = models.TextField()

    preferred_contact_method = models.CharField(
        max_length=20,
        choices=PreferredContactMethod.choices,
        default=PreferredContactMethod.EMAIL,
    )

    mobile_number = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    approver_remarks = models.TextField(blank=True, default="")
    rejection_reason = models.TextField(blank=True, default="")
    resolution_notes = models.TextField(blank=True, default="")
    closing_notes = models.TextField(blank=True, default="")

    assigned_approver_id = models.BigIntegerField(null=True, blank=True)
    assigned_approver_name = models.CharField(max_length=150, null=True, blank=True, default="")
    assigned_approver_email = models.EmailField(null=True, blank=True, default="")

    solved_by_id = models.BigIntegerField(null=True, blank=True)
    solved_by_name = models.CharField(max_length=150, null=True, blank=True, default="")
    solved_by_email = models.EmailField(null=True, blank=True, default="")

    closed_by_id = models.BigIntegerField(null=True, blank=True)
    closed_by_name = models.CharField(max_length=150, null=True, blank=True, default="")
    closed_by_email = models.EmailField(null=True, blank=True, default="")

    submitted_at = models.DateTimeField(default=timezone.now)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    solved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "system_support_request"
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.application_id or 'NEW'} - {self.subject}"

    @property
    def applicant_name(self):
        if self.user_type == self.UserType.STUDENT and self.student:
            return getattr(self.student, "name", "-")
        if self.user_type == self.UserType.FACULTY:
            return self.faculty_name or "-"
        return "-"

    @property
    def applicant_email(self):
        if self.user_type == self.UserType.STUDENT and self.student:
            return getattr(self.student, "email", "-")
        if self.user_type == self.UserType.FACULTY:
            return self.faculty_email or "-"
        return "-"

    def save(self, *args, **kwargs):
        if not self.application_id:
            today = timezone.localdate()
            prefix = f"SSR{today.strftime('%Y%m%d')}"
            last_obj = (
                SystemSupportRequest.objects
                .filter(application_id__startswith=prefix)
                .order_by("-application_id")
                .first()
            )

            if last_obj and last_obj.application_id:
                try:
                    last_number = int(last_obj.application_id.split("-")[-1])
                except (ValueError, IndexError):
                    last_number = 0
            else:
                last_number = 0

            self.application_id = f"{prefix}-{last_number + 1:04d}"

        super().save(*args, **kwargs)      




from django.db import models
from faculty_management.models import general_information
from student_management.models import StudentDetails   # change app name if different


class EmailReloginApplication(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        DEACTIVATED = "DEACTIVATED", "Deactivated"

    faculty = models.ForeignKey(
        general_information,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="email_relogin_requests",
    )

    student = models.ForeignKey(
        StudentDetails,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="email_relogin_requests",
    )

    reason = models.TextField(null=True, blank=True)
    agreement = models.BooleanField(default=False)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    processed_by = models.ForeignKey(
        general_information,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_email_relogin_requests",
    )

    approver_remarks = models.TextField(null=True, blank=True)

    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        if self.student:
            return f"{self.student.name} ({self.student.reg_no}) - {self.status}"
        return f"Email Relogin Request - {self.status}"
    
    
    
