from  django import template
from django.urls import get_resolver
from django.urls.resolvers import URLPattern


from django import template
from user_accounts.models import Role
from student_management.models import StudentManagementPermissions
from student_management.sm_urls import sm_control_urls


register = template.Library()





@register.filter(name='replace_underscore')
def replace_underscore(value):
    return value.replace('_', ' ').title()

@register.simple_tag
def current_function():
    view_name = sm_view_names()
    user_roles=Role.objects.using("rit_approval_system").filter().distinct()
    data=[view_name,user_roles]
    return data

@register.simple_tag
def has_permission(role, function):
    try:
        permission_obj = StudentManagementPermissions.objects.get(role=role, function=function)

        return permission_obj.permission  
    except StudentManagementPermissions.DoesNotExist:
        return False


def sm_view_names():
    
    resolver = get_resolver(sm_control_urls)
    view_names = []

    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLPattern):
            view_names.append(pattern.name)
    return view_names


@register.filter(name="get_attr")
def get_attr(obj, attr):
    """Get attribute value from object safely in templates"""
    return getattr(obj, attr, "")



@register.filter
def get_item(dictionary, key):
    """Fetch a dictionary value safely in templates"""
    if dictionary and key in dictionary:
        return dictionary.get(key)
    return ""




@register.filter
def get_course(courses, title):
    return next((c for c in courses if c.title == title), None)


@register.filter
def get_attr_safe(obj, attr_name):
    """Safely get attribute, returns None if not exist."""
    return getattr(obj, attr_name, None)

@register.filter
def check_attr(obj, attr_name):
    """Check if object has an attribute"""
    return hasattr(obj, attr_name)



@register.filter
def to(end):
    """
    Generate range(1, end+1) for loops. Usage: {% for q in part.total_questions|to %}
    """
    try:
        end = int(end)
        return range(1, end + 1)
    except (ValueError, TypeError):
        return []

# Optional: For safer string addition if needed
@register.filter
def add_str(value1, value2):
    return str(value1) + str(value2)



@register.filter
def get_item(value, key):
    """
    Get an item from a dictionary or an attribute from an object using a key.
    """
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)



