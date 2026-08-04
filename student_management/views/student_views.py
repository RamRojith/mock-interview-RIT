from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from user_accounts.decorators import check_permission, no_cache, is_super_user
from user_accounts.models import Role
# from course_management.models import LeaveApprovers
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Case, When, IntegerField
from course_management.models import Course, CourseEnrollment
from django.contrib import messages
from student_management.models import StudentDetails
from user_accounts.models import Add_Department
from course_management.models import Course, CourseEnrollment
from examination_management.models import Result, Regular_Course_Grade_Master
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from datetime import datetime

@check_permission("Student_Semester_Mark_Dashboard")
def Student_Semester_Mark_Dashboard(request):
    student = get_object_or_404(StudentDetails, reg_no=request.user.Employee_id)
    degree = student.department.degree
    total_semesters = degree.duration * 2

    results = Result.objects.filter(student=student)

    semester_data = []
    cum_grade_total = 0.0
    cum_credit = 0.0

    for sem in range(1, total_semesters + 1):
        sem_results = results.filter(semester=sem)

        enriched_results = []
        sem_grade_total = 0.0
        sem_credit = 0.0

        for result in sem_results:
            grade_points = None
            if result.grade:
                try:
                    grade_master = Regular_Course_Grade_Master.objects.get(
                        letter_grade=result.grade.strip().upper(),
                    )
                    grade_points = grade_master.grade_points
                except Regular_Course_Grade_Master.DoesNotExist:
                    grade_points = None

            try:
                credit_val = float(result.credit) if result.credit else 0.0
            except ValueError:
                credit_val = 0.0

            grade_total_val = result.grade_total if result.grade_total is not None else 0.0

            enriched_results.append({
                'course': result.course,
                'credit': result.credit,
                'grade': result.grade,
                'grade_total': result.grade_total,
                'grade_points': grade_points,
            })

            sem_credit += credit_val
            sem_grade_total += grade_total_val

        # Semester GPA
        gpa = sem_grade_total / sem_credit if sem_credit > 0 else None

        # Cumulative up to this semester
        cum_credit += sem_credit
        cum_grade_total += sem_grade_total
        cum_gpa = cum_grade_total / cum_credit if cum_credit > 0 else None

        semester_data.append({
            'number': sem,
            'results': enriched_results,
            'gpa': gpa,
            'cum_gpa': cum_gpa,          # ← new: CGPA up to this sem
            'cum_credit': cum_credit,    # optional – can show total credits too
        })

    # Overall final CGPA (after all semesters)
    overall_cgpa = cum_gpa if cum_credit > 0 else None

    return render(request, 'student_management/student/Student_Semester_Mark_Dashboard.html', {
        'student': student,
        'degree': degree,
        'semester_data': semester_data,
        'current_semester': student.semester,
        'overall_cgpa': overall_cgpa,
    })



import os
from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib.staticfiles import finders
from django.conf import settings

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.utils import ImageReader

# Models (keep your actual imports)
# from student_management.models import StudentDetails, Result
# from examination_management.models import Regular_Course_Grade_Master


