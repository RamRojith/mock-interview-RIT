from django import template
from nba.models import NBAPerimissonFunction
from course_management.models import Course
from user_accounts.models import Role


register = template.Library()

@register.filter(name='replace_underscore')
def replace_underscore(value):
    return value.replace('_', ' ').title()

@register.simple_tag
def nba_current_function():
    view_name = nba_view_names()
    user_roles=Role.objects.using("rit_approval_system").filter().distinct()
    data=[view_name,user_roles]
    return data
@register.simple_tag
def has_permission(role, function):
    try:
        permission_obj = NBAPerimissonFunction.objects.get(role=role, function=function)

        return permission_obj.permission  
    except NBAPerimissonFunction.DoesNotExist:
        return False
    
    
from django.urls import get_resolver
from django.urls.resolvers import URLPattern
from nba.urls import nba_controls_urls

def nba_view_names():
    
    resolver = get_resolver(nba_controls_urls)
    view_names = []

    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLPattern):
            view_names.append(pattern.name)              
    return view_names



