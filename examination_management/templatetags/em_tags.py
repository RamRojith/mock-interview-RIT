from django import template
from course_management.models import Regulations
from examination_management.models import ExaminationFunction
from user_accounts.models import USER, Role
from user_accounts.models import Degree


register = template.Library()

@register.simple_tag
def regulations():
    return Regulations.objects.all()

@register.simple_tag
def em_degrees():
    return Degree.objects.filter(is_active=True).order_by('degree_code')

@register.filter(name='replace_underscore')
def replace_underscore(value):
    return value.replace('_', ' ').title()

@register.simple_tag
def em_current_function():
    view_name = em_view_names()
    user_roles=Role.objects.using("rit_approval_system").filter().distinct()
    # # print("Roles => ", user_roles)
    data=[view_name,user_roles]
    return data
@register.simple_tag
def has_permission(role, function):
    try:
        permission_obj = ExaminationFunction.objects.get(role=role, function=function)

        return permission_obj.permission  
    except ExaminationFunction.DoesNotExist:
        return False
    

from django.urls import get_resolver
from django.urls.resolvers import URLPattern
from examination_management.urls import em_control_urls





def em_view_names():
    
    resolver = get_resolver(em_control_urls)
    view_names = []

    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLPattern):
            view_names.append(pattern.name)              
    return view_names


@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    return dictionary.get(key)

@register.filter
def add_str(value1, value2):
    """Concatenate two strings"""
    if value1 and value2:
        return f"{value1}{value2}"
    return value1 or value2 or ""

@register.filter
def to_range(value):
    """Convert number to range for template looping"""
    try:
        return range(1, int(value) + 1)
    except (ValueError, TypeError):
        return []