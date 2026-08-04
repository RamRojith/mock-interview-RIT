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

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.dateparse import parse_date

@check_permission("course_survey_entry")
def course_exit_survey_entry(request):
    question = None

    user = request.user.Employee_id
    faculty = get_object_or_404(general_information, faculty_id=user)
    department = faculty.department

    edit_id = request.GET.get("edit")
    if edit_id:
        question = get_object_or_404(ExitSurveyQuestion, pk=edit_id)

    if request.method == "POST":
        action_type = request.POST.get("action_type")

        if action_type == "set_window":
            start_date = parse_date(request.POST.get("common_start_date") or "")
            end_date = parse_date(request.POST.get("common_end_date") or "")

            if start_date and end_date and end_date < start_date:
                messages.error(request, "End date cannot be earlier than start date.")
                return redirect("exit_survey_entry")

            try:
                ExitSurveyQuestion.objects.filter(department__isnull=True).update(
                    start_date=start_date,
                    end_date=end_date
                )
                messages.success(request, "Common exit survey window updated for all departments successfully.")
            except Exception as e:
                messages.error(request, f"Error updating exit survey window: {str(e)}")

            return redirect("course_exit_survey_entry")

        question_text = (request.POST.get("question_text") or "").strip()
        category = (request.POST.get("category") or "").strip()

        if not question_text:
            messages.error(request, "Question text is required.")
            return redirect("course_exit_survey_entry")

        existing_question_with_window = (
            ExitSurveyQuestion.objects
            .filter(department__isnull=True)
            .exclude(start_date__isnull=True, end_date__isnull=True)
            .order_by("-id")
            .first()
        )

        inherited_start_date = existing_question_with_window.start_date if existing_question_with_window else None
        inherited_end_date = existing_question_with_window.end_date if existing_question_with_window else None

        if question:
            question.question_text = question_text
            question.category = category
            question.department = None

            if inherited_start_date or inherited_end_date:
                question.start_date = inherited_start_date
                question.end_date = inherited_end_date

            action = "updated"
        else:
            question = ExitSurveyQuestion.objects.create(
                question_text=question_text,
                category=category,
                department=None,
                start_date=inherited_start_date,
                end_date=inherited_end_date
            )
            action = "added"

        try:
            question.save()
            messages.success(request, f"Exit survey question {action} successfully for all departments!")
            return redirect("course_exit_survey_entry")
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            if question and question.pk:
                return redirect(f"{request.path}?edit={question.pk}")
            return redirect("course_exit_survey_entry")

    exit_survey_questions = ExitSurveyQuestion.objects.filter(department__isnull=True).order_by("-id")

    common_window_obj = (
        ExitSurveyQuestion.objects
        .filter(department__isnull=True)
        .exclude(start_date__isnull=True, end_date__isnull=True)
        .order_by("-id")
        .first()
    )

    common_start_date = common_window_obj.start_date if common_window_obj else None
    common_end_date = common_window_obj.end_date if common_window_obj else None

    return render(
        request,
        "feedback_management/faculty/entry/course_exit_survey_entry.html",
        {
            "exit_survey_questions": exit_survey_questions,
            "question": question,
            "faculty": faculty,
            "common_start_date": common_start_date,
            "common_end_date": common_end_date,
        }
    )

@check_permission("course_survey_entry")
def delete_exit_survey_question(request, pk):
    question = get_object_or_404(ExitSurveyQuestion, pk=pk)

    try:
        question.delete()
        messages.success(request, "Exit survey question deleted successfully.")
    except Exception as e:
        messages.error(request, f"Error deleting exit survey question: {str(e)}")

    return redirect("course_exit_survey_entry")




from collections import OrderedDict
from datetime import date

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from course_management.models import CourseEnrollment
from feedback_management.models import (
    ExitSurveyQuestion,
    ExitSurveySubmission,
    ExitSurveyAnswer,
    gradeupload,
)
from user_accounts.models import StudentDetails

# import your model correctly if already elsewhere
# from course_management.models import AssignSubjectFaculty


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


