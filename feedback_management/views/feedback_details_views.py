from django.shortcuts import render
from django.http import HttpResponse
from django.contrib import messages
from django.shortcuts import redirect
from faculty_management.decorators import faculty_management
from user_accounts.models import Role, Department
import re
from user_accounts.decorators import faculty_login_required, no_cache, is_super_user, check_permission
from feedback_management.models import FeedbackPermission
from feedback_management.decorators import feedback_management
from course_management.models import CourseEnrollment, Course
from course_management.models import AssignSubjectFaculty
from django.utils import timezone
from user_accounts.models import StudentDetails
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from faculty_management.models import *
from datetime import date

def get_academic_year():
    """
    Dynamically returns academic year string.
    Example:
      If current month >= June → '2025-2026'
      Else (Jan–May) → '2024-2025'
    """
    today = date.today()
    current_year = today.year
    if today.month >= 6:  # June or later
        return f"{current_year}-{current_year + 1}"
    else:  # Before June → part of previous cycle
        return f"{current_year - 1}-{current_year}"

from feedback_management.models import *


@check_permission("course_survey_entry")
def course_survey_entry(request):
    return render(request, "feedback_management/faculty/entry/course_survey_entry.html")

