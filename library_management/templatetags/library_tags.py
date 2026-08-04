from django import template
from user_accounts.models import Role
from django.urls import get_resolver
from django.urls.resolvers import URLPattern
from library_management.urls import library_control_urls
from library_management.models import Library_Permissions

register = template.Library()

@register.filter(name='replace_underscore')
def replace_underscore(value):
    return value.replace('_', ' ').title()

@register.simple_tag
def library_current_function():
    view_names = library_view_names()
    roles = Role.objects.using("rit_approval_system").distinct()
    return [view_names, roles]

@register.simple_tag
def has_library_permission(role, function):
    try:
        return Library_Permissions.objects.get(role=role, function=function).permission
    except Library_Permissions.DoesNotExist:
        return False

def library_view_names():
    resolver = get_resolver(library_control_urls)
    view_names = []
    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLPattern) and pattern.name:
            view_names.append(pattern.name)
    return view_names