def group_questions_by_category(questions):
    grouped = OrderedDict()
    for q in questions:
        cat = (q.category or "General").strip()
        grouped.setdefault(cat, []).append(q)
    return grouped


def is_final_year_student(student):
    year_value = str(getattr(student, "year", "") or "").strip().lower()

    final_year_values = [
        "4",
        "4th",
        "iv",
        "final",
        "final year",
        "fourth",
        "fourth year",
    ]

    return year_value in final_year_values


from collections import OrderedDict
from datetime import date

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render

from course_management.models import CourseEnrollment
from feedback_management.models import (
    ExitSurveyQuestion,
    ExitSurveySubmission,
    ExitSurveyAnswer,
    gradeupload,
)

# Import this from your correct app
# from course_management.models import AssignSubjectFaculty


def course_exit_survey(request):

    student = get_student_details(request)

    if not student:
        messages.error(request, "Student record not found.")
        return redirect("home")

    # ---------------------------------------------------------
    # BLOCK FINAL YEAR / 4TH YEAR STUDENTS
    # IMPORTANT:
    # Do NOT redirect to course_exit_survey here.
    # It will create continuous redirect loop.
    # ---------------------------------------------------------
    if is_final_year_student(student):
        messages.error(
            request,
            "Exit survey is not allowed for final year / 4th year students."
        )
        return redirect("home")

    # ---------------------------------------------------------
    # GET CURRENT ACTIVE ENROLLMENT
    # ---------------------------------------------------------
    enrollment = (
        CourseEnrollment.objects
        .select_related("course", "faculty", "department")
        .filter(
            student=student,
            enroll=True
        )
        .order_by("-id")
        .first()
    )

    if not enrollment:
        messages.error(request, "No active enrollment found.")
        return redirect("home")

    department = enrollment.department or student.department

    if not department:
        messages.error(request, "Department not found.")
        return redirect("home")

    today = date.today()

    # ---------------------------------------------------------
    # ASSIGNED FACULTY
    # ---------------------------------------------------------
    assigned_faculty_obj = (
        AssignSubjectFaculty.objects
        .select_related("faculty", "course")
        .filter(
            department=department,
            course_id=enrollment.course_id,
            is_active=True,
        )
        .filter(
            Q(batch=enrollment.batch) |
            Q(batch__isnull=True) |
            Q(batch__exact="")
        )
        .filter(
            Q(section=enrollment.section) |
            Q(section__isnull=True) |
            Q(section__exact="")
        )
        .filter(
            Q(course__year=str(student.year)) |
            Q(course__year__isnull=True) |
            Q(course__year__exact="")
        )
        .filter(
            Q(course__semester=str(student.semester)) |
            Q(course__semester__isnull=True) |
            Q(course__semester__exact="")
        )
        .order_by("-id")
        .first()
    )

    actual_faculty = (
        assigned_faculty_obj.faculty
        if assigned_faculty_obj and assigned_faculty_obj.faculty
        else enrollment.faculty
    )

    # ---------------------------------------------------------
    # EXIT SURVEY QUESTIONS
    # ---------------------------------------------------------
    qs = (
        ExitSurveyQuestion.objects
        .filter(department__isnull=True)
        .filter(
            Q(start_date__isnull=True) | Q(start_date__lte=today),
            Q(end_date__isnull=True) | Q(end_date__gte=today),
        )
        .order_by("category", "id")
    )

    active_questions = list(qs)

    if not active_questions:
        messages.warning(request, "Exit survey is not open now.")
        return redirect("home")

    # ---------------------------------------------------------
    # GRADES
    # ---------------------------------------------------------
    grade_options = list(
        gradeupload.objects.all().order_by("-marks", "grade")
    )

    if not grade_options:
        messages.warning(request, "Grade options are not configured.")
        return redirect("home")

    # ---------------------------------------------------------
    # WINDOW
    # ---------------------------------------------------------
    window_start = min(
        [q.start_date for q in active_questions if q.start_date],
        default=None
    )

    window_end = max(
        [q.end_date for q in active_questions if q.end_date],
        default=None
    )

    grouped = group_questions_by_category(active_questions)

    # ---------------------------------------------------------
    # EXISTING SUBMISSION
    # ---------------------------------------------------------
    existing = (
        ExitSurveySubmission.objects
        .filter(
            student=student,
            enrollment=enrollment
        )
        .prefetch_related("answers")
        .first()
    )

    if existing:
        answers_map = {
            a.question_id: a.score
            for a in existing.answers.all()
        }

        score_grade_map = {}

        for g in grade_options:
            score_grade_map[g.marks] = g.grade

        return render(
            request,
            "feedback_management/student/exit_survey/exit_survey_form.html",
            {
                "student": student,
                "enrollment": enrollment,
                "display_faculty": actual_faculty,
                "assigned_faculty_obj": assigned_faculty_obj,
                "grouped": grouped,
                "already_submitted": True,
                "answers_map": answers_map,
                "submission": existing,
                "window_start": window_start,
                "window_end": window_end,
                "grade_options": grade_options,
                "score_grade_map": score_grade_map,
            }
        )

    # ---------------------------------------------------------
    # SUBMIT
    # ---------------------------------------------------------
    if request.method == "POST":

        total = 0
        answers = []

        for q in active_questions:

            grade_id_raw = (
                request.POST.get(f"q_{q.id}") or ""
            ).strip()

            if not grade_id_raw:
                messages.error(
                    request,
                    f"Please select a grade for: {q.question_text}"
                )
                return redirect("course_exit_survey")

            try:
                grade_obj = gradeupload.objects.get(pk=int(grade_id_raw))

            except (ValueError, gradeupload.DoesNotExist):
                messages.error(
                    request,
                    f"Invalid grade selected for: {q.question_text}"
                )
                return redirect("course_exit_survey")

            val = int(grade_obj.marks or 0)
            total += val

            answers.append(
                ExitSurveyAnswer(
                    question=q,
                    selected_grade=grade_obj.grade,
                    score=val
                )
            )

        try:
            with transaction.atomic():

                sub = ExitSurveySubmission.objects.create(
                    student=student,
                    enrollment=enrollment,
                    department=department,
                    course=enrollment.course,
                    faculty=actual_faculty,
                    total_score=total,
                    window_start=window_start,
                    window_end=window_end,
                )

                for ans in answers:
                    ans.submission = sub

                ExitSurveyAnswer.objects.bulk_create(answers)

            messages.success(request, "Exit survey submitted successfully!")
            return redirect("course_exit_survey")

        except Exception as e:
            messages.error(request, f"Error saving exit survey: {str(e)}")
            return redirect("course_exit_survey")

    # ---------------------------------------------------------
    # INITIAL LOAD
    # ---------------------------------------------------------
    return render(
        request,
        "feedback_management/student/exit_survey/exit_survey_form.html",
        {
            "student": student,
            "enrollment": enrollment,
            "display_faculty": actual_faculty,
            "assigned_faculty_obj": assigned_faculty_obj,
            "grouped": grouped,
            "already_submitted": False,
            "answers_map": {},
            "submission": None,
            "window_start": window_start,
            "window_end": window_end,
            "grade_options": grade_options,
            "score_grade_map": {},
        }
    )


