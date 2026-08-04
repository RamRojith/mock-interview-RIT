from datetime import date

from django.contrib import messages
from django.db.models import Min, Max, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from feedback_management.views.course_feedback_views import _draw_rit_header_footer
from user_accounts.decorators import check_permission
from user_accounts.models import StudentDetails

from faculty_management.models import general_information
from course_management.models import (
    CourseEnrollment,
    AssignSubjectFaculty,
    Co_Po_Mapping,
)
from feedback_management.models import CourseOutcomeDescription


def get_academic_year():
    """
    Dynamically returns academic year string.
    Example:
      If current month >= June → '2025-2026'
      Else (Jan–May) → '2024-2025'
    """
    today = date.today()
    current_year = today.year
    if today.month >= 6:
        return f"{current_year}-{current_year + 1}"
    return f"{current_year - 1}-{current_year}"


def get_student_details(request):
    emp = getattr(request.user, "Employee_id", None)
    uname = getattr(request.user, "username", None)

    if emp:
        s = StudentDetails.objects.filter(reg_no=emp).first() or StudentDetails.objects.filter(umis_id=emp).first()
        if s:
            return s

    if uname:
        s = StudentDetails.objects.filter(reg_no=uname).first() or StudentDetails.objects.filter(umis_id=uname).first()
        if s:
            return s

    return None


def get_current_academic_year():
    """
    Returns current academic year string like '2025-2026'.

    Change ACADEMIC_YEAR_START_MONTH if your institution starts
    the academic year in a different month.
    """
    ACADEMIC_YEAR_START_MONTH = 6  # June
    today = date.today()

    if today.month >= ACADEMIC_YEAR_START_MONTH:
        start_year = today.year
        end_year = today.year + 1
    else:
        start_year = today.year - 1
        end_year = today.year

    return f"{start_year}-{end_year}"


def get_current_semester_values():
    """
    Returns list of semester values for current semester cycle.

    Assumption:
    - June to November  => Odd semester cycle
    - December to May   => Even semester cycle
    """
    today = date.today()

    if 6 <= today.month <= 11:
        return ["1", "3", "5", "7"]
    return ["2", "4", "6", "8"]


def get_current_semester_label():
    """
    For display purpose only.
    """
    today = date.today()
    return "Odd" if 6 <= today.month <= 11 else "Even"


@check_permission("course_end_survey_entry")
def course_end_survey_entry(request):
    user_employee_id = request.user.Employee_id
    faculty = get_object_or_404(
        general_information.objects.select_related("department"),
        faculty_id=user_employee_id
    )

    current_academic_year = get_current_academic_year()
    current_semester_values = get_current_semester_values()
    current_semester_label = get_current_semester_label()

    # ---------------------------------------------------------
    # ASSIGNED SUBJECTS - same working method as subject_feedback
    # ---------------------------------------------------------
    assigned_subjects = (
        AssignSubjectFaculty.objects
        .select_related("course", "department", "regulation", "faculty", "skilled_faculty")
        .filter(
            Q(faculty=faculty) | Q(skilled_faculty=faculty),
            is_active=True,
            course__isnull=False,
            course__is_active=True,
        )
        .order_by(
            "academic_year",
            "course__year",
            "course__semester",
            "course__course_code",
            "section",
            "batch",
            "id"
        )
    )

    selected_assign_id = (
        request.POST.get("assign_id") if request.method == "POST"
        else request.GET.get("assign_id")
    )
    selected_assign_id = (selected_assign_id or "").strip()

    selected_assignment = None
    selected_course = None
    co_po_mappings = []
    saved_start_datetime = ""
    saved_end_datetime = ""
    saved_desc_map = {}

    # ---------------------------------------------------------
    # SELECTED ASSIGNMENT
    # ---------------------------------------------------------
    if selected_assign_id:
        selected_assignment = assigned_subjects.filter(id=selected_assign_id).first()

        if not selected_assignment:
            messages.error(request, "Invalid course selection.")
            return redirect("course_end_survey_entry")

        selected_course = selected_assignment.course

        # First try faculty-specific mapping
        co_po_mappings = list(
            Co_Po_Mapping.objects
            .filter(
                assigned_faculty=selected_assignment,
                course=selected_course
            )
            .select_related("course", "co_number", "assigned_faculty")
            .order_by("id")
        )

        # Fallback to course-level mapping
        if not co_po_mappings:
            co_po_mappings = list(
                Co_Po_Mapping.objects
                .filter(course=selected_course)
                .select_related("course", "co_number", "assigned_faculty")
                .order_by("id")
            )

        saved_descriptions = (
            CourseOutcomeDescription.objects
            .filter(co_po_mapping__in=co_po_mappings)
            .select_related("co_po_mapping")
            .order_by("id")
        )

        saved_desc_map = {
            obj.co_po_mapping_id: obj
            for obj in saved_descriptions
        }

        first_saved = (
            saved_descriptions
            .exclude(start_datetime__isnull=True, end_datetime__isnull=True)
            .first()
        )

        if first_saved and first_saved.start_datetime:
            local_start = timezone.localtime(first_saved.start_datetime)
            saved_start_datetime = local_start.strftime("%Y-%m-%dT%H:%M")

        if first_saved and first_saved.end_datetime:
            local_end = timezone.localtime(first_saved.end_datetime)
            saved_end_datetime = local_end.strftime("%Y-%m-%dT%H:%M")

    # ---------------------------------------------------------
    # SAVE POST
    # ---------------------------------------------------------
    if request.method == "POST":
        if not selected_assign_id:
            messages.error(request, "Please select a course.")
            return redirect("course_end_survey_entry")

        if not selected_assignment or not selected_course:
            messages.error(request, "Selected course is invalid.")
            return redirect("course_end_survey_entry")

        start_datetime_str = (request.POST.get("start_datetime") or "").strip()
        end_datetime_str = (request.POST.get("end_datetime") or "").strip()

        start_datetime = parse_datetime(start_datetime_str) if start_datetime_str else None
        end_datetime = parse_datetime(end_datetime_str) if end_datetime_str else None

        if start_datetime and timezone.is_naive(start_datetime):
            start_datetime = timezone.make_aware(
                start_datetime,
                timezone.get_current_timezone()
            )

        if end_datetime and timezone.is_naive(end_datetime):
            end_datetime = timezone.make_aware(
                end_datetime,
                timezone.get_current_timezone()
            )

        if start_datetime and end_datetime and end_datetime < start_datetime:
            messages.error(request, "End date/time cannot be earlier than start date/time.")
            return redirect(f"{request.path}?assign_id={selected_assignment.id}")

        updated_count = 0

        for mapping in co_po_mappings:
            field_name = f"co_description_{mapping.id}"
            original_field_name = f"original_co_description_{mapping.id}"

            new_co_description = request.POST.get(field_name)
            original_co_description = request.POST.get(original_field_name, "")

            if new_co_description is None:
                new_co_description = original_co_description

            new_co_description = (new_co_description or "").strip()

            CourseOutcomeDescription.objects.update_or_create(
                co_po_mapping=mapping,
                defaults={
                    "co_description": new_co_description,
                    "start_datetime": start_datetime,
                    "end_datetime": end_datetime,
                }
            )

            if new_co_description:
                updated_count += 1

        messages.success(
            request,
            f"Course outcome descriptions saved successfully for {selected_course}. Updated {updated_count} record(s)."
        )
        return redirect(f"{request.path}?assign_id={selected_assignment.id}")

    # ---------------------------------------------------------
    # RENDER
    # ---------------------------------------------------------
    return render(
        request,
        "feedback_management/faculty/entry/course_end_survey_entry.html",
        {
            "faculty": faculty,
            "assigned_subjects": assigned_subjects,
            "selected_assign_id": str(selected_assign_id),
            "selected_assignment": selected_assignment,
            "selected_course": selected_course,
            "co_po_mappings": co_po_mappings,
            "saved_desc_map": saved_desc_map,
            "saved_start_datetime": saved_start_datetime,
            "saved_end_datetime": saved_end_datetime,
            "current_academic_year": current_academic_year,
            "current_semester_values": current_semester_values,
            "current_semester_label": current_semester_label,
        }
    )


