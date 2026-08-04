from collections import OrderedDict

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.dateparse import parse_date
from datetime import date

from user_accounts.decorators import check_permission
from user_accounts.models import StudentDetails
from faculty_management.models import general_information
from examination_management.models import Regulations
from feedback_management.models import (
    AcademicActivityQuestion,
    AcademicActivitySubmission,
    AcademicActivityAnswer,
    gradeupload,
)



from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from user_accounts.models import Role
from feedback_management.models import academic_activity_Permission
from course_management.models import Program_outcomes

def academic_activity_permission(request):
    edit_permission = None

    if request.method == "POST" and request.POST.get("action") == "delete":
        perm_id = request.POST.get("perm_id")
        academic_activity_Permission.objects.filter(id=perm_id).delete()
        messages.success(request, "Academic activity permission deleted successfully.")
        return redirect("academic_activity_permission")

    if request.method == "GET" and request.GET.get("edit"):
        edit_permission = get_object_or_404(
            academic_activity_Permission,
            id=request.GET.get("edit")
        )

    if request.method == "POST" and request.POST.get("action") == "save":
        role_ids = request.POST.getlist("roles[]")
        can_view_all = request.POST.get("can_view_all_academic_activity_data") == "on"
        can_view_dept = request.POST.get("can_view_department_academic_activity_data") == "on"
        perm_id = request.POST.get("perm_id")

        if perm_id:
            academic_activity_Permission.objects.filter(id=perm_id).update(
                can_view_all_academic_activity_data=can_view_all,
                can_view_department_academic_activity_data=can_view_dept,
            )
            messages.success(request, "Academic activity permission updated successfully.")
            return redirect("academic_activity_permission")

        if not role_ids:
            messages.error(request, "At least one role is required.")
            return redirect("academic_activity_permission")

        for role_id in role_ids:
            academic_activity_Permission.objects.update_or_create(
                role_id=role_id,
                defaults={
                    "can_view_all_academic_activity_data": can_view_all,
                    "can_view_department_academic_activity_data": can_view_dept,
                }
            )

        messages.success(request, "Academic activity permission saved successfully.")
        return redirect("academic_activity_permission")

    roles = Role.objects.using("rit_approval_system").all()

    context = {
        "roles": roles,
        "edit_permission": edit_permission,
    }

    return render(
        request,
        "feedback_management/admin/academic_activity_permission.html",
        context
    )


@require_GET
def academic_activity_permission_api(request):
    search = (request.GET.get("search") or "").strip()
    page = int(request.GET.get("page", 1))

    permissions = academic_activity_Permission.objects.all().order_by("id")

    roles_qs = Role.objects.using("rit_approval_system").all()
    role_map = {r.id: r.role for r in roles_qs}

    if search:
        role_ids = list(
            roles_qs.filter(role__icontains=search).values_list("id", flat=True)
        )

        if not role_ids:
            permissions = academic_activity_Permission.objects.none()
        else:
            permissions = permissions.filter(role_id__in=role_ids)

    page_size = 25
    paginator = Paginator(permissions, page_size)
    page_obj = paginator.get_page(page)

    data = [
        {
            "id": perm.id,
            "role": role_map.get(perm.role_id, "Unknown"),
            "can_view_all": perm.can_view_all_academic_activity_data,
            "can_view_dept": perm.can_view_department_academic_activity_data,
        }
        for perm in page_obj
    ]

    return JsonResponse({
        "results": data,
        "page": page_obj.number,
        "total_pages": paginator.num_pages,
        "has_next": page_obj.has_next(),
        "has_prev": page_obj.has_previous(),
        "total_count": paginator.count,
        "page_size": page_size,
    })



from collections import OrderedDict, defaultdict
from datetime import date
import os

from django.conf import settings
from django.contrib import messages
from django.contrib.staticfiles import finders
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from user_accounts.decorators import check_permission
from user_accounts.models import Add_Department, StudentDetails
from faculty_management.models import general_information
from examination_management.models import Regulations

from feedback_management.models import (
    AcademicActivityQuestion,
    AcademicActivitySubmission,
    AcademicActivityAnswer,
    gradeupload,
    academic_activity_Permission,
)