from collections import defaultdict

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden, HttpResponseBadRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from user_accounts.models import Add_Department, StudentDetails
from faculty_management.models import general_information
from course_management.models import Course, CourseEnrollment
from feedback_management.models import (
    ExitSurveyQuestion,
    ExitSurveySubmission,
    ExitSurveyAnswer,
    course_exit_Permission,
)

# PDF imports
import os
from collections import OrderedDict
from django.conf import settings
from django.contrib.staticfiles import finders
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer


def _get_course_exit_permission_scope(request):
    role_id = (
        getattr(request.user, "role_id", None)
        or getattr(request.user, "Role_id", None)
        or getattr(request.user, "role", None)
    )

    permission = None

    if role_id:
        permission = course_exit_Permission.objects.filter(role_id=role_id).first()

    if not permission:
        return {
            "has_access": False,
            "can_view_all": False,
            "can_view_department": False,
        }

    can_view_all = permission.can_view_all_course_exit_data
    can_view_department = permission.can_view_department_course_exit_data

    return {
        "has_access": can_view_all or can_view_department,
        "can_view_all": can_view_all,
        "can_view_department": can_view_department,
    }


from collections import defaultdict

from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import render

from user_accounts.models import Add_Department, StudentDetails
from faculty_management.models import general_information
from feedback_management.models import (
    ExitSurveyQuestion,
    ExitSurveySubmission,
    ExitSurveyAnswer,
)


