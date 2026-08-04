from django import template
from django.urls import get_resolver
from django.urls.resolvers import URLPattern

from course_management.models import Course
from user_accounts.models import Role, AdmissionRecords, Add_Department, Scholarships, Degree
from datetime import datetime

from feedback_management.models import FeedbackPermission
from feedback_management.urls import feedback_control_urls

register = template.Library()

# ---------------------------
# Filters
# ---------------------------

@register.filter(name="replace_underscore")
def replace_underscore(value):
    """
    Replace underscores with spaces and title-case the string.
    Example: 'first_name' -> 'First Name'
    """
    if not isinstance(value, str):
        return value
    return value.replace("_", " ").title()


@register.filter
def get_item(dictionary, key):
    """
    Safely get a value from a dictionary.
    Returns None if key is missing or dictionary invalid.
    Works for both int & str keys.
    """
    try:
        if isinstance(dictionary, dict):
            # try exact key first
            if key in dictionary:
                return dictionary.get(key)
            # then string key
            return dictionary.get(str(key))
    except Exception:
        pass
    return None


@register.filter
def scholarship(_=None):
    """Return all scholarships from the admissionform1 database."""
    try:
        return Scholarships.objects.using("admissionform1").all()
    except Exception:
        return []


# ---------------------------
# Simple Tags
# ---------------------------

@register.simple_tag
def feedback_current_function():
    """
    Return a list containing all view names and all roles for feedback module.
    Template usage:
      {% feedback_current_function as permission_data %}
      permission_data.0 -> view names
      permission_data.1 -> roles
    """
    view_names = feedback_view_names()
    try:
        user_roles = Role.objects.using("rit_approval_system").all().distinct()
    except Exception:
        user_roles = []
    return [view_names, user_roles]


@register.simple_tag
def has_permission(role, function):
    """
    Check if a role has permission for a specific function in Feedback module.

    Template usage:
      {% has_permission per field as has_per %}
    """
    try:
        permission_obj = FeedbackPermission.objects.get(role=role, function=function)
        return bool(permission_obj.permission)
    except FeedbackPermission.DoesNotExist:
        return False
    except Exception:
        return False


def feedback_view_names():
    """Return all named URL patterns from feedback_control_urls."""
    try:
        resolver = get_resolver(feedback_control_urls)
        return [
            pattern.name
            for pattern in resolver.url_patterns
            if isinstance(pattern, URLPattern) and pattern.name
        ]
    except Exception:
        return []


@register.filter
def get_feedback(feedbacks, course):
    """
    Given a queryset of Course_Exit_Survey (feedbacks) and a course object,
    return the feedback object for that course if it exists.
    """
    try:
        return feedbacks.filter(course=course).first()
    except Exception:
        return None