def get_academic_year():
    today = date.today()
    current_year = today.year

    if today.month >= 6:
        return f"{current_year}-{current_year + 1}"

    return f"{current_year - 1}-{current_year}"


def get_student_details(request):
    emp = getattr(request.user, "Employee_id", None)
    username = getattr(request.user, "username", None)

    if emp:
        student = (
            StudentDetails.objects.filter(reg_no=emp).first()
            or StudentDetails.objects.filter(umis_id=emp).first()
        )
        if student:
            return student

    if username:
        student = (
            StudentDetails.objects.filter(reg_no=username).first()
            or StudentDetails.objects.filter(umis_id=username).first()
        )
        if student:
            return student

    return None


def group_questions_by_category(questions):
    grouped = OrderedDict()

    for question in questions:
        category = (question.category or "General").strip()
        grouped.setdefault(category, []).append(question)

    return grouped


def get_student_regulation(student):
    regulation_value = str(student.regulation or "").strip()

    if not regulation_value:
        return None

    return (
        Regulations.objects.filter(year=regulation_value).first()
        or Regulations.objects.filter(id=regulation_value).first()
        or Regulations.objects.filter(regulation_number=regulation_value).first()
    )


def _get_faculty_and_department(request):
    user = request.user.Employee_id
    faculty = general_information.objects.select_related("department").get(faculty_id=user)
    return faculty, faculty.department


def _get_academic_activity_permission_scope(request):
    role_id = (
        getattr(request.user, "role_id", None)
        or getattr(request.user, "Role_id", None)
        or getattr(request.user, "role", None)
    )

    permission = None

    if role_id:
        permission = academic_activity_Permission.objects.filter(role_id=role_id).first()

    if not permission:
        return {
            "has_access": False,
            "can_view_all": False,
            "can_view_department": False,
        }

    can_view_all = permission.can_view_all_academic_activity_data
    can_view_department = permission.can_view_department_academic_activity_data

    return {
        "has_access": can_view_all or can_view_department,
        "can_view_all": can_view_all,
        "can_view_department": can_view_department,
    }


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from user_accounts.decorators import check_permission
from faculty_management.models import general_information
from examination_management.models import Regulations

from feedback_management.models import AcademicActivityQuestion