# ======================================================================================
# ✅ Helpers
# ======================================================================================
def safe_str(value):
    """Safely convert any value to a clean string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def safe_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


# ======================================================================================
# ✅ Perfectly aligned Header/Footer (RIT branded)
# ======================================================================================
def _marksheet_header_footer(canvas, doc, meta=None):
    """
    Strongly aligned header & footer.
    - Uses exact left/right boundaries based on doc margins.
    - Avoids overlapping by reserving enough top margin.
    """
    c = canvas
    c.saveState()
    page_w, page_h = A4

    meta = meta or {}
    subtitle = meta.get("subtitle", "SEMESTER GRADE CARD")
    watermark_text = meta.get("watermark_text", "RIT • CONFIDENTIAL")
    show_watermark = meta.get("show_watermark", True)

    LEFT = doc.leftMargin
    RIGHT = page_w - doc.rightMargin
    CENTER = (LEFT + RIGHT) / 2

    # Colors
    PRIMARY = colors.HexColor("#0F2F57")
    SECONDARY = colors.HexColor("#1A4B8C")
    ACCENT = colors.HexColor("#B91C1C")
    MUTED = colors.HexColor("#6B7280")
    BORDER = colors.HexColor("#E5E7EB")

    # Watermark
    if show_watermark:
        try:
            c.saveState()
            c.setFillColor(colors.Color(0.75, 0.75, 0.75, alpha=0.14))
            c.setFont("Helvetica-Bold", 58)
            c.translate(page_w / 2, page_h / 2)
            c.rotate(30)
            c.drawCentredString(0, 0, watermark_text)
            c.restoreState()
        except Exception:
            pass

    # Logo resolve
    logo_rel = "images/ritlogo.png"
    logo_path = finders.find(logo_rel)

    if not logo_path:
        static_root = getattr(settings, "STATIC_ROOT", None)
        if static_root:
            cand = os.path.join(static_root, logo_rel)
            if os.path.exists(cand):
                logo_path = cand

        if not logo_path and getattr(settings, "STATICFILES_DIRS", None):
            for d in settings.STATICFILES_DIRS:
                cand = os.path.join(d, logo_rel)
                if os.path.exists(cand):
                    logo_path = cand
                    break

    # Header geometry (all absolute)
    header_top = page_h - 9 * mm
    logo_box_h = 22 * mm

    # Draw logo (left aligned)
    if logo_path and os.path.exists(logo_path):
        try:
            img = ImageReader(logo_path)
            iw, ih = img.getSize()
            logo_h = logo_box_h
            logo_w = logo_h * (iw / ih)
            c.drawImage(
                img,
                LEFT,
                header_top - logo_h,
                width=logo_w,
                height=logo_h,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            pass

    # Institution text (center aligned)
    c.setFillColor(PRIMARY)
    c.setFont("Helvetica-Bold", 14.5)
    c.drawCentredString(CENTER, header_top - 6.5 * mm, "RAMCO INSTITUTE OF TECHNOLOGY")

    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 9.6)
    c.drawCentredString(CENTER, header_top - 13.5 * mm, "An Autonomous Institution")

    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8.5)
    c.drawCentredString(CENTER, header_top - 18.7 * mm, "Rajapalayam - 626 117 | Tamil Nadu")
    c.setFont("Helvetica", 8.2)
    c.drawCentredString(CENTER, header_top - 23.3 * mm, "Approved by AICTE • Affiliated to Anna University • NAAC Accredited")

    # Subtitle pill (center, consistent)
    pill_w = 92 * mm
    pill_h = 8.5 * mm
    pill_x = CENTER - pill_w / 2
    pill_y = header_top - 34.5 * mm

    c.setFillColor(colors.HexColor("#EEF2FF"))
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setLineWidth(0.9)
    c.roundRect(pill_x, pill_y, pill_w, pill_h, 4.5, fill=1, stroke=1)

    c.setFillColor(SECONDARY)
    c.setFont("Helvetica-Bold", 9.4)
    c.drawCentredString(CENTER, pill_y + 2.6 * mm, subtitle)

    # Bottom header line aligned exactly to margins
    # header_bottom = page_h - 41.5 * mm
    # c.setStrokeColor(PRIMARY)
    # c.setLineWidth(1.15)
    # c.line(LEFT, header_bottom, RIGHT, header_bottom)

    # Footer
    footer_line_y = 21 * mm
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.85)
    c.line(LEFT, footer_line_y, RIGHT, footer_line_y)

    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8)
    c.drawString(LEFT, 14 * mm, "Computer Generated Document • No Signature Required")
    c.drawRightString(RIGHT, 14 * mm, f"Page {doc.page}")

    c.restoreState()


# ======================================================================================
# ✅ Properly aligned Marksheet PDF
# ======================================================================================
def semester_grade_pdf(request, semester_number):
    student = get_object_or_404(StudentDetails, reg_no=request.user.Employee_id)
    degree = student.department.degree

    results = Result.objects.filter(student=student, semester=semester_number).select_related("course")
    cumulative_results = Result.objects.filter(student=student, semester__lte=semester_number).select_related("course")

    styles = getSampleStyleSheet()

    # Palette
    PRIMARY = colors.HexColor("#0F2F57")
    MUTED = colors.HexColor("#6B7280")
    BORDER = colors.HexColor("#E5E7EB")
    BG = colors.HexColor("#F8FAFC")
    WHITE = colors.white
    DANGER = colors.HexColor("#B91C1C")
    SUCCESS = colors.HexColor("#166534")

    # Title styles
    title_style = ParagraphStyle(
        "Title", parent=styles["Normal"], fontSize=13.5, textColor=PRIMARY,
        alignment=TA_CENTER, spaceAfter=2, fontName="Helvetica-Bold"
    )
    sub_style = ParagraphStyle(
        "Sub", parent=styles["Normal"], fontSize=9.4, textColor=MUTED,
        alignment=TA_CENTER, spaceAfter=10
    )

    # Info styles
    info_k = ParagraphStyle(
        "InfoK", parent=styles["Normal"], fontSize=9.0, textColor=MUTED,
        alignment=TA_LEFT, fontName="Helvetica-Bold", leading=12
    )
    info_v = ParagraphStyle(
        "InfoV", parent=styles["Normal"], fontSize=9.0, textColor=colors.HexColor("#111827"),
        alignment=TA_LEFT, leading=12
    )

    # Table styles
    th = ParagraphStyle(
        "TH", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=9.2,
        leading=11, alignment=TA_CENTER, textColor=WHITE, wordWrap="CJK"
    )
    td_c = ParagraphStyle(
        "TDC", parent=styles["Normal"], fontName="Helvetica", fontSize=8.9,
        leading=11, alignment=TA_CENTER, textColor=colors.HexColor("#111827"), wordWrap="CJK"
    )
    td_l = ParagraphStyle(
        "TDL", parent=styles["Normal"], fontName="Helvetica", fontSize=8.9,
        leading=11, alignment=TA_LEFT, textColor=colors.HexColor("#111827"), wordWrap="CJK"
    )

    note_style = ParagraphStyle(
        "Note", parent=styles["Normal"], fontSize=8.1, textColor=MUTED,
        alignment=TA_CENTER, leading=10
    )

    # ---------- Build rows + GPA ----------
    enriched_rows = []
    sem_credit = 0.0
    sem_grade_total = 0.0
    any_fail = False

    for idx, result in enumerate(results, start=1):
        grade_points = None
        if result.grade:
            try:
                gm = Regular_Course_Grade_Master.objects.get(letter_grade=result.grade.strip().upper())
                grade_points = gm.grade_points
            except Regular_Course_Grade_Master.DoesNotExist:
                grade_points = None

        credit_val = safe_float(result.credit, 0.0)
        grade_total_val = safe_float(result.grade_total, 0.0)

        course_code = safe_str(getattr(result.course, "course_code", "—")) or "—"
        course_title = safe_str(getattr(result.course, "title", "Not specified")) or "Not specified"

        grade = safe_str(result.grade) or "—"
        if grade.strip().upper() in ("F", "FA", "FE"):
            any_fail = True

        enriched_rows.append([
            Paragraph(str(idx), td_c),
            Paragraph(course_code, td_c),
            Paragraph(course_title, td_l),
            Paragraph(f"{result.credit}" if result.credit is not None else "—", td_c),
            Paragraph(grade, td_c),
            Paragraph(f"{grade_points}" if grade_points is not None else "—", td_c),
            Paragraph(f"{int(grade_total_val)}" if grade_total_val else "—", td_c),
        ])

        sem_credit += credit_val
        sem_grade_total += grade_total_val

    sgpa_val = round(sem_grade_total / sem_credit, 2) if sem_credit > 0 else None

    # ---------- CGPA ----------
    cum_credit = 0.0
    cum_grade_total = 0.0
    for r in cumulative_results:
        cum_credit += safe_float(r.credit, 0.0)
        cum_grade_total += safe_float(r.grade_total, 0.0)

    cgpa_val = round(cum_grade_total / cum_credit, 2) if cum_credit > 0 else None

    # ---------- Remarks ----------
    if not enriched_rows:
        remark = "No marks/grades have been published for this semester yet."
        remark_color = DANGER
    elif any_fail:
        remark = "Remarks: REAPPEAR / ARREAR PRESENT (One or more courses show F/FA/FE)."
        remark_color = DANGER
    else:
        remark = "Remarks: PASS"
        remark_color = SUCCESS

    remark_style = ParagraphStyle(
        "Remark", parent=styles["Normal"], fontSize=9.4,
        textColor=remark_color, alignment=TA_CENTER,
        fontName="Helvetica-Bold", spaceBefore=5, spaceAfter=10
    )

    # ---------- Response ----------
    response = HttpResponse(content_type="application/pdf")
    filename = f"Semester_{semester_number}_Marksheet_{student.reg_no}.pdf"
    response["Content-Disposition"] = f'inline; filename="{filename}"'

    # ✅ alignment key: margins consistent with header
    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=54 * mm,      # reserve space for header
        bottomMargin=26 * mm,   # reserve space for footer
    )

    elements = []

    # Title
    elements.append(Paragraph(f"Semester {semester_number} Marksheet", title_style))
    elements.append(Paragraph("Academic Performance Statement", sub_style))
    elements.append(Spacer(1, 2 * mm))

    # ---------- Student Info (perfect aligned 2-column grid) ----------
    # Using one table with 4 columns: K,V | K,V to guarantee alignment
    degree_name = safe_str(getattr(degree, "degree", getattr(degree, "Degree", "—"))) or "—"
    dept_name = safe_str(getattr(student.department, "name", getattr(student.department, "Department", "—"))) or "—"

    info_grid = [
        [Paragraph("Name", info_k), Paragraph(safe_str(student.name or student.reg_no) or "—", info_v),
         Paragraph("Register No.", info_k), Paragraph(safe_str(student.reg_no) or "—", info_v)],

        [Paragraph("Degree", info_k), Paragraph(degree_name, info_v),
         Paragraph("Department", info_k), Paragraph(dept_name, info_v)],

        [Paragraph("Batch", info_k), Paragraph(safe_str(student.batch) or "—", info_v),
         Paragraph("Regulation", info_k), Paragraph(safe_str(student.regulation) or "—", info_v)],

        [Paragraph("Current Year", info_k), Paragraph(safe_str(student.year) or "—", info_v),
         Paragraph("Current Semester", info_k), Paragraph(safe_str(student.semester) or "—", info_v)],
    ]

    info_table = Table(
        info_grid,
        colWidths=[28*mm, (doc.width/2) - 28*mm, 32*mm, (doc.width/2) - 32*mm]
    )
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG),
        ("BOX", (0, 0), (-1, -1), 0.9, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))

    elements.append(info_table)
    elements.append(Spacer(1, 8 * mm))

    # ---------- Marks Table ----------
    if enriched_rows:
        table_data = [[
            Paragraph("#", th),
            Paragraph("Course Code", th),
            Paragraph("Course Title", th),
            Paragraph("Credit", th),
            Paragraph("Grade", th),
            Paragraph("GP", th),
            Paragraph("Total", th),
        ]] + enriched_rows

        # ✅ widths sum to doc.width for perfect alignment
        col_widths = [9*mm, 26*mm, 78*mm, 16*mm, 15*mm, 14*mm, doc.width - (9*mm+26*mm+78*mm+16*mm+15*mm+14*mm)]
        marks_table = Table(table_data, colWidths=col_widths, repeatRows=1)

        ts = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),

            ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),

            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("ALIGN", (0, 1), (0, -1), "CENTER"),
            ("ALIGN", (1, 1), (1, -1), "CENTER"),
            ("ALIGN", (2, 1), (2, -1), "LEFT"),
            ("ALIGN", (3, 1), (-1, -1), "CENTER"),

            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#F8FAFC")]),
            ("TOPPADDING", (0, 0), (-1, -1), 5.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5.5),
        ])

        # highlight failed rows
        for i, row in enumerate(enriched_rows, start=1):
            grade_text = row[4].getPlainText() if hasattr(row[4], "getPlainText") else str(row[4])
            if grade_text.strip().upper() in ("F", "FA", "FE"):
                ts.add("TEXTCOLOR", (0, i), (-1, i), DANGER)
                ts.add("FONTNAME", (0, i), (-1, i), "Helvetica-Bold")

        marks_table.setStyle(ts)
        elements.append(marks_table)
        elements.append(Spacer(1, 8 * mm))

        # ---------- Summary strip (aligned) ----------
        sgpa_show = f"{sgpa_val:.2f}" if sgpa_val is not None else "—"
        cgpa_show = f"{cgpa_val:.2f}" if cgpa_val is not None else "—"

        summary_data = [[
            Paragraph("Semester Credits", info_k), Paragraph(f"{sem_credit:.1f}" if sem_credit else "—", info_v),
            Paragraph("SGPA", info_k), Paragraph(sgpa_show, info_v),
            Paragraph(f"CGPA up to Sem {semester_number}", info_k), Paragraph(cgpa_show, info_v),
        ]]

        summary = Table(
            summary_data,
            colWidths=[30*mm, 18*mm, 16*mm, 18*mm, doc.width - (30*mm+18*mm+16*mm+18*mm+20*mm), 20*mm]
        )
        summary.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BG),
            ("BOX", (0, 0), (-1, -1), 0.9, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.45, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),

            # emphasize values
            ("FONTNAME", (1, 0), (1, 0), "Helvetica-Bold"),
            ("FONTNAME", (3, 0), (3, 0), "Helvetica-Bold"),
            ("FONTNAME", (5, 0), (5, 0), "Helvetica-Bold"),
            ("TEXTCOLOR", (1, 0), (5, 0), colors.HexColor("#111827")),
        ]))
        elements.append(summary)

        elements.append(Spacer(1, 4 * mm))
        elements.append(Paragraph(remark, remark_style))

    else:
        elements.append(Spacer(1, 10 * mm))
        elements.append(Paragraph(
            "No marks/grades have been published for this semester yet.",
            ParagraphStyle(
                "NoData", parent=styles["Normal"], fontSize=11,
                textColor=DANGER, alignment=TA_CENTER, spaceBefore=20,
            )
        ))

    # Final note
    elements.append(Spacer(1, 6 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.7, color=BORDER, spaceBefore=4, spaceAfter=6))
    elements.append(Paragraph(
        f"Generated on {datetime.now().strftime('%d %b %Y, %I:%M %p')}",
        note_style
    ))
    elements.append(Paragraph(
        "If you find any discrepancy, contact the Examination Cell within 7 working days.",
        note_style
    ))

    # Build with header/footer
    def _on_page(c, d):
        _marksheet_header_footer(c, d, meta={
            "subtitle": f"SEMESTER {semester_number} GRADE CARD",
            "watermark_text": "RIT • CONFIDENTIAL",
            "show_watermark": True,
        })

    doc.build(elements, onFirstPage=_on_page, onLaterPages=_on_page)
    return response