@check_permission("course_end_survey")
def course_end_survey(request):
    student = get_student_details(request)
    if not student:
        messages.error(request, "Student record not found.")
        return redirect("home")

    dept = student.department
    batch = (getattr(student, "batch", "") or "").strip()
    section = (getattr(student, "section", "") or "").strip()
    sem = str((getattr(student, "semester", "") or "")).strip()
    year = str((getattr(student, "year", "") or "")).strip()

    if not dept:
        messages.error(request, "Student department not set.")
        return redirect("home")

    qs = (
        CourseEnrollment.objects
        .select_related("course", "faculty", "department", "regulation")
        .filter(
            student=student,
            enroll=True,
            department=dept
        )
    )

    if batch:
        qs = qs.filter(batch=batch)

    if section:
        qs = qs.filter(section=section)

    # Handle whether semester/year live in enrollment or course
    if sem:
        try:
            qs = qs.filter(semester=sem)
        except Exception:
            qs = qs.filter(course__semester=sem)

    if year:
        try:
            qs = qs.filter(year=year)
        except Exception:
            qs = qs.filter(course__year=year)

    now = timezone.now()
    enrollments = []

    enrollment_list = list(qs.order_by("course__course_code", "id"))
    enrollment_ids = [e.id for e in enrollment_list]

    submitted_at_by_enrollment = {}
    for enrollment_id, submitted_at in (
        CourseOutcomeSubmission.objects
        .filter(student=student, enrollment_id__in=enrollment_ids)
        .values_list("enrollment_id", "submitted_at")
        .order_by("submitted_at")
    ):
        submitted_at_by_enrollment.setdefault(enrollment_id, submitted_at)

    for e in enrollment_list:
        course = e.course
        selected_assignment = None

        # Try to match the exact faculty assignment for this enrolled subject
        assign_qs = AssignSubjectFaculty.objects.filter(
            course=course,
            is_active=True
        )

        if getattr(e, "faculty", None):
            assign_qs = assign_qs.filter(faculty=e.faculty)

        if getattr(e, "department", None):
            assign_qs = assign_qs.filter(department=e.department)

        if getattr(e, "regulation", None):
            assign_qs = assign_qs.filter(regulation=e.regulation)

        if getattr(e, "batch", None):
            assign_qs = assign_qs.filter(batch=e.batch)

        if getattr(e, "section", None):
            assign_qs = assign_qs.filter(section=e.section)

        selected_assignment = assign_qs.first()

        # First preference: mapping linked to exact faculty assignment
        if selected_assignment:
            mappings = Co_Po_Mapping.objects.filter(
                assigned_faculty=selected_assignment,
                course=course
            )
        else:
            mappings = Co_Po_Mapping.objects.none()

        # Fallback: course-level mappings
        if not mappings.exists():
            mappings = Co_Po_Mapping.objects.filter(course=course)

        desc_qs = CourseOutcomeDescription.objects.filter(
            co_po_mapping__in=mappings
        )

        # Keep only rows that actually have description content if needed
        # (optional, but usually better)
        desc_qs = desc_qs.exclude(co_description__isnull=True).exclude(co_description="")

        # Window summary
        window = desc_qs.aggregate(
            win_start=Min("start_datetime"),
            win_end=Max("end_datetime"),
        )

        win_start = window.get("win_start")
        win_end = window.get("win_end")

        # Determine status strictly from saved window
        is_open = False
        is_upcoming = False
        is_closed = False
        is_available = desc_qs.exists()

        if is_available:
            # Open if at least one record is active now
            is_open = desc_qs.filter(
                Q(start_datetime__isnull=True) | Q(start_datetime__lte=now),
                Q(end_datetime__isnull=True) | Q(end_datetime__gte=now),
            ).exists()

            # Upcoming if not open and earliest start is in future
            if not is_open and win_start and now < win_start:
                is_upcoming = True

            # Closed if not open and latest end is in past
            if not is_open and win_end and now > win_end:
                is_closed = True

        submitted_at = submitted_at_by_enrollment.get(e.id)

        enrollments.append({
            "obj": e,
            "submitted": submitted_at is not None,
            "submitted_at": submitted_at,
            "is_available": is_available,
            "is_open": is_open,
            "is_upcoming": is_upcoming,
            "is_closed": is_closed,
            "win_start": win_start,
            "win_end": win_end,
        })

    return render(
        request,
        "feedback_management/student/end_survey/end_course_list.html",
        {
            "student": student,
            "enrollments": enrollments,
            "current_sem": sem,
            "current_year": year,
            "now": now,
        }
    )











from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from user_accounts.models import StudentDetails
from course_management.models import CourseEnrollment, AssignSubjectFaculty, Co_Po_Mapping
from feedback_management.models import CourseOutcomeDescription, gradeupload, CourseOutcomeSubmission
from faculty_management.models import general_information


@check_permission("course_end_survey")
def course_end_survey_form(request):
    from django.contrib import messages
    from django.db import transaction
    from django.db.models import Q
    from django.shortcuts import get_object_or_404, redirect, render
    from django.utils import timezone

    enrollment_id = (
        request.GET.get("enrollment_id")
        if request.method == "GET"
        else request.POST.get("enrollment_id")
    )


    student = get_student_details(request)

    if not student:
        messages.error(request, "Student record not found.")
        return redirect("home")


    if not enrollment_id:
        messages.error(request, "Enrollment information is missing.")
        return redirect("course_end_survey")

    # ---------------------------------------------------------
    # Get the selected course enrollment
    # ---------------------------------------------------------
    enrollment = get_object_or_404(
        CourseEnrollment.objects.select_related(
            "course",
            "faculty",
            "department",
            "regulation",
        ),
        pk=enrollment_id,
        student=student,
        enroll=True,
    )

    course = enrollment.course
    now = timezone.now()


    # ---------------------------------------------------------
    # Find faculty assignment for this student/course
    # ---------------------------------------------------------
    assign_qs = AssignSubjectFaculty.objects.filter(
        course=course,
        faculty=enrollment.faculty,
        is_active=True,
    )

    if getattr(enrollment, "department", None):
        assign_qs = assign_qs.filter(
            department=enrollment.department
        )

    if getattr(enrollment, "regulation", None):
        assign_qs = assign_qs.filter(
            regulation=enrollment.regulation
        )

    if getattr(enrollment, "batch", None):
        assign_qs = assign_qs.filter(
            batch=enrollment.batch
        )

    if getattr(enrollment, "section", None):
        assign_qs = assign_qs.filter(
            section=enrollment.section
        )

    selected_assignment = assign_qs.order_by("id").first()


    # ---------------------------------------------------------
    # Find CO-PO mappings
    # ---------------------------------------------------------
    if selected_assignment:
        co_po_mappings = list(
            Co_Po_Mapping.objects
            .filter(
                assigned_faculty=selected_assignment,
                course=course,
            )
            .select_related(
                "course",
                "co_number",
                "assigned_faculty",
            )
            .order_by("id")
        )
    else:
        co_po_mappings = []

    # Fallback to course-level mappings when an exact faculty
    # assignment mapping is unavailable.
    if not co_po_mappings:

        co_po_mappings = list(
            Co_Po_Mapping.objects
            .filter(course=course)
            .select_related(
                "course",
                "co_number",
                "assigned_faculty",
            )
            .order_by("id")
        )


    # ---------------------------------------------------------
    # Get questions only from CourseOutcomeDescription
    # co_description column
    # ---------------------------------------------------------
    saved_descriptions_qs = (
        CourseOutcomeDescription.objects
        .filter(
            co_po_mapping__in=co_po_mappings,
        )
        .exclude(co_description__isnull=True)
        .exclude(co_description__exact="")
        .select_related(
            "co_po_mapping",
            "co_po_mapping__co_number",
            "co_po_mapping__course",
            "co_po_mapping__assigned_faculty",
        )
        .order_by(
            "co_po_mapping_id",
            "id",
        )
    )

    saved_descriptions = list(saved_descriptions_qs)


    # ---------------------------------------------------------
    # Build survey questions
    #
    # The question shown to the student is strictly taken from:
    # CourseOutcomeDescription.co_description
    # ---------------------------------------------------------
    survey_questions = []

    # Keep one question for each mapping because the existing
    # CourseOutcomeSubmission model stores co_po_mapping.
    #
    # If duplicate CourseOutcomeDescription rows exist for the same
    # mapping, the first valid description is used.
    used_mapping_ids = set()

    for description in saved_descriptions:
        mapping = description.co_po_mapping

        if mapping.id in used_mapping_ids:
            continue

        used_mapping_ids.add(mapping.id)

        co_label = ""

        if (
            getattr(mapping, "co_number", None)
            and getattr(mapping.co_number, "co_code", None)
        ):
            co_label = str(mapping.co_number.co_code).strip()

        elif (
            getattr(mapping, "co_number", None)
            and getattr(mapping.co_number, "co_number", None)
        ):
            co_label = str(mapping.co_number.co_number).strip()

        if not co_label:
            co_label = f"CO {len(survey_questions) + 1}"

        survey_questions.append({
            "mapping": mapping,
            "mapping_id": mapping.id,
            "description_obj": description,
            "description_id": description.id,
            "co_label": co_label,

            # This is the only question text sent to the template.
            "question": description.co_description.strip(),

            "start_datetime": description.start_datetime,
            "end_datetime": description.end_datetime,
        })


    # Only mappings having a valid co_description should be submitted.
    question_mappings = [
        item["mapping"]
        for item in survey_questions
    ]

    # ---------------------------------------------------------
    # Description maps
    #
    # Retained for compatibility with the existing template.
    # ---------------------------------------------------------
    saved_desc_map = {
        item["mapping_id"]: item["description_obj"]
        for item in survey_questions
    }

    # ---------------------------------------------------------
    # Survey open window
    #
    # Check only descriptions that are displayed as questions.
    # ---------------------------------------------------------
    displayed_description_ids = [
        item["description_id"]
        for item in survey_questions
    ]

    displayed_descriptions_qs = (
        CourseOutcomeDescription.objects
        .filter(id__in=displayed_description_ids)
    )

    is_open = False

    if displayed_description_ids:
        is_open = displayed_descriptions_qs.filter(
            Q(start_datetime__isnull=True)
            | Q(start_datetime__lte=now),
            Q(end_datetime__isnull=True)
            | Q(end_datetime__gte=now),
        ).exists()

    window_start = (
        displayed_descriptions_qs
        .filter(start_datetime__isnull=False)
        .order_by("start_datetime")
        .values_list("start_datetime", flat=True)
        .first()
    )

    window_end = (
        displayed_descriptions_qs
        .filter(end_datetime__isnull=False)
        .order_by("-end_datetime")
        .values_list("end_datetime", flat=True)
        .first()
    )


    # ---------------------------------------------------------
    # Grade options
    # ---------------------------------------------------------
    grade_options = list(
        gradeupload.objects
        .all()
        .order_by("-marks", "grade")
    )


    if not grade_options:
        messages.warning(
            request,
            "Grade options are not configured.",
        )
        return redirect("course_end_survey")

    # ---------------------------------------------------------
    # Existing submissions by this student
    #
    # Restrict to the mappings that have displayed descriptions.
    # ---------------------------------------------------------
    existing_submissions = list(
        CourseOutcomeSubmission.objects
        .filter(
            student=student,
            enrollment=enrollment,
            course=course,
            co_po_mapping__in=question_mappings,
        )
        .select_related(
            "co_po_mapping",
            "selected_grade",
        )
        .order_by("co_po_mapping_id")
    )

    already_submitted = len(existing_submissions) > 0

    submission_map = {
        obj.co_po_mapping_id: obj
        for obj in existing_submissions
    }


    # Add existing selected submission to every survey item.
    for item in survey_questions:
        item["submission"] = submission_map.get(
            item["mapping_id"]
        )

    # ---------------------------------------------------------
    # POST submit
    # ---------------------------------------------------------
    if request.method == "POST":

        if not survey_questions:
            messages.error(
                request,
                "No course outcome questions are available "
                "for this subject.",
            )
            return redirect(
                f"{request.path}?enrollment_id={enrollment.id}"
            )

        if not is_open:
            messages.error(
                request,
                "Course end survey is not open now.",
            )
            return redirect(
                f"{request.path}?enrollment_id={enrollment.id}"
            )

        if already_submitted:
            messages.warning(
                request,
                "You have already submitted this course end survey.",
            )
            return redirect(
                f"{request.path}?enrollment_id={enrollment.id}"
            )

        submission_rows = []

        # Iterate through CourseOutcomeDescription-based questions,
        # not through every CO-PO mapping.
        for index, item in enumerate(survey_questions, start=1):
            mapping = item["mapping"]
            description_obj = item["description_obj"]
            co_label = item["co_label"]
            question_text = item["question"]

            field_name = f"co_{mapping.id}"
            grade_id_raw = (
                request.POST.get(field_name) or ""
            ).strip()


            if not grade_id_raw:
                messages.error(
                    request,
                    f"Please select a grade for {co_label}.",
                )
                return redirect(
                    f"{request.path}?enrollment_id={enrollment.id}"
                )

            try:
                grade_obj = gradeupload.objects.get(
                    pk=int(grade_id_raw)
                )

            except (ValueError, TypeError, gradeupload.DoesNotExist):
                messages.error(
                    request,
                    "Invalid grade selected.",
                )
                return redirect(
                    f"{request.path}?enrollment_id={enrollment.id}"
                )

            try:
                score_value = int(grade_obj.marks or 0)
            except (TypeError, ValueError):
                score_value = 0

            submission_rows.append(
                CourseOutcomeSubmission(
                    student=student,
                    enrollment=enrollment,
                    course=course,
                    faculty=enrollment.faculty,
                    co_po_mapping=mapping,
                    selected_grade=grade_obj,
                    score=score_value,
                )
            )


        try:
            with transaction.atomic():
                created_submissions = (
                    CourseOutcomeSubmission.objects.bulk_create(
                        submission_rows
                    )
                )


            messages.success(
                request,
                "Course end survey submitted successfully.",
            )
            return redirect("course_end_survey")

        except Exception as error:

            messages.error(
                request,
                f"Error saving course end survey: {str(error)}",
            )
            return redirect(
                f"{request.path}?enrollment_id={enrollment.id}"
            )

    # ---------------------------------------------------------
    # GET
    # ---------------------------------------------------------

    return render(
        request,
        "feedback_management/student/end_survey/end_survey_form.html",
        {
            "student": student,
            "enrollment": enrollment,
            "course": course,
            "selected_assignment": selected_assignment,

            # Contains only mappings that have a valid description.
            "co_po_mappings": question_mappings,

            # Use this variable in the template to display questions.
            "survey_questions": survey_questions,

            # Retained for compatibility with the old template.
            "saved_desc_map": saved_desc_map,

            "is_open": is_open,
            "window_start": window_start,
            "window_end": window_end,
            "grade_options": grade_options,
            "already_submitted": already_submitted,
            "submission_map": submission_map,
        },
    )


