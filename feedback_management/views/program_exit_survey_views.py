from typing_extensions import OrderedDict

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

from feedback_management.models import ProgramExitQuestion
from user_accounts.models import Add_Department   # only if needed


from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date

@check_permission("course_survey_entry")
def program_exit_survey_entry(request):
    question = None

    user = request.user.Employee_id
    faculty = get_object_or_404(general_information, faculty_id=user)
    department = faculty.department

    edit_id = request.GET.get("edit")
    if edit_id:
        question = get_object_or_404(ProgramExitQuestion, pk=edit_id)

    if request.method == "POST":
        action_type = request.POST.get("action_type")

        # =====================================================
        # 1) COMMON SURVEY WINDOW FOR ALL COMMON QUESTIONS
        # =====================================================
        if action_type == "set_window":
            start_date = parse_date(request.POST.get("common_start_date") or "")
            end_date = parse_date(request.POST.get("common_end_date") or "")

            if start_date and end_date and end_date < start_date:
                messages.error(request, "End date cannot be earlier than start date.")
                return redirect("program_exit_survey_entry")

            try:
                ProgramExitQuestion.objects.filter(department__isnull=True).update(
                    start_date=start_date,
                    end_date=end_date
                )
                messages.success(request, "Common survey window updated for all departments successfully.")
            except Exception as e:
                messages.error(request, f"Error updating survey window: {str(e)}")

            return redirect("program_exit_survey_entry")

        # =====================================================
        # 2) ADD / EDIT QUESTION
        # =====================================================
        question_text = (request.POST.get("question_text") or "").strip()
        category = (request.POST.get("category") or "").strip()
        po_type = (request.POST.get("po_type") or "").strip()
        selected_po_ids = request.POST.getlist("program_outcomes")

        if not question_text:
            messages.error(request, "Question text is required.")
            return redirect("program_exit_survey_entry")

        if selected_po_ids and po_type not in ["revised", "non_revised"]:
            messages.error(request, "Please choose Revised or Non Revised PO type.")
            return redirect("program_exit_survey_entry")

        po_qs = Program_outcomes.objects.none()
        if po_type == "revised":
            po_qs = Program_outcomes.objects.filter(is_active=True, is_revised=True)
        elif po_type == "non_revised":
            po_qs = Program_outcomes.objects.filter(is_active=True, is_revised=False)

        valid_po_ids = []
        if selected_po_ids:
            valid_po_ids = list(
                po_qs.filter(id__in=selected_po_ids).values_list("id", flat=True)
            )

        existing_question_with_window = (
            ProgramExitQuestion.objects
            .filter(department__isnull=True)
            .exclude(start_date__isnull=True, end_date__isnull=True)
            .order_by("-id")
            .first()
        )

        inherited_start_date = existing_question_with_window.start_date if existing_question_with_window else None
        inherited_end_date = existing_question_with_window.end_date if existing_question_with_window else None

        try:
            if question:
                question.question_text = question_text
                question.category = category
                question.department = None
                question.po_type = po_type or None
                question.program_outcomes = valid_po_ids

                if inherited_start_date or inherited_end_date:
                    question.start_date = inherited_start_date
                    question.end_date = inherited_end_date

                question.save()
                action = "updated"
            else:
                ProgramExitQuestion.objects.create(
                    question_text=question_text,
                    category=category,
                    department=None,
                    start_date=inherited_start_date,
                    end_date=inherited_end_date,
                    po_type=po_type or None,
                    program_outcomes=valid_po_ids
                )
                action = "added"

            messages.success(request, f"Program exit question {action} successfully for all departments!")
            return redirect("program_exit_survey_entry")

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            if question and question.pk:
                return redirect(f"{request.path}?edit={question.pk}")
            return redirect("program_exit_survey_entry")

    feedback_questions = ProgramExitQuestion.objects.filter(
        department__isnull=True
    ).order_by("-id")

    common_window_obj = (
        ProgramExitQuestion.objects
        .filter(department__isnull=True)
        .exclude(start_date__isnull=True, end_date__isnull=True)
        .order_by("-id")
        .first()
    )

    common_start_date = common_window_obj.start_date if common_window_obj else None
    common_end_date = common_window_obj.end_date if common_window_obj else None

    program_outcomes = Program_outcomes.objects.filter(
        is_active=True
    ).order_by("-is_revised", "program_number", "id")

    selected_po_ids = []
    if question and question.program_outcomes:
        selected_po_ids = question.program_outcomes

    # Build PO objects for each question from JSONField ids
    for q in feedback_questions:
        q.selected_po_objects = []
        if q.program_outcomes:
            q.selected_po_objects = list(
                Program_outcomes.objects.filter(id__in=q.program_outcomes)
            )

    return render(
        request,
        "feedback_management/faculty/entry/program_exit_survey_entry.html",
        {
            "feedback_questions": feedback_questions,
            "question": question,
            "faculty": faculty,
            "common_start_date": common_start_date,
            "common_end_date": common_end_date,
            "program_outcomes": program_outcomes,
            "selected_po_ids": selected_po_ids,
        }
    )


