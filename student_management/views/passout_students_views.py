from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Count
from django.db import connection
from datetime import date
from datetime import datetime   # <-- ADDED: ensure datetime is available throughout the file
import pandas as pd
from io import BytesIO
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

from django.urls import reverse
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from user_accounts.decorators import no_cache, is_super_user
from student_management.models import *
from django.shortcuts import render
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers.json import DjangoJSONEncoder
import re

from student_management.decorators import student_management

from user_accounts.models import Role, USER
from student_management.models import StudentManagementPermissions
from user_accounts.decorators import faculty_login_required, check_permission, no_cache

from user_accounts.models import StudentDetails
from course_management.models import *
from course_management.models import PassOutStudents


from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A3, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from datetime import date
from io import BytesIO
from django.utils import timezone
from django.conf import settings
import os
from xml.sax.saxutils import escape
from user_accounts.models import PersonalDetails, AdmissionRecords, AcademicDetails

HEADER_TOP = A4[1] - 62
DETAILS_START_Y = 568
DETAILS_END_Y = 216
FOOTER_START_Y = 120
FOOTER_START_Y = 120

TC_TABLE_X = 36
TC_LABEL_WIDTH = 224
TC_COLON_WIDTH = 10
TC_VALUE_WIDTH = 289
TC_ROW_SLOT_HEIGHTS = [18, 18, 28, 28, 18, 28, 28, 18, 18, 18, 28, 28, 18, 18, 28, 28, 18]
TC_ROW_GAP = 4
TC_BODY_FONT = "Times-Roman"
TC_BODY_FONT_SIZE = 12.2
TC_BODY_MIN_FONT_SIZE = 9.6

# Add helper to convert integers to Roman numerals
def int_to_roman(num):
	"""
	Convert positive integer to Roman numeral (supports up to 3999).
	Returns "N/A" for missing/invalid input, or the original value as string if non-numeric.
	"""
	if num is None or (isinstance(num, str) and not num.strip()):
		return "N/A"
	try:
		val = int(str(num).strip())
	except Exception:
		# non-numeric, return original value as-is
		return str(num)
	if val <= 0:
		return "N/A"
	val_map = [
		(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
		(100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
		(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")
	]
	res = ""
	for v, r in val_map:
		while val >= v:
			res += r
			val -= v
	return res


def _academic_departments_qs():
    return Add_Department.objects.filter(is_active=True, is_academic=True).order_by("Department")


def _get_department_degree_names(student):
    department_name = "N/A"
    degree_name = "N/A"
    try:
        if getattr(student, "department", None) and getattr(student.department, "id", None):
            dept = Add_Department.objects.select_related("degree").get(id=student.department.id)
            department_name = _safe_text(getattr(dept, "Department", None))
            degree_name = _safe_text(getattr(getattr(dept, "degree", None), "degree", None))
    except Exception:
        department_name = "N/A"
        degree_name = "N/A"
    return department_name, degree_name


def _parse_conduct_certificate_date(value):
    raw = _safe_text(value, fallback="")
    if not raw:
        return date.today().strftime("%d.%m.%Y")
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y", "%b. %d, %Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%d.%m.%Y")
        except Exception:
            continue
    return raw


def _draw_conduct_certificate_page(
    pdf,
    student,
    department_name,
    degree_name,
    batch_start,
    batch_end,
    from_month,
    to_month,
    
    formatted_date,
   serial_no="001",
):
    width, height = A4
    border_color = colors.HexColor("#9B4E2C")
    title_color = colors.HexColor("#B13A18")
    header_blue = colors.HexColor("#23335E")
    subtitle_green = colors.HexColor("#3A6E2B")
    footer_blue = colors.HexColor("#243A66")

    student_name = _safe_text(getattr(getattr(student, "student", None), "name", None))
    reg_no = _safe_text(getattr(getattr(student, "student", None), "reg_no", None))
    conduct_value = (getattr(student, "conduct", None) or "Good").strip().title()
    certificate_number = _safe_text(getattr(student, "certificate_number", None))
    batch_start_text = _safe_text(batch_start)
    batch_end_text = _safe_text(batch_end)
    left_margin = 88
    right_margin = width - 88

    pdf.saveState()
    try:
        _draw_watermark(pdf, width, height)

        pdf.setStrokeColor(border_color)
        pdf.setLineWidth(1.2)
        pdf.rect(28, 25, width - 56, height - 50, stroke=1, fill=0)
        pdf.setLineWidth(0.6)
        pdf.rect(34, 31, width - 68, height - 62, stroke=1, fill=0)

        _draw_fit_image(pdf, _static_image_path("images", "ritlogo.png"), 44, height - 118, 72, 72)
        pdf.setFillColor(header_blue)
        pdf.setFont("Times-Bold", 20)
        pdf.drawCentredString(width / 2.0 +15, height - 70, "RAMCO INSTITUTE OF TECHNOLOGY")
        pdf.setFillColor(colors.HexColor("#B13A18"))
        pdf.setFont("Times-Roman", 11.5)
        pdf.drawCentredString(width / 2.0, height - 86, "(An Autonomous Institution)")
        pdf.setFillColor(colors.HexColor("#3A6E2B"))
        pdf.setFont("Times-Roman", 11)
        pdf.drawCentredString(
            width / 2.0,
            height - 102,
            "(Approved by AICTE - New Delhi and Affiliated to Anna University - Chennai)",
        )
        pdf.setFillColor(colors.HexColor("#3A6E2B"))
        pdf.setFont("Times-Roman", 10.5)
        pdf.drawCentredString(width / 2.0, height - 118, "Rajapalayam - 626117.")

        pdf.setFillColor(colors.black)
        pdf.setFont("Times-Roman", 11)

        if serial_no:
            pdf.drawString(52, height - 178, f"S.No. : {serial_no}")

        pdf.drawString(52, height - 194, f"REF. No. : {certificate_number}")
        pdf.drawRightString(width - 52, height - 194, f"Date : {formatted_date}")

        pdf.setFillColor(title_color)
        pdf.setFont("Times-Bold", 28)
        pdf.drawCentredString(width / 2.0, height - 238, "CONDUCT CERTIFICATE")

        body_font = "Times-Italic"
        body_size = 16.5
        body_width = width - 130
        body_left = (width - body_width) / 2.0
        body_style = ParagraphStyle(
            "conduct_body",
            fontName=body_font,
            fontSize=body_size,
            leading=31,
            alignment=TA_JUSTIFY,
            textColor=colors.black,
            leftIndent=0,
            rightIndent=0,
        )
        body_text = (
            f'This is to certify that Mr. / Ms. '
            f'<b>{escape(student_name)} ({escape(reg_no)})</b> has studied in '
            f'<b>{escape(_safe_text(degree_name))} - {escape(_safe_text(department_name))}</b>. '
            f'Branch of this college from <b>{escape(_safe_text(from_month))} {escape(batch_start_text)}</b> to '
            f'<b>{escape(_safe_text(to_month))} {escape(batch_end_text)}</b>, and that during the period '
            f'his / her character &amp; conduct have been <b>{escape(conduct_value)}</b>.'
        )
        body_para = Paragraph(body_text, body_style)
        _, body_para_h = body_para.wrap(body_width, 260)
        body_para.drawOn(pdf, body_left, 465 - body_para_h)

        pdf.setFillColor(footer_blue)
        pdf.setFont("Times-Bold", 12)
        footer_y = 130
        _draw_certificate_footer_seal(pdf, width, footer_y)
        pdf.drawCentredString(110, footer_y, "HOD")
        pdf.drawCentredString(width - 110, footer_y, "PRINCIPAL")
    finally:
        pdf.restoreState()


from datetime import datetime, date

def _build_conduct_certificate_data(student, request):
    department_name, degree_name = _get_department_degree_names(student)

    try:
        # Use Year of Admission instead of Batch
        year_of_admission = _safe_text(
            getattr(getattr(student, "student", None), "year_of_admission", None)
        )

        batch = _safe_text(
            getattr(getattr(student, "student", None), "batch", None)
        )

        degree_duration = None

        # Fetch duration from Degree
        if getattr(student, "department", None):
            department_obj = Add_Department.objects.select_related("degree").get(
                id=student.department.id
            )

            degree_duration = getattr(
                getattr(department_obj, "degree", None),
                "effective_duration",
                None,
            )

            if degree_duration in (None, 0):
                degree_duration = getattr(
                    getattr(department_obj, "degree", None),
                    "duration",
                    None,
                )

        duration = int(str(degree_duration).strip()) if degree_duration else 4

        start_year = int(str(year_of_admission).strip())

        # If admission year is greater than batch year,
        # reduce duration by 1
        try:
            batch_year = int(str(batch).strip())
            if start_year > batch_year:
                duration -= 1
        except Exception:
            pass

        batch_start = str(start_year)
        batch_end = str(start_year + duration)

    except Exception:
        batch_start = "N/A"
        batch_end = "N/A"

    # Get From Month from StudentDetails.date_of_admission
    date_of_admission = _safe_text(
        getattr(getattr(student, "student", None), "date_of_admission", None)
    )

    try:
        from_month = datetime.strptime(
            date_of_admission,
            "%d/%m/%Y"
        ).strftime("%B")
    except Exception:
        from_month = "January"

    # To Month from frontend
    to_month = request.GET.get("to_month", "December")

    current_date = (
        request.GET.get("date")
        or request.GET.get("date_entry")
        or date.today().strftime("%Y-%m-%d")
    )

    formatted_date = _parse_conduct_certificate_date(current_date)

    return {
        "department_name": department_name,
        "degree_name": degree_name,
        "batch_start": batch_start,
        "batch_end": batch_end,
        "from_month": from_month,
        "to_month": to_month,
        "formatted_date": formatted_date,
    }



def _draw_course_completion_certificate_page(
    pdf,
    student,
    department_name,
    degree_name,
    batch_start,
    batch_end,
    from_month,
    to_month,
    formatted_date,
    serial_no="001",
):
    width, height = A4
    border_color = colors.HexColor("#2CA9D4")
    header_blue = colors.HexColor("#23335E")
    subtitle_green = colors.HexColor("#3A6E2B")
    title_color = colors.HexColor("#B13A18")
    student_name = _safe_text(getattr(getattr(student, "student", None), "name", None))
    reg_no = _safe_text(getattr(getattr(student, "student", None), "reg_no", None))
    certificate_number = _safe_text(getattr(student, "certificate_number", None))
    body_font = "Times-Italic"
    body_width = width - 110
    body_left = (width - body_width) / 2.0
    left_margin = 52
    right_margin = width - 52

    pdf.saveState()
    try:
        _draw_watermark(pdf, width, height)

        pdf.setStrokeColor(border_color)
        pdf.setLineWidth(0.5)
        pdf.rect(28, 25, width - 56, height - 50, stroke=1, fill=0)
        pdf.setLineWidth(0.6)
        pdf.rect(34, 31, width - 68, height - 62, stroke=1, fill=0)

        _draw_fit_image(pdf, _static_image_path("images", "ritlogo.png"), 44, height - 118, 72, 72)
        pdf.setFillColor(header_blue)
        pdf.setFont("Times-Bold", 20)
        pdf.drawCentredString(width / 2.0 + 15, height - 70, "RAMCO INSTITUTE OF TECHNOLOGY")
        pdf.setFillColor(colors.HexColor("#B13A18"))
        pdf.setFont("Times-Roman", 11.5)
        pdf.drawCentredString(width / 2.0, height - 86, "(An Autonomous Institution)")
        pdf.setFillColor(colors.HexColor("#3A6E2B"))
        pdf.setFont("Times-Roman", 11)
        pdf.drawCentredString(
            width / 2.0,
            height - 102,
            "(Approved by AICTE - New Delhi and Affiliated to Anna University - Chennai)",
        )
        pdf.setFillColor(colors.HexColor("#3A6E2B"))
        pdf.setFont("Times-Roman", 10.5)
        pdf.drawCentredString(width / 2.0, height - 118, "Rajapalayam - 626117.")

        pdf.setFillColor(colors.black)
        pdf.setFont("Times-Roman", 10.5)

        # Serial Number
        pdf.drawString(
            left_margin,
            height - 155,
            f"S.No. : {serial_no}"
        )

        # Reference Number
        meta_y = height - 175
        pdf.drawString(
            left_margin,
            meta_y,
            f"REF.No. : {certificate_number}"
        )

        pdf.drawRightString(
            right_margin,
            meta_y,
            f"Date : {formatted_date}"
        )

        title_text = "COURSE COMPLETION CERTIFICATE"
        pdf.setFillColor(title_color)
        pdf.setFont("Times-Bold", 20)
        title_y = height - 226
        pdf.drawCentredString(width / 2.0, title_y, title_text)

        body_style = ParagraphStyle(
            "course_body",
            fontName=body_font,
            fontSize=16.2,
            leading=27,
            alignment=TA_JUSTIFY,
            textColor=colors.black,
            leftIndent=0,
            rightIndent=0,
        )

        body_text = (
    f'This is to certify that Mr. / Ms. <b>{escape(student_name)}</b> '
    f'<b>({escape(reg_no)})</b> has studied '
    f'<b>{escape(_safe_text(degree_name))}</b> Degree Course in the department of '
    f'<b>{escape(_safe_text(department_name))}</b> in the college from '
    f'<b>{escape(_safe_text(from_month))} {escape(_safe_text(batch_start))}</b> to '
    f'<b>{escape(_safe_text(to_month))} {escape(_safe_text(batch_end))}</b>. '
    f'He / She has successfully completed the prescribed duration of course and passed / appeared '
    'for the final semester examination.'
)

        para = Paragraph(body_text, body_style)
        para_w, para_h = para.wrap(body_width, height)
        para.drawOn(pdf, body_left, title_y - 62 - para_h)

        pdf.setFillColor(colors.HexColor("#B13A18"))
        pdf.setFont("Times-Bold", 12)
        footer_y = 130
        _draw_certificate_footer_seal(pdf, width, footer_y)
        pdf.drawCentredString(110, footer_y, "HOD")
        pdf.drawCentredString(width - 110, footer_y, "PRINCIPAL")
    finally:
        pdf.restoreState()



@check_permission('conduct_certificate')
def conduct_certificate(request):
    # Get all departments from the external DB
    departments = _academic_departments_qs()

    # Get unique batches from passout records (academic departments only)
    batches = (
        PassOutStudents.objects.filter(department__in=departments)
        .values_list("student__batch", flat=True)
        .exclude(student__batch__isnull=True)
        .exclude(student__batch__exact="")
        .distinct()
        .order_by("student__batch")
    )

    selected_department = request.GET.get('department')
    selected_batch = request.GET.get('batch')
    from_month = request.GET.get('from_month', "January")
    to_month = request.GET.get('to_month', "December")
    date_entry = request.GET.get('date_entry') or date.today().strftime('%Y-%m-%d')

    students = PassOutStudents.objects.filter(department__in=departments).order_by('student__reg_no')

    # Filter by department
    if selected_department:
        students = students.filter(department=selected_department)

    # Filter by batch
    if selected_batch:
        students = students.filter(student__batch=selected_batch)

    group_last_date_of_attendance = (
        students.exclude(last_date_of_attendance__isnull=True)
        .order_by("-last_date_of_attendance")
        .values_list("last_date_of_attendance", flat=True)
        .first()
    )

    # Add department names using external DB


    # Full month names
    months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]

    context = {
        'departments': departments,
        'batches': batches,
        'students': students,
        'selected_department': selected_department,
        'selected_batch': selected_batch,
        'from_month': from_month,
        'to_month': to_month,
        'months': months,
        'date_entry': date_entry,
        'group_last_date_of_attendance': group_last_date_of_attendance,
    }
    return render(request, "student_management/passout_students/conduct_certificate.html", context)



def generate_conduct_certificate(request, student_id):
    student = get_object_or_404(PassOutStudents, id=student_id)

    selected_department = request.GET.get("department")
    selected_batch = request.GET.get("batch")

    students = PassOutStudents.objects.filter(
        department__in=_academic_departments_qs()
    ).order_by("student__reg_no")

    if selected_department:
        students = students.filter(department=selected_department)

    if selected_batch:
        students = students.filter(student__batch=selected_batch)

    student_ids = list(students.values_list("id", flat=True))

    try:
        serial_no = str(student_ids.index(student.id) + 1).zfill(3)
    except ValueError:
        serial_no = "001"

    data = _build_conduct_certificate_data(student, request)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    pdf.setTitle(
        f"Conduct Certificate - {student.student.name} ({student.student.reg_no})"
    )

    _draw_conduct_certificate_page(
        pdf,
        student,
        data["department_name"],
        data["degree_name"],
        data["batch_start"],
        data["batch_end"],
        data["from_month"],
        data["to_month"],
        data["formatted_date"],
        serial_no=serial_no,   # pass serial no
    )

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'inline; filename="{_certificate_filename(student.student.name, "Conduct Certificate")}"'
    )
    return response




def generate_bulk_conduct_certificate(request):
    selected_department = request.GET.get('department')
    selected_batch = request.GET.get('batch')

    students = PassOutStudents.objects.filter(
        department__in=_academic_departments_qs()
    ).order_by("student__reg_no")
    if selected_department:
        students = students.filter(department=selected_department)
    if selected_batch:
        students = students.filter(student__batch=selected_batch)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setTitle("Conduct Certificates")

    for index, student in enumerate(students, start=1):
        data = _build_conduct_certificate_data(student, request)
        _draw_conduct_certificate_page(
    pdf,
    student,
    data["department_name"],
    data["degree_name"],
    data["batch_start"],
    data["batch_end"],
    data["from_month"],
    data["to_month"],
    data["formatted_date"],
    serial_no=f"{index:03d}",   # 001, 002, 003...
)
        pdf.showPage()

    pdf.save()
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'inline; filename="{_certificate_filename(_bulk_certificate_owner_name(selected_department), "Conduct Certificate")}"'
    )
    return response