import os
from collections import defaultdict

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from user_accounts.decorators import check_permission
from faculty_management.models import general_information
from user_accounts.models import StudentDetails
from course_management.models import CourseEnrollment, Course, AssignSubjectFaculty, Co_Po_Mapping
from feedback_management.models import CourseOutcomeDescription
from feedback_management.models import CourseOutcomeSubmission


from collections import defaultdict

from django.contrib import messages
from django.shortcuts import get_object_or_404, render

from user_accounts.decorators import check_permission
from faculty_management.models import general_information
from user_accounts.models import StudentDetails
from course_management.models import (
    CourseEnrollment,
    Course,
    AssignSubjectFaculty,
    Co_Po_Mapping,
)
from feedback_management.models import CourseOutcomeDescription
from feedback_management.models import CourseOutcomeSubmission


from collections import defaultdict

from django.contrib import messages
from django.shortcuts import get_object_or_404, render

from collections import defaultdict
from django.shortcuts import get_object_or_404, render

@check_permission("end_survey")
def end_survey(request):
    # ---------------------------------------------------------
    # faculty
    # ---------------------------------------------------------
    user_employee_id = request.user.Employee_id
    faculty = get_object_or_404(
        general_information.objects.select_related("department"),
        faculty_id=user_employee_id
    )
    department = faculty.department

    # ---------------------------------------------------------
    # all assigned subjects for this faculty
    # ---------------------------------------------------------
    assigned_subjects = (
        AssignSubjectFaculty.objects
        .select_related("course", "department", "regulation", "faculty")
        .filter(
            Q(faculty=faculty) | Q(skilled_faculty=faculty),
            department=department,
            is_active=True,
            course__isnull=False
        )
        .order_by(
            "academic_year",
            "course__year",
            "course__semester",
            "course__course_code",
            "section",
            "batch",
            "id"
        )
    )

    # ---------------------------------------------------------
    # filters
    # ---------------------------------------------------------
    sel_batch = (request.GET.get("batch") or "").strip()
    sel_year = (request.GET.get("year") or "").strip()
    sel_sem = (request.GET.get("semester") or "").strip()
    sel_section = (request.GET.get("section") or "").strip()
    sel_assign_id = (request.GET.get("assign_id") or "").strip()

    filters_applied = bool(sel_year and sel_sem)

    # ---------------------------------------------------------
    # dropdown values from faculty assigned subjects only
    # ---------------------------------------------------------
    batches = (
        assigned_subjects.exclude(batch__isnull=True)
        .exclude(batch__exact="")
        .values_list("batch", flat=True)
        .distinct()
        .order_by("batch")
    )

    years = (
        assigned_subjects.exclude(course__year__isnull=True)
        .exclude(course__year__exact="")
        .values_list("course__year", flat=True)
        .distinct()
        .order_by("course__year")
    )

    semesters = (
        assigned_subjects.exclude(course__semester__isnull=True)
        .exclude(course__semester__exact="")
        .values_list("course__semester", flat=True)
        .distinct()
        .order_by("course__semester")
    )

    sections = (
        assigned_subjects.exclude(section__isnull=True)
        .exclude(section__exact="")
        .values_list("section", flat=True)
        .distinct()
        .order_by("section")
    )

    # ---------------------------------------------------------
    # filtered assignments
    # ---------------------------------------------------------
    filtered_assignments = assigned_subjects

    if sel_batch:
        filtered_assignments = filtered_assignments.filter(batch=sel_batch)

    if sel_section:
        filtered_assignments = filtered_assignments.filter(section=sel_section)

    if sel_year:
        filtered_assignments = filtered_assignments.filter(course__year=str(sel_year))

    if sel_sem:
        filtered_assignments = filtered_assignments.filter(course__semester=str(sel_sem))

    course_assignments = list(filtered_assignments)

    if filters_applied and not sel_assign_id and course_assignments:
        sel_assign_id = str(course_assignments[0].id)

    valid_assign_ids = {str(a.id) for a in course_assignments}
    if sel_assign_id and sel_assign_id not in valid_assign_ids:
        sel_assign_id = ""

    # ---------------------------------------------------------
    # selected assignment / course
    # ---------------------------------------------------------
    selected_assignment = None
    selected_course = None

    if sel_assign_id:
        selected_assignment = filtered_assignments.filter(id=sel_assign_id).first()
        if selected_assignment:
            selected_course = selected_assignment.course

    # ---------------------------------------------------------
    # students for selected assignment only
    # ---------------------------------------------------------
    students = []

    if selected_assignment:
        enroll_qs = (
            CourseEnrollment.objects
            .select_related("student", "course", "faculty", "department")
            .filter(
                department=selected_assignment.department,
                course_id=selected_assignment.course_id,
                enroll=True
            )
        )

        if selected_assignment.batch:
            enroll_qs = enroll_qs.filter(batch=selected_assignment.batch)

        if selected_assignment.section:
            enroll_qs = enroll_qs.filter(section=selected_assignment.section)

        if selected_assignment.course and selected_assignment.course.year:
            enroll_qs = enroll_qs.filter(student__year=str(selected_assignment.course.year))

        if selected_assignment.course and selected_assignment.course.semester:
            enroll_qs = enroll_qs.filter(student__semester=str(selected_assignment.course.semester))

        students = [
            obj.student
            for obj in enroll_qs.order_by("student__reg_no")
            if obj.student
        ]

    student_ids = [s.id for s in students]

    # ---------------------------------------------------------
    # CO mappings for selected assignment
    # ---------------------------------------------------------
    co_po_mappings = []

    if selected_assignment and selected_course:
        co_po_mappings = list(
            Co_Po_Mapping.objects
            .filter(
                assigned_faculty=selected_assignment,
                course=selected_course
            )
            .select_related("course", "co_number", "assigned_faculty")
            .order_by("id")
        )

        if not co_po_mappings:
            co_po_mappings = list(
                Co_Po_Mapping.objects
                .filter(course=selected_course)
                .select_related("course", "co_number", "assigned_faculty")
                .order_by("id")
            )

    # ---------------------------------------------------------
    # CO descriptions
    # ---------------------------------------------------------
    saved_descriptions = (
        CourseOutcomeDescription.objects
        .filter(co_po_mapping__in=co_po_mappings)
        .select_related("co_po_mapping")
        .order_by("id")
    )

    saved_desc_map = {
        obj.co_po_mapping_id: obj
        for obj in saved_descriptions
    }

    ordered_questions = []
    for i, mapping in enumerate(co_po_mappings, start=1):
        co_label = (
            mapping.co_number.co_code
            if getattr(mapping, "co_number", None) and getattr(mapping.co_number, "co_code", None)
            else (
                mapping.co_number.co_number
                if getattr(mapping, "co_number", None) and getattr(mapping.co_number, "co_number", None)
                else f"CO {i}"
            )
        )

        saved_obj = saved_desc_map.get(mapping.id)
        question_text = (
            saved_obj.co_description.strip()
            if saved_obj and saved_obj.co_description
            else "-"
        )

        mapping.question_text = f"{co_label} - {question_text}"
        mapping.category = "Course Outcomes"
        ordered_questions.append(mapping)

    # ---------------------------------------------------------
    # category spans
    # ---------------------------------------------------------
    category_spans = []
    if ordered_questions:
        category_spans.append({
            "category": "Course Outcomes",
            "span": len(ordered_questions)
        })

    # ---------------------------------------------------------
    # submissions for selected assignment only
    # ---------------------------------------------------------
    submitted_student_ids = set()
    student_q_marks = defaultdict(dict)
    student_total = defaultdict(int)

    if selected_assignment and student_ids and ordered_questions:
        mapping_ids = [obj.id for obj in ordered_questions]

        submission_qs = (
            CourseOutcomeSubmission.objects
            .filter(
                student_id__in=student_ids,
                course_id=selected_assignment.course_id,
                co_po_mapping_id__in=mapping_ids,
                faculty=selected_assignment.faculty
            )
            .select_related(
                "student",
                "course",
                "co_po_mapping",
                "selected_grade",
                "faculty",
                "enrollment"
            )
            .order_by("student__reg_no", "co_po_mapping_id")
        )

        if selected_assignment.batch:
            submission_qs = submission_qs.filter(enrollment__batch=selected_assignment.batch)

        if selected_assignment.section:
            submission_qs = submission_qs.filter(enrollment__section=selected_assignment.section)

        if selected_assignment.department:
            submission_qs = submission_qs.filter(enrollment__department=selected_assignment.department)

        for sub in submission_qs:
            sid = sub.student_id
            mid = sub.co_po_mapping_id
            score = int(sub.score or 0)

            submitted_student_ids.add(sid)
            student_q_marks[sid][mid] = score
            student_total[sid] += score

    # ---------------------------------------------------------
    # rows
    # ---------------------------------------------------------
    rows = []
    for idx, st in enumerate(students, start=1):
        rows.append({
            "sno": idx,
            "reg_no": st.reg_no or "-",
            "student_name": getattr(st, "student_name", "") or getattr(st, "name", "") or "-",
            "marks": student_q_marks.get(st.id, {}),
            "total": student_total.get(st.id, 0),
        })

    return render(
        request,
        "feedback_management/faculty/end_survey/subject_end_survey.html",
        {
            "faculty": faculty,
            "department": department,

            "batches": batches,
            "years": years,
            "semesters": semesters,
            "sections": sections,

            "sel_batch": sel_batch,
            "sel_year": sel_year,
            "sel_sem": sel_sem,
            "sel_section": sel_section,
            "sel_assign_id": sel_assign_id,

            "filters_applied": filters_applied,
            "course_assignments": course_assignments,

            "selected_assignment": selected_assignment,
            "selected_course": selected_course,

            "total_students": len(students),
            "submitted_students": len(submitted_student_ids),
            "not_submitted_students": len(students) - len(submitted_student_ids),

            "category_spans": category_spans,
            "ordered_questions": ordered_questions,
            "rows": rows,
        }
    )


