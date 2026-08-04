# signals.py
from django.dispatch import Signal, receiver
from faculty_leave_management.models import DeviceLogLocal
import logging

# Define the custom signal
punch_data_fetched = Signal()  # provides: userid, month, year, rows

# Set up logging for the signal
logger = logging.getLogger(__name__)

# Signal receiver that syncs punch data to the local database
@receiver(punch_data_fetched)
def sync_punch_to_local(sender, userid, month, year, rows, **kwargs):
    """
    Sync any new records into the local DeviceLogLocal table when punch data
    is fetched from MSSQL attendance_db.
    """
    if not rows:
        return

    try:
        # Get the existing log ids from DeviceLogLocal
        existing_ids = set(
            DeviceLogLocal.objects.filter(userid=userid)
            .values_list("devicelogid", flat=True)
        )

        # Prepare a list for new records
        new_records = []
        for row in rows:
            log_id = row.get("DeviceLogId")
            if log_id is None or log_id in existing_ids:
                continue
            new_records.append(DeviceLogLocal(
                devicelogid=log_id,
                deviceid=row.get("DeviceId"),
                userid=row.get("UserId"),
                logdate=row.get("LogDate"),
                direction=row.get("Direction"),
            ))

        # Bulk create new records in the local database if there are any
        if new_records:
            DeviceLogLocal.objects.bulk_create(new_records, ignore_conflicts=True)
            logger.info(
                f"sync_punch_to_local: synced {len(new_records)} new record(s) "
                f"for user={userid} {month}/{year}"
            )

    except Exception as e:
        logger.warning(f"sync_punch_to_local failed: {e}")




# @receiver(post_save, sender=LeaveAllotment)
# def leave_balance_updation(sender, instance, created, **kwargs):
#     if not created:  # Only log updates, not creation
#         data = LeaveBalance.objects.filter(
#             academic_year=instance.academic_year,
#             leave_type=instance.leave_type,
#             designation=instance.role
#         )
        
#         if data.exists():
#             data.update(
#                 start_date=instance.start_date,
#                 end_date=instance.end_date,
#                 available=instance.default_allotment - data.first().used
#             )
            
            
# @receiver(post_save, sender=LeaveApplication)
# def update_leave_balance(sender, instance, created, **kwargs):
#     # Check if this is a new object or an update
#     if not created and instance.status == 'Pending':
#         return  # Prevents double execution on updates
    
#     # Calculate the leave days
#     new_days = (instance.to_date - instance.from_date).days + 1
    
#     # Find the existing leave balance
#     leave_balance = LeaveBalance.objects.filter(
#         user=instance.user,
#         designation=instance.designation,
#         leave_type=instance.leave_type,
#         start_date__lte=instance.from_date,
#         end_date__gte=instance.to_date
#     ).first()
    
#     # If no balance is found, create one (if that's your business logic)
#     if not leave_balance:
#         leave_balance = LeaveBalance.objects.create(
#             user=instance.user,
#             designation=instance.designation,
#             leave_type=instance.leave_type,
#             available=0,  # Or some default value
#             used=0,      # Or some default value
#             start_date=instance.from_date,
#             end_date=instance.to_date
#         )
    
#     # Debugging Output
#     # print(leave_balance.designation, "ldf")
#     # print(leave_balance.available, "leoqe", new_days)
    
#     # Apply the new balance changes
    
    
#     if instance.status == 'Rejected':
#         # Revert the balance if the application is rejected
#         # print("working")
#         leave_balance.available += new_days
#         leave_balance.used -= new_days
#         leave_balance.save()
        
# @receiver(post_save, sender=LeaveApplication)
# def add_approvers_on_submit(sender, instance, created, **kwargs):
#     if created:  # Only trigger when a new application is submitted
#         # Get the creator's role
#         creator_role = instance.user.role  # Assuming USER model has a role field
        
#         # Get all approvers for this creator's role
#         approvers = LeaveApprovers.objects.filter(
#             creator_role=creator_role
#         ).order_by('approver_level')
        
#         # Create approver data for each approver role
#         for approver in approvers:
#             if approver.is_cross_department_approver==LeaveApprovers.DefaultApprover.YES:
#                 approver_id = USER.objects.filter(role=approver.approver_role, Department=approver.approver_department).first()

#             if approver.is_cross_department_approver==LeaveApprovers.DefaultApprover.NO:
#                 approver_id = USER.objects.filter(role=approver.approver_role, Department=instance.user.Department).first()
            
#             if approver_id:
#                 LeaveApproversData.objects.create(
#                     leave_application=instance,
#                     approver_id=approver_id,
#                     creator_id=instance.user,
#                     approver_level=approver.approver_level,
#                     status=LeaveApproversData.Status.PENDING,
#                 )
#             if not approvers.exists():
#                 instance.status="Pre-approved"
#             new_days = (instance.to_date - instance.from_date).days + 1
    
#     # Find the existing leave balance
#             leave_balance = LeaveBalance.objects.filter(
#                 user=instance.user,
#                 designation=instance.designation,
#                 leave_type=instance.leave_type,
#                 start_date__lte=instance.from_date,
#                 end_date__gte=instance.to_date
#             ).first()
#             if instance.status == 'Pending':
#                 if leave_balance.available >= new_days:
#                     leave_balance.available -= new_days
#                     leave_balance.used += new_days
#                     leave_balance.save()
#                 else:
#                     raise ValueError("Insufficient leave balance.")