@check_permission("course_survey_entry")
def delete_program_exit_question(request, pk):
    question = get_object_or_404(ProgramExitQuestion, pk=pk)

    try:
        question.delete()
        messages.success(request, "Program exit question deleted successfully!")
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")

    return redirect('program_exit_survey_entry') 





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

from datetime import date
from django.contrib import messages
from django.shortcuts import redirect, render
from django.db.models import Q, Min, Max

from collections import OrderedDict
from datetime import date

from collections import OrderedDict
from datetime import date

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone


def is_final_year_batch(batch):
    try:
        batch_year = int(str(batch).strip())
    except (TypeError, ValueError):
        return False

    current_year = date.today().year
    return batch_year + 4 == current_year


def group_questions_by_category(questions):
    grouped = OrderedDict()
    for q in questions:
        cat = (q.category or "General").strip()
        grouped.setdefault(cat, []).append(q)
    return grouped


@check_permission("program_exit_survey")
def program_exit_survey(request):
    student = get_student_details(request)
    if not student:
        messages.error(request, "Student record not found.")
        return redirect("home")

    department = student.department
    student_batch = str(student.batch or "").strip()

    if not is_final_year_batch(student_batch):
        messages.error(request, "Program Exit Survey is available only for final year students.")
        return redirect("home")

    if not department:
        messages.error(request, "Department not found.")
        return redirect("home")

    today = date.today()

    active_questions = list(
        ProgramExitQuestion.objects
        .filter(department__isnull=True)
        .filter(
            Q(start_date__isnull=True) | Q(start_date__lte=today),
            Q(end_date__isnull=True) | Q(end_date__gte=today),
        )
        .order_by("category", "id")
    )

    if not active_questions:
        messages.warning(request, "Program Exit Survey is not open now.")
        return redirect("home")

    grade_options = list(gradeupload.objects.all().order_by("-marks", "grade"))
    if not grade_options:
        messages.warning(request, "Grade options are not configured.")
        return redirect("home")

    window_start = min([q.start_date for q in active_questions if q.start_date], default=None)
    window_end = max([q.end_date for q in active_questions if q.end_date], default=None)

    grouped = group_questions_by_category(active_questions)

    existing = (
        ProgramExitSubmission.objects
        .filter(student=student)
        .prefetch_related("answers")
        .first()
    )

    if existing:
        answers_map = {a.question_id: a.score for a in existing.answers.all()}
        score_grade_map = {g.marks: g.grade for g in grade_options}

        return render(
            request,
            "feedback_management/student/program_exit/program_exit_form.html",
            {
                "student": student,
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

    if request.method == "POST":
        total = 0
        answers = []

        for q in active_questions:
            grade_id_raw = (request.POST.get(f"q_{q.id}") or "").strip()

            if not grade_id_raw:
                messages.error(request, f"Please select a grade for: {q.question_text}")
                return redirect("program_exit_survey")

            try:
                grade_obj = gradeupload.objects.get(pk=int(grade_id_raw))
            except (ValueError, gradeupload.DoesNotExist):
                messages.error(request, f"Invalid grade selected for: {q.question_text}")
                return redirect("program_exit_survey")

            score_val = int(grade_obj.marks or 0)
            total += score_val

            answers.append(
                ProgramExitAnswer(
                    question=q,
                    score=score_val
                )
            )

        try:
            with transaction.atomic():
                sub = ProgramExitSubmission.objects.create(
                    student=student,
                    enrollment=None,
                    department=department,
                    course=None,
                    faculty=None,
                    total_score=total,
                    window_start=window_start,
                    window_end=window_end,
                    submitted_at=timezone.now(),
                )

                for ans in answers:
                    ans.submission = sub

                ProgramExitAnswer.objects.bulk_create(answers)

            messages.success(request, "Program Exit Survey submitted successfully!")
            return redirect("program_exit_survey")

        except Exception as e:
            messages.error(request, f"Error saving Program Exit Survey: {str(e)}")
            return redirect("program_exit_survey")

    return render(
        request,
        "feedback_management/student/program_exit/program_exit_form.html",
        {
            "student": student,
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






from collections import OrderedDict, defaultdict
from django.contrib import messages
from django.db.models import Q, Max, Min
from django.http import HttpResponseForbidden
from django.shortcuts import render
from user_accounts.models import Add_Department, StudentDetails, Role
from faculty_management.models import general_information
from course_management.models import CourseEnrollment, Course
from feedback_management.models import ProgramExitQuestion, ProgramExitSubmission, program_exit_Permission


def _get_program_exit_permission_scope(request):
    """
    Returns:
    {
        "has_access": bool,
        "can_view_all": bool,
        "can_view_department": bool,
    }
    """

    can_view_all = False
    can_view_department = False

    # ---------------------------------------------------------
    # Adjust this part if your role id comes from another source
    # ---------------------------------------------------------
    role_id = None

    try:
        # Example: if your user has role_id directly
        role_id = getattr(request.user, "role_id", None)
    except Exception:
        role_id = None

    # Fallback example: if role stored elsewhere, adjust here
    if not role_id:
        try:
            role_id = getattr(request.user, "role", None)
            if hasattr(role_id, "id"):
                role_id = role_id.id
        except Exception:
            role_id = None

    if role_id:
        perm = program_exit_Permission.objects.filter(role_id=role_id).first()
        if perm:
            can_view_all = bool(perm.can_view_all_program_exit_data)
            can_view_department = bool(perm.can_view_department_program_exit_data)

    return {
        "has_access": can_view_all or can_view_department,
        "can_view_all": can_view_all,
        "can_view_department": can_view_department,
    }





from datetime import date
from collections import OrderedDict, defaultdict
from django.http import HttpResponseForbidden
from django.shortcuts import render


from datetime import date
from collections import OrderedDict, defaultdict
from django.http import HttpResponseForbidden


from datetime import date

def is_final_year_batch(batch):
    try:
        batch_year = int(str(batch).strip())
    except (TypeError, ValueError):
        return False

    current_year = date.today().year
    return batch_year + 4 == current_year


from datetime import date
from collections import OrderedDict, defaultdict

from django.http import HttpResponseForbidden
from django.shortcuts import render
from user_accounts.models import Add_Department, StudentDetails
from faculty_management.models import general_information
from feedback_management.models import ProgramExitQuestion, ProgramExitSubmission


def is_final_year_batch(batch):
    """
    Example:
    batch = 2022
    current year = 2026
    2022 + 4 = 2026 => final year
    """
    try:
        batch_year = int(str(batch).strip())
    except (TypeError, ValueError):
        return False

    current_year = date.today().year
    return batch_year + 4 == current_year


@check_permission("view_program_exit_survey")
def view_program_exit_survey(request):
    user = request.user.Employee_id
    faculty = general_information.objects.select_related("department").get(faculty_id=user)
    faculty_department = faculty.department

    permission_scope = _get_program_exit_permission_scope(request)

    if not permission_scope["has_access"]:
        return HttpResponseForbidden("You do not have permission to view program exit survey data.")

    sel_department_id = (request.GET.get("department_id") or "").strip()
    sel_batch = (request.GET.get("batch") or "").strip()
    sel_sem = (request.GET.get("semester") or "").strip()
    sel_section = (request.GET.get("section") or "").strip()

    # IMPORTANT:
    # This makes table/questions show only after Apply Filter button is clicked.
    filters_applied = request.GET.get("apply") == "1"

    # ---------------------------------------------------------
    # Department scope
    # ---------------------------------------------------------
    if permission_scope["can_view_all"]:
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
    # All students in selected department
    # ---------------------------------------------------------
    if department:
        all_students_qs = StudentDetails.objects.filter(department=department)
    else:
        all_students_qs = StudentDetails.objects.none()

    # ---------------------------------------------------------
    # Final-year batches only
    # batch + 4 == current year
    # ---------------------------------------------------------
    all_batches = (
        all_students_qs
        .exclude(batch__isnull=True)
        .exclude(batch__exact="")
        .values_list("batch", flat=True)
        .distinct()
        .order_by("batch")
    )

    final_year_batches = []

    for batch in all_batches:
        batch_text = str(batch).strip()

        if is_final_year_batch(batch_text):
            final_year_batches.append(batch_text)

    if sel_batch and sel_batch not in final_year_batches:
        sel_batch = ""

    # ---------------------------------------------------------
    # Base students: final-year students only
    # ---------------------------------------------------------
    base_students_qs = all_students_qs.filter(batch__in=final_year_batches)

    # ---------------------------------------------------------
    # Dropdown filters
    # ---------------------------------------------------------
    batches = final_year_batches

    students_for_filters = base_students_qs

    if sel_batch:
        students_for_filters = students_for_filters.filter(batch=sel_batch)

    semesters = (
        students_for_filters
        .exclude(semester__isnull=True)
        .exclude(semester__exact="")
        .values_list("semester", flat=True)
        .distinct()
        .order_by("semester")
    )

    section_filter_qs = students_for_filters

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
    # Default values before Apply Filter
    # ---------------------------------------------------------
    students = []
    student_ids = []
    questions = []
    rows = []
    submitted_student_ids = set()

    # ---------------------------------------------------------
    # Load table only after Apply Filter
    # ---------------------------------------------------------
    if filters_applied:
        # -----------------------------------------------------
        # Final students list
        # -----------------------------------------------------
        students_qs = base_students_qs

        if sel_batch:
            students_qs = students_qs.filter(batch=sel_batch)

        if sel_sem:
            students_qs = students_qs.filter(semester=str(sel_sem))

        if sel_section:
            students_qs = students_qs.filter(section=sel_section)

        students = list(students_qs.order_by("section", "reg_no"))
        student_ids = [st.id for st in students]

        # -----------------------------------------------------
        # Program Exit Questions
        # -----------------------------------------------------
        questions = list(
            ProgramExitQuestion.objects
            .filter(department__isnull=True)
            .order_by("category", "id")
        )

        for idx, q in enumerate(questions, start=1):
            q.display_qno = f"Q{idx}"
            q.display_category = (q.category or "General").strip() or "General"

        # -----------------------------------------------------
        # Submissions + answers
        # -----------------------------------------------------
        student_question_scores = defaultdict(dict)
        student_total = defaultdict(int)

        if student_ids and department:
            submissions = (
                ProgramExitSubmission.objects
                .filter(
                    student_id__in=student_ids,
                    department=department
                )
                .prefetch_related("answers")
                .order_by("student_id", "-submitted_at")
            )
        else:
            submissions = ProgramExitSubmission.objects.none()

        latest_submission_map = OrderedDict()

        for sub in submissions:
            if sub.student_id not in latest_submission_map:
                latest_submission_map[sub.student_id] = sub

        for student_id, sub in latest_submission_map.items():
            submitted_student_ids.add(student_id)
            student_total[student_id] = int(sub.total_score or 0)

            for ans in sub.answers.all():
                student_question_scores[student_id][ans.question_id] = ans.score

        # -----------------------------------------------------
        # Table rows
        # -----------------------------------------------------
        for idx, st in enumerate(students, start=1):
            mark_list = [
                student_question_scores.get(st.id, {}).get(q.id, "-")
                for q in questions
            ]

            rows.append({
                "sno": idx,
                "mark_list": mark_list,
                "total": student_total.get(st.id, 0),
            })

    return render(
        request,
        "feedback_management/faculty/program_exit/program_exit_survey.html",
        {
            "faculty": faculty,
            "department": department,
            "faculty_department": faculty_department,
            "departments": departments,

            "can_view_all_program_exit_data": permission_scope["can_view_all"],
            "can_view_department_program_exit_data": permission_scope["can_view_department"],

            "batches": batches,
            "semesters": semesters,
            "sections": sections,

            "sel_department_id": sel_department_id,
            "sel_batch": sel_batch,
            "sel_sem": sel_sem,
            "sel_section": sel_section,

            "filters_applied": filters_applied,

            "total_students": len(students) if filters_applied else 0,
            "submitted_students": len(submitted_student_ids) if filters_applied else 0,
            "not_submitted_students": (
                len(students) - len(submitted_student_ids)
            ) if filters_applied else 0,

            "questions": questions,
            "rows": rows,
        }
    )




from datetime import date
from collections import OrderedDict, defaultdict

from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import landscape, A3, A4
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.contrib.staticfiles import finders

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from faculty_management.models import general_information
from user_accounts.models import StudentDetails



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















def is_final_year_batch(batch):
    """
    Example:
    batch = 2022
    current year = 2026
    2022 + 4 = 2026 => final year
    """
    try:
        batch_year = int(str(batch).strip())
    except (TypeError, ValueError):
        return False

    current_year = date.today().year
    return batch_year + 4 == current_year


@check_permission("view_program_exit_survey")
def view_program_exit_survey_bulk_pdf(request):
    user = request.user.Employee_id
    faculty = general_information.objects.select_related("department").get(faculty_id=user)
    faculty_department = faculty.department

    permission_scope = _get_program_exit_permission_scope(request)
    if not permission_scope["has_access"]:
        return HttpResponseForbidden("You do not have permission to view program exit survey data.")

    sel_department_id = (request.GET.get("department_id") or "").strip()
    sel_batch = (request.GET.get("batch") or "").strip()
    sel_sem = (request.GET.get("semester") or "").strip()
    sel_section = (request.GET.get("section") or "").strip()

    # ---------------------------------------------------------
    # Department resolve
    # ---------------------------------------------------------
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

    # ---------------------------------------------------------
    # Students by department
    # ---------------------------------------------------------
    all_students_qs = StudentDetails.objects.filter(department=department)

    # ---------------------------------------------------------
    # Get final-year batches using batch + 4 == current year
    # ---------------------------------------------------------
    all_batches = (
        all_students_qs
        .exclude(batch__isnull=True)
        .exclude(batch__exact="")
        .values_list("batch", flat=True)
        .distinct()
        .order_by("batch")
    )

    final_year_batches = [
        str(batch).strip()
        for batch in all_batches
        if is_final_year_batch(batch)
    ]

    if not final_year_batches:
        return HttpResponseBadRequest("No final year batch found.")

    if sel_batch and sel_batch not in final_year_batches:
        return HttpResponseBadRequest("Selected batch is not a final year batch.")

    # ---------------------------------------------------------
    # Final-year students only
    # ---------------------------------------------------------
    students_qs = all_students_qs.filter(batch__in=final_year_batches)

    if sel_batch:
        students_qs = students_qs.filter(batch=sel_batch)

    if sel_sem:
        students_qs = students_qs.filter(semester=str(sel_sem))

    if sel_section:
        students_qs = students_qs.filter(section=sel_section)

    students = list(students_qs.order_by("reg_no"))
    student_ids = [s.id for s in students]

    if not students:
        return HttpResponseBadRequest("No final year students found for the selected filters.")

    # ---------------------------------------------------------
    # Questions
    # ---------------------------------------------------------
    questions = list(
        ProgramExitQuestion.objects
        .filter(department__isnull=True)
        .order_by("category", "id")
    )

    if not questions:
        return HttpResponseBadRequest("No Program Exit questions configured.")

    for idx, q in enumerate(questions, start=1):
        q.display_qno = f"Q{idx}"
        q.display_category = (q.category or "General").strip() or "General"

    # ---------------------------------------------------------
    # Category spans
    # ---------------------------------------------------------
    category_spans = []
    question_number_map = {}

    current_category = (questions[0].category or "General").strip() or "General"
    span = 0

    for idx, q in enumerate(questions, start=1):
        qcat = (q.category or "General").strip() or "General"
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

    # ---------------------------------------------------------
    # Latest submissions
    # ---------------------------------------------------------
    student_question_scores = defaultdict(dict)
    student_total = defaultdict(int)

    submissions = (
        ProgramExitSubmission.objects
        .filter(
            student_id__in=student_ids,
            department=department
        )
        .prefetch_related("answers")
        .order_by("student_id", "-submitted_at")
    )

    latest_submission_map = OrderedDict()

    for sub in submissions:
        if sub.student_id not in latest_submission_map:
            latest_submission_map[sub.student_id] = sub

    for sid, sub in latest_submission_map.items():
        student_total[sid] = int(sub.total_score or 0)

        for ans in sub.answers.all():
            student_question_scores[sid][ans.question_id] = ans.score

    # ---------------------------------------------------------
    # PDF setup - LANDSCAPE A4 with RIT header/footer
    # ---------------------------------------------------------
    PDF_PAGE_SIZE = landscape(A4)

    batch_text = sel_batch or "All_Final_Year_Batches"
    filename = f"Program_Exit_{department.Department}_{batch_text}.pdf"

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'

    doc = SimpleDocTemplate(
        response,
        pagesize=PDF_PAGE_SIZE,
        leftMargin=8 * mm,
        rightMargin=8 * mm,
        topMargin=50 * mm,
        bottomMargin=25 * mm,
        title="Program Exit Bulk Report"
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

    semester_type = "Odd" if str(sel_sem) in ["1", "3", "5", "7"] else "Even"
    academic_year_text = f"Academic Year: {get_academic_year()} ({semester_type} Semester)"
    subtitle = academic_year_text

    story = []

    story.append(Paragraph("Program Exit Survey - Bulk Report", heading_style))
    story.append(Paragraph(f"Department: {department.Department}", info_style))
    story.append(Paragraph(
        f"Batch: {sel_batch or 'All Final Year Batches'} &nbsp;&nbsp;&nbsp; "
        f"Semester: {sel_sem or 'All'} &nbsp;&nbsp;&nbsp; "
        f"Section: {sel_section or 'All'}",
        info_style
    ))
    story.append(Paragraph(
        "Final Year: Batch + 4 = Current Year",
        info_style
    ))
    story.append(Spacer(1, 8))

    # ---------------------------------------------------------
    # Table header
    # ---------------------------------------------------------
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

    # ---------------------------------------------------------
    # Table rows
    # ---------------------------------------------------------
    for idx, st in enumerate(students, start=1):
        row = [str(idx)]

        for q in questions:
            row.append(str(student_question_scores.get(st.id, {}).get(q.id, "-")))

        row.append(str(student_total.get(st.id, 0)))
        data.append(row)

    usable_w = doc.pagesize[0] - doc.leftMargin - doc.rightMargin

    col_w_sno = 11 * mm
    col_w_total = 15 * mm
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
            title="PROGRAM EXIT SURVEY",
            subtitle=subtitle
        )

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return response









