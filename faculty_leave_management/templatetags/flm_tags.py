from django import template
from user_accounts.models import Role
from faculty_leave_management.models import LeavePermissionFunction, LeaveType
from faculty_leave_management.views.authorizer import flm_view_names

register = template.Library()
@register.filter(name='replace_underscore')
def replace_underscore(value):
    return value.replace('_', ' ').title()

@register.simple_tag
def current_function():
    view_name = flm_view_names()
    user_roles=Role.objects.using("rit_approval_system").filter().distinct()
    data=[view_name,user_roles]
    return data
@register.simple_tag
def has_permission(role, function):
    try:
        permission_obj = LeavePermissionFunction.objects.get(role=role, function=function)

        return permission_obj.permission  
    except LeavePermissionFunction.DoesNotExist:
        return False






@register.simple_tag
def faculty_leave_types():
    leave_types = LeaveType.objects.all()
    return leave_types




@register.filter
def dict_get(d, key):
    """Safely fetch a key from a dictionary in Django templates."""
    if isinstance(d, dict):
        return d.get(key)
    return None


@register.filter
def get_item(d, key):
    if d is None:
        return None
    return d.get(key)