from collections import defaultdict
from datetime import datetime

from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from user_accounts.decorators import check_permission
from faculty_management.models import general_information
from user_accounts.models import StudentDetails
from course_management.models import (
    CourseEnrollment,
    Course,
    AssignSubjectFaculty,
    Co_Po_Mapping,
)
from feedback_management.models import CourseOutcomeDescription
from feedback_management.models import CourseOutcomeSubmission


from reportlab.lib.pagesizes import A4, landscape
@check_permission("end_survey")
def end_survey_pdf(request):

    # ---------------------------------------------------------
    # faculty
    # ---------------------------------------------------------
    user_employee_id = request.user.Employee_id
    faculty = get_object_or_404(
        general_information.objects.select_related("department"),
        faculty_id=user_employee_id
    )
    department = faculty.department

    # ---------------------------------------------------------
    # filters
    # ---------------------------------------------------------
    sel_batch = (request.GET.get("batch") or "").strip()
    sel_year = (request.GET.get("year") or "").strip()
    sel_sem = (request.GET.get("semester") or "").strip()
    sel_section = (request.GET.get("section") or "").strip()
    sel_course_id = (request.GET.get("course_id") or "").strip()

    filters_applied = bool(sel_year and sel_sem)

    # ---------------------------------------------------------
    # faculty assigned courses
    # ---------------------------------------------------------
    assign_qs = (
        AssignSubjectFaculty.objects
        .filter(
            department=department,
            faculty=faculty,
            is_active=True,
            course__isnull=False
        )
        .select_related("course", "faculty", "department", "regulation")
    )

    if sel_batch:
        assign_qs = assign_qs.filter(batch=sel_batch)
    if sel_section:
        assign_qs = assign_qs.filter(section=sel_section)
    if sel_year:
        assign_qs = assign_qs.filter(course__year=str(sel_year))
    if sel_sem:
        assign_qs = assign_qs.filter(course__semester=str(sel_sem))

    faculty_course_ids = list(assign_qs.values_list("course_id", flat=True).distinct())

    if filters_applied and not sel_course_id and faculty_course_ids:
        sel_course_id = str(faculty_course_ids[0])

    if not (sel_year and sel_sem and sel_course_id):
        return HttpResponseBadRequest("Select Year, Semester and Course to generate PDF.")

    selected_assignment = None
    selected_course = None

    filtered_assign_qs = (
        AssignSubjectFaculty.objects
        .select_related("faculty", "course", "department")
        .filter(
            department=department,
            faculty=faculty,
            course_id=sel_course_id,
            is_active=True
        )
    )

    if sel_batch:
        filtered_assign_qs = filtered_assign_qs.filter(batch=sel_batch)
    if sel_section:
        filtered_assign_qs = filtered_assign_qs.filter(section=sel_section)
    if sel_year:
        filtered_assign_qs = filtered_assign_qs.filter(course__year=str(sel_year))
    if sel_sem:
        filtered_assign_qs = filtered_assign_qs.filter(course__semester=str(sel_sem))

    selected_assignment = filtered_assign_qs.first()

    if selected_assignment:
        selected_course = selected_assignment.course
    else:
        selected_course = Course.objects.filter(id=sel_course_id, is_active=True).first()

    if not selected_course:
        return HttpResponseBadRequest("Invalid course.")

    # ---------------------------------------------------------
    # students
    # ---------------------------------------------------------
    enroll_qs = (
        CourseEnrollment.objects
        .select_related("student", "course", "faculty", "department")
        .filter(
            department=department,
            course_id=sel_course_id,
            enroll=True
        )
    )

    if sel_batch:
        enroll_qs = enroll_qs.filter(batch=sel_batch)
    if sel_section:
        enroll_qs = enroll_qs.filter(section=sel_section)
    if sel_year:
        enroll_qs = enroll_qs.filter(student__year=str(sel_year))
    if sel_sem:
        enroll_qs = enroll_qs.filter(student__semester=str(sel_sem))

    students = [
        obj.student
        for obj in enroll_qs.order_by("student__reg_no")
        if obj.student
    ]
    student_ids = [s.id for s in students]

    # ---------------------------------------------------------
    # CO mappings
    # ---------------------------------------------------------
    co_po_mappings = []

    if selected_assignment:
        co_po_mappings = list(
            Co_Po_Mapping.objects
            .filter(
                assigned_faculty=selected_assignment,
                course=selected_course
            )
            .select_related("course", "co_number", "assigned_faculty")
            .order_by("id")
        )

    if not co_po_mappings:
        co_po_mappings = list(
            Co_Po_Mapping.objects
            .filter(course=selected_course)
            .select_related("course", "co_number", "assigned_faculty")
            .order_by("id")
        )

    if not co_po_mappings:
        return HttpResponseBadRequest("No course outcome mappings configured for this course.")

    # ---------------------------------------------------------
    # CO descriptions
    # ---------------------------------------------------------
    saved_descriptions = (
        CourseOutcomeDescription.objects
        .filter(co_po_mapping__in=co_po_mappings)
        .select_related("co_po_mapping")
        .order_by("id")
    )

    saved_desc_map = {
        obj.co_po_mapping_id: obj
        for obj in saved_descriptions
    }

    ordered_questions = []
    category_spans = [{
        "category": "Course Outcomes",
        "span": len(co_po_mappings)
    }]

    for i, mapping in enumerate(co_po_mappings, start=1):
        co_label = (
            mapping.co_number.co_code
            if getattr(mapping, "co_number", None) and getattr(mapping.co_number, "co_code", None)
            else (
                mapping.co_number.co_number
                if getattr(mapping, "co_number", None) and getattr(mapping.co_number, "co_number", None)
                else f"CO {i}"
            )
        )

        saved_obj = saved_desc_map.get(mapping.id)
        question_text = saved_obj.co_description.strip() if saved_obj and saved_obj.co_description else "-"

        mapping.question_text = f"{co_label} - {question_text}"
        mapping.category = "Course Outcomes"
        ordered_questions.append(mapping)

    # ---------------------------------------------------------
    # submissions
    # ---------------------------------------------------------
    student_q_marks = defaultdict(dict)
    student_total = defaultdict(int)

    if sel_course_id and student_ids and ordered_questions:
        mapping_ids = [obj.id for obj in ordered_questions]

        submission_qs = (
            CourseOutcomeSubmission.objects
            .filter(
                student_id__in=student_ids,
                course_id=sel_course_id,
                co_po_mapping_id__in=mapping_ids,
                faculty=faculty
            )
            .select_related(
                "student",
                "course",
                "co_po_mapping",
                "selected_grade",
                "faculty",
                "enrollment"
            )
            .order_by("student__reg_no", "co_po_mapping_id")
        )

        for sub in submission_qs:
            sid = sub.student_id
            mid = sub.co_po_mapping_id
            score = int(sub.score or 0)

            student_q_marks[sid][mid] = score
            student_total[sid] += score

    # ---------------------------------------------------------
    # PDF response
    # ---------------------------------------------------------
    filename = f"EndSurvey_{selected_course.course_code}_{sel_year}_Sem{sel_sem}.pdf"
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'

    PDF_PAGE_SIZE = landscape(A4)

    odd_sem = str(sel_sem) in ["1", "3", "5", "7"]
    subtitle = f"Academic Year: {datetime.now().year}-{datetime.now().year + 1} ({'Odd' if odd_sem else 'Even'} Semester)"

    doc = SimpleDocTemplate(
        response,
        pagesize=PDF_PAGE_SIZE,
        leftMargin=8 * mm,
        rightMargin=8 * mm,
        topMargin=50 * mm,
        bottomMargin=20 * mm,
        title="Course End Survey"
    )

    styles = getSampleStyleSheet()

    info_style = ParagraphStyle(
        "info_style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0f172a"),
        alignment=0,
    )

    p_center = ParagraphStyle(
        "p_center",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=5.8,
        leading=6.5,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a"),
    )

    p_center_bold = ParagraphStyle(
        "p_center_bold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=6.0,
        leading=6.8,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a"),
    )

    story = []

    story.append(Paragraph(f"Name of the Subject: {selected_course.course_code} - {selected_course.title}", info_style))
    story.append(Paragraph(f"Name of the Faculty: {faculty.name}", info_style))
    story.append(
        Paragraph(
            f"Year/Semester: {sel_year} / {sel_sem} &nbsp;&nbsp;&nbsp; Section: {sel_section or '-'} &nbsp;&nbsp;&nbsp; Batch: {sel_batch or '-'}",
            info_style
        )
    )
    story.append(Spacer(1, 8))

    # ---------------------------------------------------------
    # table header
    # ---------------------------------------------------------
    row1 = ["Sl.No"]
    for c in category_spans:
        row1.append(Paragraph(str(c["category"]), p_center))
        for _ in range(c["span"] - 1):
            row1.append("")

    row1.append("Total")

    row2 = [""]
    for q in ordered_questions:
        row2.append(Paragraph(q.question_text, p_center_bold))
    row2.append("")

    data = [row1, row2]

    # ---------------------------------------------------------
    # student rows
    # ---------------------------------------------------------
    for i, st in enumerate(students, start=1):
        row = [str(i)]

        for q in ordered_questions:
            row.append(str(student_q_marks.get(st.id, {}).get(q.id, 0)))

        row.append(str(student_total.get(st.id, 0)))
        data.append(row)

    if not students:
        no_data_row = ["No students found."]
        no_data_row += [""] * len(ordered_questions)
        no_data_row += [""]
        data.append(no_data_row)

    # ---------------------------------------------------------
    # widths
    # ---------------------------------------------------------
    page_w, page_h = doc.pagesize
    usable_w = page_w - doc.leftMargin - doc.rightMargin

    col_w_sno = 12 * mm
    col_w_total = 14 * mm

    q_count = len(ordered_questions)
    fixed_width = col_w_sno + col_w_total
    q_w = (usable_w - fixed_width) / float(max(q_count, 1))
    q_w = max(q_w, 18 * mm)

    col_widths = [col_w_sno] + [q_w] * q_count + [col_w_total]

    tbl = Table(data, colWidths=col_widths, repeatRows=2)

    ts = TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d1d5db")),
        ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#f8fafc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),

        ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 1), 6),

        ("FONTNAME", (0, 2), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 2), (-1, -1), 6),

        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ff")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f8fafc")),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#111827")),

        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),

        ("BACKGROUND", (-1, 2), (-1, -1), colors.HexColor("#f8fafc")),
        ("FONTNAME", (-1, 2), (-1, -1), "Helvetica-Bold"),
    ])

    # merge Sl.No
    ts.add("SPAN", (0, 0), (0, 1))

    # merge Total
    ts.add("SPAN", (q_count + 1, 0), (q_count + 1, 1))

    # merge category
    start_col = 1
    for c in category_spans:
        end_col = start_col + c["span"] - 1
        ts.add("SPAN", (start_col, 0), (end_col, 0))
        start_col = end_col + 1

    if not students:
        ts.add("SPAN", (0, 2), (-1, 2))
        ts.add("ALIGN", (0, 2), (-1, 2), "CENTER")
        ts.add("FONTNAME", (0, 2), (-1, 2), "Helvetica-Oblique")

    tbl.setStyle(ts)
    story.append(tbl)

    def _on_page(canv, doc_):
        pw, ph = doc_.pagesize
        _draw_rit_header_footer(
            canv,
            pw,
            ph,
            title="COURSE END SURVEY",
            subtitle=subtitle
        )

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return response