@check_permission("academic_activity_question_entry")
def academic_activity_question_entry(request):
    question = None

    user = request.user.Employee_id
    faculty = get_object_or_404(general_information, faculty_id=user)

    regulations = Regulations.objects.all()

    revised_pos = Program_outcomes.objects.filter(
        is_active=True,
        is_revised=True
    ).order_by("program_number")

    non_revised_pos = Program_outcomes.objects.filter(
        is_active=True,
        is_revised=False
    ).order_by("program_number")

    edit_id = request.GET.get("edit")
    if edit_id:
        question = get_object_or_404(AcademicActivityQuestion, pk=edit_id)

    if request.method == "POST":
        action_type = request.POST.get("action_type")

        if action_type == "set_window":
            regulation_id = request.POST.get("window_regulation")
            start_date = request.POST.get("common_start_date") or None
            end_date = request.POST.get("common_end_date") or None

            regulation = get_object_or_404(Regulations, id=regulation_id)

            AcademicActivityQuestion.objects.filter(regulation=regulation).update(
                start_date=start_date,
                end_date=end_date
            )

            messages.success(request, "Academic activity survey window updated successfully.")
            return redirect("academic_activity_question_entry")

        question_text = (request.POST.get("question_text") or "").strip()
        category = (request.POST.get("category") or "").strip()
        regulation_id = request.POST.get("regulation")
        po_type = request.POST.get("po_type")
        selected_po_ids = request.POST.getlist("program_outcomes[]")

        if not regulation_id:
            messages.error(request, "Please select regulation.")
            return redirect("academic_activity_question_entry")

        if not question_text:
            messages.error(request, "Question text is required.")
            return redirect("academic_activity_question_entry")

        if po_type not in ["revised", "non_revised"]:
            messages.error(request, "Please select PO type.")
            return redirect("academic_activity_question_entry")

        if not selected_po_ids:
            messages.error(request, "Please select at least one PO.")
            return redirect("academic_activity_question_entry")

        is_revised = True if po_type == "revised" else False

        selected_pos = Program_outcomes.objects.filter(
            id__in=selected_po_ids,
            is_active=True,
            is_revised=is_revised
        )

        po_values = {
            f"po{i}": False
            for i in range(1, 13)
        }

        for po in selected_pos:
            po_number = (po.program_number or "").strip().upper().replace(" ", "")

            if po_number.startswith("PO"):
                number = po_number.replace("PO", "")

                if number.isdigit():
                    field_name = f"po{int(number)}"

                    if field_name in po_values:
                        po_values[field_name] = True

        if not any(po_values.values()):
            messages.error(request, "Selected PO numbers must be between PO1 and PO12.")
            return redirect("academic_activity_question_entry")

        regulation = get_object_or_404(Regulations, id=regulation_id)

        existing_window_question = (
            AcademicActivityQuestion.objects
            .filter(regulation=regulation)
            .exclude(start_date__isnull=True, end_date__isnull=True)
            .order_by("-id")
            .first()
        )

        inherited_start_date = existing_window_question.start_date if existing_window_question else None
        inherited_end_date = existing_window_question.end_date if existing_window_question else None

        if question:
            question.question_text = question_text
            question.category = category
            question.regulation = regulation
            question.created_by = faculty
            question.is_revised = is_revised

            for field_name, value in po_values.items():
                setattr(question, field_name, value)

            if inherited_start_date or inherited_end_date:
                question.start_date = inherited_start_date
                question.end_date = inherited_end_date

            question.save()
            messages.success(request, "Academic activity question updated successfully.")

        else:
            AcademicActivityQuestion.objects.create(
                question_text=question_text,
                category=category,
                regulation=regulation,
                created_by=faculty,
                is_revised=is_revised,
                start_date=inherited_start_date,
                end_date=inherited_end_date,
                **po_values
            )

            messages.success(request, "Academic activity question added successfully.")

        return redirect("academic_activity_question_entry")

    academic_activity_questions = (
        AcademicActivityQuestion.objects
        .select_related("regulation", "created_by")
        .order_by("-id")
    )

    common_window_obj = (
        AcademicActivityQuestion.objects
        .exclude(start_date__isnull=True, end_date__isnull=True)
        .order_by("-id")
        .first()
    )

    return render(
        request,
        "feedback_management/faculty/entry/academic_activity_question_entry.html",
        {
            "faculty": faculty,
            "regulations": regulations,
            "question": question,
            "academic_activity_questions": academic_activity_questions,
            "revised_pos": revised_pos,
            "non_revised_pos": non_revised_pos,
            "common_start_date": common_window_obj.start_date if common_window_obj else None,
            "common_end_date": common_window_obj.end_date if common_window_obj else None,
        }
    )


@check_permission("academic_activity_question_entry")
def delete_academic_activity_question(request, pk):
    question = get_object_or_404(AcademicActivityQuestion, pk=pk)
    question.delete()

    messages.success(request, "Academic activity question deleted successfully.")
    return redirect("academic_activity_question_entry")



