from django.contrib.auth.backends import BaseBackend
from user_accounts.models import USER  # Unmanaged mirror model
from django.contrib.auth.hashers import check_password

class EmployeeIDBackend(BaseBackend):
    def authenticate(self, request, Employee_id=None, password=None):
        try:
            # Use the mirror USER model from external DB
            employee = USER.objects.using('rit_approval_system').filter(Employee_id=Employee_id,is_active=True).order_by('id').first()
            if employee and check_password(password, employee.password):  # Secure password check
                return employee
        except USER.DoesNotExist:
            return None
        return None

    def get_user(self, user_id):
        try:
            return USER.objects.using('rit_approval_system').get(pk=user_id)
        except USER.DoesNotExist:
            return None
