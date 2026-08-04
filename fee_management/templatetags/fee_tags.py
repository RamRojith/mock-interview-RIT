from django import template
from django.urls import get_resolver
from django.urls.resolvers import URLPattern
from fee_management.models import FeePerimissonFunction , ScholarshipType
from course_management.models import Course
from user_accounts.models import Role, AdmissionRecords, Add_Department, Scholarships, Degree
from fee_management.urls import fee_controls_url
from datetime import datetime

register = template.Library()

# ---------------------------
# Filters
# ---------------------------

@register.filter(name='replace_underscore')
def replace_underscore(value):
    """
    Replace underscores with spaces and title-case the string.
    Example: 'first_name' -> 'First Name'
    """
    if not isinstance(value, str):
        return value
    return value.replace('_', ' ').title()


@register.filter
def get_item(dictionary, key):
    """
    Safely get a value from a dictionary.
    Returns 'Unknown' if key is missing.
    """
    if not isinstance(dictionary, dict):
        return "Unknown"
    return dictionary.get(str(key), "Unknown")


@register.filter
def scholarship():
    """Return all scholarships from the admissionform1 database."""
    try:
        return Scholarships.objects.using('admissionform1').all()
    except Exception:
        return []


# ---------------------------
# Simple Tags
# ---------------------------

@register.simple_tag
def fee_current_function():
    """Return a list containing all view names and all roles for fee module."""
    view_names = fee_view_names()
    try:
        user_roles = Role.objects.using("rit_approval_system").distinct()
    except Exception:
        user_roles = []
    return [view_names, user_roles]


@register.simple_tag
def has_permission(role, function):
    """Check if a role has permission for a specific function in Fee module."""
    try:
        permission_obj = FeePerimissonFunction.objects.get(role=role, function=function)
        return permission_obj.permission  
    except FeePerimissonFunction.DoesNotExist:
        return False


def fee_view_names():
    """Return all named URL patterns from fee_controls_url."""
    try:
        resolver = get_resolver(fee_controls_url)
        return [pattern.name for pattern in resolver.url_patterns if isinstance(pattern, URLPattern)]
    except Exception:
        return []


@register.simple_tag
def departments():
    """Return all active departments."""
    try:
        return Add_Department.objects.all()
    except Exception:
        return []


@register.simple_tag
def quotas():
    """Return distinct quotas from AdmissionRecords."""
    try:
        return AdmissionRecords.objects.using('admissionform1').values_list('Quota', flat=True).distinct()
    except Exception:
        return []


@register.simple_tag
def batches():
    """Return a list of batches from 3 years back to 3 years forward."""
    current_year = datetime.now().year
    return [str(current_year + i) for i in range(-3, 4)]


@register.simple_tag
def degrees():
    """Return degree list including id, code, name, and duration."""
    try:
        return Degree.objects.all().only("id", "degree_code", "degree", "duration")
    except Exception:
        return []


@register.simple_tag
def scholarship_types():
    """Return all scholarship types from the database."""
    try:
        return ScholarshipType.objects.all()
    except Exception:
        return []