from collections import defaultdict
from datetime import datetime

from django.contrib import messages
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render
from django.db.models import Q

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
)

from faculty_management.models import general_information
from user_accounts.models import Add_Department, StudentDetails
from course_management.models import Course, CourseEnrollment, Co_Po_Mapping, AssignSubjectFaculty
from feedback_management.models import CourseOutcomeDescription
from feedback_management.models import end_survey_data_Permission
from feedback_management.models import CourseOutcomeSubmission  

def _get_end_survey_permission_scope(request):
    role_id = getattr(request.user, "role_id", None)

    perm = end_survey_data_Permission.objects.filter(role_id=role_id).first()

    if not perm:
        return {
            "has_access": False,
            "can_view_all": False,
            "can_view_department": False,
        }

    return {
        "has_access": bool(
            perm.can_view_all_end_survey_data or
            perm.can_view_department_end_survey_data
        ),
        "can_view_all": bool(perm.can_view_all_end_survey_data),
        "can_view_department": bool(perm.can_view_department_end_survey_data),
    }


from collections import defaultdict

from django.http import HttpResponseForbidden
from django.shortcuts import render

from user_accounts.decorators import check_permission
from faculty_management.models import general_information
from user_accounts.models import Add_Department, StudentDetails
from course_management.models import Course, CourseEnrollment, Co_Po_Mapping
from feedback_management.models import CourseOutcomeDescription
from feedback_management.models import CourseOutcomeSubmission


