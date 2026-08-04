from django.db import models
from user_accounts.models import Add_Department
from faculty_management.models import general_information
# Create your models here.

class Library_Permissions(models.Model):
    role = models.ForeignKey("user_accounts.Role", on_delete=models.DO_NOTHING, 
        db_constraint=False, blank=True, null=True)
    function = models.CharField(max_length=255, blank=True, null=True)
    permission = models.BooleanField()









class BookType(models.Model):
    # User can type any book type (ex: BK, Xerox, Magazine, Journal, etc.)
    book_type = models.CharField(max_length=100, unique=True, blank=True, null=True)

    is_active = models.BooleanField(default=True, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        db_table = "library_book_type"
        ordering = ["book_type"]

    def __str__(self):
        return self.book_type
    
    
    
    
    
class LibraryBook(models.Model):
    department = models.ForeignKey(Add_Department,on_delete=models.SET_NULL,
         null=True,
        blank=True,)
    faculty = models.ForeignKey(general_information, on_delete=models.CASCADE, null=True, blank=True)
    academic_year = models.CharField(max_length=10, blank=True, null=True)
    dept_code = models.CharField(max_length=20, blank=True, null=True)
    accession_book = models.CharField(max_length=50, blank=True, null=True)
    first_edition_year = models.PositiveIntegerField(blank=True, null=True)

    title = models.CharField(max_length=255, blank=True, null=True)
    title_no = models.CharField(max_length=50, blank=True, null=True)
    volume = models.CharField(max_length=50, blank=True, null=True)

    authors = models.CharField(max_length=255, blank=True, null=True)
    publisher = models.CharField(max_length=255, blank=True, null=True)

    address = models.TextField(blank=True, null=True)
    mobile_no = models.CharField(max_length=15, blank=True, null=True)

    book_type = models.ForeignKey(BookType, on_delete=models.PROTECT, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    issue_date = models.DateField(blank=True, null=True)
    return_date = models.DateField(blank=True, null=True)

    class Meta:
        db_table = "library_books"

    def __str__(self):
        return self.title



from django.db import models
from datetime import date
from faculty_management.models import general_information, Add_Department
from library_management.models import LibraryBook


class LibraryNotification(models.Model):
    """
    Simple notification table (optional but useful).
    """
    to_faculty_id = models.IntegerField(null=True, blank=True)   # HOD faculty_id
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "library_notifications"
        ordering = ["-id"]

    def __str__(self):
        return self.title


from django.db import models
from django.utils import timezone
from datetime import date

from faculty_management.models import Add_Department, general_information
from user_accounts.models import Role
from library_management.models import LibraryBook  # adjust import if needed


class LibraryBookRequest(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("RETURN_REQUESTED", "Return Requested"),
        ("RETURNED", "Returned"),
    )

    student_name = models.CharField(max_length=200)
    student_rollno = models.CharField(max_length=50, blank=True, null=True)

    department = models.ForeignKey(Add_Department, on_delete=models.SET_NULL, null=True, blank=True)
    book = models.ForeignKey(LibraryBook, on_delete=models.CASCADE)
    incharge_faculty_id = models.IntegerField(null=True, blank=True)

    hod_faculty_id = models.IntegerField(null=True, blank=True)

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="PENDING")

    requested_on = models.DateField(default=date.today)
    approved_on = models.DateField(blank=True, null=True)
    issued_on = models.DateField(blank=True, null=True)

    return_requested_on = models.DateField(blank=True, null=True)
    returned_on = models.DateField(blank=True, null=True)

    remarks = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "library_book_requests"
        ordering = ["-id"]

    def __str__(self):
        return f"{self.student_name} -> {self.book.title} ({self.status})"


class LibraryRequestApprovers(models.Model):
    """
    Like LeaveApprovers:
    Defines APPROVAL ROUTE for LibraryBookRequest based on creator role.
    """
    class DefaultApprover(models.TextChoices):
        YES = "YES", "Yes"
        NO = "NO", "No"

    creator_role = models.ForeignKey(
        "user_accounts.Role",
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        related_name="library_request_creator",
        blank=True,
        null=True
    )

    approver_role = models.ForeignKey(
        "user_accounts.Role",
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        related_name="library_request_approver_role",
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
        db_table = "library_request_approvers"
        ordering = ["creator_role_id", "approver_level"]

    def __str__(self):
        creator = self.creator_role.role if self.creator_role else "Unknown"
        approver = self.approver_role.role if self.approver_role else "Unknown"
        return f"[Library] Level {self.approver_level}: {approver} for {creator}"
 

class LibraryRequestApproversData(models.Model):
    """
    Like LeaveApproversData:
    Stores per-request approval actions for each approver level.
    """
    class Status(models.TextChoices):
        APPROVED = "APPROVED", "Approved"
        PENDING = "PENDING", "Pending"
        REJECTED = "REJECTED", "Rejected"

    request = models.ForeignKey(
        LibraryBookRequest,
        on_delete=models.CASCADE,
        related_name="approval_entries",
        blank=True,
        null=True
    )

    approver_id = models.ForeignKey(
        general_information,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="library_request_approver_entries"
    )

    creator_id = models.ForeignKey(
        general_information,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="library_request_creator_entries"
    )

    reason = models.CharField(max_length=225, null=True, blank=True)

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        blank=True,
        null=True
    )

    approver_level = models.PositiveIntegerField(blank=True, null=True)
    acted_on = models.DateTimeField(default=timezone.now, blank=True, null=True)

    class Meta:
        db_table = "library_request_approvers_data"
        ordering = ["-id"]

    def __str__(self):
        approver = getattr(self.approver_id, "username", None) or "N/A"
        req_id = self.request.id if self.request else "N/A"
        return f"[LibraryReq #{req_id}] {approver} ({self.status})"
 


