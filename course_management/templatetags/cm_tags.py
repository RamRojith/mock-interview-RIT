from django import template
from course_management.models import CourseandexaminationFunction
from user_accounts.models import Add_Department, Role
from course_management.models import Regulations



register = template.Library()
@register.filter(name='replace_underscore')
def replace_underscore(value):
    return value.replace('_', ' ').title()

@register.simple_tag
def cm_current_function():
    view_name = cm_view_names()
    user_roles=Role.objects.using("rit_approval_system").filter().distinct()
    
    data=[view_name,user_roles]
    return data
@register.simple_tag
def has_permission(role, function):
    try:
        permission_obj = CourseandexaminationFunction.objects.get(role=role, function=function)

        return permission_obj.permission  
    except CourseandexaminationFunction.DoesNotExist:
        return False
from django.urls import get_resolver
from django.urls.resolvers import URLPattern
from course_management.cm_urls import course_examination_urls

def cm_view_names():
    
    resolver = get_resolver(course_examination_urls)
    view_names = []

    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLPattern):
            view_names.append(pattern.name)              
    return view_names


@register.simple_tag
def departments():
    return Add_Department.objects.filter(is_active=True)

@register.simple_tag
def regulations():
    return Regulations.objects.all()

@register.filter
def get_from_dict(dictionary, key):
    """Safely get a value from a dictionary."""
    if dictionary and key in dictionary:
        return dictionary[key]
    return None




@register.filter
def get_item(dictionary, key):
   
    """Get item from dictionary by key"""
    if isinstance(dictionary, dict):
        
        return dictionary.get(key)
    return None

@register.filter
def get_nested_item(dictionary, keys):
    """Get nested item from dictionary by dot-separated keys"""
    if not isinstance(dictionary, dict) or not keys:
        return None
    
    keys_list = str(keys).split('.')
    current = dictionary
    
    for key in keys_list:
        if isinstance(current, dict):
            current = current.get(key)
            if current is None:
                return None
        else:
            return None
    
    return current

@register.filter
def slice(value, arg):
    """Slice a dictionary or list"""
    if isinstance(value, dict):
        items = list(value.items())
        start, end = arg.split(':') if ':' in arg else (arg, None)
        start = int(start) if start else 0
        end = int(end) if end else None
        return dict(items[start:end])
    return value




@register.filter
def dict_get(d, key):
    return d.get(key)


@register.filter
def get_from_dict(d, key):
    """Get value from dictionary safely"""
    return d.get(key)



# @register.filter
# def get_item(dictionary, key):
    
#     return dictionary.get(key)