@check_permission("view_end_survey")
def view_end_survey(request):
    from collections import defaultdict
    from django.db.models import Q
    from django.http import HttpResponseForbidden
    from django.shortcuts import render

    user = request.user.Employee_id
    faculty = general_information.objects.select_related("department").get(faculty_id=user)
    faculty_department = faculty.department

    permission_scope = _get_end_survey_permission_scope(request)

    if not permission_scope["has_access"]:
        return HttpResponseForbidden("You do not have permission to view end survey data.")

    # ---------------------------------------------------------
    # Read request params
    # ---------------------------------------------------------
    if request.method == "POST":
        sel_department_id = (request.POST.get("department_id") or "").strip()
        sel_batch = (request.POST.get("batch") or "").strip()
        sel_year = (request.POST.get("year") or "").strip()
        sel_sem = (request.POST.get("semester") or "").strip()
        sel_section = (request.POST.get("section") or "").strip()
        sel_course_id = (request.POST.get("course_id") or "").strip()
    else:
        sel_department_id = (request.GET.get("department_id") or "").strip()
        sel_batch = (request.GET.get("batch") or "").strip()
        sel_year = (request.GET.get("year") or "").strip()
        sel_sem = (request.GET.get("semester") or "").strip()
        sel_section = (request.GET.get("section") or "").strip()
        sel_course_id = (request.GET.get("course_id") or "").strip()

    # ---------------------------------------------------------
    # Department permission scope
    # ---------------------------------------------------------
    if permission_scope["can_view_all"]:
        departments = Add_Department.objects.filter(
            is_active=True
        ).order_by("Department")

        if sel_department_id:
            department = Add_Department.objects.filter(
                id=sel_department_id,
                is_active=True
            ).first()
        else:
            department = faculty_department or departments.first()
    else:
        department = faculty_department
        departments = (
            Add_Department.objects.filter(id=faculty_department.id)
            if faculty_department else Add_Department.objects.none()
        )

    sel_department_id = str(department.id) if department else ""

    # ---------------------------------------------------------
    # Base students by selected department
    # Remove discontinued students globally
    # ---------------------------------------------------------
    if department:
        base_students_qs = StudentDetails.objects.filter(
            department=department,
            is_discontinued=False
        )
    else:
        base_students_qs = StudentDetails.objects.none()

    # ---------------------------------------------------------
    # Filter dropdown querysets
    # ---------------------------------------------------------
    students_for_filters = base_students_qs

    if sel_batch:
        students_for_filters = students_for_filters.filter(batch=sel_batch)

    batches = (
        base_students_qs
        .exclude(batch__isnull=True)
        .exclude(batch__exact="")
        .values_list("batch", flat=True)
        .distinct()
        .order_by("batch")
    )

    years = (
        students_for_filters
        .exclude(year__isnull=True)
        .exclude(year__exact="")
        .values_list("year", flat=True)
        .distinct()
        .order_by("year")
    )

    sem_filter_qs = students_for_filters

    if sel_year:
        sem_filter_qs = sem_filter_qs.filter(year=str(sel_year))

    semesters = (
        sem_filter_qs
        .exclude(semester__isnull=True)
        .exclude(semester__exact="")
        .values_list("semester", flat=True)
        .distinct()
        .order_by("semester")
    )

    section_filter_qs = sem_filter_qs

    if sel_sem:
        section_filter_qs = section_filter_qs.filter(semester=str(sel_sem))

    sections = (
        section_filter_qs
        .exclude(section__isnull=True)
        .exclude(section__exact="")
        .values_list("section", flat=True)
        .distinct()
        .order_by("section")
    )

    filters_applied = bool(department and sel_year and sel_sem)

    # ---------------------------------------------------------
    # Courses dropdown
    # ---------------------------------------------------------
    if department:
        courses_qs = Course.objects.filter(
            department=department,
            is_active=True
        )
    else:
        courses_qs = Course.objects.none()

    if sel_year:
        courses_qs = courses_qs.filter(year=str(sel_year))

    if sel_sem:
        courses_qs = courses_qs.filter(semester=str(sel_sem))

    if sel_batch or sel_section:
        enroll_course_ids = CourseEnrollment.objects.filter(
            department=department,
            enroll=True,
            student__is_discontinued=False,
        )

        if sel_batch:
            enroll_course_ids = enroll_course_ids.filter(batch=sel_batch)

        if sel_section:
            enroll_course_ids = enroll_course_ids.filter(section=sel_section)

        if sel_year:
            enroll_course_ids = enroll_course_ids.filter(student__year=str(sel_year))

        if sel_sem:
            enroll_course_ids = enroll_course_ids.filter(student__semester=str(sel_sem))

        course_ids = enroll_course_ids.values_list(
            "course_id",
            flat=True
        ).distinct()

        courses_qs = courses_qs.filter(id__in=course_ids)

    courses = courses_qs.values(
        "id",
        "title",
        "course_code"
    ).order_by("course_code")

    selected_course = None

    if department and sel_course_id:
        selected_course = Course.objects.filter(
            id=sel_course_id,
            department=department
        ).first()

    # ---------------------------------------------------------
    # Students list
    # ---------------------------------------------------------
    if department and sel_course_id:
        enroll_qs = CourseEnrollment.objects.select_related("student").filter(
            department=department,
            course_id=sel_course_id,
            enroll=True,
            student__is_discontinued=False,
        )

        if sel_batch:
            enroll_qs = enroll_qs.filter(batch=sel_batch)

        if sel_year:
            enroll_qs = enroll_qs.filter(student__year=str(sel_year))

        if sel_sem:
            enroll_qs = enroll_qs.filter(student__semester=str(sel_sem))

        if sel_section:
            enroll_qs = enroll_qs.filter(section=sel_section)

        students = [
            enr.student
            for enr in enroll_qs.order_by("student__reg_no")
            if enr.student and not enr.student.is_discontinued
        ]
    else:
        students_qs = base_students_qs

        if sel_batch:
            students_qs = students_qs.filter(batch=sel_batch)

        if sel_year:
            students_qs = students_qs.filter(year=str(sel_year))

        if sel_sem:
            students_qs = students_qs.filter(semester=str(sel_sem))

        if sel_section:
            students_qs = students_qs.filter(section=sel_section)

        students = list(students_qs.order_by("reg_no"))

    student_ids = [student.id for student in students]

    # ---------------------------------------------------------
    # CO mappings + descriptions
    # ---------------------------------------------------------
    co_po_mappings = []

    if selected_course:
        co_po_mappings = list(
            Co_Po_Mapping.objects
            .select_related("co_number", "course")
            .filter(course=selected_course)
            .order_by("id")
        )

    desc_qs = CourseOutcomeDescription.objects.filter(
        co_po_mapping__in=co_po_mappings
    ).select_related("co_po_mapping")

    desc_map = {
        d.co_po_mapping_id: d
        for d in desc_qs
    }

    for idx, mapping in enumerate(co_po_mappings, start=1):
        desc_obj = desc_map.get(mapping.id)

        mapping.display_co = (
            getattr(getattr(mapping, "co_number", None), "co_code", None)
            or f"CO{idx}"
        )

        mapping.saved_desc = (
            desc_obj.co_description
            if desc_obj and desc_obj.co_description
            else "-"
        )

        mapping.start_datetime = desc_obj.start_datetime if desc_obj else None
        mapping.end_datetime = desc_obj.end_datetime if desc_obj else None

    mapping_ids = [m.id for m in co_po_mappings]

    # ---------------------------------------------------------
    # Submissions
    # ---------------------------------------------------------
    student_co_scores = defaultdict(dict)
    student_total = defaultdict(int)
    submitted_student_ids = set()

    if selected_course and student_ids and mapping_ids:
        submissions_qs = (
            CourseOutcomeSubmission.objects
            .filter(
                student_id__in=student_ids,
                student__is_discontinued=False,
                course=selected_course,
                co_po_mapping_id__in=mapping_ids
            )
            .select_related(
                "student",
                "course",
                "faculty",
                "co_po_mapping",
                "selected_grade",
                "enrollment"
            )
            .order_by("student_id", "co_po_mapping_id")
        )

        for sub in submissions_qs:
            sid = sub.student_id
            mid = sub.co_po_mapping_id
            score_value = int(sub.score or 0)

            submitted_student_ids.add(sid)
            student_co_scores[sid][mid] = score_value
            student_total[sid] += score_value

    # ---------------------------------------------------------
    # Rows
    # ---------------------------------------------------------
    rows = []

    for idx, st in enumerate(students, start=1):
        mark_list = [
            student_co_scores.get(st.id, {}).get(m.id, "-")
            for m in co_po_mappings
        ]

        rows.append({
            "sno": idx,
            "student_id": st.id,
            "student_name": getattr(st, "student_name", "") or getattr(st, "name", "") or "-",
            "reg_no": getattr(st, "reg_no", "") or "-",
            "mark_list": mark_list,
            "total": student_total.get(st.id, 0),
            "is_submitted": st.id in submitted_student_ids,
        })

    return render(
        request,
        "feedback_management/faculty/end_survey/course_end_survey.html",
        {
            "faculty": faculty,
            "department": department,
            "faculty_department": faculty_department,
            "departments": departments,

            "can_view_all_end_survey_data": permission_scope["can_view_all"],
            "can_view_department_end_survey_data": permission_scope["can_view_department"],

            "batches": batches,
            "years": years,
            "semesters": semesters,
            "sections": sections,

            "sel_department_id": sel_department_id,
            "sel_batch": sel_batch,
            "sel_year": sel_year,
            "sel_sem": sel_sem,
            "sel_section": sel_section,
            "sel_course_id": sel_course_id,

            "filters_applied": filters_applied,
            "courses": courses,
            "selected_course": selected_course,

            "total_students": len(students),
            "submitted_students": len(submitted_student_ids),
            "not_submitted_students": len(students) - len(submitted_student_ids),

            "co_po_mappings": co_po_mappings,
            "rows": rows,
        }
    )