import calendar
from django.utils.timezone import now
from datetime import datetime

@check_permission("course_completion_certificate")
def course_completion_certificate(request):
    # Dropdown data
    departments = _academic_departments_qs()
    batches = (
        PassOutStudents.objects.filter(department__in=departments)
        .values_list("student__batch", flat=True)
        .exclude(student__batch__isnull=True)
        .exclude(student__batch__exact="")
        .distinct()
        .order_by("-student__batch")
    )
    months = list(calendar.month_name)[1:]  # January–December

    selected_department = request.GET.get("department")
    selected_batch = request.GET.get("batch")
    from_month = request.GET.get("from_month", "January")
    to_month = request.GET.get("to_month", "December")
    date_entry = request.GET.get("date_entry", timezone.now().date())

    students = PassOutStudents.objects.filter(department__in=departments).order_by("student__reg_no")

    if selected_department:
        students = students.filter(department__id=selected_department)
    if selected_batch:
        students = students.filter(student__batch=selected_batch)




    # Add serial number (001, 002, 003 ...)
    students_with_serial = []
    for i, s in enumerate(students, start=1):
        s.sl_no = f"{s.certificate_number}"
        students_with_serial.append(s)

    context = {
        "departments": departments,
        "batches": batches,
        "months": months,
        "selected_department": selected_department,
        "selected_batch": selected_batch,
        "from_month": from_month,
        "to_month": to_month,
        "date_entry": date_entry,
        "students": students_with_serial,
    }

    return render(request, "student_management/passout_students/course_completion_certificate.html", context)





def generate_course_completion_certificate(request, student_id):
    student = get_object_or_404(PassOutStudents, id=student_id)

    selected_department = request.GET.get("department")
    selected_batch = request.GET.get("batch")

    to_month = request.GET.get("to_month", "December")

    date_entry = request.GET.get(
        "date_entry",
        timezone.now().strftime("%Y-%m-%d")
    )

    students_qs = PassOutStudents.objects.filter(
        department__in=_academic_departments_qs()
    ).order_by("student__reg_no")

    if selected_department:
        students_qs = students_qs.filter(department_id=selected_department)

    if selected_batch:
        students_qs = students_qs.filter(student__batch=selected_batch)

    serial_param = request.GET.get("serial_no")

    if serial_param and serial_param.isdigit():
        serial_no = f"{int(serial_param):03d}"
    else:
        student_serial_map = {
            obj.id: f"{idx:03d}"
            for idx, obj in enumerate(students_qs, start=1)
        }
        serial_no = student_serial_map.get(student.id, "001")

    try:
        formatted_date = datetime.strptime(
            date_entry,
            "%Y-%m-%d"
        ).strftime("%d.%m.%Y")
    except ValueError:
        try:
            formatted_date = datetime.strptime(
                date_entry,
                "%b. %d, %Y"
            ).strftime("%d.%m.%Y")
        except ValueError:
            formatted_date = date_entry

    department = student.department.Department

    degree_name = getattr(
        getattr(student.department, "degree", None),
        "degree",
        None
    ) or "N/A"

    try:
        admission_date = str(student.student.date_of_admission).strip()
        from_month = datetime.strptime(
            admission_date,
            "%d/%m/%Y"
        ).strftime("%B")
    except Exception:
        from_month = "January"

    try:
        year_of_admission = int(str(student.student.year_of_admission).strip())
        batch_year = int(str(student.student.batch).strip())

        degree_duration = getattr(
            getattr(student.department, "degree", None),
            "effective_duration",
            None
        )

        if degree_duration in (None, 0):
            degree_duration = getattr(
                getattr(student.department, "degree", None),
                "duration",
                4
            )

        duration = int(degree_duration)

        if year_of_admission > batch_year:
            duration -= 1

        batch_start = str(year_of_admission)
        batch_end = str(year_of_admission + duration)

    except Exception:
        batch_start = "N/A"
        batch_end = "N/A"

    buffer = BytesIO()

    pdf = canvas.Canvas(buffer, pagesize=landscape(A3))

    pdf.setTitle(
        f"Course Completion Certificate - "
        f"{student.student.name} ({student.student.reg_no})"
    )

    page_width, page_height = landscape(A3)
    half_width = A4[0]

    for x_offset in (0, half_width):
        pdf.saveState()
        pdf.translate(x_offset, 0)

        _draw_course_completion_certificate_page(
            pdf,
            student,
            department,
            degree_name,
            batch_start,
            batch_end,
            from_month,
            to_month,
            formatted_date,
            serial_no,
        )

        pdf.restoreState()

    pdf.setStrokeColor(colors.HexColor("#C8C8C8"))
    pdf.setDash(3, 3)
    pdf.setLineWidth(0.5)
    pdf.line(half_width, 18, half_width, page_height - 18)
    pdf.setDash()

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'inline; filename="'
        f'{_certificate_filename(student.student.name, "Course Completion Certificate")}"'
    )

    return response


def generate_bulk_course_completion_certificate(request):
    selected_department = request.GET.get("department")
    selected_batch = request.GET.get("batch")

    to_month = request.GET.get("to_month", "December")

    date_entry = request.GET.get(
        "date_entry",
        timezone.now().strftime("%Y-%m-%d")
    )

    students = PassOutStudents.objects.filter(
        department__in=_academic_departments_qs()
    ).order_by("student__reg_no")

    if selected_department:
        students = students.filter(department_id=selected_department)

    if selected_batch:
        students = students.filter(student__batch=selected_batch)

    buffer = BytesIO()

    pdf = canvas.Canvas(buffer, pagesize=landscape(A3))

    page_width, page_height = landscape(A3)
    half_width = A4[0]

    pdf.setTitle("Course Completion Certificates")

    # ✅ SERIAL NUMBER FIXED HERE
    for idx, student in enumerate(students, start=1):

        serial_no = f"{idx:03d}"   # 001, 002, 003...

        department = student.department.Department

        degree_name = getattr(
            getattr(student.department, "degree", None),
            "degree",
            None
        ) or "N/A"

        try:
            from_month = datetime.strptime(
                str(student.student.date_of_admission),
                "%d/%m/%Y"
            ).strftime("%B")
        except:
            from_month = "January"

        try:
            year_of_admission = int(str(student.student.year_of_admission).strip())
            batch_year = int(str(student.student.batch).strip())

            degree_duration = getattr(
                getattr(student.department, "degree", None),
                "effective_duration",
                None
            ) or 4

            duration = int(degree_duration)

            if year_of_admission > batch_year:
                duration -= 1

            batch_start = str(year_of_admission)
            batch_end = str(year_of_admission + duration)

        except:
            batch_start = "N/A"
            batch_end = "N/A"

        try:
            formatted_date = datetime.strptime(
                date_entry,
                "%Y-%m-%d"
            ).strftime("%d.%m.%Y")
        except:
            formatted_date = date_entry

        for x_offset in (0, half_width):
            pdf.saveState()
            pdf.translate(x_offset, 0)

            _draw_course_completion_certificate_page(
                pdf,
                student,
                department,
                degree_name,
                batch_start,
                batch_end,
                from_month,
                to_month,
                formatted_date,
                serial_no,   # ✅ IMPORTANT FIX
            )

            pdf.restoreState()

        pdf.setStrokeColor(colors.HexColor("#C8C8C8"))
        pdf.setDash(3, 3)
        pdf.setLineWidth(0.5)

        pdf.line(
            half_width,
            18,
            half_width,
            page_height - 18
        )

        pdf.setDash()
        pdf.showPage()

    pdf.save()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'inline; filename="{_certificate_filename(_bulk_certificate_owner_name(selected_department), "Course Completion Certificate")}"'
    )

    return response



@check_permission('transfer_certificate')
def transfer_certificate(request):


    selected_department = request.GET.get("department")
    selected_batch = request.GET.get("batch")
    date_entry = request.GET.get("date_entry", timezone.now().date())

    academic_departments = _academic_departments_qs()
    batches = (
        PassOutStudents.objects.filter(department__in=academic_departments)
        .values_list("student__batch", flat=True)
        .exclude(student__batch__isnull=True)
        .exclude(student__batch__exact="")
        .distinct()
        .order_by("-student__batch")
    )
    students = PassOutStudents.objects.filter(department__in=academic_departments).order_by("student__reg_no")
    if selected_department and selected_department != "None":
        students = students.filter(department__id=selected_department)
        # students = students.filter(department=selected_department)
    if selected_batch and selected_batch != "None":
        students = students.filter(student__batch=selected_batch)
    

    departments = academic_departments


    context = {
        "departments": departments,
        "batches": batches,
        "selected_department": selected_department,
        "selected_batch": selected_batch,
        "date_entry": date_entry,
        "students": students,
    }

    return render(request, "student_management/passout_students/transfer_certificate.html", context)


@check_permission('discontinue_transfer_certificate')
def discontinue_transfer_certificate(request):
    selected_department = request.GET.get("department")
    selected_batch = request.GET.get("batch")
    date_entry = request.GET.get("date_entry", timezone.now().date())

    academic_departments = _academic_departments_qs()

    batches = (
        Discontinued_Student.objects
        .filter(department__in=academic_departments)
        .values_list("student__batch", flat=True)
        .exclude(student__batch__isnull=True)
        .exclude(student__batch__exact="")
        .distinct()
        .order_by("-student__batch")
    )

    students = (
        Discontinued_Student.objects
        .select_related("student", "department", "department__degree")
        .filter(department__in=academic_departments)
        .order_by("student__reg_no")
    )

    if selected_department and selected_department != "None":
        students = students.filter(department_id=selected_department)

    if selected_batch and selected_batch != "None":
        students = students.filter(student__batch=selected_batch)

    departments = academic_departments

    context = {
        "departments": departments,
        "batches": batches,
        "selected_department": selected_department,
        "selected_batch": selected_batch,
        "date_entry": date_entry,
        "students": students,
    }

    return render(
        request,
        "student_management/passout_students/discontinue_transfer_certificate.html",
        context
    )

