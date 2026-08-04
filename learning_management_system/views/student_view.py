
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages  # Import the messages framework
from faculty_management.models import general_information
from learning_management_system.models import Folder, FacultyDocument, FacultyVideo  # Adjust import according to your models
from user_accounts.models import USER, StudentDetails  # Assuming USER is the model for users
from course_management.models import CourseEnrollment, AssignSubjectFaculty, Course  # Adjust import according to your models

def student_lms_dashboard(request):
    # This view can be used to render the dashboard for students
    return render(request, 'learning_management_system/student_lms_dashboard.html')

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

# @login_required
from collections import OrderedDict
from django.shortcuts import get_object_or_404, render
from user_accounts.decorators import check_permission

@check_permission("student_lms_dashboard")
def view_uploaded_documents(request):
    student_reg_no = request.user.Employee_id
    student = get_object_or_404(StudentDetails, reg_no=student_reg_no)

    current_sem = str(student.semester).strip() if student.semester is not None else ""

    enrollments = (
        CourseEnrollment.objects
        .select_related("course", "department", "regulation")
        .filter(student=student, enroll=True, section=student.section, batch=student.batch)
        .order_by("course__semester", "course__course_code")
    )

    assigned_courses = (
        AssignSubjectFaculty.objects
        .select_related("faculty", "course", "department", "regulation")
        .filter(
            is_active=True,
            course__in=enrollments.values_list("course_id", flat=True),
            section=student.section,
            batch=student.batch
        )
    )

    assigned_map = {}
    for a in assigned_courses:
        assigned_map.setdefault(a.course_id, []).append(a)

    # ✅ Split current semester + group others
    current_semester_enrollments = []
    other_semester_groups = OrderedDict()

    for e in enrollments:
        e_sem = str(getattr(e.course, "semester", "")).strip()
        if current_sem and e_sem == current_sem:
            current_semester_enrollments.append(e)
        else:
            other_semester_groups.setdefault(e_sem or "—", []).append(e)

    context = {
        "student": student,
        "current_sem": current_sem,
        "current_semester_enrollments": current_semester_enrollments,
        "other_semester_groups": other_semester_groups,
        "assigned_map": assigned_map,
    }
    return render(request, "learning_management_system/student/view_uploaded_documents.html", context)




# @login_required
def view_folders_and_files(request, course_id):
    # ✅ Logged-in student
    student_reg_no = request.user.Employee_id
    student = get_object_or_404(StudentDetails, reg_no=student_reg_no)

    # ✅ Current related data (use student values first, fallback to GET)
    year = request.GET.get("year") or student.year
    semester = request.GET.get("semester") or student.semester
    batch = request.GET.get("batch") or student.batch
    section = request.GET.get("section") or student.section

    # ✅ Course from URL param
    course = get_object_or_404(Course, id=course_id)

    # ✅ Fetch folders primarily by course/batch/section.
    # Faculty folders are created using course.year/course.semester and can differ
    # from student profile year/semester values.
    base_qs = Folder.objects.filter(
        course=course,
        batch=batch,
        folder_type="subject",
        section=section
    )

    # Prefer strict year/semester match when possible, fallback to base set.
    strict_qs = base_qs
    if year:
        strict_qs = strict_qs.filter(Q(year=year) | Q(year__isnull=True) | Q(year__exact=""))
    if semester:
        strict_qs = strict_qs.filter(Q(semester=semester) | Q(semester__isnull=True) | Q(semester__exact=""))

    folders = strict_qs if strict_qs.exists() else base_qs
    folders = folders.prefetch_related("lms_documents", "lms_videos").order_by("folder_name")

    return render(
        request,
        "learning_management_system/student/view_folders_and_files.html",
        {
            "folders": folders,
            "course": course,
            "student": student,
            "year": year,
            "semester": semester,
            "batch": batch,
        },
    )


