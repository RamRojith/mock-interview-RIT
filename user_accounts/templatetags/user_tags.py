from django import template
from user_accounts.models import Department,Role,USER
from django.urls import reverse
import json

register = template.Library()



@register.simple_tag
def user_data_count(Employee_id):
    try:
        su_data_obj = USER.objects.using("rit_approval_system").filter(Employee_id=Employee_id).count()
        return su_data_obj  
    except USER.DoesNotExist:
        return False


@register.simple_tag
def switch_user_data(Employee_id):
    try:
        su_data_obj = USER.objects.using("rit_approval_system").filter(Employee_id=Employee_id,is_active=True)
        return su_data_obj  
    except USER.DoesNotExist:
        return False
    

@register.filter
def is_faculty_or_hod(user):
    """Return True only for Faculty/HOD ERP roles (see access service).

    Used by templates to show/hide the Faculty Mock Interview module link
    and card. Delegates to mock_interview.services.access so there is a
    single source of truth for the authorization rule.
    """
    from mock_interview.services.access import is_faculty_or_hod as _check
    return _check(user)
