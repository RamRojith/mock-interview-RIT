from django import template
from user_accounts.models import Role
from learning_management_system.models import LMS_Permissions
from django.urls import get_resolver
from django.urls.resolvers import URLPattern
from learning_management_system.urls import lms_control_urls

register = template.Library()

@register.filter(name='replace_underscore')
def replace_underscore(value):
    return value.replace('_', ' ').title()

@register.simple_tag
def lms_current_function():
    view_names = lms_view_names()
    roles = Role.objects.using("rit_approval_system").distinct()
    return [view_names, roles]

@register.simple_tag
def has_lms_permission(role, function):
    try:
        return LMS_Permissions.objects.get(role=role, function=function).permission
    except LMS_Permissions.DoesNotExist:
        return False

def lms_view_names():
    resolver = get_resolver(lms_control_urls)
    view_names = []
    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLPattern) and pattern.name:
            view_names.append(pattern.name)
    return view_names



from django import template
import os

# register = template.Library()

@register.filter
def basename(value):
    return os.path.basename(value)



@register.filter
def subtract(value, arg):
    return value - arg

@register.filter
def get_item(d, key):
    if not d:
        return None
    return d.get(key)