@check_permission("view_course_exit_survey")
def view_course_exit_survey(request):
    user = request.user.Employee_id
    faculty = general_information.objects.select_related("department").get(faculty_id=user)
    faculty_department = faculty.department

    permission_scope = _get_course_exit_permission_scope(request)

    if not permission_scope["has_access"]:
        return HttpResponseForbidden("You do not have permission to view course exit survey data.")

    # ---------------------------------------------------------
    # Read request params
    # ---------------------------------------------------------
    if request.method == "POST":
        sel_department_id = (request.POST.get("department_id") or "").strip()
        sel_batch = (request.POST.get("batch") or "").strip()
        sel_year = (request.POST.get("year") or "").strip()
        sel_sem = (request.POST.get("semester") or "").strip()
        sel_section = (request.POST.get("section") or "").strip()
    else:
        sel_department_id = (request.GET.get("department_id") or "").strip()
        sel_batch = (request.GET.get("batch") or "").strip()
        sel_year = (request.GET.get("year") or "").strip()
        sel_sem = (request.GET.get("semester") or "").strip()
        sel_section = (request.GET.get("section") or "").strip()

    # ---------------------------------------------------------
    # Department permission scope
    # ---------------------------------------------------------
    if permission_scope.get("can_view_all"):
        departments = Add_Department.objects.filter(is_active=True).order_by("Department")

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
    # Base students
    # ---------------------------------------------------------
    if department:
        base_students_qs = StudentDetails.objects.filter(department=department)
    else:
        base_students_qs = StudentDetails.objects.none()

    # ---------------------------------------------------------
    # Dropdown filters
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

    # ---------------------------------------------------------
    # Section is optional:
    # empty section means ALL sections
    # ---------------------------------------------------------
    filters_applied = bool(
        department and sel_batch and sel_year and sel_sem
    )

    # ---------------------------------------------------------
    # Questions
    # ---------------------------------------------------------
    ordered_questions = []
    question_ids = []
    category_spans = []

    if department:
        ordered_questions = list(
            ExitSurveyQuestion.objects
            .filter(Q(department__isnull=True) | Q(department=department))
            .order_by("category", "id")
        )

        question_ids = [q.id for q in ordered_questions]

        if ordered_questions:
            current_category = ordered_questions[0].category or "General"
            span = 0

            for q in ordered_questions:
                qcat = q.category or "General"

                if qcat != current_category:
                    category_spans.append({
                        "category": current_category,
                        "span": span,
                    })
                    current_category = qcat
                    span = 1
                else:
                    span += 1

            category_spans.append({
                "category": current_category,
                "span": span,
            })

    # ---------------------------------------------------------
    # Students list after filters
    # If section empty, all sections will be shown
    # ---------------------------------------------------------
    students_qs = base_students_qs

    if sel_batch:
        students_qs = students_qs.filter(batch=sel_batch)

    if sel_year:
        students_qs = students_qs.filter(year=str(sel_year))

    if sel_sem:
        students_qs = students_qs.filter(semester=str(sel_sem))

    if sel_section:
        students_qs = students_qs.filter(section=sel_section)

    students = list(students_qs.order_by("section", "reg_no"))
    student_ids = [student.id for student in students]

    # ---------------------------------------------------------
    # Submissions
    # If section empty, do not filter section
    # ---------------------------------------------------------
    submissions_qs = ExitSurveySubmission.objects.none()
    submission_ids = []

    if department and filters_applied and student_ids:
        submissions_qs = (
            ExitSurveySubmission.objects
            .filter(
                student_id__in=student_ids,
                department=department,
                enrollment__department=department,
                enrollment__batch=sel_batch,
                enrollment__student__year=str(sel_year),
                enrollment__student__semester=str(sel_sem),
            )
            .select_related("student", "course", "faculty", "enrollment")
        )

        if sel_section:
            submissions_qs = submissions_qs.filter(enrollment__section=sel_section)

        submission_ids = list(submissions_qs.values_list("id", flat=True))

    # ---------------------------------------------------------
    # Answers
    # ---------------------------------------------------------
    student_q_marks = defaultdict(dict)
    student_total = defaultdict(int)
    submitted_student_ids = set()

    if submission_ids:
        answers = (
            ExitSurveyAnswer.objects
            .filter(
                submission_id__in=submission_ids,
                question_id__in=question_ids
            )
            .select_related("submission", "question")
            .order_by("submission__student_id", "question_id")
        )

        for ans in answers:
            sid = ans.submission.student_id
            qid = ans.question_id
            score_value = int(ans.score or 0)

            submitted_student_ids.add(sid)
            student_q_marks[sid][qid] = score_value
            student_total[sid] += score_value

    # ---------------------------------------------------------
    # Rows
    # ---------------------------------------------------------
    rows = []

    if filters_applied:
        for idx, st in enumerate(students, start=1):
            rows.append({
                "sno": idx,
                "student_id": st.id,
                "section": st.section or "-",
                "marks": student_q_marks.get(st.id, {}),
                "total": student_total.get(st.id, 0),
                "is_submitted": st.id in submitted_student_ids,
            })

    return render(
        request,
        "feedback_management/faculty/exit_survey/view_course_exit_survey.html",
        {
            "faculty": faculty,
            "department": department,
            "faculty_department": faculty_department,
            "departments": departments,

            "can_view_all_course_exit_data": permission_scope.get("can_view_all", False),
            "can_view_department_course_exit_data": permission_scope.get("can_view_department", False),

            "batches": batches,
            "years": years,
            "semesters": semesters,
            "sections": sections,

            "sel_department_id": sel_department_id,
            "sel_batch": sel_batch,
            "sel_year": sel_year,
            "sel_sem": sel_sem,
            "sel_section": sel_section,

            "filters_applied": filters_applied,

            "total_students": len(students) if filters_applied else 0,
            "submitted_students": len(submitted_student_ids),
            "not_submitted_students": (len(students) - len(submitted_student_ids)) if filters_applied else 0,

            "category_spans": category_spans,
            "ordered_questions": ordered_questions,
            "rows": rows,
        }
    )