def academic_activity_survey(request):
    student = get_student_details(request)

    if not student:
        messages.error(request, "Student record not found.")
        return redirect("home")

    regulation = get_student_regulation(student)

    if not regulation:
        messages.error(request, "Student regulation not found or not mapped.")
        return redirect("home")

    academic_year = get_academic_year()
    today = date.today()

    active_questions = list(
        AcademicActivityQuestion.objects
        .filter(regulation=regulation)
        .filter(
            Q(start_date__isnull=True) | Q(start_date__lte=today),
            Q(end_date__isnull=True) | Q(end_date__gte=today),
        )
        .order_by("category", "id")
    )

    if not active_questions:
        messages.warning(request, "Academic activity survey is not open now.")
        return redirect("home")

    grade_options = list(gradeupload.objects.all().order_by("-marks", "grade"))

    if not grade_options:
        messages.warning(request, "Grade options are not configured.")
        return redirect("home")

    window_start = min(
        [question.start_date for question in active_questions if question.start_date],
        default=None
    )

    window_end = max(
        [question.end_date for question in active_questions if question.end_date],
        default=None
    )

    grouped = group_questions_by_category(active_questions)

    existing = (
        AcademicActivitySubmission.objects
        .filter(
            student=student,
            regulation=regulation,
            academic_year=academic_year,
        )
        .prefetch_related("answers")
        .first()
    )

    if existing:
        answers_map = {
            answer.question_id: answer.score
            for answer in existing.answers.all()
        }

        score_grade_map = {
            grade.marks: grade.grade
            for grade in grade_options
        }

        return render(
            request,
            "feedback_management/student/academic_activity/academic_activity_form.html",
            {
                "student": student,
                "regulation": regulation,
                "academic_year": academic_year,
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

        for question in active_questions:
            grade_id = (request.POST.get(f"q_{question.id}") or "").strip()

            if not grade_id:
                messages.error(request, f"Please select a grade for: {question.question_text}")
                return redirect("academic_activity_survey")

            try:
                grade_obj = gradeupload.objects.get(pk=int(grade_id))
            except (ValueError, gradeupload.DoesNotExist):
                messages.error(request, f"Invalid grade selected for: {question.question_text}")
                return redirect("academic_activity_survey")

            score = int(grade_obj.marks or 0)
            total += score

            answers.append(
                AcademicActivityAnswer(
                    question=question,
                    selected_grade=grade_obj.grade,
                    score=score,
                )
            )

        try:
            with transaction.atomic():
                submission = AcademicActivitySubmission.objects.create(
                    student=student,
                    regulation=regulation,
                    department=student.department,
                    academic_year=academic_year,
                    total_score=total,
                    window_start=window_start,
                    window_end=window_end,
                )

                for answer in answers:
                    answer.submission = submission

                AcademicActivityAnswer.objects.bulk_create(answers)

            messages.success(request, "Academic activity survey submitted successfully.")
            return redirect("academic_activity_survey")

        except Exception as e:
            messages.error(request, f"Error saving academic activity survey: {str(e)}")
            return redirect("academic_activity_survey")

    return render(
        request,
        "feedback_management/student/academic_activity/academic_activity_form.html",
        {
            "student": student,
            "regulation": regulation,
            "academic_year": academic_year,
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


@check_permission("view_academic_activity_survey")
def view_academic_activity_survey(request):
    faculty, faculty_department = _get_faculty_and_department(request)

    permission_scope = _get_academic_activity_permission_scope(request)

    if not permission_scope["has_access"]:
        return HttpResponseBadRequest("You do not have permission to view academic activity survey data.")

    sel_department_id = (request.GET.get("department_id") or "").strip()
    sel_regulation_id = (request.GET.get("regulation_id") or "").strip()
    sel_academic_year = (request.GET.get("academic_year") or "").strip()
    sel_batch = (request.GET.get("batch") or "").strip()
    sel_year = (request.GET.get("year") or "").strip()
    sel_sem = (request.GET.get("semester") or "").strip()
    sel_section = (request.GET.get("section") or "").strip()

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

    regulations = Regulations.objects.all()
    regulation = Regulations.objects.filter(id=sel_regulation_id).first() if sel_regulation_id else None

    academic_years = (
        AcademicActivitySubmission.objects
        .exclude(academic_year__isnull=True)
        .exclude(academic_year__exact="")
        .values_list("academic_year", flat=True)
        .distinct()
        .order_by("-academic_year")
    )

    if not sel_academic_year:
        sel_academic_year = get_academic_year()

    base_students_qs = StudentDetails.objects.filter(department=department) if department else StudentDetails.objects.none()

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

    filters_applied = bool(
        department and regulation and sel_academic_year and sel_batch and sel_year and sel_sem
    )

    ordered_questions = []
    question_ids = []
    category_spans = []

    if regulation:
        ordered_questions = list(
            AcademicActivityQuestion.objects
            .filter(regulation=regulation)
            .order_by("category", "id")
        )

        question_ids = [question.id for question in ordered_questions]

        if ordered_questions:
            current_category = ordered_questions[0].category or "General"
            span = 0

            for question in ordered_questions:
                qcat = question.category or "General"

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

    latest_submission_map = OrderedDict()
    submitted_student_ids = set()
    student_q_marks = defaultdict(dict)
    student_total = defaultdict(int)

    if filters_applied and student_ids:
        submissions_qs = (
            AcademicActivitySubmission.objects
            .filter(
                student_id__in=student_ids,
                regulation=regulation,
                department=department,
                academic_year=sel_academic_year,
            )
            .select_related("student", "regulation", "department")
            .order_by("student_id", "-submitted_at")
        )

        for submission in submissions_qs:
            if submission.student_id not in latest_submission_map:
                latest_submission_map[submission.student_id] = submission

        latest_submission_ids = [submission.id for submission in latest_submission_map.values()]

        if latest_submission_ids:
            answers = (
                AcademicActivityAnswer.objects
                .filter(
                    submission_id__in=latest_submission_ids,
                    question_id__in=question_ids,
                )
                .select_related("submission", "question")
                .order_by("submission__student_id", "question_id")
            )

            for answer in answers:
                sid = answer.submission.student_id
                qid = answer.question_id
                score_value = int(answer.score or 0)

                submitted_student_ids.add(sid)
                student_q_marks[sid][qid] = score_value
                student_total[sid] += score_value

    rows = []

    if filters_applied:
        for idx, student in enumerate(students, start=1):
            submission = latest_submission_map.get(student.id)

            rows.append({
                "sno": idx,
                "student": student,
                "submission": submission,
                "section": student.section or "-",
                "marks": student_q_marks.get(student.id, {}),
                "total": student_total.get(student.id, 0),
                "is_submitted": student.id in submitted_student_ids,
            })

    return render(
        request,
        "feedback_management/faculty/academic_activity/view_academic_activity_survey.html",
        {
            "faculty": faculty,
            "department": department,
            "departments": departments,
            "can_view_all": permission_scope["can_view_all"],
            "can_view_department": permission_scope["can_view_department"],

            "regulations": regulations,
            "selected_regulation": regulation,
            "academic_years": academic_years,

            "sel_department_id": sel_department_id,
            "sel_regulation_id": sel_regulation_id,
            "sel_academic_year": sel_academic_year,
            "sel_batch": sel_batch,
            "sel_year": sel_year,
            "sel_sem": sel_sem,
            "sel_section": sel_section,

            "batches": batches,
            "years": years,
            "semesters": semesters,
            "sections": sections,

            "filters_applied": filters_applied,

            "total_students": len(students) if filters_applied else 0,
            "submitted_students": len(submitted_student_ids),
            "not_submitted_students": (len(students) - len(submitted_student_ids)) if filters_applied else 0,

            "category_spans": category_spans,
            "ordered_questions": ordered_questions,
            "rows": rows,
        }
    )


def _draw_rit_header_footer(c: canvas.Canvas, page_w, page_h, title="ACADEMIC ACTIVITY SURVEY", subtitle=""):
    left_margin = 18 * mm
    right_margin = page_w - 18 * mm
    top_margin = page_h - 12 * mm
    bottom_margin = 14 * mm

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
            c.drawImage(img, left_margin, top_margin - th + 2 * mm, width=tw, height=th, mask="auto")
        except Exception:
            pass

    c.setFillColor(colors.HexColor("#2C3E50"))
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(page_w / 2.0, top_margin, "RAMCO INSTITUTE OF TECHNOLOGY")

    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(page_w / 2.0, top_margin - 7 * mm, title)

    if subtitle:
        c.setFont("Helvetica", 10)
        c.drawCentredString(page_w / 2.0, top_margin - 13 * mm, subtitle)

    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.line(left_margin, top_margin - 16 * mm, right_margin, top_margin - 16 * mm)

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


@check_permission("view_academic_activity_survey")
def academic_activity_submission_pdf(request, pk):
    submission = get_object_or_404(
        AcademicActivitySubmission.objects.select_related("student", "regulation", "department"),
        pk=pk
    )

    answers = (
        AcademicActivityAnswer.objects
        .filter(submission=submission)
        .select_related("question")
        .order_by("question__category", "question__id")
    )

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="Academic_Activity_Survey.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=48 * mm,
        bottomMargin=25 * mm,
    )

    styles = getSampleStyleSheet()

    info_style = ParagraphStyle(
        "info_style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
    )

    q_style = ParagraphStyle(
        "q_style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        alignment=TA_LEFT,
    )

    story = []

    story.append(Paragraph("Academic Activity Survey - Student Report", styles["Heading4"]))
    story.append(Paragraph(f"Student: {submission.student}", info_style))
    story.append(Paragraph(f"Department: {submission.department}", info_style))
    story.append(Paragraph(f"Regulation: {submission.regulation}", info_style))
    story.append(Paragraph(f"Academic Year: {submission.academic_year or '-'}", info_style))
    story.append(Paragraph(f"Submitted On: {submission.submitted_at.strftime('%d-%m-%Y')}", info_style))
    story.append(Paragraph(f"Total Score: {submission.total_score}", info_style))
    story.append(Spacer(1, 10))

    data = [["S.No", "Category", "Question", "Grade", "Score"]]

    for idx, answer in enumerate(answers, start=1):
        data.append([
            str(idx),
            answer.question.category if answer.question and answer.question.category else "General",
            Paragraph(answer.question.question_text if answer.question else "-", q_style),
            answer.selected_grade or "-",
            str(answer.score or 0),
        ])

    table = Table(
        data,
        colWidths=[15 * mm, 35 * mm, 90 * mm, 22 * mm, 20 * mm],
        repeatRows=1
    )

    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d1d5db")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ff")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (2, 1), (2, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    story.append(table)

    def _on_page(canv, doc_):
        page_w, page_h = doc_.pagesize
        _draw_rit_header_footer(
            canv,
            page_w,
            page_h,
            title="ACADEMIC ACTIVITY SURVEY",
            subtitle=f"Regulation: {submission.regulation} | Academic Year: {submission.academic_year or '-'}"
        )

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)

    return response


@check_permission("view_academic_activity_survey")
def view_academic_activity_survey_bulk_pdf(request):
    faculty, faculty_department = _get_faculty_and_department(request)

    permission_scope = _get_academic_activity_permission_scope(request)

    if not permission_scope["has_access"]:
        return HttpResponseBadRequest("You do not have permission to view academic activity survey data.")

    sel_department_id = (request.GET.get("department_id") or "").strip()
    sel_regulation_id = (request.GET.get("regulation_id") or "").strip()
    sel_academic_year = (request.GET.get("academic_year") or "").strip()
    sel_batch = (request.GET.get("batch") or "").strip()
    sel_year = (request.GET.get("year") or "").strip()
    sel_sem = (request.GET.get("semester") or "").strip()
    sel_section = (request.GET.get("section") or "").strip()

    if permission_scope["can_view_all"]:
        if sel_department_id:
            department = Add_Department.objects.filter(id=sel_department_id, is_active=True).first()
        else:
            department = faculty_department
    else:
        department = faculty_department

    if not department:
        return HttpResponseBadRequest("Invalid department.")

    regulation = Regulations.objects.filter(id=sel_regulation_id).first()

    if not regulation:
        return HttpResponseBadRequest("Invalid regulation.")

    if not sel_academic_year:
        return HttpResponseBadRequest("Academic year is required.")

    if not sel_batch or not sel_year or not sel_sem:
        return HttpResponseBadRequest("Batch, year and semester are required.")

    questions = list(
        AcademicActivityQuestion.objects
        .filter(regulation=regulation)
        .order_by("category", "id")
    )

    if not questions:
        return HttpResponseBadRequest("No academic activity questions configured.")

    question_ids = [question.id for question in questions]

    category_spans = []
    question_number_map = {}

    current_category = questions[0].category or "General"
    span = 0

    for idx, question in enumerate(questions, start=1):
        qcat = question.category or "General"
        question_number_map[question.id] = idx

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

    students_qs = StudentDetails.objects.filter(
        department=department,
        batch=sel_batch,
        year=str(sel_year),
        semester=str(sel_sem),
    )

    if sel_section:
        students_qs = students_qs.filter(section=sel_section)

    students = list(students_qs.order_by("section", "reg_no"))
    student_ids = [student.id for student in students]

    if not students:
        return HttpResponseBadRequest("No students found for selected filters.")

    submissions_qs = (
        AcademicActivitySubmission.objects
        .filter(
            student_id__in=student_ids,
            regulation=regulation,
            department=department,
            academic_year=sel_academic_year,
        )
        .select_related("student", "regulation", "department")
        .prefetch_related("answers")
        .order_by("student_id", "-submitted_at")
    )

    latest_submission_map = OrderedDict()

    for submission in submissions_qs:
        if submission.student_id not in latest_submission_map:
            latest_submission_map[submission.student_id] = submission

    student_question_scores = defaultdict(dict)
    student_total = defaultdict(int)

    for sid, submission in latest_submission_map.items():
        student_total[sid] = int(submission.total_score or 0)

        for answer in submission.answers.all():
            if answer.question_id in question_ids:
                student_question_scores[sid][answer.question_id] = int(answer.score or 0)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="Academic_Activity_Survey_Bulk_Report.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        leftMargin=8 * mm,
        rightMargin=8 * mm,
        topMargin=50 * mm,
        bottomMargin=25 * mm,
    )

    styles = getSampleStyleSheet()

    info_style = ParagraphStyle(
        "info_style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
    )

    p_center = ParagraphStyle(
        "p_center",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=5.2,
        leading=6,
        alignment=TA_CENTER,
    )

    p_center_bold = ParagraphStyle(
        "p_center_bold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=5.4,
        leading=6,
        alignment=TA_CENTER,
    )

    story = []

    story.append(Paragraph("Academic Activity Survey - Bulk Report", styles["Heading4"]))
    story.append(Paragraph(f"Department: {department.Department}", info_style))
    story.append(Paragraph(f"Regulation: {regulation}", info_style))
    story.append(Paragraph(f"Academic Year: {sel_academic_year}", info_style))
    story.append(Paragraph(
        f"Batch: {sel_batch} &nbsp;&nbsp;&nbsp; "
        f"Year: {sel_year} &nbsp;&nbsp;&nbsp; "
        f"Semester: {sel_sem} &nbsp;&nbsp;&nbsp; "
        f"Section: {sel_section or 'All'}",
        info_style
    ))
    story.append(Spacer(1, 8))

    row1 = ["S.No", "Reg No"]

    for category in category_spans:
        row1.append(Paragraph(str(category["category"]), p_center))
        for _ in range(category["span"] - 1):
            row1.append("")

    row1.append(Paragraph("Total", p_center))

    row2 = ["", ""]

    for question in questions:
        row2.append(Paragraph(str(question_number_map.get(question.id, "")), p_center_bold))

    row2.append("")

    data = [row1, row2]

    for idx, student in enumerate(students, start=1):
        row = [
            str(idx),
            str(getattr(student, "reg_no", "") or "-"),
        ]

        for question in questions:
            row.append(str(student_question_scores.get(student.id, {}).get(question.id, "-")))

        row.append(str(student_total.get(student.id, 0)))

        data.append(row)

    usable_w = doc.pagesize[0] - doc.leftMargin - doc.rightMargin

    col_w_sno = 12 * mm
    col_w_reg = 26 * mm
    col_w_total = 16 * mm
    q_count = len(questions)

    fixed_w = col_w_sno + col_w_reg + col_w_total
    q_w = max((usable_w - fixed_w) / max(q_count, 1), 7 * mm)

    col_widths = [col_w_sno, col_w_reg] + [q_w] * q_count + [col_w_total]

    table = Table(data, colWidths=col_widths, repeatRows=2)

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
    ])

    table_style.add("SPAN", (0, 0), (0, 1))
    table_style.add("SPAN", (1, 0), (1, 1))
    table_style.add("SPAN", (-1, 0), (-1, 1))

    start_col = 2

    for category in category_spans:
        end_col = start_col + category["span"] - 1
        table_style.add("SPAN", (start_col, 0), (end_col, 0))
        start_col = end_col + 1

    table.setStyle(table_style)
    story.append(table)

    def _on_page(canv, doc_):
        page_w, page_h = doc_.pagesize
        _draw_rit_header_footer(
            canv,
            page_w,
            page_h,
            title="ACADEMIC ACTIVITY SURVEY",
            subtitle=f"Academic Year: {sel_academic_year} | Regulation: {regulation}"
        )

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)

    return response