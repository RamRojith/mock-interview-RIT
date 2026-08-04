from django import template
from data_center_management.models import Data_Center_Permission
from user_accounts.models import Add_Department, Role



register = template.Library()
@register.filter(name='replace_underscore')
def replace_underscore(value):
    return value.replace('_', ' ').title()

@register.simple_tag
def dc_current_function():
    view_name = dc_view_names()
    user_roles=Role.objects.using("rit_approval_system").filter().distinct()
    
    data=[view_name,user_roles]
    return data
@register.simple_tag
def has_permission(role, function):
    try:
        permission_obj = Data_Center_Permission.objects.get(role=role, function=function)

        return permission_obj.permission  
    except Data_Center_Permission.DoesNotExist:
        return False
from django.urls import get_resolver
from django.urls.resolvers import URLPattern
from data_center_management.urls import dc_control_urls
def dc_view_names():
    
    resolver = get_resolver(dc_control_urls)
    view_names = []

    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLPattern):
            view_names.append(pattern.name)              
    return view_names