def _draw_rit_header_footer(c: canvas.Canvas, page_w, page_h, title="STUDENTS FEEDBACK", subtitle=""):
    left_margin = 18 * mm
    right_margin = page_w - 18 * mm
    top_margin = page_h - 12 * mm
    bottom_margin = 14 * mm

    # --- Left Logo (RIT) ---
    logo_rel = "images/ritlogo.png"
    logo_path = finders.find(logo_rel)
    if not logo_path:
        for d in getattr(settings, "STATICFILES_DIRS", []):
            cand = os.path.join(d, logo_rel)
            if os.path.exists(cand):
                logo_path = cand
                break

    if logo_path and os.path.exists(logo_path):
        try:
            img = ImageReader(logo_path)
            iw, ih = img.getSize()
            th = 18 * mm
            tw = th * (iw / float(ih))
            c.drawImage(img, left_margin, top_margin - th + 2 * mm, width=tw, height=th, mask='auto')
        except Exception:
            pass

    # --- Right Logo (TUV) ---
    tuv_logo_rel = "images/tuvlogo.png"
    tuv_path = finders.find(tuv_logo_rel)
    if tuv_path and os.path.exists(tuv_path):
        try:
            img2 = ImageReader(tuv_path)
            iw, ih = img2.getSize()
            th = 13 * mm
            tw = th * (iw / float(ih))
            c.drawImage(img2, right_margin - tw, top_margin - th + 4 * mm, width=tw, height=th, mask='auto')
        except Exception:
            pass

    # --- Institute header ---
    c.setFillColor(colors.HexColor("#2C3E50"))
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(page_w / 2.0, top_margin, "RAMCO INSTITUTE OF TECHNOLOGY")

    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(page_w / 2.0, top_margin - 7 * mm, title)

    if subtitle:
        c.setFont("Helvetica", 10)
        c.drawCentredString(page_w / 2.0, top_margin - 13 * mm, subtitle)

    # Line
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.line(left_margin, top_margin - 16 * mm, right_margin, top_margin - 16 * mm)

    # Footer
    footer_y = bottom_margin
    c.setStrokeColor(colors.HexColor("#C0392B"))
    c.setLineWidth(0.8)
    c.line(left_margin, footer_y + 7 * mm, right_margin, footer_y + 7 * mm)

    c.setFont("Helvetica", 8.8)
    c.setFillColor(colors.HexColor("#2C3E50"))
    c.drawCentredString(
        page_w / 2.0,
        footer_y + 2.5 * mm,
        "North Venganallur, Ayyanarkovil Road, Rajapalayam - 626 117, Virudhunagar District, Tamil Nadu."
    )
    c.drawCentredString(
        page_w / 2.0,
        footer_y - 2.0 * mm,
        "Tel: 04563 233400 | E-mail: rit@ritrjpm.ac.in | Web: www.ritrjpm.ac.in"
    )














