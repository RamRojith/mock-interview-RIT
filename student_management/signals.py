from django.db.models.signals import pre_save
from django.dispatch import receiver
from user_accounts.models import USER, StudentDetails
from student_management.models import *
from course_management.models import *
from django.db import transaction


from examination_management.models import StudentExam

@receiver(pre_save, sender=StudentDetails)
def sync_user_on_reg_email_change(sender, instance, **kwargs):
    """
    Signal to sync USER model whenever StudentDetails' reg_no or email changes.
    Triggered before saving StudentDetails.
    """
    # print(f"DEBUG: Signal triggered for StudentDetails (PK={instance.pk})")

    # Skip if this is a new StudentDetails record
    if instance._state.adding:
        return

    try:
        old_instance = StudentDetails.objects.get(pk=instance.pk)
        # print(f"DEBUG: Fetched old instance -> reg_no: {old_instance.reg_no}, email: {old_instance.email}")
    except StudentDetails.DoesNotExist:
        # print("DEBUG: Old StudentDetails instance not found. Aborting sync.")
        return

    # Check if registration number or email has changed
    reg_changed = old_instance.reg_no != instance.reg_no
    email_changed = old_instance.email != instance.email
    # print(f"DEBUG: reg_changed={reg_changed}, email_changed={email_changed}")

    if not (reg_changed or email_changed):
        # print("DEBUG: No changes in reg_no or email. Nothing to update in USER.")
        return
    try:
        user = USER.objects.using("rit_approval_system").get(unique_id=instance.aadhar_number)
        # print(f"DEBUG: Found USER -> Employee_id: {user.Employee_id}, email: {user.email}")

        if reg_changed:
            # print(f"DEBUG: Updating USER.Employee_id from {user.Employee_id} -> {instance.reg_no}")
            user.Employee_id = instance.reg_no

        if email_changed:
            # print(f"DEBUG: Updating USER.email from {user.email} -> {instance.email}")
            user.email = instance.email

        user.save(using="rit_approval_system")
        print(f"✅ USER updated successfully for Aadhaar {instance.aadhar_number}")

    except USER.DoesNotExist:
        # print(f" USER not found for Aadhaar {instance.aadhar_number}. Cannot sync.")
        print(f" USER not found for Aadhaar {instance.aadhar_number}. Cannot sync.")
    except Exception as e:
        print(f"Exception while updating USER: {e}")





@receiver(pre_save, sender=StudentDetails)
def cascade_reg_no_update(sender, instance, **kwargs):
    """
    If reg_no or email changes in StudentDetails, update:
    - USER model
    - Daily_Attendance
    - Other related tables
    """
    if not instance.pk:
        # New student, nothing to cascade
        return

    try:
        old_instance = StudentDetails.objects.get(pk=instance.pk)
    except StudentDetails.DoesNotExist:
        return

    old_reg_no = old_instance.reg_no
    new_reg_no = instance.reg_no
    old_email = old_instance.email
    new_email = instance.email

    old_name = old_instance.name
    
    new_name = instance.name
    # print(f"DEBUG: Old name: {old_name}, New name: {new_name}")
    reg_changed = old_reg_no != new_reg_no
    email_changed = old_email != new_email
    name_changed = old_name != new_name

    if not (reg_changed or email_changed or name_changed):
        # print("DEBUG: No reg_no, email or name change detected. Nothing to update.")
        return

    # print(f"DEBUG: Changes detected for Student {instance.name}: reg_no {old_reg_no}->{new_reg_no}, email {old_email}->{new_email}, name {old_name}->{new_name}")

    try:
        with transaction.atomic():
            # ✅ Update USER
            try:
                user = USER.objects.using("rit_approval_system").get(unique_id=instance.aadhar_number)
                if reg_changed:
                    # print(f"DEBUG: Updating USER.Employee_id {user.Employee_id} -> {new_reg_no}")
                    user.Employee_id = new_reg_no
                if email_changed:
                    # print(f"DEBUG: Updating USER.email {user.email} -> {new_email}")
                    user.email = new_email
                if name_changed:
                    # print(f"DEBUG: Updating USER.name {user.username} -> {new_name}")
                    user.username = new_name
                user.save(using="rit_approval_system")
            except USER.DoesNotExist:
                 print(f" USER not found for Aadhaar {instance.aadhar_number}")

            # ✅ Update Daily_Attendance
            if reg_changed:
                updated_count = Daily_Attendance.objects.filter(reg_no=old_reg_no).update(reg_no=new_reg_no)
                print(f"DEBUG: Daily_Attendance updated {updated_count} rows.")

            if reg_changed:
                updated_count = HourAttendance.objects.filter(reg_no=old_reg_no).update(reg_no=new_reg_no)
                print(f"DEBUG: HourAttendance updated {updated_count} rows.")

            
            if reg_changed:
                updated_count = PassOutStudents.objects.filter(reg_no=old_reg_no).update(reg_no=new_reg_no)
                print(f"DEBUG: PassOutStudents updated {updated_count} rows.")


            if reg_changed:
                updated_count = StudentExam.objects.filter(reg_no=old_reg_no).update(reg_no=new_reg_no)
                print(f"DEBUG: StudentExam updated {updated_count} rows.")
            
            # if reg_changed:
            #     updated_count = StudentFeeReceipt.objects.filter(register_no=old_reg_no).update(register_no=new_reg_no)
            #     # print(f"DEBUG: StudentFeeReceipt updated {updated_count} rows.")



            # ✅ Add similar updates for other tables
            # Example:
            # StudentResults.objects.filter(reg_no=old_reg_no).update(reg_no=new_reg_no)
            # StudentAchievements.objects.filter(reg_no=old_reg_no).update(reg_no=new_reg_no)

            # print(f"Cascading updates completed for Student {instance.name}")

    except Exception as e:
        print(f"Error during cascading updates: {e}")








