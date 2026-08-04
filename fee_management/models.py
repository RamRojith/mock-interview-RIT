from django.db import models


from django.db import models

# Create your models here.
from django.db import models
from user_accounts.models import Department  
from user_accounts.models import Degree

from faculty_management.models import *
import uuid
import random
import string


class FeePerimissonFunction(models.Model):
    role = models.ForeignKey(
        "user_accounts.Role",       # Role from external DB
        on_delete=models.DO_NOTHING, 
        db_constraint=False, blank=True, null=True      # 🚨 disables DB-level FK
    )
    function = models.CharField(max_length=500, blank=True, null=True)
    permission = models.BooleanField(blank=True, null=True)
 

class FeeType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class FeeEntry(models.Model):
    department = models.ForeignKey(Add_Department, on_delete=models.CASCADE, blank=True, null=True)
    
    batch = models.CharField(max_length=4)  # e.g., "2025"
    quota = models.CharField(max_length=100, blank=True, null=True)
    fee_category = models.ForeignKey(FeeType, on_delete=models.CASCADE, blank=True, null=True)
    degree = models.ForeignKey(Degree, null=True, blank=True, on_delete=models.SET_NULL)

    # ✅ Instead of JSONField, store each year fee separately
    year_1 = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, null=True)
    year_2 = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, null=True)
    year_3 = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, null=True)
    year_4 = models.DecimalField(max_digits=10, decimal_places=2, default=0, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    def __str__(self):
        return f"{self.fee_category.name} - {self.department_id} - Batch {self.batch} - Quota {self.quota}"

    def total_fee(self):
        return self.year_1 + self.year_2 + self.year_3 + self.year_4

    # Optional safety: ensure extra years are zeroed before save based on degree.duration
    def clamp_years_to_degree(self):
        dur = 0
        try:
            dur = int(getattr(self.degree, "duration", 0) or 0)
        except (TypeError, ValueError):
            dur = 0
        dur = max(0, min(dur, 4))
        vals = [self.year_1, self.year_2, self.year_3, self.year_4]
        for i in range(4):
            if i >= dur:
                vals[i] = 0
        self.year_1, self.year_2, self.year_3, self.year_4 = vals

    def save(self, *args, **kwargs):
        try:
            self.clamp_years_to_degree()
        except Exception:
            pass
        return super().save(*args, **kwargs)
   

class TransportStage(models.Model):
    """
    Defines a transport stage with a stage number and distance range.
    """
    stage_no = models.PositiveIntegerField(unique=True)
    distance_from = models.DecimalField(max_digits=6, decimal_places=2)
    distance_to = models.DecimalField(max_digits=6, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["stage_no"]

    def __str__(self):
        return f"Stage {self.stage_no}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.distance_to is not None and self.distance_from is not None:
            if self.distance_to < self.distance_from:
                raise ValidationError({
                    "distance_to": "Ending distance must be greater than or equal to starting distance."
                })
 


class TransportFee(models.Model):
    """
    Fee amounts associated with a transport stage.
    """
    stage = models.OneToOneField(TransportStage, on_delete=models.CASCADE, related_name="fee")
    bus_stop = models.CharField(max_length=255, blank=True, null=True)
    amount_per_semester = models.DecimalField(max_digits=10, decimal_places=2)
    amount_per_year = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["stage"], name="unique_fee_per_stage"),
        ]

    def __str__(self):
        label = f"Fee for {self.stage}"
        if self.bus_stop:
            label += f" - {self.bus_stop}"
        return label



class ScholarshipType(models.Model):
    name = models.CharField(max_length=255, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return self.name

class JaScholarshipEntry(models.Model):
    student = models.ForeignKey(StudentDetails, on_delete=models.CASCADE, null=True, blank=True)
    created_by = models.ForeignKey(general_information, on_delete=models.CASCADE, null=True, blank=True)
    scholarship = models.ForeignKey(ScholarshipType, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"{self.student} - {self.created_by} - {self.scholarship}"


class ScholarshipDeduction(models.Model):
    scholarship = models.ForeignKey(ScholarshipType, on_delete=models.CASCADE, null=True, blank=True)
    degree = models.ForeignKey(Degree, on_delete=models.CASCADE, null=True, blank=True)
    department = models.ForeignKey(Add_Department, on_delete=models.CASCADE, null=True, blank=True)
    quota = models.CharField(max_length=100, null=True, blank=True)
    batch = models.CharField(max_length=20, null=True, blank=True)

    scholarship_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"{self.scholarship} - {self.degree} - {self.department} - {self.quota} - {self.batch}"

class Fee_Permission(models.Model):
    role_id = models.PositiveIntegerField(null=True, blank=True)   # 👈 store ID only

    can_view_all_fee = models.BooleanField(default=False, null=True, blank=True)
    can_view_department_fee = models.BooleanField(default=False, null=True, blank=True)
