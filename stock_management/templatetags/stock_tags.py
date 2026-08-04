from django import template
from stock_management.models import Stock_Permission
from user_accounts.models import Add_Department, Role



register = template.Library()
@register.filter(name='replace_underscore')
def replace_underscore(value):
    return value.replace('_', ' ').title()

@register.simple_tag
def stock_current_function():
    view_name = stock_view_names()
    user_roles=Role.objects.using("rit_approval_system").filter().distinct()

    data=[view_name,user_roles]
    return data
@register.simple_tag
def has_permission(role, function):
    try:
        permission_obj = Stock_Permission.objects.get(role=role, function=function)

        return permission_obj.permission
    except Stock_Permission.DoesNotExist:
        return False


@register.simple_tag
def has_any_stock_permission(role):
    """True if the given role has at least one granted stock function.
    Used to show/hide the Stock Management card on the faculty dashboard."""
    if role is None:
        return False
    return Stock_Permission.objects.filter(role=role, permission=True).exists()
from django.urls import get_resolver
from django.urls.resolvers import URLPattern
from stock_management.urls import stock_control_urls
def stock_view_names():

    resolver = get_resolver(stock_control_urls)
    view_names = []

    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLPattern):
            view_names.append(pattern.name)
    return view_names