from reportlab.lib.pagesizes import A4, landscape

@check_permission("view_end_survey")
def view_end_survey_bulk_pdf(request):
    from collections import defaultdict
    from datetime import datetime

    from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        PageBreak,
        Table,
        TableStyle,
    )

    user = request.user.Employee_id
    faculty = general_information.objects.select_related("department").get(faculty_id=user)
    faculty_department = faculty.department

    permission_scope = _get_end_survey_permission_scope(request)

    if not permission_scope["has_access"]:
        return HttpResponseForbidden("You do not have permission to view end survey data.")

    sel_department_id = (request.GET.get("department_id") or "").strip()
    sel_batch = (request.GET.get("batch") or "").strip()
    sel_year = (request.GET.get("year") or "").strip()
    sel_sem = (request.GET.get("semester") or "").strip()
    sel_section = (request.GET.get("section") or "").strip()

    if permission_scope["can_view_all"]:
        if sel_department_id:
            department = Add_Department.objects.filter(
                id=sel_department_id,
                is_active=True
            ).first()
        else:
            department = faculty_department
    else:
        department = faculty_department

    if not department:
        return HttpResponseBadRequest("Invalid department.")

    if not (sel_year and sel_sem):
        return HttpResponseBadRequest("Select Year and Semester to generate Bulk PDF.")

    courses_qs = Course.objects.filter(
        department=department,
        year=str(sel_year),
        semester=str(sel_sem),
        is_active=True
    )

    if sel_batch or sel_section:
        enroll_course_qs = CourseEnrollment.objects.filter(
            department=department,
            enroll=True,
            student__is_discontinued=False,
        )

        if sel_batch:
            enroll_course_qs = enroll_course_qs.filter(batch=sel_batch)

        if sel_section:
            enroll_course_qs = enroll_course_qs.filter(section=sel_section)

        enroll_course_qs = enroll_course_qs.filter(
            student__year=str(sel_year),
            student__semester=str(sel_sem)
        )

        filtered_course_ids = enroll_course_qs.values_list(
            "course_id",
            flat=True
        ).distinct()

        courses_qs = courses_qs.filter(id__in=filtered_course_ids)

    courses = list(courses_qs.order_by("course_code"))

    if not courses:
        return HttpResponseBadRequest("No courses found for the selected filters.")

    PDF_PAGE_SIZE = landscape(A4)

    filename = f"Bulk_End_Survey_{department.Department}_{sel_year}_Sem{sel_sem}.pdf"
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'

    doc = SimpleDocTemplate(
        response,
        pagesize=PDF_PAGE_SIZE,
        leftMargin=8 * mm,
        rightMargin=8 * mm,
        topMargin=50 * mm,
        bottomMargin=20 * mm,
        title="Course End Survey Bulk Report"
    )

    styles = getSampleStyleSheet()

    info_style = ParagraphStyle(
        "info",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0f172a"),
        alignment=0,
    )

    heading_style = ParagraphStyle(
        "heading_style",
        parent=styles["Heading4"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1e3a8a"),
        spaceAfter=6,
    )

    p_center = ParagraphStyle(
        "p_center",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=4.8,
        leading=5.5,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a"),
    )

    p_center_bold = ParagraphStyle(
        "p_center_bold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=5.0,
        leading=5.8,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a"),
    )

    p_small_left = ParagraphStyle(
        "p_small_left",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=5.0,
        leading=5.8,
        alignment=0,
        textColor=colors.HexColor("#0f172a"),
        wordWrap="CJK",
    )

    legend_category_style = ParagraphStyle(
        "legend_category_style",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#1e3a8a"),
        spaceAfter=4,
        spaceBefore=6,
    )

    legend_text_style = ParagraphStyle(
        "legend_text_style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.8,
        leading=12,
        textColor=colors.HexColor("#111827"),
    )

    summary_title_style = ParagraphStyle(
        "summary_title_style",
        parent=styles["Heading4"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1e3a8a"),
        spaceAfter=6,
    )

    academic_year_text = (
        f"Academic Year: {datetime.now().year}-{datetime.now().year + 1} "
        f"({'Odd' if str(sel_sem) in ['1', '3', '5', '7'] else 'Even'} Semester)"
    )

    subtitle = academic_year_text

    story = []
    course_summary_rows = []
    legend_items = []

    for course_index, course in enumerate(courses, start=1):
        assign_qs = AssignSubjectFaculty.objects.select_related(
            "faculty",
            "course"
        ).filter(
            department=department,
            course_id=course.id,
            is_active=True,
        )

        if sel_batch:
            assign_qs = assign_qs.filter(batch=sel_batch)

        if sel_section:
            assign_qs = assign_qs.filter(section=sel_section)

        assign_qs = assign_qs.filter(
            course__year=str(sel_year),
            course__semester=str(sel_sem)
        )

        assign_obj = assign_qs.first()
        mapped_faculty = assign_obj.faculty if assign_obj and assign_obj.faculty else None
        filtered_faculty_name = mapped_faculty.name if mapped_faculty else faculty.name

        enroll_qs = CourseEnrollment.objects.select_related("student").filter(
            department=department,
            course_id=course.id,
            enroll=True,
            student__is_discontinued=False,
        )

        if sel_batch:
            enroll_qs = enroll_qs.filter(batch=sel_batch)

        if sel_section:
            enroll_qs = enroll_qs.filter(section=sel_section)

        enroll_qs = enroll_qs.filter(
            student__year=str(sel_year),
            student__semester=str(sel_sem)
        )

        students = [
            e.student
            for e in enroll_qs.order_by("student__reg_no")
            if e.student and not e.student.is_discontinued
        ]

        student_ids = [s.id for s in students]
        student_count = len(students)

        co_po_mappings = list(
            Co_Po_Mapping.objects
            .select_related("co_number", "course")
            .filter(course=course)
            .order_by("id")
        )

        if not co_po_mappings:
            continue

        desc_qs = CourseOutcomeDescription.objects.filter(
            co_po_mapping__in=co_po_mappings
        )

        desc_map = {
            d.co_po_mapping_id: d
            for d in desc_qs
        }

        for idx, mapping in enumerate(co_po_mappings, start=1):
            desc_obj = desc_map.get(mapping.id)

            mapping.display_co = (
                getattr(getattr(mapping, "co_number", None), "co_code", None)
                or f"CO{idx}"
            )

            mapping.saved_desc = (
                desc_obj.co_description
                if desc_obj and desc_obj.co_description
                else "-"
            )

            legend_items.append({
                "course_code": course.course_code or "-",
                "course_title": course.title or "-",
                "number": idx,
                "co_code": mapping.display_co,
                "description": mapping.saved_desc,
            })

        mapping_ids = [m.id for m in co_po_mappings]

        student_scores = defaultdict(dict)
        student_total = defaultdict(int)
        course_mapping_totals = defaultdict(int)

        if student_ids and mapping_ids:
            submissions = (
                CourseOutcomeSubmission.objects
                .filter(
                    student_id__in=student_ids,
                    student__is_discontinued=False,
                    course=course,
                    co_po_mapping_id__in=mapping_ids
                )
                .select_related("student", "co_po_mapping")
                .order_by("student_id", "co_po_mapping_id")
            )

            for sub in submissions:
                sid = sub.student_id
                mid = sub.co_po_mapping_id
                sc = int(sub.score or 0)

                student_scores[sid][mid] = sc
                student_total[sid] += sc
                course_mapping_totals[mid] += sc

        course_grand_total = sum(course_mapping_totals.values())

        mapping_averages = {}

        if student_count > 0:
            for m in co_po_mappings:
                mapping_averages[m.id] = round(
                    course_mapping_totals.get(m.id, 0) / student_count,
                    2
                )

            course_grand_average = round(course_grand_total / student_count, 2)
        else:
            for m in co_po_mappings:
                mapping_averages[m.id] = 0

            course_grand_average = 0

        course_summary_rows.append({
            "course_code": course.course_code or "-",
            "course_title": course.title or "-",
            "student_count": student_count,
            "mapping_averages": mapping_averages,
            "grand_average": course_grand_average,
            "co_po_mappings": co_po_mappings,
        })

        story.append(
            Paragraph(
                f"Course {course_index}: {course.course_code} - {course.title}",
                heading_style
            )
        )

        story.append(Paragraph(f"Department: {department.Department}", info_style))
        story.append(Paragraph(f"Name of the Faculty: {filtered_faculty_name}", info_style))

        story.append(Paragraph(
            f"Year/Semester: {sel_year} / {sel_sem} &nbsp;&nbsp;&nbsp; "
            f"Section: {sel_section or '-'} &nbsp;&nbsp;&nbsp; Batch: {sel_batch or '-'}",
            info_style
        ))

        story.append(Spacer(1, 6))

        row1 = [Paragraph("Sl.No", p_center_bold)]

        for m in co_po_mappings:
            row1.append(Paragraph(m.display_co, p_center))

        row1.append(Paragraph("Total", p_center_bold))

        row2 = [""]

        for m in co_po_mappings:
            row2.append(Paragraph(m.saved_desc, p_small_left))

        row2.append("")

        data = [row1, row2]

        for i, st in enumerate(students, start=1):
            row = [str(i)]

            for m in co_po_mappings:
                row.append(str(student_scores.get(st.id, {}).get(m.id, "-")))

            row.append(str(student_total.get(st.id, 0)))
            data.append(row)

        if not students:
            no_data_row = ["No students found."]
            no_data_row += [""] * len(co_po_mappings)
            no_data_row += [""]
            data.append(no_data_row)

        page_w, page_h = doc.pagesize
        usable_w = page_w - doc.leftMargin - doc.rightMargin

        col_w_sno = 10 * mm
        col_w_total = 12 * mm

        co_count = len(co_po_mappings)
        fixed_width = col_w_sno + col_w_total
        co_w = (usable_w - fixed_width) / float(max(co_count, 1))
        co_w = max(co_w, 18 * mm)

        total_table_w = fixed_width + (co_w * co_count)

        if total_table_w > usable_w:
            co_w = max(
                (usable_w - fixed_width) / float(max(co_count, 1)),
                8 * mm
            )

        col_widths = [col_w_sno] + [co_w] * co_count + [col_w_total]

        tbl = Table(data, colWidths=col_widths, repeatRows=2)

        table_style = TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d1d5db")),
            ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#f8fafc")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, 1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 1), 5),
            ("FONTNAME", (0, 2), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 2), (-1, -1), 5),
            ("ALIGN", (0, 2), (-1, -1), "CENTER"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ff")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f8fafc")),
            ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#111827")),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("BACKGROUND", (-1, 2), (-1, -1), colors.HexColor("#f8fafc")),
            ("FONTNAME", (-1, 2), (-1, -1), "Helvetica-Bold"),
        ])

        table_style.add("SPAN", (0, 0), (0, 1))
        table_style.add("SPAN", (co_count + 1, 0), (co_count + 1, 1))

        if not students:
            table_style.add("SPAN", (0, 2), (-1, 2))
            table_style.add("ALIGN", (0, 2), (-1, 2), "CENTER")
            table_style.add("FONTNAME", (0, 2), (-1, 2), "Helvetica-Oblique")

        tbl.setStyle(table_style)
        story.append(tbl)

        if course_index < len(courses):
            story.append(PageBreak())

    if not course_summary_rows:
        return HttpResponseBadRequest("No end survey mappings found for the selected filters.")

    story.append(Paragraph("Course-wise CO Average Summary", summary_title_style))
    story.append(Paragraph(f"Department: {department.Department}", info_style))

    story.append(Paragraph(
        f"Year/Semester: {sel_year} / {sel_sem} &nbsp;&nbsp;&nbsp; "
        f"Section: {sel_section or '-'} &nbsp;&nbsp;&nbsp; Batch: {sel_batch or '-'}",
        info_style
    ))

    story.append(Spacer(1, 8))

    max_co_count = max(
        len(item["co_po_mappings"])
        for item in course_summary_rows
    )

    summary_row1 = [Paragraph("Course Code", p_center_bold)]

    for i in range(1, max_co_count + 1):
        summary_row1.append(Paragraph(f"CO{i}", p_center_bold))

    summary_row1.extend([
        Paragraph("Avg Total", p_center_bold),
        Paragraph("Students", p_center_bold)
    ])

    summary_row2 = [""]

    for i in range(1, max_co_count + 1):
        summary_row2.append("")

    summary_row2.extend(["", ""])

    summary_data = [summary_row1, summary_row2]

    for item in course_summary_rows:
        row = [Paragraph(f"{item['course_code']}", p_center_bold)]

        local_mappings = item["co_po_mappings"]

        for m in local_mappings:
            row.append(str(item["mapping_averages"].get(m.id, 0)))

        missing = max_co_count - len(local_mappings)

        if missing > 0:
            row.extend([""] * missing)

        row.extend([
            str(item["grand_average"]),
            str(item["student_count"]),
        ])

        summary_data.append(row)

    page_w, page_h = doc.pagesize
    usable_w = page_w - doc.leftMargin - doc.rightMargin

    summary_course_col_w = 28 * mm
    summary_avg_total_col_w = 18 * mm
    summary_students_col_w = 16 * mm

    summary_fixed_w = (
        summary_course_col_w +
        summary_avg_total_col_w +
        summary_students_col_w
    )

    summary_co_w = (usable_w - summary_fixed_w) / float(max(max_co_count, 1))
    summary_co_w = max(summary_co_w, 12 * mm)

    summary_total_w = summary_fixed_w + (summary_co_w * max_co_count)

    if summary_total_w > usable_w:
        summary_co_w = max(
            (usable_w - summary_fixed_w) / float(max(max_co_count, 1)),
            8 * mm
        )

    summary_col_widths = (
        [summary_course_col_w] +
        [summary_co_w] * max_co_count +
        [summary_avg_total_col_w, summary_students_col_w]
    )

    summary_tbl = Table(summary_data, colWidths=summary_col_widths, repeatRows=2)

    summary_style = TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d1d5db")),
        ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#f8fafc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 1), 6),
        ("FONTNAME", (0, 2), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 2), (-3, -1), "Helvetica"),
        ("FONTNAME", (-2, 2), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 2), (-1, -1), 6),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ff")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f8fafc")),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#111827")),
        ("BACKGROUND", (-2, 2), (-1, -1), colors.HexColor("#f8fafc")),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ])

    summary_style.add("SPAN", (0, 0), (0, 1))
    summary_style.add("SPAN", (-2, 0), (-2, 1))
    summary_style.add("SPAN", (-1, 0), (-1, 1))

    summary_tbl.setStyle(summary_style)
    story.append(summary_tbl)

    story.append(PageBreak())
    story.append(Paragraph("CO Reference / Legend", heading_style))
    story.append(Paragraph(f"Department: {department.Department}", info_style))

    story.append(Paragraph(
        f"Year/Semester: {sel_year} / {sel_sem} &nbsp;&nbsp;&nbsp; "
        f"Section: {sel_section or '-'} &nbsp;&nbsp;&nbsp; Batch: {sel_batch or '-'}",
        info_style
    ))

    story.append(Spacer(1, 8))

    legend_grouped = defaultdict(list)

    for item in legend_items:
        legend_grouped[f"{item['course_code']} - {item['course_title']}"].append(item)

    legend_page_w, legend_page_h = doc.pagesize
    legend_usable_w = legend_page_w - doc.leftMargin - doc.rightMargin

    for course_label in legend_grouped:
        story.append(Paragraph(course_label, legend_category_style))

        legend_data = [["No.", "CO Code", "Description"]]

        for item in legend_grouped[course_label]:
            legend_data.append([
                str(item["number"]),
                Paragraph(str(item["co_code"]), legend_text_style),
                Paragraph(item["description"], legend_text_style)
            ])

        legend_tbl = Table(
            legend_data,
            colWidths=[15 * mm, 22 * mm, legend_usable_w - (37 * mm)],
            repeatRows=1
        )

        legend_tbl.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ff")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8.5),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (1, 1), (2, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8.3),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ]))

        story.append(legend_tbl)
        story.append(Spacer(1, 8))

    def _on_page(canv, doc_):
        page_w, page_h = doc_.pagesize
        _draw_rit_header_footer(
            canv,
            page_w,
            page_h,
            title="COURSE END SURVEY",
            subtitle=subtitle
        )

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)

    return response