@check_permission("view_course_exit_survey")
def view_course_exit_survey_bulk_pdf(request):
    user = request.user.Employee_id
    faculty = general_information.objects.select_related("department").get(faculty_id=user)
    faculty_department = faculty.department

    permission_scope = _get_course_exit_permission_scope(request)

    if not permission_scope["has_access"]:
        return HttpResponseForbidden("You do not have permission to view course exit survey data.")

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

    if not sel_batch or not sel_year or not sel_sem:
        return HttpResponseBadRequest("Batch, year and semester are required.")

    questions = list(
        ExitSurveyQuestion.objects
        .filter(Q(department__isnull=True) | Q(department=department))
        .order_by("category", "id")
    )

    if not questions:
        return HttpResponseBadRequest("No Course Exit Survey questions configured.")

    question_ids = [q.id for q in questions]

    category_spans = []
    question_number_map = {}

    current_category = questions[0].category or "General"
    span = 0

    for idx, q in enumerate(questions, start=1):
        qcat = q.category or "General"
        question_number_map[q.id] = idx

        if qcat != current_category:
            category_spans.append({
                "category": current_category,
                "span": span
            })
            current_category = qcat
            span = 1
        else:
            span += 1

    category_spans.append({
        "category": current_category,
        "span": span
    })

    students_qs = StudentDetails.objects.filter(
        department=department,
        batch=sel_batch,
        year=str(sel_year),
        semester=str(sel_sem),
    )

    if sel_section:
        students_qs = students_qs.filter(section=sel_section)

    students = list(students_qs.order_by("section", "reg_no"))
    student_ids = [s.id for s in students]

    if not students:
        return HttpResponseBadRequest("No students found for selected filters.")

    submissions_qs = ExitSurveySubmission.objects.filter(
        student_id__in=student_ids,
        department=department,
        enrollment__department=department,
        enrollment__batch=sel_batch,
        enrollment__student__year=str(sel_year),
        enrollment__student__semester=str(sel_sem),
    ).select_related("student", "enrollment")

    if sel_section:
        submissions_qs = submissions_qs.filter(enrollment__section=sel_section)

    submissions_qs = submissions_qs.prefetch_related("answers").order_by("student_id", "-submitted_at")

    latest_submission_map = OrderedDict()

    for sub in submissions_qs:
        if sub.student_id not in latest_submission_map:
            latest_submission_map[sub.student_id] = sub

    student_question_scores = defaultdict(dict)
    student_total = defaultdict(int)

    for sid, sub in latest_submission_map.items():
        student_total[sid] = int(sub.total_score or 0)

        for ans in sub.answers.all():
            if ans.question_id in question_ids:
                student_question_scores[sid][ans.question_id] = int(ans.score or 0)

    section_text = sel_section or "All_Sections"
    filename = f"Course_Exit_Survey_{department.Department}_{sel_batch}_{sel_year}_{sel_sem}_{section_text}.pdf"

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        leftMargin=8 * mm,
        rightMargin=8 * mm,
        topMargin=50 * mm,
        bottomMargin=25 * mm,
        title="Course Exit Survey Bulk Report"
    )

    styles = getSampleStyleSheet()

    heading_style = ParagraphStyle(
        "heading_style",
        parent=styles["Heading4"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1e3a8a"),
        spaceAfter=6
    )

    info_style = ParagraphStyle(
        "info_style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
    )

    p_center = ParagraphStyle(
        "p_center",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=5.2,
        leading=6,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a"),
    )

    p_center_bold = ParagraphStyle(
        "p_center_bold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=5.4,
        leading=6,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a"),
    )

    story = []

    story.append(Paragraph("Course Exit Survey - Bulk Report", heading_style))
    story.append(Paragraph(f"Department: {department.Department}", info_style))
    story.append(Paragraph(
        f"Batch: {sel_batch} &nbsp;&nbsp;&nbsp; "
        f"Year: {sel_year} &nbsp;&nbsp;&nbsp; "
        f"Semester: {sel_sem} &nbsp;&nbsp;&nbsp; "
        f"Section: {sel_section or 'All'}",
        info_style
    ))
    story.append(Spacer(1, 8))

    row1 = ["S.No"]

    for c in category_spans:
        row1.append(Paragraph(str(c["category"]), p_center))
        for _ in range(c["span"] - 1):
            row1.append("")

    row1.append(Paragraph("Total", p_center))

    row2 = [""]

    for q in questions:
        row2.append(Paragraph(str(question_number_map.get(q.id, "")), p_center_bold))

    row2.append("")

    data = [row1, row2]

    for idx, st in enumerate(students, start=1):
        row = [str(idx)]

        for q in questions:
            row.append(str(student_question_scores.get(st.id, {}).get(q.id, "-")))

        row.append(str(student_total.get(st.id, 0)))

        data.append(row)

    usable_w = doc.pagesize[0] - doc.leftMargin - doc.rightMargin

    col_w_sno = 12 * mm
    col_w_total = 16 * mm
    q_count = len(questions)

    fixed_w = col_w_sno + col_w_total
    q_w = max((usable_w - fixed_w) / max(q_count, 1), 7 * mm)

    col_widths = [col_w_sno] + [q_w] * q_count + [col_w_total]

    tbl = Table(data, colWidths=col_widths, repeatRows=2)

    table_style = TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d1d5db")),
        ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#f8fafc")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ff")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 1), 5.8),
        ("FONTNAME", (0, 2), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 2), (-1, -1), 5.8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (-1, 2), (-1, -1), colors.HexColor("#f8fafc")),
        ("FONTNAME", (-1, 2), (-1, -1), "Helvetica-Bold"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ])

    table_style.add("SPAN", (0, 0), (0, 1))
    table_style.add("SPAN", (-1, 0), (-1, 1))

    start_col = 1

    for c in category_spans:
        end_col = start_col + c["span"] - 1
        table_style.add("SPAN", (start_col, 0), (end_col, 0))
        start_col = end_col + 1

    tbl.setStyle(table_style)
    story.append(tbl)

    def _on_page(canv, doc_):
        page_w, page_h = doc_.pagesize
        _draw_rit_header_footer(
            canv,
            page_w,
            page_h,
            title="COURSE EXIT SURVEY",
            subtitle=f"Batch: {sel_batch} | Year: {sel_year} | Semester: {sel_sem} | Section: {sel_section or 'All'}"
        )

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)

    return response