def transfer_certificate_upload_excel(request):
    """
    Upload TC excel data and save into PassOutStudents records.
    Expected header row is at index 4 (0-based) as in provided TC sheets.
    """
    if request.method == "POST":
        upload_file = request.FILES.get("tc_excel")
        if not upload_file:
            messages.error(request, "Please choose an Excel file to upload.")
            return redirect("transfer_certificate_upload_excel")

        required_cols = [
            "TC No",
            "Register No",
            "Whether quallified for promotion to Higher class",
            "Date in which student requested for TC",
            "Last date of Attendance in the Institution",
            "Reason for which TC was Issued",
            "Character and Conduct",
        ]
        try:
            # Support both formats:
            # 1) Legacy TC sheets (header in row index 4)
            # 2) Template download sheets (header in first row)
            raw_df = pd.read_excel(upload_file, header=None)
            header_row_index = None

            scan_rows = min(len(raw_df), 15)
            for i in range(scan_rows):
                row_values = {str(v).strip() for v in raw_df.iloc[i].tolist() if pd.notna(v)}
                if "TC No" in row_values and "Register No" in row_values:
                    header_row_index = i
                    break

            if header_row_index is None:
                messages.error(
                    request,
                    "Header row not found. Please use the provided template or valid TC format.",
                )
                return redirect("transfer_certificate_upload_excel")

            upload_file.seek(0)
            df = pd.read_excel(upload_file, header=header_row_index)
        except Exception as exc:
            messages.error(request, f"Unable to read Excel file: {exc}")
            return redirect("transfer_certificate_upload_excel")

        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            messages.error(request, f"Missing columns: {', '.join(missing_cols)}")
            return redirect("transfer_certificate_upload_excel")

        created_count = 0
        updated_count = 0
        skipped_count = 0
        skipped_rows = []
        admission_created_count = 0
        admission_updated_count = 0
        admission_error_count = 0

        def _to_date(value):
            if pd.isna(value) or value is None:
                return None
            try:
                dt = pd.to_datetime(value, dayfirst=True, errors="coerce")
                if pd.isna(dt):
                    return None
                return dt.date()
            except Exception:
                return None

        def _first_text(*values):
            for value in values:
                if value is None:
                    continue
                text = str(value).strip()
                if text and text.lower() != "nan":
                    return text
            return ""

        for idx, row in df.iterrows():
            reg_raw = row.get("Register No")
            tc_no = row.get("TC No")
            if pd.isna(reg_raw) or pd.isna(tc_no):
                continue

            reg_no = str(reg_raw).strip()
            if reg_no.endswith(".0"):
                reg_no = reg_no[:-2]

            try:
                student_obj = StudentDetails.objects.get(reg_no=reg_no)
            except StudentDetails.DoesNotExist:
                skipped_count += 1
                skipped_rows.append(f"Row {idx + 6}: Register No {reg_no} not found")
                continue

            # Excel upload process is only for 2022 batch students.
            try:
                if int(str(student_obj.batch).strip()) != 2022:
                    skipped_count += 1
                    skipped_rows.append(
                        f"Row {idx + 6}: Register No {reg_no} skipped (batch {student_obj.batch}, only 2022 allowed)"
                    )
                    continue
            except Exception:
                skipped_count += 1
                skipped_rows.append(
                    f"Row {idx + 6}: Register No {reg_no} skipped (invalid batch, only 2022 allowed)"
                )
                continue

            # Save UMIS number into StudentDetails from uploaded excel.
            umis_no = str(row.get("UMIS No") or "").strip()
            if umis_no and str(getattr(student_obj, "umis_id", "") or "").strip() != umis_no:
                student_obj.umis_id = umis_no
                student_obj.save(update_fields=["umis_id"])

            qualified_src = str(
                row.get("Whether quallified for promotion to Higher class") or ""
            ).strip()
            qualified_norm = "No" if qualified_src.lower() == "no" else "Yes"

            tc_requested_date = _to_date(row.get("Date in which student requested for TC"))
            last_date_of_attendance = _to_date(row.get("Last date of Attendance in the Institution"))

            reason = str(row.get("Reason for which TC was Issued") or "").strip() or None
            conduct_raw = str(row.get("Character and Conduct") or "").strip().title()
            conduct_norm = conduct_raw if conduct_raw in {"Good", "Average", "Bad"} else "Good"

            try:
                year_of_passing = int(student_obj.batch) + 4 if student_obj.batch else timezone.now().year
            except Exception:
                year_of_passing = timezone.now().year

            defaults = {
                "department": student_obj.department,
                "year_of_passing": year_of_passing,
                "certificate_number": str(tc_no).strip(),
                "qualified_higher_class": qualified_norm,
                "tc_requested_date": tc_requested_date,
                "last_date_of_attendance": last_date_of_attendance,
                "reason_for_tc": reason,
                "conduct": conduct_norm,
            }

            obj, created = PassOutStudents.objects.update_or_create(
                student=student_obj,
                defaults=defaults,
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

            # Sync admission DB so TC PDF fields (father name, DOB, etc.) are available.
            try:
                admission_db = "admissionform1"
                full_name = str(
    row.get("Name of the Student") or student_obj.name or ""
).strip()

# Update StudentDetails.name from Excel if changed
                if full_name and student_obj.name != full_name:
                    student_obj.name = full_name
                    student_obj.save(update_fields=["name"])

                father_name = str(row.get("Father Name") or "N/A").strip()
                roll_no = str(row.get("Roll No.") or "").strip()
                umis_no = str(row.get("UMIS No") or student_obj.umis_id or "").strip()
                gender = str(row.get("Gender") or "").strip().title() or (
                    student_obj.gender or "N/A"
                )

                dob_value = _to_date(
    row.get("Date of Birth (DD/MM/YYYY)")
) or getattr(student_obj, "date_of_birth", None)

# Update StudentDetails.date_of_birth from Excel if changed
                if dob_value:
                    try:
                        if student_obj.date_of_birth != dob_value:
                            student_obj.date_of_birth = dob_value
                            student_obj.save(update_fields=["date_of_birth"])
                    except Exception:
                        pass

                admission_date = _to_date(
                    row.get("Date of Admission")
                ) or timezone.now().date()
                # Store/Update Year of Admission in StudentDetails
                admission_date = _to_date(row.get("Date of Admission")) or timezone.now().date()

                # Store/Update Year of Admission and Date of Admission in StudentDetails
                if admission_date:
                    admission_year = str(admission_date.year)
                    admission_date_text = admission_date.strftime("%d/%m/%Y")

                    update_fields = []

                    if student_obj.year_of_admission != admission_year:
                        student_obj.year_of_admission = admission_year
                        update_fields.append("year_of_admission")

                    if student_obj.date_of_admission != admission_date_text:
                        student_obj.date_of_admission = admission_date_text
                        update_fields.append("date_of_admission")

                    if update_fields:
                        student_obj.save(update_fields=update_fields)

                nat_rel = str(row.get("Nationality & Religion") or "").strip()
                nationality = "N/A"
                religion = "N/A"
                if "&" in nat_rel:
                    left, right = nat_rel.split("&", 1)
                    nationality = left.strip() or "N/A"
                    religion = right.strip() or "N/A"
                elif nat_rel:
                    nationality = nat_rel

                aadhar_value = _first_text(
                    getattr(student_obj, "aadhar_number", None),
                    row.get("Aadhaar Number"),
                    row.get("Aadhar Number"),
                    row.get("Aadhaar"),
                    row.get("Aadhar"),
                )
                if not aadhar_value:
                    aadhar_value = _first_text(getattr(student_obj, "aadhar_number", None))

                age_val = 0
                if dob_value:
                    try:
                        today = timezone.now().date()
                        age_val = max(0, today.year - dob_value.year - ((today.month, today.day) < (dob_value.month, dob_value.day)))
                    except Exception:
                        age_val = 0

                personal_defaults = {
                    "age": age_val,
                    "caste": "N/A",
                    "community": "N/A",
                    "community_no": "N/A",
                    "date_of_birth": dob_value or timezone.now().date(),
                    "father_mobile_no": "0000000000",
                    "father_name": father_name,
                    "guardian_mobile_no": "0000000000",
                    "guardian_name": father_name,
                    "mother_mobile_no": "0000000000",
                    "mother_name": "N/A",
                    "mother_tounge": "N/A",
                    "name": full_name or student_obj.name or reg_no,
                    "nationality": nationality,
                    "personal_email_id": (student_obj.email or "na@example.com"),
                    "personal_mobile_no": (student_obj.mobile_no or "0000000000"),
                    "registration_no": reg_no,
                    "religion": religion,
                    "roll_no": roll_no or reg_no,
                    "EMIS_ID": umis_no or None,
                    "gender": gender,
                    "Permanent_Address_Door_No": "N/A",
                    "Permanent_Address_Street_Name": "N/A",
                    "Permanent_Address_Location": "N/A",
                    "Permanent_Address_Pincode": "000000",
                    "Permanent_Address_Taluk": "N/A",
                    "Permanent_Address_District": "N/A",
                    "Permanent_Address_State": "N/A",
                    "Communication_Address_Door_No": "N/A",
                    "Communication_Address_Street_Name": "N/A",
                    "Communication_Address_Location": "N/A",
                    "Communication_Address_Pincode": "000000",
                    "Communication_Address_Taluk": "N/A",
                    "Communication_Address_District": "N/A",
                    "Communication_Address_State": "N/A",
                }

                # Prefer Aadhaar for external admission sync, then fall back to registration number.
                personal_obj = None
                if aadhar_value:
                    personal_obj = PersonalDetails.objects.using(admission_db).filter(Aadhaar_Number=aadhar_value).first()
                if not personal_obj and reg_no:
                    personal_obj = PersonalDetails.objects.using(admission_db).filter(registration_no=reg_no).first()

                if personal_obj and not aadhar_value:
                    aadhar_value = _first_text(getattr(personal_obj, "Aadhaar_Number", None))

                if aadhar_value and _first_text(getattr(student_obj, "aadhar_number", None)) != aadhar_value:
                    student_obj.aadhar_number = aadhar_value
                    student_obj.save(update_fields=["aadhar_number"])

                if personal_obj:
                    for k, v in personal_defaults.items():
                        setattr(personal_obj, k, v)
                    if aadhar_value and _first_text(getattr(personal_obj, "Aadhaar_Number", None)) != aadhar_value:
                        personal_obj.Aadhaar_Number = aadhar_value
                    personal_obj.save(using=admission_db)
                else:
                    if not aadhar_value:
                        aadhar_value = f"TEMP{reg_no}"[:20]
                    personal_obj, _ = PersonalDetails.objects.using(admission_db).update_or_create(
                        Aadhaar_Number=aadhar_value,
                        defaults=personal_defaults,
                    )
                    if _first_text(getattr(student_obj, "aadhar_number", None)) != aadhar_value:
                        student_obj.aadhar_number = aadhar_value
                        student_obj.save(update_fields=["aadhar_number"])

                existing_adm_by_no = AdmissionRecords.objects.using(admission_db).filter(admissionNo=reg_no).first()
                existing_adm_by_personal = AdmissionRecords.objects.using(admission_db).filter(PersonalDetailsId=personal_obj).first()
                target_adm = existing_adm_by_personal or existing_adm_by_no

                academic_obj = None
                if target_adm and getattr(target_adm, "AcademicDetailsId_id", None):
                    academic_obj = AcademicDetails.objects.using(admission_db).filter(id=target_adm.AcademicDetailsId_id).first()
                if not academic_obj:
                    academic_obj = AcademicDetails.objects.using(admission_db).create(
                        Occupation="N/A",
                        JobDetails="N/A",
                        AnnualIncome="0",
                        NameOfTheBank="N/A",
                        BranchNameOfTheBank="N/A",
                        IFSC="N/A",
                        MICR="N/A",
                        AccountHolderName=full_name or "N/A",
                        AccountNo="N/A",
                        How="Regular",
                        DateAdmission=datetime.combine(admission_date, datetime.min.time()),
                        AdmissionCategory="Regular",
                        AcademicYear=str(student_obj.batch or ""),
                        AdmissionRecordsId=0,
                    )
                else:
                    academic_obj.DateAdmission = datetime.combine(admission_date, datetime.min.time())
                    academic_obj.AdmissionCategory = getattr(academic_obj, "AdmissionCategory", None) or "Regular"
                    academic_obj.AcademicYear = getattr(academic_obj, "AcademicYear", None) or (str(student_obj.batch) if student_obj.batch else "")
                    academic_obj.save(using=admission_db)

                transport_obj = TransportDetails.objects.using(admission_db).filter(admission_records_id=personal_obj.id).first()
                if not transport_obj:
                    transport_obj = TransportDetails.objects.using(admission_db).create(
                        bus_route=None,
                        bus_stop=None,
                        bus_no=None,
                        bus_time=None,
                        admission_records_id=personal_obj,
                    )

                dept_name = ""
                if getattr(student_obj, "department", None):
                    dept_name = student_obj.department.Department or student_obj.department.degree_department or ""
                if not dept_name:
                    dept_name = str(row.get("Program and Branch in which student was admitted") or "N/A")

                school_details_id = None
                if target_adm and getattr(target_adm, "SchoolDetailsId", None):
                    sid = target_adm.SchoolDetailsId
                    if SchoolDetails.objects.using(admission_db).filter(id=sid).exists():
                        school_details_id = sid
                if not school_details_id:
                    # schooldetails table has many NOT NULL columns; insert a valid placeholder row.
                    with connections[admission_db].cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO schooldetails
                            (SchoolName6th, SchoolType6th, SchoolCategory6th, SchoolMedium6th, PassingYear6th,
                             SchoolName7th, SchoolType7th, SchoolCategory7th, SchoolMedium7th, PassingYear7th,
                             SchoolName8th, SchoolCategory8th, SchoolType8th, SchoolMedium8th, PassingYear8th,
                             SchoolName9th, SchoolType9th, SchoolCategory9th, SchoolMedium9th, PassingYear9th,
                             TPSEligibility, PPSchoolName, AdmissionRecordsId, HSCDetailsId, SSLCDetailsId, DiplomoDetailsId, Qualification)
                            VALUES
                            (%s, %s, %s, %s, %s,
                             %s, %s, %s, %s, %s,
                             %s, %s, %s, %s, %s,
                             %s, %s, %s, %s, %s,
                             %s, %s, %s, %s, %s, %s, %s)
                            """,
                            [
                                "N/A", "N/A", "N/A", "N/A", "N/A",
                                "N/A", "N/A", "N/A", "N/A", "N/A",
                                "N/A", "N/A", "N/A", "N/A", "N/A",
                                "N/A", "N/A", "N/A", "N/A", "N/A",
                                0, 0, 0, None, None, None, "None",
                            ],
                        )
                        school_details_id = cur.lastrowid

                admission_defaults = {
                    "admissionFor": str(row.get("Program and Branch in which student was admitted") or "N/A"),
                    "Quota": "N/A",
                    "Department": dept_name or "N/A",
                    "Mode": "Regular",
                    "PersonalDetailsId": personal_obj,
                    "AcademicDetailsId": academic_obj,
                    "SchoolDetailsId": school_details_id,
                    "TransportDetailsId": transport_obj,
                    "academic_Category": "Regular",
                    "certificate_status": True,
                    "certification_valiation_date": timezone.now().date(),
                    "degree": getattr(getattr(student_obj, "department", None), "degree_department", None) or None,
                }

                if target_adm:
                    for key, val in admission_defaults.items():
                        setattr(target_adm, key, val)
                    if not getattr(target_adm, "admissionNo", None):
                        target_adm.admissionNo = reg_no
                    target_adm.save(using=admission_db)
                    admission_updated_count += 1
                else:
                    AdmissionRecords.objects.using(admission_db).create(
                        admissionNo=reg_no,
                        **admission_defaults,
                    )
                    admission_created_count += 1

            except Exception as adm_exc:
                admission_error_count += 1
                skipped_rows.append(f"Row {idx + 1}: admission sync failed for {reg_no} ({adm_exc})")

        if skipped_count or admission_error_count:
            messages.warning(
                request,
                f"Upload completed. TC Created: {created_count}, TC Updated: {updated_count}, "
                f"TC Skipped: {skipped_count}, Admission Created: {admission_created_count}, "
                f"Admission Updated: {admission_updated_count}, Admission Errors: {admission_error_count}.",
            )
            request.session["tc_upload_skipped_rows"] = skipped_rows[:50]
        else:
            messages.success(
                request,
                f"Upload completed successfully. TC Created: {created_count}, TC Updated: {updated_count}, "
                f"Admission Created: {admission_created_count}, Admission Updated: {admission_updated_count}.",
            )
            request.session.pop("tc_upload_skipped_rows", None)

        return redirect("transfer_certificate_upload_excel")

    skipped_rows = request.session.pop("tc_upload_skipped_rows", [])
    return render(
        request,
        "student_management/passout_students/transfer_certificate_upload_excel.html",
        {"skipped_rows": skipped_rows},
    )





def transfer_certificate_template_excel(request):
    """
    Download TC upload template excel with expected headers.
    """
    columns = [
        "TC No",
        "Roll No.",
        "Register No",
        "Name of the Student",
        "Father Name",
        "Nationality & Religion",
        "Gender",
        "Date of Birth (DD/MM/YYYY)",
        "in Words",
        "Program and Branch in which student was admitted",
        "Date of Admission",
        "Medium Instruction",
        "Duration of Study",
        "Status of the candidate while leaving the college (Year / semester)",
        "Whether quallified for promotion to Higher class",
        "Last date of Attendance in the Institution",
        "Date in which student requested for TC",
        "Reason for which TC was Issued",
        "Character and Conduct",
        "Date",
        "UMIS No",
    ]

    sample_row = {
        "TC No": "2026/AD/001",
        "Roll No.": "22AD001",
        "Register No": "953622243004",
        "Name of the Student": "STUDENT NAME",
        "Father Name": "FATHER NAME",
        "Nationality & Religion": "Indian & Hindu",
        "Gender": "Male",
        "Date of Birth (DD/MM/YYYY)": "29.05.2005",
        "in Words": "Twenty Nine May Two Thousand Five",
        "Program and Branch in which student was admitted": "B.Tech AI &DS",
        "Date of Admission": "20.10.2022",
        "Medium Instruction": "ENGLISH",
        "Duration of Study": "Four Years 2022-2026",
        "Status of the candidate while leaving the college (Year / semester)": "Completed - IV Year - VIII Semester",
        "Whether quallified for promotion to Higher class": "Yes",
        "Last date of Attendance in the Institution": "",
        "Date in which student requested for TC": "",
        "Reason for which TC was Issued": "Course Completed",
        "Character and Conduct": "Good",
        "Date": "",
        "UMIS No": "9000000001",
    }

    df = pd.DataFrame([sample_row], columns=columns)
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="TC Template")
    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="TC_Upload_Template.xlsx"'
    return response




import re

def get_next_certificate_number():
    """
    Returns the next certificate number by checking both
    PassOutStudents and Discontinued_Student.
    Example: 2026/AD/001 -> 2026/AD/002
    """

    numbers = []

    for certificate in PassOutStudents.objects.exclude(
        certificate_number__isnull=True
    ).exclude(certificate_number="").values_list("certificate_number", flat=True):
        numbers.append(certificate)

    for certificate in Discontinued_Student.objects.exclude(
        certificate_number__isnull=True
    ).exclude(certificate_number="").values_list("certificate_number", flat=True):
        numbers.append(certificate)

    latest_year = timezone.now().year
    latest_department = "AD"
    latest_sequence = 0

    pattern = re.compile(r"(\d{4})/([A-Za-z]+)/(\d+)")

    for number in numbers:
        match = pattern.match(number)
        if match:
            year = int(match.group(1))
            department = match.group(2)
            sequence = int(match.group(3))

            if sequence > latest_sequence:
                latest_sequence = sequence
                latest_year = year
                latest_department = department

    return f"{latest_year}/{latest_department}/{latest_sequence + 1:03d}"



def _fetch_personal_and_admission(aadhar=None, reg_no=None):
    """
    Helper: returns tuple (personal_obj or None, admission_record or None, academic_obj or None)
    Lookup order:
    1) by Aadhaar_Number
    2) fallback by registration_no (reg_no)
    """
    personal = None
    admission_record = None
    academic = None
    if aadhar:
        try:
            personal = PersonalDetails.objects.using("admissionform1").get(Aadhaar_Number=aadhar)
        except PersonalDetails.DoesNotExist:
            personal = None

    if not personal and reg_no:
        personal = (
            PersonalDetails.objects.using("admissionform1")
            .filter(registration_no=str(reg_no).strip())
            .first()
        )

    if personal:
        try:
            admission_record = AdmissionRecords.objects.using("admissionform1").filter(PersonalDetailsId=personal.id).first()
        except AdmissionRecords.DoesNotExist:
            admission_record = None
        if not admission_record and reg_no:
            admission_record = AdmissionRecords.objects.using("admissionform1").filter(admissionNo=str(reg_no).strip()).first()

    if admission_record:
        
        try:
            if hasattr(admission_record, "AcademicDetailsId_id") and admission_record.AcademicDetailsId_id:
                academic = AcademicDetails.objects.using("admissionform1").filter(id=admission_record.AcademicDetailsId_id).first()
        except AcademicDetails.DoesNotExist:
            academic = None

    return personal, admission_record, academic


def _format_date_safe(d):
	if not d:
		return "N/A"
	try:
		return d.strftime("%d.%m.%Y")
	except Exception:
		return str(d)

# def _number_to_words(n):
# 	ones = ["Zero","One","Two","Three","Four","Five","Six","Seven","Eight","Nine","Ten","Eleven","Twelve","Thirteen","Fourteen","Fifteen","Sixteen","Seventeen","Eighteen","Nineteen"]
# 	tens = ["","","Twenty","Thirty","Forty","Fifty","Sixty","Seventy","Eighty","Ninety"]
# 	if n < 20:
# 		return ones[n]
# 	if n < 100:
# 		return tens[n // 10] + ("" if n % 10 == 0 else f" {ones[n % 10]}")
# 	if n < 1000:
# 		return ones[n // 100] + " Hundred" + ("" if n % 100 == 0 else f" {_number_to_words(n % 100)}")
# 	if n < 10000:
# 		return _number_to_words(n // 1000) + " Thousand" + ("" if n % 1000 == 0 else f" {_number_to_words(n % 1000)}")
# 	return str(n)

def _number_to_words(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""

    ones = [
        "Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven",
        "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen",
        "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"
    ]

    tens = [
        "", "", "Twenty", "Thirty", "Forty", "Fifty",
        "Sixty", "Seventy", "Eighty", "Ninety"
    ]

    if n < 20:
        return ones[n]

    if n < 100:
        return tens[n // 10] + (
            "" if n % 10 == 0 else f" {ones[n % 10]}"
        )

    if n < 1000:
        return ones[n // 100] + " Hundred" + (
            "" if n % 100 == 0 else f" {_number_to_words(n % 100)}"
        )

    if n < 10000:
        return _number_to_words(n // 1000) + " Thousand" + (
            "" if n % 1000 == 0 else f" {_number_to_words(n % 1000)}"
        )

    return str(n)


def _date_to_words(value):
	if not value:
		return "N/A"
	if isinstance(value, str):
		for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
			try:
				value = datetime.strptime(value, fmt).date()
				break
			except Exception:
				continue
		else:
			return "N/A"
	if isinstance(value, datetime):
		value = value.date()
	if not hasattr(value, "day"):
		return "N/A"
	try:
		day_words = _number_to_words(int(value.day))
		month_words = calendar.month_name[int(value.month)]
		year_words = _number_to_words(int(value.year))
		return f"{day_words} {month_words} {year_words}"
	except Exception:
		return "N/A"

# def _tc_identity_texts(personal, passout_student):
#     community = getattr(personal, "community", "N/A") if personal else "N/A"
#     caste = getattr(personal, "caste", "N/A") if personal else "N/A"
#     nationality = getattr(personal, "nationality", "N/A") if personal else "N/A"
#     religion = getattr(personal, "religion", "N/A") if personal else "N/A"

#     is_2022_batch = False
#     try:
#         is_2022_batch = int(str(getattr(passout_student.student, "batch", "")).strip()) == 2022
#     except Exception:
#         is_2022_batch = False

#     if is_2022_batch:
#         if (not community or community == "N/A") and (not caste or caste == "N/A"):
#             community = "Refer Community Certificate"
#             caste = ""
#         if not nationality or nationality == "N/A":
#             nationality = "Indian"
#         # For 2022 fallback, always show nationality + "Refer Community Certificate"
#         religion = "Refer Community Certificate"

#     comm_parts = [v for v in (community, caste) if v and v != "N/A"]
#     comm_caste_text = " & ".join(comm_parts) if comm_parts else "N/A"

#     nat_parts = [v for v in (nationality, religion) if v and v != "N/A"]
#     nat_rel_text = " & ".join(nat_parts) if nat_parts else "N/A"
#     return comm_caste_text, nat_rel_text


def _tc_identity_texts(personal, passout_student):
    nationality = getattr(personal, "nationality", "N/A") if personal else "N/A"
    religion = getattr(personal, "religion", "N/A") if personal else "N/A"

    comm_caste_text = "Refer Community Certificate"

    nat_parts = [v for v in (nationality, religion) if v and v != "N/A"]
    nat_rel_text = " & ".join(nat_parts) if nat_parts else "N/A"

    return comm_caste_text, nat_rel_text

def _safe_text(value, fallback="N/A"):
    value = fallback if value is None else str(value).strip()
    return value or fallback


def _safe_filename_part(value, fallback="Certificate"):
    text = _safe_text(value, fallback=fallback)
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text or fallback


def _certificate_filename(owner_name, certificate_type):
    return f"{_safe_filename_part(owner_name, 'Student')} - {_safe_filename_part(certificate_type)}.pdf"


def _bulk_certificate_owner_name(selected_department):
    if selected_department and selected_department != "None":
        try:
            department = Add_Department.objects.filter(id=selected_department).first()
        except Exception:
            department = None
        if department:
            return _safe_text(getattr(department, "Department", None), fallback="Department")
    return "All Departments"


def _static_image_path(*parts):
    return os.path.join(settings.BASE_DIR, "static", *parts)


def _resolve_personal_and_academic(student):
    student_details = None
    try:
        student_details = StudentDetails.objects.get(reg_no=student.student.reg_no)
    except StudentDetails.DoesNotExist:
        student_details = None

    aadhar = getattr(student_details, "aadhar_number", None) if student_details else None
    personal, admission_record, academic = _fetch_personal_and_admission(
        aadhar=aadhar,
        reg_no=getattr(student.student, "reg_no", None),
    )
    return student_details, personal, admission_record, academic


def _get_program_branch_label(student, admission_record):
    department_name = _safe_text(getattr(admission_record, "Department", None))
    department_obj = None

    try:
        if getattr(student, "department_id", None):
            department_obj = Add_Department.objects.filter(id=student.department_id).select_related("degree").first()
        if not department_obj and department_name != "N/A":
            department_obj = (
                Add_Department.objects.select_related("degree")
                .filter(Department__iexact=department_name)
                .first()
            )
    except Exception:
        department_obj = None

    degree_department = _safe_text(getattr(department_obj, "degree_department_label", None))
    if degree_department != "N/A" and department_name != "N/A":
        if department_name.lower() not in degree_department.lower():
            return f"{degree_department} - {department_name}"
        return degree_department
    if degree_department != "N/A":
        return degree_department
    return department_name


# def _get_duration_of_study(student, department_obj):
#     year_of_admission = getattr(student.student, "year_of_admission", None)

#     degree_duration = None
#     try:
#         degree_duration = getattr(
#             getattr(department_obj, "degree", None),
#             "effective_duration",
#             None,
#         )
#         if degree_duration in (None, 0):
#             degree_duration = getattr(
#                 getattr(department_obj, "degree", None),
#                 "duration",
#                 None,
#             )
#     except Exception:
#         degree_duration = None

#     duration = int(str(degree_duration).strip()) if degree_duration else 4

#     try:
#         batch_year = int(str(student.student.batch).strip())
#         admission_year = int(str(year_of_admission).strip())

#         if admission_year > batch_year:
#             duration -= 1
#     except Exception:
#         pass

#     years_text = None
#     try:
#         years_text = f"{_number_to_words(duration)} Years"
#     except Exception:
#         years_text = None

#     batch_range = None
#     try:
#         if year_of_admission:
#             start_year = int(str(year_of_admission).strip())
#             batch_range = f"{start_year}-{start_year + duration}"
#     except Exception:
#         batch_range = None

#     parts = [part for part in (years_text, batch_range) if part]
#     return " ".join(parts) if parts else "N/A"





# def _get_duration_of_study(student, department_obj):
#     try:
#         current_year = int(student.student.year)

#         return (
#             f"{_number_to_words(current_year)} Year"
#             if current_year == 1
#             else f"{_number_to_words(current_year)} Years"
#         )

#     except Exception:
#         return "N/A"


def _get_duration_of_study(student, department_obj):
    try:
        current_year = int(student.student.year)
        admission_year = int(student.student.year_of_admission)

        duration = current_year - admission_year + 1

        if duration < 1:
            duration = 1

        return (
            f"{_number_to_words(duration)} Year"
            if duration == 1
            else f"{_number_to_words(duration)} Years"
        )

    except Exception:
        return "N/A"


def _build_transfer_certificate_data(student):
    student_details, personal, admission_record, academic = _resolve_personal_and_academic(student)

    father_name = _safe_text(
        getattr(personal, "father_name", None) or getattr(personal, "guardian_name", None)
    )
    roll_no_text = _safe_text(
        getattr(personal, "roll_no", None)
        or getattr(student_details, "reg_no", None)
        or getattr(getattr(student, "student", None), "reg_no", None)
    )
    dob_raw = getattr(personal, "date_of_birth", None) if personal else None
    dob = _format_date_safe(dob_raw) if dob_raw else "N/A"
    dob_words = _date_to_words(dob_raw)
    comm_caste_text, nat_rel = _tc_identity_texts(personal, student)
    gender = _safe_text(getattr(personal, "gender", None) or getattr(student_details, "gender", None))

    date_of_admission = _safe_text(
        _format_date_safe(getattr(academic, "DateAdmission", None)) if academic else None
    )
    if date_of_admission == "N/A" and admission_record and getattr(admission_record, "AcademicDetailsId_id", None):
        academic_fallback = AcademicDetails.objects.using("admissionform1").filter(id=admission_record.AcademicDetailsId_id).first()
        if academic_fallback:
            date_of_admission = _safe_text(_format_date_safe(getattr(academic_fallback, "DateAdmission", None)))

    department_obj = None
    try:
        if getattr(student, "department_id", None):
            department_obj = Add_Department.objects.select_related("degree").filter(id=student.department_id).first()
        if not department_obj:
            department_name = _safe_text(getattr(admission_record, "Department", None))
            if department_name != "N/A":
                department_obj = (
                    Add_Department.objects.select_related("degree")
                    .filter(Department__iexact=department_name)
                    .first()
                )
    except Exception:
        department_obj = None

    program_branch = _get_program_branch_label(student, admission_record)

    medium_of_instruction = _safe_text(
        getattr(student_details, "medium_of_study", None)
        or getattr(personal, "medium_of_study", None)
        or "ENGLISH"
    )

    roman_year = "N/A"
    roman_semester = "N/A"
    if student_details:
        year_raw = getattr(student_details, "year", None)
        semester_raw = getattr(student_details, "semester", None)
        try:
            roman_year = int_to_roman(int(year_raw)) if year_raw and str(year_raw).strip().isdigit() else _safe_text(year_raw)
        except Exception:
            roman_year = _safe_text(year_raw)
        try:
            roman_semester = int_to_roman(int(semester_raw)) if semester_raw and str(semester_raw).strip().isdigit() else _safe_text(semester_raw)
        except Exception:
            roman_semester = _safe_text(semester_raw)

    duration_of_study = _get_duration_of_study(student, department_obj)

    qualified = _safe_text(getattr(student, "qualified_higher_class", None))
    tc_request_date = _safe_text(_format_date_safe(getattr(student, "tc_requested_date", None)) if getattr(student, "tc_requested_date", None) else None)
    reason = _safe_text(getattr(student, "reason_for_discontinuation", None)) or _safe_text(getattr(student, "reason_for_tc", None))
    conduct = _safe_text(getattr(student, "conduct", None))
    last_date_saved = getattr(student, "last_date_of_attendance", None)
    umis_text = _safe_text(
        getattr(student_details, "umis_id", None)
        or getattr(personal, "EMIS_ID", None)
    )

    date_of_admission_default = _safe_text(date_of_admission)
    if last_date_saved:
        last_date_of_attendance = _format_date_safe(last_date_saved)
    else:
        last_date_of_attendance = "N/A"
        if student_details:
            latest_attendance = (
                Daily_Attendance.objects.filter(student=student_details)
                .exclude(date__isnull=True)
                .order_by("-date")
                .values_list("date", flat=True)
                .first()
            )
            if latest_attendance:
                last_date_of_attendance = _format_date_safe(latest_attendance)

    return {
        "student_details": student_details,
        "personal": personal,
        "admission_record": admission_record,
        "academic": academic,
        "father_name": father_name,
        "roll_no_text": roll_no_text,
        "dob": dob,
        "dob_words": dob_words,
        "comm_caste_text": comm_caste_text,
        "nat_rel": nat_rel,
        "gender": gender,
        "program_branch": program_branch,
        "date_of_admission": date_of_admission_default,
        "medium_of_instruction": medium_of_instruction,
        "duration_of_study": duration_of_study,
        "year_semester": f"{roman_year} Year / {roman_semester} Semester" if (roman_year != "N/A" or roman_semester != "N/A") else "N/A",
        "qualified": qualified,
        "last_date_of_attendance": last_date_of_attendance,
        "tc_request_date": tc_request_date,
        "reason": reason,
        "conduct": conduct,
        "umis_text": umis_text,
        "certificate_number": _safe_text(getattr(student, "certificate_number", None)),
        "student_name": _safe_text(getattr(getattr(student, "student", None), "name", None)),
        "reg_no": _safe_text(getattr(getattr(student, "student", None), "reg_no", None)),
        "batch": _safe_text(getattr(getattr(student, "student", None), "batch", None)),
    }


def _tc_markup(text):
    value = _safe_text(text)
    return escape(value).replace("\n", "<br/>")


def draw_tc_row(pdf, label, value, y_position):
    """
    Draw one TC row inside a fixed-height 3-column table slot.
    The slot heights are template-driven so the footer zone is never touched.
    """
    row_index = getattr(draw_tc_row, "_row_index", 0)
    slot_height = TC_ROW_SLOT_HEIGHTS[row_index] if row_index < len(TC_ROW_SLOT_HEIGHTS) else 14
    draw_tc_row._row_index = row_index + 1

    font_size = TC_BODY_FONT_SIZE
    row_height = slot_height
    label_container = value_para = colon_para = None

    while font_size >= TC_BODY_MIN_FONT_SIZE:
        leading = font_size + 2.5
        number_match = re.match(r"^(\d+\.\s*)", label)
        number_prefix = number_match.group(1) if number_match else ""
        label_body = label[len(number_prefix):].lstrip() if number_prefix else label
        fixed_number_width = pdf.stringWidth("17. ", TC_BODY_FONT, font_size) + 14 if number_prefix else 0
        number_width = fixed_number_width
        label_body_width = max(TC_LABEL_WIDTH - number_width, 1)

        number_style = ParagraphStyle(
            "tc_number_style",
            fontName=TC_BODY_FONT,
            fontSize=font_size,
            leading=leading,
            textColor=colors.black,
            alignment=0,
            spaceBefore=0,
            spaceAfter=0,
        )
        label_style = ParagraphStyle(
            "tc_label_style",
            fontName=TC_BODY_FONT,
            fontSize=font_size,
            leading=leading,
            textColor=colors.black,
            alignment=0,
            spaceBefore=0,
            spaceAfter=0,
        )
        value_style = ParagraphStyle(
            "tc_value_style",
            fontName=TC_BODY_FONT,
            fontSize=font_size,
            leading=leading,
            textColor=colors.black,
            alignment=0,
            spaceBefore=0,
            spaceAfter=0,
        )
        colon_style = ParagraphStyle(
            "tc_colon_style",
            fontName=TC_BODY_FONT,
            fontSize=font_size,
            leading=leading,
            textColor=colors.black,
            alignment=1,
            spaceBefore=0,
            spaceAfter=0,
        )

        number_para = Paragraph(escape(number_prefix), number_style)
        label_para = Paragraph(_tc_markup(label_body), label_style)
        label_container = Table(
            [[number_para, label_para]],
            colWidths=[number_width, label_body_width],
        )
        label_container.setStyle(
            TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        value_para = Paragraph(_tc_markup(value), value_style)
        colon_para = Paragraph(":", colon_style)
        _, label_height = label_container.wrap(TC_LABEL_WIDTH, 1000)
        _, value_height = value_para.wrap(TC_VALUE_WIDTH, 1000)
        _, colon_height = colon_para.wrap(TC_COLON_WIDTH, 1000)
        row_height = max(label_height, value_height, colon_height)
        if row_height <= slot_height:
            break
        font_size -= 0.4

    table = Table(
        [[label_container, colon_para, value_para]],
        colWidths=[TC_LABEL_WIDTH, TC_COLON_WIDTH, TC_VALUE_WIDTH],
        rowHeights=[slot_height],
    )
    table.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "CENTER"),
            ]
        )
    )
    table.wrapOn(pdf, TC_LABEL_WIDTH + TC_COLON_WIDTH + TC_VALUE_WIDTH, slot_height)
    table.drawOn(pdf, TC_TABLE_X, y_position - slot_height)

    return y_position - slot_height - TC_ROW_GAP


# Backward-compatible alias for any stale references.
draw_field = draw_tc_row


def _draw_watermark(pdf, width, height, text="RIT"):
    pdf.saveState()
    try:
        pdf.setFillColor(colors.Color(0.78, 0.63, 0.18))
        try:
            pdf.setFillAlpha(0.18)
        except Exception:
            pass
        pdf.translate(width / 2.0, height / 2.0)
        pdf.rotate(45)
        watermark_text = _safe_text(text)
        font_size = 154 if watermark_text.upper() == "RIT" else 88
        pdf.setFont("Times-Bold", font_size)
        pdf.drawCentredString(0, -font_size / 3.0, watermark_text)
    finally:
        pdf.restoreState()


def _draw_fit_image(pdf, image_path, x, y, width_limit, height_limit):
    if not image_path or not os.path.exists(image_path):
        return
    try:
        img = ImageReader(image_path)
        iw, ih = img.getSize()
        scale = min(width_limit / float(iw), height_limit / float(ih))
        draw_w = iw * scale
        draw_h = ih * scale
        draw_x = x + (width_limit - draw_w) / 2.0
        draw_y = y + (height_limit - draw_h) / 2.0
        pdf.drawImage(img, draw_x, draw_y, width=draw_w, height=draw_h, mask="auto")
    except Exception:
        pass


def _draw_certificate_footer_seal(pdf, width, footer_y, seal_size=82):
    # Center the seal between the HOD and Principal labels.
    seal_x = (width - seal_size) / 2.0
    seal_y = footer_y + 12
    _draw_fit_image(pdf, _static_image_path("images", "rit_seal1.png"), seal_x, seal_y, seal_size, seal_size)


def _draw_transfer_certificate_page(pdf, student, data, watermark_text="RIT"):
    
    width, height = A4
    transfer_shift = 18

    def ty(value):
        return value + transfer_shift

    outer_x = 28
    outer_y = 25
    outer_w = width - 56
    outer_h = height - 50
    inner_gap = 3
    inner_x = outer_x + inner_gap
    inner_y = outer_y + inner_gap
    inner_w = outer_w - 2 * inner_gap
    inner_h = outer_h - 2 * inner_gap

    border_color = colors.HexColor("#9B4E2C")
    title_bg = colors.HexColor("#243B55")
    header_blue = colors.HexColor("#1F3D4F")
    header_brown = colors.HexColor("#9B4E2C")

    pdf.saveState()
    _draw_watermark(pdf, width, height, watermark_text)
    pdf.restoreState()

    pdf.setStrokeColor(border_color)
    pdf.setLineWidth(1.2)
    pdf.rect(outer_x, outer_y, outer_w, outer_h, stroke=1, fill=0)
    pdf.setLineWidth(0.6)
    pdf.rect(inner_x, inner_y, inner_w, inner_h, stroke=1, fill=0)

    logo_y = height - 118
    _draw_fit_image(pdf, _static_image_path("images", "ritlogo.png"), 44, logo_y, 72, 72)
    pdf.setFillColor(header_blue)
    pdf.setFont("Times-Bold", 20)
    pdf.drawCentredString(width / 2.0 + 15, height - 70, "RAMCO INSTITUTE OF TECHNOLOGY")

    pdf.setFillColor(colors.HexColor("#B13A18"))
    pdf.setFont("Times-Roman", 10.5)
    pdf.drawCentredString(width / 2.0, height - 86, "(An Autonomous Institution)")
    pdf.setFillColor(colors.HexColor("#3A6E2B"))
    pdf.setFont("Times-Roman", 11)
    pdf.drawCentredString(
        width / 2.0,
        height - 102,
        "(Approved by AICTE - New Delhi and Affiliated to Anna University - Chennai)",
    )
    pdf.setFillColor(colors.HexColor("#3A6E2B"))
    pdf.setFont("Times-Roman", 10.5)
    pdf.drawCentredString(width / 2.0, height - 118, "Rajapalayam - 626117.")

    # Title
    title_w = 200
    title_x = (width - title_w) / 2.0
    title_y = ty(660)
    title_h = 28
    pdf.setFillColor(title_bg)
    pdf.setStrokeColor(title_bg)
    pdf.rect(title_x, title_y, title_w, title_h, stroke=1, fill=1)
    pdf.setFillColor(colors.white)
    pdf.setFont("Times-Bold", 16)
    pdf.drawCentredString(title_x + title_w / 2.0, title_y + 8.5, "Transfer Certificate")

    # Top boxes
    box_line_color = colors.HexColor("#6A7A63")
    pdf.setStrokeColor(box_line_color)
    pdf.setLineWidth(1)
    box_h = 25
    left_box_x = 36
    left_box_w = 150
    right_box_x = width - 36 - 180
    right_box_w = 180
    top_box_y = ty(638)
    second_box_y = ty(589)
    third_box_y = ty(589)
    

    for x, y, w, label, value in [
        (left_box_x, top_box_y, left_box_w, "TC No :", data["certificate_number"]),
        (left_box_x, second_box_y, left_box_w, "Roll No :", data["roll_no_text"]),
        (right_box_x, third_box_y, right_box_w, "Register No :", data["reg_no"]),
    ]:
        pdf.rect(x, y, w, box_h, stroke=1, fill=0)
        pdf.setFillColor(colors.black)
        pdf.setFont("Times-Roman", 13)

        value_text = _safe_text(value)

        # Default positions
        label_y = y + 13
        value_y = y + 13

        # Custom Y positions
        if label == "TC No :":
            label_y = y + 8
            value_y = y + 8

        elif label == "Roll No :":
            label_y = y + 8
            value_y = y + 8

        elif label == "Register No :":
            label_y = y + 9
            value_y = y + 9

        # Draw labels
        pdf.drawString(x + 10, label_y, label)

        # Draw values
        if label == "Register No :":
            pdf.drawString(x + 86, value_y, value_text)
        else:
            pdf.drawRightString(x + w - 10, value_y, value_text)

    # Body fields
    draw_tc_row._row_index = 0
    current_y = ty(DETAILS_START_Y)

    rows = [
        ("1.", "Name of the Student", data["student_name"]),
        ("2.", "Name of the Father / Guardian", data["father_name"]),
        ("3.", "Nationality & Religion", data["nat_rel"]),
        ("4.", "Community & Caste", data["comm_caste_text"]),
        ("5.", "Gender", data["gender"]),
        ("6.", "Date of Birth [DD/MM/YYYY]\n(in words)", f"{data['dob']}\n({data['dob_words']})" if data["dob_words"] != "N/A" else data["dob"]),
        ("7.", "Program and Branch in which student\nwas admitted", data["program_branch"]),
        ("8.", "Date of Admission", data["date_of_admission"]),
        ("9.", "Medium of Instruction", data["medium_of_instruction"]),
        ("10.", "Duration of Study", data["duration_of_study"]),
        ("11.", "Status of the candidate while leaving\nthe college (year / semester)", data["year_semester"]),
        ("12.", "Whether qualified for promotion to\nHigher Class", data["qualified"]),
        ("13.", "Last date of Attendance in the Institution", data["last_date_of_attendance"]),
        ("14.", "Date in which student requested for TC", data["tc_request_date"]),
        ("15.", "Reason for which TC was issued", data["reason"]),
        ("16.", "Character and Conduct", data["conduct"]),
        ("17.", "EMIS No / UMIS No", data["umis_text"]),
    ]

    for number, label, value in rows:
        current_y = draw_tc_row(pdf, f"{number} {label}", value, current_y)

    footer_y = ty(65)
    _draw_certificate_footer_seal(pdf, width, footer_y - 39, seal_size=76)
    pdf.setFont("Times-Roman", 13)
    # pdf.drawString(74, footer_y, f"Date : {data.get('certificate_date', '')}")
    from datetime import datetime

    certificate_date = data.get("certificate_date", "")

    try:
        certificate_date = datetime.strptime(
            certificate_date, "%B %d, %Y"
        ).strftime("%d.%m.%Y")
    except Exception:
        pass

    pdf.drawString(74, footer_y, f"Date : {certificate_date}")
    pdf.drawRightString(width - 84, footer_y, "Principal")





from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from course_management.models import PassOutStudents
from datetime import datetime

@csrf_exempt
def save_tc_details(request, student_id):
    """
    Save TC popup details to PassOutStudents model via AJAX.
    """
    if request.method == "POST":
        try:
            student = get_object_or_404(PassOutStudents, id=student_id)
            group_student_ids = list(
                PassOutStudents.objects.filter(
                    department=student.department,
                    student__batch=getattr(getattr(student, "student", None), "batch", None),
                ).values_list("id", flat=True)
            )

            # Extract and safely parse date
            tc_date_str = request.POST.get("tc_requested_date")
            tc_date = None
            if tc_date_str:
                try:
                    tc_date = datetime.strptime(tc_date_str, "%Y-%m-%d").date()
                except ValueError:
                    tc_date = None  # fallback if invalid format
            if not tc_date:
                tc_date = timezone.now().date()

            last_date_str = request.POST.get("last_date_of_attendance")
            last_date_of_attendance = None
            if last_date_str:
                try:
                    last_date_of_attendance = datetime.strptime(last_date_str, "%Y-%m-%d").date()
                except ValueError:
                    return JsonResponse({"status": "error", "message": "Invalid last date of attendance format"})
            if not last_date_of_attendance:
                return JsonResponse({"status": "error", "message": "Last date of attendance is required"})

            # Update only provided fields; keep existing values intact.
            qualified_higher_class = (request.POST.get("qualified_higher_class") or "").strip()
            reason_for_tc = (request.POST.get("reason_for_tc") or "").strip()
            conduct = (request.POST.get("conduct") or "").strip()

            PassOutStudents.objects.filter(id__in=group_student_ids).update(
                qualified_higher_class=qualified_higher_class or student.qualified_higher_class,
                tc_requested_date=tc_date,
                last_date_of_attendance=last_date_of_attendance,
                reason_for_tc=reason_for_tc or student.reason_for_tc,
                conduct=conduct or student.conduct,
            )
            return JsonResponse({"status": "success"})
        except Exception as e:
            # print("❌ Error saving TC details:", str(e))
            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "error", "message": "Invalid request"})

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime


@csrf_exempt
def save_discontinue_tc_details(request, student_id):
    """
    Save TC popup details to Discontinued_Student model via AJAX.
    """
    if request.method != "POST":
        messages.error(request, "Invalid request.")
        return JsonResponse({"status": "error"})

    try:
        student = get_object_or_404(Discontinued_Student, id=student_id)

        tc_date_str = request.POST.get("tc_requested_date")
        tc_requested_date = None

        if tc_date_str:
            try:
                tc_requested_date = datetime.strptime(tc_date_str, "%Y-%m-%d").date()
            except ValueError:
                messages.error(request, "Invalid TC requested date format.")
                return JsonResponse({"status": "error"})

        if not tc_requested_date:
            tc_requested_date = timezone.now().date()

        tc_issued = (request.POST.get("tc_issued") or "").strip()
        conduct = (request.POST.get("conduct") or "").strip()
        remarks = (request.POST.get("remarks") or "").strip()

        if tc_issued not in ["Yes", "No"]:
            messages.error(request, "Please select TC issued status.")
            return JsonResponse({"status": "error"})

        student.tc_requested_date = tc_requested_date
        student.tc_issued = tc_issued
        student.conduct = conduct or None
        student.remarks = remarks or None
        student.save(update_fields=[
            "tc_requested_date",
            "tc_issued",
            "conduct",
            "remarks",
            "updated_at",
        ])

        messages.success(request, "Discontinued student TC details saved successfully.")
        return JsonResponse({"status": "success"})

    except Exception as e:
        messages.error(request, f"Unable to save TC details. {str(e)}")
        return JsonResponse({"status": "error"})
    




def generate_transfer_certificate_pdf(request, student_id):
    """
    Generate a single Transfer Certificate PDF entirely from drawing commands.
    """
    student = get_object_or_404(PassOutStudents, id=student_id)

    date_entry = request.GET.get("date_entry")

    if date_entry:
        try:
            from datetime import datetime
            selected_date = datetime.strptime(
                date_entry, "%Y-%m-%d"
            ).strftime("%d/%m/%Y")
        except Exception:
            selected_date = date_entry
    else:
        selected_date = timezone.now().strftime("%d/%m/%Y")

    data = _build_transfer_certificate_data(student)

    # Override certificate date with selected date
    data["certificate_date"] = selected_date

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setTitle(
        f"Transfer Certificate - {student.student.name} ({student.student.reg_no})"
    )

    _draw_transfer_certificate_page(
        pdf,
        student,
        data,
        watermark_text="RIT"
    )

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'inline; filename="{_certificate_filename(student.student.name, "Office Transfer Certificate")}"'
    )

    return response


def generate_discontinue_transfer_certificate_pdf(request, student_id):
    """
    Generate discontinued student Transfer Certificate PDF.
    """
    student = get_object_or_404(Discontinued_Student, id=student_id)

    # Generate certificate number only once
    if not student.certificate_number or not student.certificate_number.strip():
        certificate_number = get_next_certificate_number()

        print("Generated:", certificate_number)

        student.certificate_number = certificate_number
        student.save()

        print(
            "Saved:",
            Discontinued_Student.objects.get(id=student.id).certificate_number
        )      # Reload the updated object

    date_entry = request.GET.get("date_entry")

    if date_entry:
        try:
            selected_date = datetime.strptime(date_entry, "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            selected_date = date_entry
    else:
        selected_date = timezone.now().strftime("%d/%m/%Y")

    data = _build_transfer_certificate_data(student)
    data["certificate_date"] = selected_date

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    student_name = student.student.name if student.student else "Student"
    student_reg = student.student.reg_no if student.student else ""

    pdf.setTitle(f"Discontinued Transfer Certificate - {student_name} ({student_reg})")

    _draw_transfer_certificate_page(
        pdf,
        student,
        data,
        watermark_text="RIT"
    )

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'inline; filename="{_certificate_filename(student_name, "Discontinued Transfer Certificate")}"'
    )

    return response



def generate_bulk_transfer_certificate(request):
    """
    Generate bulk transfer certificates entirely from drawing commands.
    Filters supported via GET params:
    - department
    - batch
    """
    selected_department = request.GET.get("department")
    selected_batch = request.GET.get("batch")
    date_entry = request.GET.get("date_entry")   # <-- ADD THIS

    if date_entry:
        try:
            from datetime import datetime
            selected_date = datetime.strptime(
                date_entry, "%Y-%m-%d"
            ).strftime("%d/%m/%Y")
        except Exception:
            selected_date = date_entry
    else:
        selected_date = timezone.now().strftime("%d/%m/%Y")

    students = PassOutStudents.objects.filter(
        department__in=_academic_departments_qs()
    ).order_by("student__reg_no")

    if selected_department and selected_department != "None":
        students = students.filter(department_id=selected_department)

    if selected_batch and selected_batch != "None":
        students = students.filter(student__batch=selected_batch)

    try:
        departments = Department.objects.using(
            "rit_approval_system"
        ).all().order_by("Department")
    except Exception:
        departments = []

    dept_map = {str(d.id): d.Department for d in departments}

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setTitle("Bulk Transfer Certificates")

    for student in students:
        student.dept_name = dept_map.get(str(student.department_id), "N/A")

        data = _build_transfer_certificate_data(student)

        # ADD THIS
        data["certificate_date"] = selected_date

        _draw_transfer_certificate_page(pdf, student, data)

        pdf.showPage()

    pdf.save()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response['Content-Disposition'] = (
        f'inline; filename="{_certificate_filename(_bulk_certificate_owner_name(selected_department), "Transfer Certificate")}"'
    )

    return response








def generate_transfer_certificate_office_pdf(request, student_id):
    student = get_object_or_404(PassOutStudents, id=student_id)

    date_entry = request.GET.get("date_entry")

    if date_entry:
        try:
            from datetime import datetime
            selected_date = datetime.strptime(
                date_entry, "%Y-%m-%d"
            ).strftime("%d/%m/%Y")
        except Exception:
            selected_date = date_entry
    else:
        selected_date = timezone.now().strftime("%d/%m/%Y")

    data = _build_transfer_certificate_data(student)

    # Override certificate date with selected date
    data["certificate_date"] = selected_date

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setTitle(
        f"Transfer Certificate - {student.student.name} ({student.student.reg_no})"
    )

    _draw_transfer_certificate_page(
        pdf,
        student,
        data,
        watermark_text="Office Copy"
    )

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'inline; filename="{_certificate_filename(student.student.name, "Office Transfer Certificate")}"'
    )

    return response






def generate_bulk_transfer_certificate_office(request):
    """
    Generate bulk transfer certificates (Office Copy)
    Filters:
    - department
    - batch
    """

    selected_department = request.GET.get("department")
    selected_batch = request.GET.get("batch")
    date_entry = request.GET.get("date_entry")

    if date_entry:
        try:
            from datetime import datetime
            selected_date = datetime.strptime(
                date_entry,
                "%Y-%m-%d"
            ).strftime("%d/%m/%Y")
        except Exception:
            selected_date = date_entry
    else:
        selected_date = timezone.now().strftime("%d/%m/%Y")

    students = PassOutStudents.objects.filter(
        department__in=_academic_departments_qs()
    ).order_by("student__reg_no")

    if selected_department and selected_department != "None":
        students = students.filter(
            department_id=selected_department
        )

    if selected_batch and selected_batch != "None":
        students = students.filter(
            student__batch=selected_batch
        )

    try:
        departments = Department.objects.using(
            "rit_approval_system"
        ).all().order_by("Department")
    except Exception:
        departments = []

    dept_map = {
        str(d.id): d.Department
        for d in departments
    }

    buffer = BytesIO()

    pdf = canvas.Canvas(
        buffer,
        pagesize=A4
    )

    pdf.setTitle(
        "Bulk Transfer Certificates - Office Copy"
    )

    for student in students:

        student.dept_name = dept_map.get(
            str(student.department_id),
            "N/A"
        )

        data = _build_transfer_certificate_data(
            student
        )

        # Override certificate date
        data["certificate_date"] = selected_date

        # OFFICE COPY WATERMARK
        _draw_transfer_certificate_page(
            pdf,
            student,
            data,
            watermark_text="Office Copy"
        )

        pdf.showPage()

    pdf.save()

    buffer.seek(0)

    response = HttpResponse(
        buffer,
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        f'inline; filename="{_certificate_filename(_bulk_certificate_owner_name(selected_department), "Office Transfer Certificate")}"'
    )

    return response




 
@check_permission("transfer_certificate_office")
def transfer_certificate_office(request):
   
    try:
        departments = _academic_departments_qs()

    except Exception:
        departments = []

    selected_department = request.GET.get("department")
    selected_batch = request.GET.get("batch")
    date_entry = request.GET.get("date_entry", timezone.now().date())

    batches = (
        PassOutStudents.objects.filter(department__in=departments)
        .values_list("student__batch", flat=True)
        .exclude(student__batch__isnull=True)
        .exclude(student__batch__exact="")
        .distinct()
        .order_by("-student__batch")
    )
    students = PassOutStudents.objects.filter(department__in=departments).order_by("student__reg_no")
    if selected_department and selected_department != "None":
        students = students.filter(department_id=selected_department)
    if selected_batch and selected_batch != "None":
        students = students.filter(student__batch=selected_batch)

  
    dept_map = {str(d.id): d.Department for d in departments}
    for i, student in enumerate(students, start=1):
        student.dept_name = dept_map.get(str(student.department_id), "N/A")
        student.sl_no = f"{student.certificate_number}"

    context = {
        "departments": departments,
        "batches": batches,
        "selected_department": selected_department,
        "selected_batch": selected_batch,
        "date_entry": date_entry,
        "students": students,
    }

    return render(request, "student_management/passout_students/transfer_certificate_office.html", context)




@check_permission("discontinue_transfer_certificate_office")
def discontinue_transfer_certificate_office(request):
    try:
        departments = _academic_departments_qs()
    except Exception:
        departments = []

    selected_department = request.GET.get("department")
    selected_batch = request.GET.get("batch")
    date_entry = request.GET.get("date_entry", timezone.now().date())

    batches = (
        Discontinued_Student.objects
        .filter(department__in=departments)
        .values_list("student__batch", flat=True)
        .exclude(student__batch__isnull=True)
        .exclude(student__batch__exact="")
        .distinct()
        .order_by("-student__batch")
    )

    students = (
        Discontinued_Student.objects
        .select_related("student", "department", "department__degree")
        .filter(department__in=departments)
        .order_by("student__reg_no")
    )

    if selected_department and selected_department != "None":
        students = students.filter(department_id=selected_department)

    if selected_batch and selected_batch != "None":
        students = students.filter(student__batch=selected_batch)

    dept_map = {str(d.id): d.Department for d in departments}

    for i, student in enumerate(students, start=1):
        student.dept_name = dept_map.get(str(student.department_id), "N/A")
        student.sl_no = i

    context = {
        "departments": departments,
        "batches": batches,
        "selected_department": selected_department,
        "selected_batch": selected_batch,
        "date_entry": date_entry,
        "students": students,
    }

    return render(
        request,
        "student_management/passout_students/discontinue_transfer_certificate_office.html",
        context
    )




def generate_discontinue_transfer_certificate_office_pdf(request, student_id):
    student = get_object_or_404(Discontinued_Student, id=student_id)

    date_entry = request.GET.get("date_entry")

    if date_entry:
        try:
            selected_date = datetime.strptime(date_entry, "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            selected_date = date_entry
    else:
        selected_date = timezone.now().strftime("%d/%m/%Y")

    data = _build_transfer_certificate_data(student)
    data["certificate_date"] = selected_date

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    student_name = student.student.name if student.student else "Student"
    student_reg = student.student.reg_no if student.student else ""

    pdf.setTitle(
        f"Discontinued Transfer Certificate - {student_name} ({student_reg})"
    )

    _draw_transfer_certificate_page(
        pdf,
        student,
        data,
        watermark_text="Office Copy"
    )

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'inline; filename="{_certificate_filename(student_name, "Discontinued Office Transfer Certificate")}"'
    )

    return response




def generate_bulk_discontinue_transfer_certificate_office(request):
    selected_department = request.GET.get("department")
    selected_batch = request.GET.get("batch")
    date_entry = request.GET.get("date_entry")

    if date_entry:
        try:
            selected_date = datetime.strptime(date_entry, "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            selected_date = date_entry
    else:
        selected_date = timezone.now().strftime("%d/%m/%Y")

    students = (
        Discontinued_Student.objects
        .select_related("student", "department", "department__degree")
        .filter(department__in=_academic_departments_qs())
        .order_by("student__reg_no")
    )

    if selected_department and selected_department != "None":
        students = students.filter(department_id=selected_department)

    if selected_batch and selected_batch != "None":
        students = students.filter(student__batch=selected_batch)

    try:
        departments = _academic_departments_qs()
    except Exception:
        departments = []

    dept_map = {
        str(d.id): d.Department
        for d in departments
    }

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    pdf.setTitle("Bulk Discontinued Transfer Certificates - Office Copy")

    for student in students:
        student.dept_name = dept_map.get(
            str(student.department_id),
            "N/A"
        )

        data = _build_transfer_certificate_data(student)
        data["certificate_date"] = selected_date

        _draw_transfer_certificate_page(
            pdf,
            student,
            data,
            watermark_text="Office Copy"
        )

        pdf.showPage()

    pdf.save()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'inline; filename="{_certificate_filename(_bulk_certificate_owner_name(selected_department), "Discontinued Office Transfer Certificate")}"'
    )

    return response


from django.shortcuts import render
from django.db.models import Count, Q
from django.http import JsonResponse
from django.utils import timezone
from django.db import connections
import json
from decimal import Decimal
from io import BytesIO
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Count
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)

from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Count
from django.db import connections
from django.utils import timezone
from django.core.exceptions import PermissionDenied
import json

# Assumed imports
# from .models import (
#     Faculty_Data_Permission, StudentDetails, Add_Department,
#     PersonalDetails, AdmissionRecords, Daily_Attendance
# )

from faculty_management.models import Faculty_Data_Permission, general_information as gi


@no_cache
@check_permission("student_analysis_dashboard")
def student_analysis_dashboard(request):
    # ---------------------------------------------------------
    # Filters
    # ---------------------------------------------------------
    department_id = (request.GET.get("department") or "").strip()
    batch = (request.GET.get("batch") or "").strip()
    year = (request.GET.get("year") or "").strip()
    semester = (request.GET.get("semester") or "").strip()
    section = (request.GET.get("section") or "").strip()
    gender = (request.GET.get("gender") or "").strip()
    regulation = (request.GET.get("regulation") or "").strip()

    # NEW: date range filters
    date_from = (request.GET.get("from") or "").strip()
    date_to = (request.GET.get("to") or "").strip()

    parsed_from = None
    parsed_to = None

    try:
        if date_from:
            parsed_from = datetime.strptime(date_from, "%Y-%m-%d").date()
        if date_to:
            parsed_to = datetime.strptime(date_to, "%Y-%m-%d").date()
    except ValueError:
        parsed_from = None
        parsed_to = None
        date_from = ""
        date_to = ""

    if parsed_from and parsed_to and parsed_from > parsed_to:
        parsed_from, parsed_to = parsed_to, parsed_from
        date_from = parsed_from.strftime("%Y-%m-%d")
        date_to = parsed_to.strftime("%Y-%m-%d")

    # ---------------------------------------------------------
    # Allowed Academic Departments Only
    # ---------------------------------------------------------
    allowed_departments = Add_Department.objects.filter(
        is_active=True,
        is_academic=True
    ).order_by("Department")

    # ---------------------------------------------------------
    # Base Query
    # ---------------------------------------------------------
    students = StudentDetails.objects.select_related(
        "department", "mentor", "ca"
    ).filter(
        department__in=allowed_departments
    )

    # ---------------------------------------------------------
    # Apply Filters
    # ---------------------------------------------------------
    if department_id and department_id.isdigit():
        if allowed_departments.filter(id=int(department_id)).exists():
            students = students.filter(department_id=int(department_id))
        else:
            department_id = ""

    if batch:
        students = students.filter(batch=batch)

    if year:
        students = students.filter(year=year)

    if semester:
        students = students.filter(semester=semester)

    if section:
        students = students.filter(section=section)

    if gender:
        students = students.filter(gender=gender)

    if regulation:
        students = students.filter(regulation=regulation)

    students_list = list(students)

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------
    def _safe_str(v):
        return (v or "").strip()

    def _gender_bucket(gvalue):
        g = _safe_str(gvalue).lower()
        if g in ("m", "male"):
            return "male"
        if g in ("f", "female"):
            return "female"
        if g in ("o", "other"):
            return "other"
        return ""

    def _classify_level(degree_str):
        text = _safe_str(degree_str).upper()
        if any(key in text for key in ["M.E", "M.TECH", "MBA", "MCA", "PG"]):
            return "PG"
        return "UG"

    # ---------------------------------------------------------
    # KPI Cards
    # ---------------------------------------------------------
    total_students = len(students_list)
    male_count = sum(1 for s in students_list if _gender_bucket(s.gender) == "male")
    female_count = sum(1 for s in students_list if _gender_bucket(s.gender) == "female")
    other_count = sum(1 for s in students_list if _gender_bucket(s.gender) == "other")

    male_percentage = (male_count / total_students * 100) if total_students > 0 else 0
    female_percentage = (female_count / total_students * 100) if total_students > 0 else 0
    other_percentage = (other_count / total_students * 100) if total_students > 0 else 0

    mentor_assigned = sum(1 for s in students_list if s.mentor_id is not None)
    ca_assigned = sum(1 for s in students_list if s.ca_id is not None)

    mentor_percentage = (mentor_assigned / total_students * 100) if total_students > 0 else 0
    ca_percentage = (ca_assigned / total_students * 100) if total_students > 0 else 0

    profile_uploaded = sum(
        1 for s in students_list
        if getattr(s, "profile_img", None) not in [None, ""]
    )
    email_count = sum(1 for s in students_list if _safe_str(s.email))
    mobile_count = sum(1 for s in students_list if _safe_str(s.mobile_no))
    aadhar_count = sum(1 for s in students_list if _safe_str(s.aadhar_number))

    full_profile_count = sum(
        1
        for s in students_list
        if _safe_str(s.name)
        and _safe_str(s.reg_no)
        and _safe_str(s.email)
        and _safe_str(s.mobile_no)
    )

    incomplete_profile_count = total_students - full_profile_count

    profile_completion = 0
    if total_students > 0:
        total_profile_fields = total_students * 4
        completed_fields = email_count + mobile_count + aadhar_count + profile_uploaded
        profile_completion = round((completed_fields / total_profile_fields) * 100, 2)

    # ---------------------------------------------------------
    # Department-wise Analytics
    # ---------------------------------------------------------
    dept_data = (
        students.values("department__Department")
        .annotate(count=Count("id"))
        .order_by("-count", "department__Department")
    )
    department_labels = [item["department__Department"] or "Unknown" for item in dept_data]
    department_counts = [item["count"] for item in dept_data]

    # ---------------------------------------------------------
    # Year-wise Analytics
    # ---------------------------------------------------------
    year_data = (
        students.values("year")
        .annotate(count=Count("id"))
        .order_by("year")
    )
    year_labels = [item["year"] or "Not Set" for item in year_data]
    year_counts = [item["count"] for item in year_data]

    # ---------------------------------------------------------
    # Semester-wise Analytics
    # ---------------------------------------------------------
    sem_data = (
        students.values("semester")
        .annotate(count=Count("id"))
        .order_by("semester")
    )
    semester_labels = [item["semester"] or "Not Set" for item in sem_data]
    semester_counts = [item["count"] for item in sem_data]

    # ---------------------------------------------------------
    # Batch-wise Analytics
    # ---------------------------------------------------------
    batch_data = (
        students.values("batch")
        .annotate(count=Count("id"))
        .order_by("batch")
    )
    batch_labels = [item["batch"] or "Not Set" for item in batch_data]
    batch_counts = [item["count"] for item in batch_data]

    # ---------------------------------------------------------
    # Section-wise Analytics
    # ---------------------------------------------------------
    section_data = (
        students.values("section")
        .annotate(count=Count("id"))
        .order_by("section")
    )
    section_labels = [item["section"] or "Not Set" for item in section_data]
    section_counts = [item["count"] for item in section_data]

    # ---------------------------------------------------------
    # Regulation-wise Analytics
    # ---------------------------------------------------------
    regulation_data = (
        students.values("regulation")
        .annotate(count=Count("id"))
        .order_by("regulation")
    )
    regulation_labels = [item["regulation"] or "Not Set" for item in regulation_data]
    regulation_counts = [item["count"] for item in regulation_data]

    # ---------------------------------------------------------
    # Gender Analytics
    # ---------------------------------------------------------
    gender_labels = ["Male", "Female", "Other"]
    gender_counts = [male_count, female_count, other_count]

    # ---------------------------------------------------------
    # UG / PG, Quota, State, Hostel / Day Scholar
    # ---------------------------------------------------------
    ug_stats = {
        "total": 0,
        "male": 0,
        "female": 0,
        "gq": 0,
        "mq": 0,
        "other_state": 0,
        "hostel": 0,
        "day_scholar": 0,
    }
    pg_stats = {
        "total": 0,
        "male": 0,
        "female": 0,
        "gq": 0,
        "mq": 0,
        "other_state": 0,
        "hostel": 0,
        "day_scholar": 0,
    }

    aadhaars = [s.aadhar_number for s in students_list if _safe_str(s.aadhar_number)]
    personal_details_map = {}
    pid_to_quota = {}
    pid_to_state = {}
    pid_to_mode = {}
    pid_to_degree = {}

    if aadhaars:
        try:
            with connections["admissionform1"].cursor():
                p_qs = (
                    PersonalDetails.objects.using("admissionform1")
                    .filter(Aadhaar_Number__in=aadhaars)
                    .values("Aadhaar_Number", "id", "Permanent_Address_State")
                )
                for row in p_qs:
                    pid = row["id"]
                    aadhaar = row["Aadhaar_Number"]
                    personal_details_map[aadhaar] = pid
                    pid_to_state[pid] = _safe_str(row.get("Permanent_Address_State")).upper()

                pid_list = list(personal_details_map.values())
                if pid_list:
                    ar_rows = (
                        AdmissionRecords.objects.using("admissionform1")
                        .filter(PersonalDetailsId_id__in=pid_list)
                        .values("PersonalDetailsId_id", "Quota", "Mode", "degree")
                    )
                    for r in ar_rows:
                        pid = r["PersonalDetailsId_id"]
                        pid_to_quota[pid] = _safe_str(r.get("Quota")).upper()
                        pid_to_mode[pid] = _safe_str(r.get("Mode")).lower()
                        pid_to_degree[pid] = _safe_str(r.get("degree")).upper()
        except Exception:
            pass

    tamil_states = {"TAMIL NADU", "TAMILNADU"}
    overall_tn = 0
    overall_other_state = 0

    for s in students_list:
        aadhaar = _safe_str(s.aadhar_number)
        pid = personal_details_map.get(aadhaar)
        degree_raw = pid_to_degree.get(pid, "")
        level = _classify_level(degree_raw)
        bucket = ug_stats if level == "UG" else pg_stats

        bucket["total"] += 1

        g = _safe_str(s.gender).lower()
        if g.startswith("m"):
            bucket["male"] += 1
        elif g.startswith("f"):
            bucket["female"] += 1

        quota = _safe_str(pid_to_quota.get(pid, "")).upper()
        if quota.startswith("GQ"):
            bucket["gq"] += 1
        elif quota.startswith("MQ"):
            bucket["mq"] += 1

        state = _safe_str(pid_to_state.get(pid, "")).upper()
        if state:
            if state in tamil_states:
                overall_tn += 1
            else:
                overall_other_state += 1
                bucket["other_state"] += 1

        mode_text = _safe_str(pid_to_mode.get(pid, "")).lower()
        is_hostel = any(k in mode_text for k in ["hostel", "residential"])
        if is_hostel:
            bucket["hostel"] += 1
        else:
            bucket["day_scholar"] += 1

    # ---------------------------------------------------------
    # Attendance Snapshot for Selected Date Range
    # ---------------------------------------------------------
    today = timezone.localdate()
    range_from = parsed_from or today
    range_to = parsed_to or today

    attendance_snapshot_qs = Daily_Attendance.objects.filter(
        student__in=students,
        date__gte=range_from,
        date__lte=range_to,
        full_day_status="Absent",
    ).select_related("student", "student__department")

    today_total_absent = attendance_snapshot_qs.count()

    today_absent_male = attendance_snapshot_qs.filter(
        student__gender__in=["Male", "male", "M", "m"]
    ).count()

    today_absent_female = attendance_snapshot_qs.filter(
        student__gender__in=["Female", "female", "F", "f"]
    ).count()

    total_possible_absent_base = total_students
    if parsed_from or parsed_to:
        total_days_in_range = (range_to - range_from).days + 1
        total_possible_absent_base = total_students * total_days_in_range if total_students > 0 else 0

    today_absent_percentage = (
        (today_total_absent / total_possible_absent_base) * 100
        if total_possible_absent_base > 0 else 0
    )
    today_absent_male_percentage = (
        (today_absent_male / today_total_absent) * 100
        if today_total_absent > 0 else 0
    )
    today_absent_female_percentage = (
        (today_absent_female / today_total_absent) * 100
        if today_total_absent > 0 else 0
    )

    absent_dept_data = (
        attendance_snapshot_qs.values("student__department__Department")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    today_absent_department_labels = [
        item["student__department__Department"] or "Unknown"
        for item in absent_dept_data
    ]
    today_absent_department_counts = [item["count"] for item in absent_dept_data]

    # ---------------------------------------------------------
    # Mentor-wise Student Load
    # ---------------------------------------------------------
    mentor_data = (
        students.values("mentor__name")
        .annotate(count=Count("id"))
        .order_by("-count", "mentor__name")[:10]
    )
    mentor_labels = [item["mentor__name"] or "Not Assigned" for item in mentor_data]
    mentor_counts = [item["count"] for item in mentor_data]

    # ---------------------------------------------------------
    # CA-wise Student Load
    # ---------------------------------------------------------
    ca_data = (
        students.values("ca__name")
        .annotate(count=Count("id"))
        .order_by("-count", "ca__name")[:10]
    )
    ca_labels = [item["ca__name"] or "Not Assigned" for item in ca_data]
    ca_counts = [item["count"] for item in ca_data]

    # ---------------------------------------------------------
    # Quota Distribution
    # ---------------------------------------------------------
    total_gq = ug_stats["gq"] + pg_stats["gq"]
    total_mq = ug_stats["mq"] + pg_stats["mq"]
    total_other_quota = total_students - (total_gq + total_mq)

    quota_labels = ["GQ", "MQ", "Others"]
    quota_counts = [total_gq, total_mq, total_other_quota]

    # ---------------------------------------------------------
    # State Distribution
    # ---------------------------------------------------------
    state_labels = ["Tamil Nadu", "Other States"]
    state_counts = [overall_tn, overall_other_state]

    # ---------------------------------------------------------
    # All Students Table (AJAX)
    # ---------------------------------------------------------
    all_students = students.order_by("department__Department", "year", "semester", "name")

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest" or request.GET.get("ajax") == "1"
    if is_ajax:
        try:
            page = int(request.GET.get("page", 1))
        except (TypeError, ValueError):
            page = 1

        page = max(page, 1)
        page_size = 50
        start = (page - 1) * page_size
        end = start + page_size

        students_for_table = list(all_students[start:end])
        total_count = all_students.count()
        total_pages = (total_count + page_size - 1) // page_size if total_count else 1

        data = []
        for s in students_for_table:
            data.append({
                "name": _safe_str(s.name) or "N/A",
                "email": _safe_str(s.email),
                "reg_no": _safe_str(s.reg_no),
                "department": _safe_str(getattr(getattr(s, "department", None), "Department", "")),
                "regulation": _safe_str(s.regulation),
                "batch": _safe_str(s.batch),
                "year": _safe_str(s.year),
                "semester": _safe_str(s.semester),
                "section": _safe_str(s.section),
                "gender": _safe_str(s.gender),
                "mobile_no": _safe_str(s.mobile_no),
                "mentor_name": _safe_str(getattr(getattr(s, "mentor", None), "name", "")),
                "ca_name": _safe_str(getattr(getattr(s, "ca", None), "name", "")),
                "profile_img_url": s.profile_img.url if getattr(s, "profile_img", None) and hasattr(s.profile_img, "url") else "",
            })

        return JsonResponse({
            "students": data,
            "page": page,
            "total_pages": total_pages,
            "total_count": total_count
        })

    # ---------------------------------------------------------
    # Filter Dropdown Data
    # ---------------------------------------------------------
    departments = allowed_departments

    batch_options = (
        students.exclude(batch__isnull=True)
        .exclude(batch="")
        .values_list("batch", flat=True)
        .distinct()
        .order_by("batch")
    )

    year_options = (
        students.exclude(year__isnull=True)
        .exclude(year="")
        .values_list("year", flat=True)
        .distinct()
        .order_by("year")
    )

    semester_options = (
        students.exclude(semester__isnull=True)
        .exclude(semester="")
        .values_list("semester", flat=True)
        .distinct()
        .order_by("semester")
    )

    section_options = (
        students.exclude(section__isnull=True)
        .exclude(section="")
        .values_list("section", flat=True)
        .distinct()
        .order_by("section")
    )

    regulation_options = (
        students.exclude(regulation__isnull=True)
        .exclude(regulation="")
        .values_list("regulation", flat=True)
        .distinct()
        .order_by("regulation")
    )

    selected_department_name = ""
    if department_id and department_id.isdigit():
        selected_department_obj = departments.filter(id=int(department_id)).first()
        if selected_department_obj:
            selected_department_name = selected_department_obj.Department

    context = {
        "current_date": timezone.now(),

        "total_students": total_students,
        "male_count": male_count,
        "female_count": female_count,
        "other_count": other_count,
        "male_percentage": male_percentage,
        "female_percentage": female_percentage,
        "other_percentage": other_percentage,

        "mentor_assigned": mentor_assigned,
        "ca_assigned": ca_assigned,
        "mentor_percentage": mentor_percentage,
        "ca_percentage": ca_percentage,

        "profile_uploaded": profile_uploaded,
        "email_count": email_count,
        "mobile_count": mobile_count,
        "aadhar_count": aadhar_count,
        "full_profile_count": full_profile_count,
        "incomplete_profile_count": incomplete_profile_count,
        "profile_completion": profile_completion,

        "ug_total": ug_stats["total"],
        "ug_male": ug_stats["male"],
        "ug_female": ug_stats["female"],
        "ug_gq": ug_stats["gq"],
        "ug_mq": ug_stats["mq"],
        "ug_other_state": ug_stats["other_state"],
        "ug_hostel": ug_stats["hostel"],
        "ug_day_scholar": ug_stats["day_scholar"],

        "pg_total": pg_stats["total"],
        "pg_male": pg_stats["male"],
        "pg_female": pg_stats["female"],
        "pg_gq": pg_stats["gq"],
        "pg_mq": pg_stats["mq"],
        "pg_other_state": pg_stats["other_state"],
        "pg_hostel": pg_stats["hostel"],
        "pg_day_scholar": pg_stats["day_scholar"],

        "today_total_absent": today_total_absent,
        "today_absent_male": today_absent_male,
        "today_absent_female": today_absent_female,
        "today_absent_percentage": today_absent_percentage,
        "today_absent_male_percentage": today_absent_male_percentage,
        "today_absent_female_percentage": today_absent_female_percentage,
        "today_absent_department_labels": json.dumps(today_absent_department_labels),
        "today_absent_department_counts": json.dumps(today_absent_department_counts),

        "ug_pg_labels": json.dumps(["UG", "PG"]),
        "ug_pg_counts": json.dumps([ug_stats["total"], pg_stats["total"]]),
        "hostel_labels": json.dumps(["Hostel", "Day Scholar"]),
        "hostel_counts": json.dumps(
            [ug_stats["hostel"] + pg_stats["hostel"], ug_stats["day_scholar"] + pg_stats["day_scholar"]]
        ),
        "quota_labels": json.dumps(quota_labels),
        "quota_counts": json.dumps(quota_counts),
        "state_labels": json.dumps(state_labels),
        "state_counts": json.dumps(state_counts),

        "department_labels": json.dumps(department_labels),
        "department_counts": json.dumps(department_counts),

        "year_labels": json.dumps(year_labels),
        "year_counts": json.dumps(year_counts),

        "semester_labels": json.dumps(semester_labels),
        "semester_counts": json.dumps(semester_counts),

        "batch_labels": json.dumps(batch_labels),
        "batch_counts": json.dumps(batch_counts),

        "section_labels": json.dumps(section_labels),
        "section_counts": json.dumps(section_counts),

        "regulation_labels": json.dumps(regulation_labels),
        "regulation_counts": json.dumps(regulation_counts),

        "gender_labels": json.dumps(gender_labels),
        "gender_counts": json.dumps(gender_counts),

        "mentor_labels": json.dumps(mentor_labels),
        "mentor_counts": json.dumps(mentor_counts),
        "ca_labels": json.dumps(ca_labels),
        "ca_counts": json.dumps(ca_counts),

        "departments": departments,
        "batch_options": batch_options,
        "year_options": year_options,
        "semester_options": semester_options,
        "section_options": section_options,
        "regulation_options": regulation_options,

        "selected_department": department_id or "",
        "selected_department_name": selected_department_name,
        "selected_batch": batch or "",
        "selected_year": year or "",
        "selected_semester": semester or "",
        "selected_section": section or "",
        "selected_gender": gender or "",
        "selected_regulation": regulation or "",

        "selected_from_date": date_from or "",
        "selected_to_date": date_to or "",
    }

    return render(request, "student_management/student_analysis_dashboard.html", context)


import io
import os
from datetime import datetime
from collections import defaultdict
from io import BytesIO

from django.http import HttpResponse
from django.conf import settings
from django.contrib.staticfiles import finders
from django.db.models import Count
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4  # Changed from landscape to A4 (portrait)
from reportlab.lib.units import mm, inch
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Table, TableStyle, Paragraph, Spacer, PageBreak
)



def _safe(v):
    """Safe string conversion"""
    return "" if v is None else str(v).strip()


import io
import os
from datetime import datetime, timedelta
from collections import defaultdict
from io import BytesIO

from django.http import HttpResponse
from django.conf import settings
from django.contrib.staticfiles import finders
from django.db.models import Count, Q
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Table, TableStyle, Paragraph, Spacer, PageBreak, KeepTogether, CondPageBreak
)


def _safe(v):
    """Safely convert value to string"""
    return "" if v is None else str(v).strip()


def student_analysis_dashboard_pdf(request):
    """
    Generate PDF report showing ONLY students who were absent
    during the selected date range, grouped by department
    """
    today = timezone.localdate()
    
    # ---------------------------------------------------------
    # Get filters from request
    # ---------------------------------------------------------
    department_id = (request.GET.get("department") or "").strip()
    batch = (request.GET.get("batch") or "").strip()
    year = (request.GET.get("year") or "").strip()
    semester = (request.GET.get("semester") or "").strip()
    section = (request.GET.get("section") or "").strip()
    gender = (request.GET.get("gender") or "").strip()
    regulation = (request.GET.get("regulation") or "").strip()
    
    # Date range filters
    date_from = (request.GET.get("from") or "").strip()
    date_to = (request.GET.get("to") or "").strip()
    
    # Parse dates
    parsed_from = None
    parsed_to = None
    
    try:
        if date_from:
            parsed_from = datetime.strptime(date_from, "%Y-%m-%d").date()
        if date_to:
            parsed_to = datetime.strptime(date_to, "%Y-%m-%d").date()
    except ValueError:
        return HttpResponse("Invalid date format. Use YYYY-MM-DD.", status=400)
    
    if parsed_from and parsed_to and parsed_from > parsed_to:
        return HttpResponse("'From Date' cannot be greater than 'To Date'.", status=400)
    
    # Default to last 30 days if no date range specified
    if not parsed_from and not parsed_to:
        parsed_to = today
        parsed_from = today - timedelta(days=30)
    
    report_from = parsed_from
    report_to = parsed_to
    
    # ---------------------------------------------------------
    # Import models
    # ---------------------------------------------------------
    from user_accounts.models import StudentDetails, Add_Department
    from student_management.models import Daily_Attendance
    
    # ---------------------------------------------------------
    # Student filters
    # ---------------------------------------------------------
    students = StudentDetails.objects.select_related(
        "department", "mentor", "ca"
    ).all()
    
    if department_id and department_id.isdigit():
        students = students.filter(department_id=int(department_id))
    
    if batch:
        students = students.filter(batch=batch)
    
    if year:
        students = students.filter(year=year)
    
    if semester:
        students = students.filter(semester=semester)
    
    if section:
        students = students.filter(section=section)
    
    if gender:
        students = students.filter(gender=gender)
    
    if regulation:
        students = students.filter(regulation=regulation)
    
    # ---------------------------------------------------------
    # Get attendance data and identify absent students
    # ---------------------------------------------------------
    attendance_qs = Daily_Attendance.objects.filter(
        student__in=students,
        date__gte=report_from,
        date__lte=report_to,
    ).select_related("student", "student__department", "student__mentor", "student__ca", "faculty")
    
    # Calculate total days in range
    total_days = attendance_qs.values("date").distinct().count()
    
    # Student-wise attendance aggregation
    attendance_agg = (
        attendance_qs.values("student_id")
        .annotate(
            present_count=Count(
                "id",
                filter=Q(full_day_status="Present")
            ),
            absent_count=Count(
                "id",
                filter=Q(full_day_status="Absent")
            ),
            on_duty_count=Count(
                "id",
                filter=Q(full_day_status="On Duty")
            ),
            half_day_count=Count(
                "id",
                filter=Q(full_day_status="Half Day")
            ),
        )
    )
    
    # Filter ONLY students who have at least one absence
    absent_students_data = {}
    absent_students_set = set()
    
    for row in attendance_agg:
        student_id = row["student_id"]
        absent = int(row.get("absent_count") or 0)
        
        if absent > 0:  # Only include students with absences
            absent_students_set.add(student_id)
            absent_students_data[student_id] = {
                "present": int(row.get("present_count") or 0),
                "absent": absent,
                "on_duty": int(row.get("on_duty_count") or 0),
                "half_day": int(row.get("half_day_count") or 0),
            }
    
    # Get full student details for absent students
    absent_students = students.filter(id__in=absent_students_set).select_related("department")
    absent_students_list = list(absent_students)
    total_absent_students = len(absent_students_list)
    
    if total_absent_students == 0:
        return HttpResponse("No absent students found for the selected filters and date range.", status=404)
    
    # ---------------------------------------------------------
    # Group absent students by department
    # ---------------------------------------------------------
    department_absent_students = defaultdict(list)
    
    for s in absent_students_list:
        dept_name = _safe(getattr(getattr(s, "department", None), "Department", "")) or "Unknown Department"
        department_absent_students[dept_name].append(s)
    
    # Sort departments alphabetically
    sorted_departments = sorted(department_absent_students.items(), key=lambda x: x[0])
    
    # ---------------------------------------------------------
    # Calculate overall statistics (only for absent students)
    # ---------------------------------------------------------
    total_present = 0
    total_absent = 0
    total_on_duty = 0
    total_half_day = 0
    low_attendance_count = 0
    
    for s in absent_students_list:
        row = absent_students_data.get(s.id, {})
        present = row.get("present", 0)
        absent = row.get("absent", 0)
        on_duty = row.get("on_duty", 0)
        half_day = row.get("half_day", 0)
        
        total_present += present
        total_absent += absent
        total_on_duty += on_duty
        total_half_day += half_day
        
        attended = present + on_duty + (half_day * 0.5)
        attendance_percentage = (attended / total_days * 100) if total_days > 0 else 0
        
        if attendance_percentage < 75 and total_days > 0:
            low_attendance_count += 1
    
    total_possible = total_absent_students * total_days if total_days > 0 else 0
    overall_attended = total_present + total_on_duty + (total_half_day * 0.5)
    overall_attendance_percentage = round((overall_attended / total_possible) * 100, 2) if total_possible else 0
    
    low_attendance_percentage = round((low_attendance_count / total_absent_students) * 100, 2) if total_absent_students else 0
    
    # ---------------------------------------------------------
    # PDF Setup
    # ---------------------------------------------------------
    buffer = BytesIO()
    PAGE_SIZE = landscape(A4)
    
    doc = BaseDocTemplate(
        buffer,
        pagesize=PAGE_SIZE,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=20 * mm,
        bottomMargin=15 * mm,
        title="Student Absentees Report",
        showBoundary=0
    )
    
    # Color definitions
    PRIMARY_BLUE = colors.HexColor("#0f2f57")
    SECONDARY_BLUE = colors.HexColor("#1a4b8c")
    ACCENT_RED = colors.HexColor("#b91c1c")
    SUCCESS_GREEN = colors.HexColor("#10b981")
    WARNING_ORANGE = colors.HexColor("#f59e0b")
    DARK_GRAY = colors.HexColor("#111827")
    MEDIUM_GRAY = colors.HexColor("#4b5563")
    LIGHT_GRAY = colors.HexColor("#9ca3af")
    BG_GRAY = colors.HexColor("#f9fafb")
    BORDER_GRAY = colors.HexColor("#e5e7eb")
    
    # Styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        "title_style",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=PRIMARY_BLUE,
        alignment=TA_CENTER,
        spaceAfter=6,
        spaceBefore=0,
        fontName="Helvetica-Bold",
    )
    
    sub_title_style = ParagraphStyle(
        "sub_title_style",
        parent=styles["Normal"],
        fontSize=11,
        textColor=MEDIUM_GRAY,
        alignment=TA_CENTER,
        spaceAfter=10,
        fontName="Helvetica",
    )
    
    section_style = ParagraphStyle(
        "section_style",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=PRIMARY_BLUE,
        alignment=TA_LEFT,
        spaceBefore=12,
        spaceAfter=6,
        fontName="Helvetica-Bold",
    )
    
    dept_section_style = ParagraphStyle(
        "dept_section_style",
        parent=styles["Heading3"],
        fontSize=12,
        textColor=SECONDARY_BLUE,
        alignment=TA_LEFT,
        spaceBefore=8,
        spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    
    info_style = ParagraphStyle(
        "info_style",
        parent=styles["Normal"],
        fontSize=9,
        textColor=DARK_GRAY,
        alignment=TA_LEFT,
        leading=12,
        fontName="Helvetica",
    )
    
    table_header_style = ParagraphStyle(
        "table_header",
        parent=styles["Normal"],
        fontSize=8.5,
        textColor=colors.white,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        leading=11,
    )
    
    cell_left_style = ParagraphStyle(
        "cell_left",
        parent=styles["Normal"],
        fontSize=8,
        textColor=DARK_GRAY,
        alignment=TA_LEFT,
        leading=10,
    )
    
    cell_center_style = ParagraphStyle(
        "cell_center",
        parent=styles["Normal"],
        fontSize=8,
        textColor=DARK_GRAY,
        alignment=TA_CENTER,
        leading=10,
    )
    
    cell_right_style = ParagraphStyle(
        "cell_right",
        parent=styles["Normal"],
        fontSize=8,
        textColor=DARK_GRAY,
        alignment=TA_RIGHT,
        leading=10,
    )
    
    small_note_style = ParagraphStyle(
        "small_note",
        parent=styles["Normal"],
        fontSize=7.5,
        textColor=MEDIUM_GRAY,
        alignment=TA_LEFT,
        leading=9,
    )
    
    def p_left(txt):
        return Paragraph(_safe(txt), cell_left_style)
    
    def p_center(txt):
        return Paragraph(_safe(txt), cell_center_style)
    
    def p_right(txt):
        return Paragraph(_safe(txt), cell_right_style)
    
    def create_table(data, col_widths, header_bg=SECONDARY_BLUE, zebra=True):
        """Helper function to create styled tables"""
        t = Table(data, colWidths=col_widths, repeatRows=1)
        ts = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), header_bg),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8.5),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER_GRAY),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
        if zebra and len(data) > 2:
            ts.add("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_GRAY])
        t.setStyle(ts)
        return t
    
    # ---------------------------------------------------------
    # Header/Footer
    # ---------------------------------------------------------
    HEADER_HEIGHT = 32 * mm
    
    def draw_header_footer(canvas_obj, doc_obj):
        canvas_obj.saveState()
        page_w, page_h = PAGE_SIZE
        left = doc_obj.leftMargin
        right = page_w - doc_obj.rightMargin
        center_x = (left + right) / 2
        top_y = page_h - 5 * mm
        
        # Logo
        logo_rel = "images/ritlogo.png"
        logo_path = finders.find(logo_rel)
        if not logo_path:
            static_root = getattr(settings, "STATIC_ROOT", "")
            if static_root:
                cand = os.path.join(static_root, logo_rel)
                if os.path.exists(cand):
                    logo_path = cand
        
        if logo_path and os.path.exists(logo_path):
            try:
                canvas_obj.drawImage(
                    ImageReader(logo_path),
                    left, top_y - 16 * mm,
                    width=22 * mm, height=13 * mm,
                    preserveAspectRatio=True, mask="auto"
                )
            except:
                pass
        
        # Institute name and details
        canvas_obj.setFillColor(PRIMARY_BLUE)
        canvas_obj.setFont("Helvetica-Bold", 14)
        canvas_obj.drawCentredString(center_x, top_y - 5 * mm, "RAMCO INSTITUTE OF TECHNOLOGY")
        
        canvas_obj.setFillColor(ACCENT_RED)
        canvas_obj.setFont("Helvetica-Bold", 9)
        canvas_obj.drawCentredString(center_x, top_y - 10 * mm, "An Autonomous Institution")
        
        canvas_obj.setFillColor(MEDIUM_GRAY)
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.drawCentredString(center_x, top_y - 14.5 * mm, "Approved by AICTE, New Delhi")
        canvas_obj.setFont("Helvetica", 7.5)
        canvas_obj.drawCentredString(center_x, top_y - 18 * mm, "Accredited by NAAC & ISO 9001:2015 Certified")
        
        # Footer
        footer_y = 12 * mm
        canvas_obj.setStrokeColor(BORDER_GRAY)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(left, footer_y + 4 * mm, right, footer_y + 4 * mm)
        
        canvas_obj.setFillColor(LIGHT_GRAY)
        canvas_obj.setFont("Helvetica", 7)
        gen_time = datetime.now().strftime("%d %b %Y, %I:%M %p")
        canvas_obj.drawString(left, footer_y, f"Generated: {gen_time}")
        canvas_obj.drawCentredString(
            center_x,
            footer_y,
            f"Period: {report_from.strftime('%d-%m-%Y')} to {report_to.strftime('%d-%m-%Y')}"
        )
        canvas_obj.drawRightString(right, footer_y, f"Page {doc_obj.page}")
        
        canvas_obj.restoreState()
    
    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin + 3 * mm,
        doc.width,
        doc.height - HEADER_HEIGHT + 3 * mm,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
        id="normal"
    )
    doc.addPageTemplates([PageTemplate(id="All", frames=[frame], onPage=draw_header_footer)])
    
    # ---------------------------------------------------------
    # Build Content
    # ---------------------------------------------------------
    elements = []
    
    # Title and Header Section
    elements.append(Spacer(1, 2 * mm))
    elements.append(Paragraph("STUDENT ABSENTEES REPORT", title_style))
    elements.append(Paragraph("Students with at least one absence during the selected period", sub_title_style))
    elements.append(Spacer(1, 3 * mm))
    
    # Filter information
    dept_display = "All Departments"
    if department_id and department_id.isdigit():
        dept_obj = Add_Department.objects.filter(id=int(department_id)).first()
        if dept_obj:
            dept_display = dept_obj.Department
    
    filter_data = [
        [
            Paragraph("<b>Department:</b>", info_style), 
            Paragraph(dept_display, info_style),
            Paragraph("<b>Batch:</b>", info_style), 
            Paragraph(batch or "All", info_style),
        ],
        [
            Paragraph("<b>Year:</b>", info_style), 
            Paragraph(year or "All", info_style),
            Paragraph("<b>Semester:</b>", info_style), 
            Paragraph(semester or "All", info_style),
        ],
        [
            Paragraph("<b>Section:</b>", info_style), 
            Paragraph(section or "All", info_style),
            Paragraph("<b>Gender:</b>", info_style), 
            Paragraph(gender or "All", info_style),
        ],
        [
            Paragraph("<b>Regulation:</b>", info_style), 
            Paragraph(regulation or "All", info_style),
            Paragraph("<b>Total Absent Students:</b>", info_style), 
            Paragraph(str(total_absent_students), info_style),
        ],
    ]
    
    if total_days > 0:
        filter_data.append([
            Paragraph("<b>Total Days:</b>", info_style), 
            Paragraph(str(total_days), info_style),
            Paragraph("<b>Date Range:</b>", info_style), 
            Paragraph(f"{report_from.strftime('%d-%m-%Y')} to {report_to.strftime('%d-%m-%Y')}", info_style),
        ])
    
    filter_table = Table(filter_data, colWidths=[35 * mm, 65 * mm, 35 * mm, 65 * mm])
    filter_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.3, BORDER_GRAY),
        ("BACKGROUND", (0, 0), (-1, -1), BG_GRAY),
    ]))
    elements.append(filter_table)
    elements.append(Spacer(1, 6 * mm))
    
    # ---------------------------------------------------------
    # Overall Statistics for Absent Students
    # ---------------------------------------------------------
    elements.append(Paragraph("ABSENT STUDENTS STATISTICS", section_style))
    
    if total_days > 0:
        stats_data = [
            [
                Paragraph("<b>Total Absent Students:</b>", info_style), 
                Paragraph(str(total_absent_students), info_style),
                Paragraph("<b>Total Days:</b>", info_style), 
                Paragraph(str(total_days), info_style),
                Paragraph("<b>Total Absent Records:</b>", info_style), 
                Paragraph(str(total_absent), info_style),
            ],
            [
                Paragraph("<b>Total Present:</b>", info_style), 
                Paragraph(str(total_present), info_style),
                Paragraph("<b>Total On Duty:</b>", info_style), 
                Paragraph(str(total_on_duty), info_style),
                Paragraph("<b>Total Half Days:</b>", info_style), 
                Paragraph(str(total_half_day), info_style),
            ],
            [
                Paragraph("<b>Overall Attendance:</b>", info_style), 
                Paragraph(f"{overall_attendance_percentage}%", info_style),
                Paragraph("<b>Low Attendance (&lt;75%):</b>", info_style), 
                Paragraph(f"{low_attendance_count} ({low_attendance_percentage}%)", info_style),
                Paragraph("<b>Avg Absent/Student:</b>", info_style), 
                Paragraph(f"{total_absent / total_absent_students:.1f}" if total_absent_students > 0 else "0", info_style),
            ],
        ]
        
        stats_table = Table(stats_data, colWidths=[35 * mm, 30 * mm, 35 * mm, 30 * mm, 35 * mm, 30 * mm])
        stats_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BG_GRAY),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_GRAY),
            ("GRID", (0, 0), (-1, -1), 0.3, BORDER_GRAY),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        elements.append(stats_table)
        elements.append(Spacer(1, 6 * mm))
    
    # ---------------------------------------------------------
    # Department-wise Absent Students Summary
    # ---------------------------------------------------------
    elements.append(Paragraph("DEPARTMENT-WISE ABSENT STUDENTS SUMMARY", section_style))
    
    dept_summary_header = [
        Paragraph("S.No", table_header_style),
        Paragraph("Department", table_header_style),
        Paragraph("Absent Students", table_header_style),
        Paragraph("Total Present", table_header_style),
        Paragraph("Total Absent", table_header_style),
        Paragraph("Total OD", table_header_style),
        Paragraph("Total Half Day", table_header_style),
        Paragraph("Attendance %", table_header_style),
    ]
    
    dept_summary_data = [dept_summary_header]
    
    for idx, (dept_name, dept_students) in enumerate(sorted_departments, start=1):
        dept_total = len(dept_students)
        dept_present = 0
        dept_absent = 0
        dept_od = 0
        dept_half = 0
        
        for stu in dept_students:
            row = absent_students_data.get(stu.id, {})
            dept_present += row.get("present", 0)
            dept_absent += row.get("absent", 0)
            dept_od += row.get("on_duty", 0)
            dept_half += row.get("half_day", 0)
        
        dept_attended = dept_present + dept_od + (dept_half * 0.5)
        dept_possible = dept_total * total_days if total_days > 0 else 0
        dept_percentage = round((dept_attended / dept_possible) * 100, 2) if dept_possible > 0 else 0
        
        dept_summary_data.append([
            p_center(str(idx)),
            p_left(dept_name),
            p_center(str(dept_total)),
            p_center(str(dept_present)),
            p_center(str(dept_absent)),
            p_center(str(dept_od)),
            p_center(str(dept_half)),
            p_center(f"{dept_percentage:.2f}%"),
        ])
    
    dept_summary_table = create_table(
        dept_summary_data,
        col_widths=[12 * mm, 50 * mm, 22 * mm, 20 * mm, 20 * mm, 18 * mm, 20 * mm, 22 * mm],
        header_bg=PRIMARY_BLUE,
        zebra=True
    )
    elements.append(dept_summary_table)
    elements.append(Spacer(1, 3 * mm))
    
    # ---------------------------------------------------------
    # DETAILED LIST OF ABSENT STUDENTS - GROUPED BY DEPARTMENT
    # ---------------------------------------------------------
    elements.append(PageBreak())
    elements.append(Paragraph("DETAILED LIST OF ABSENT STUDENTS", section_style))
    elements.append(Paragraph("Grouped by Department (Alphabetical Order)", sub_title_style))
    elements.append(Spacer(1, 3 * mm))
    
    # Define common column widths for student tables
    student_col_widths = [
        10 * mm,   # S.No
        25 * mm,   # Reg No
        40 * mm,   # Student Name
        12 * mm,   # Year
        12 * mm,   # Sem
        12 * mm,   # Sec
        20 * mm,   # Dept
        15 * mm,   # Present
        12 * mm,   # OD
        15 * mm,   # Half Day
        15 * mm,   # Absent
        15 * mm,   # Total Days
        18 * mm,   # Attendance %
        15 * mm,   # Status
    ]
    
    total_depts = len(sorted_departments)
    
    # Process each department in order
    for dept_index, (dept_name, dept_students) in enumerate(sorted_departments, start=1):
        # Create a container for the entire department section
        dept_elements = []
        
        # Department header
        dept_header = Paragraph(
            f"{dept_index}. {dept_name.upper()} - Absent Students: {len(dept_students)}",
            dept_section_style
        )
        dept_elements.append(dept_header)
        dept_elements.append(Spacer(1, 2 * mm))
        
        # Sort students within department by registration number
        dept_students_sorted = sorted(
            dept_students,
            key=lambda x: (_safe(getattr(x, "reg_no", "")), _safe(getattr(x, "name", "")))
        )
        
        # Calculate department summary
        dept_total_students = len(dept_students_sorted)
        dept_present = 0
        dept_absent = 0
        dept_on_duty = 0
        dept_half_day = 0
        
        # Create student table for this department
        student_header = [
            Paragraph("S.No", table_header_style),
            Paragraph("Reg No", table_header_style),
            Paragraph("Student Name", table_header_style),
            Paragraph("Year", table_header_style),
            Paragraph("Sem", table_header_style),
            Paragraph("Sec", table_header_style),
            Paragraph("Dept", table_header_style),
            Paragraph("Present", table_header_style),
            Paragraph("OD", table_header_style),
            Paragraph("Half Day", table_header_style),
            Paragraph("Absent", table_header_style),
            Paragraph("Days", table_header_style),
            Paragraph("Att %", table_header_style),
            Paragraph("Status", table_header_style),
        ]
        
        student_data = [student_header]
        
        for idx, student in enumerate(dept_students_sorted, start=1):
            row = absent_students_data.get(student.id, {})
            present = row.get("present", 0)
            absent = row.get("absent", 0)
            on_duty = row.get("on_duty", 0)
            half_day = row.get("half_day", 0)
            
            dept_present += present
            dept_absent += absent
            dept_on_duty += on_duty
            dept_half_day += half_day
            
            attended = present + on_duty + (half_day * 0.5)
            percentage = round((attended / total_days) * 100, 2) if total_days > 0 else 0
            
            # Determine status based on attendance percentage
            if percentage >= 75:
                status = "Good"
                status_color = SUCCESS_GREEN
            elif percentage >= 50:
                status = "Moderate"
                status_color = WARNING_ORANGE
            else:
                status = "Critical"
                status_color = ACCENT_RED
            
            status_style = ParagraphStyle(
                "status_style",
                parent=cell_center_style,
                textColor=status_color,
                alignment=TA_CENTER
            )
            
            student_data.append([
                p_center(str(idx)),
                p_center(_safe(student.reg_no)),
                p_left(_safe(student.name)),
                p_center(_safe(student.year)),
                p_center(_safe(student.semester)),
                p_center(_safe(student.section)),
                p_left(dept_name[:15]),
                p_center(str(present)),
                p_center(str(on_duty)),
                p_center(str(half_day)),
                p_center(str(absent)),
                p_center(str(total_days)),
                p_center(f"{percentage:.2f}%"),
                Paragraph(status, status_style),
            ])
        
        # Add department summary info table
        dept_attended = dept_present + dept_on_duty + (dept_half_day * 0.5)
        dept_possible = dept_total_students * total_days if total_days > 0 else 0
        dept_percentage = round((dept_attended / dept_possible) * 100, 2) if dept_possible > 0 else 0
        
        dept_info_data = [
            [
                Paragraph("<b>Department Summary:</b>", info_style),
                Paragraph(f"Total Students: {dept_total_students}", info_style),
                Paragraph(f"Total Present: {dept_present}", info_style),
                Paragraph(f"Total Absent: {dept_absent}", info_style),
            ],
            [
                Paragraph("", info_style),
                Paragraph(f"Total On Duty: {dept_on_duty}", info_style),
                Paragraph(f"Total Half Days: {dept_half_day}", info_style),
                Paragraph(f"Attendance: {dept_percentage}%", info_style),
            ],
        ]
        
        dept_info_table = Table(dept_info_data, colWidths=[35 * mm, 40 * mm, 35 * mm, 40 * mm])
        dept_info_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BG_GRAY),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_GRAY),
            ("GRID", (0, 0), (-1, -1), 0.25, BORDER_GRAY),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        dept_elements.append(dept_info_table)
        dept_elements.append(Spacer(1, 4 * mm))
        
        # Add the student table for this department
        student_table = create_table(
            student_data,
            col_widths=student_col_widths,
            header_bg=SECONDARY_BLUE,
            zebra=True
        )
        dept_elements.append(student_table)
        dept_elements.append(Spacer(1, 6 * mm))
        
        # Add department elements to main elements with KeepTogether
        # This helps keep department content together, but allows page breaks between departments
        if dept_index < total_depts:
            # For all but the last department, wrap in KeepTogether to try to keep department together
            elements.append(KeepTogether(dept_elements))
            # Add a page break between departments for better organization
            elements.append(PageBreak())
        else:
            # For the last department, just add the elements without a following page break
            elements.extend(dept_elements)
    
    # ---------------------------------------------------------
    # Detailed Daily Absence Records (Optional)
    # ---------------------------------------------------------
    if request.GET.get("show_daily_details") == "yes" and total_days <= 31:
        elements.append(PageBreak())
        elements.append(Paragraph("DAILY ABSENCE DETAILS", section_style))
        elements.append(Paragraph("Showing only days when students were absent", sub_title_style))
        elements.append(Spacer(1, 3 * mm))
        
        for dept_name, dept_students in sorted_departments:
            # Add department header for daily details
            daily_dept_elements = []
            daily_dept_elements.append(Paragraph(f"{dept_name}", dept_section_style))
            daily_dept_elements.append(Spacer(1, 2 * mm))
            
            for student in dept_students[:10]:  # Limit to 10 per department to avoid too many pages
                student_name = _safe(student.name)
                reg_no = _safe(student.reg_no)
                
                daily_dept_elements.append(Paragraph(f"<b>{student_name}</b> ({reg_no})", info_style))
                daily_dept_elements.append(Spacer(1, 2 * mm))
                
                # Get only absent records for this student
                absent_records = attendance_qs.filter(
                    student=student,
                    full_day_status="Absent"
                ).order_by("date")
                
                if absent_records.exists():
                    daily_header = [
                        Paragraph("Date", table_header_style),
                        Paragraph("Morning", table_header_style),
                        Paragraph("Afternoon", table_header_style),
                        Paragraph("Remarks", table_header_style),
                    ]
                    
                    daily_data = [daily_header]
                    
                    for att in absent_records:
                        daily_data.append([
                            p_center(att.date.strftime("%d-%m-%Y")),
                            p_center(_safe(att.morning_status or "-")),
                            p_center(_safe(att.afternoon_status or "-")),
                            p_left(_safe(att.remarks or "-")),
                        ])
                    
                    daily_table = create_table(
                        daily_data,
                        col_widths=[30 * mm, 35 * mm, 35 * mm, 90 * mm],
                        header_bg=ACCENT_RED,
                        zebra=True
                    )
                    daily_dept_elements.append(daily_table)
                    daily_dept_elements.append(Spacer(1, 5 * mm))
                else:
                    daily_dept_elements.append(Paragraph("No absence records found.", info_style))
                    daily_dept_elements.append(Spacer(1, 3 * mm))
            
            # Add department daily details with page break between departments
            elements.extend(daily_dept_elements)
            elements.append(PageBreak())
    
    # Add notes section
    elements.append(Spacer(1, 8 * mm))
    elements.append(Paragraph("NOTES:", section_style))
    notes = [
        "• This report shows ONLY students who had at least one absence during the selected period",
        "• Students are grouped by department in alphabetical order for easier department-wise analysis",
        "• Attendance percentage is calculated as: (Present + On Duty + Half Day × 0.5) / Total Days × 100",
        "• Half Day attendance is counted as 0.5 days",
        "• 'Good' status: ≥75% attendance, 'Moderate': 50-75%, 'Critical': <50%",
        "• Total Absent Students count represents unique students with at least one absence",
    ]
    for note in notes:
        elements.append(Paragraph(note, small_note_style))
    
    # ---------------------------------------------------------
    # Build PDF
    # ---------------------------------------------------------
    try:
        doc.build(elements)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return HttpResponse(f"PDF generation failed: {e}", status=500)
    
    pdf = buffer.getvalue()
    buffer.close()
    
    # Generate filename
    file_suffix = f"{report_from.strftime('%Y_%m_%d')}_to_{report_to.strftime('%Y_%m_%d')}"
    filename = f"student_absentees_{file_suffix}.pdf"
    
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    response.write(pdf)
    return response



