from django.shortcuts import render, redirect, get_object_or_404
from student_management.models import StudentCO_EX_Curricular, StudentPublication, StudentAchievements,StudentProfessionl, StudentProjects
from user_accounts.models import StudentDetails
from faculty_management.models import *


#     return render(request, template, {"grouped_activities": grouped_activities})


import datetime
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Case, When, IntegerField

from faculty_management.models import general_information
from user_accounts.models import StudentDetails
from student_management.models import StudentPublication


def mentor_publications_approval(request):
    emp_id = request.user.Employee_id
    faculty = get_object_or_404(general_information, faculty_id=emp_id)

    assigned_students = StudentDetails.objects.filter(mentor=faculty)
    assigned_reg_nos = set(assigned_students.values_list("reg_no", flat=True))

    publications = (
        StudentPublication.objects.filter(student__in=assigned_students)
        .select_related("student", "department")
        .annotate(
            pending_first=Case(
                When(status="Pending", then=0),
                default=1,
                output_field=IntegerField(),
            )
        )
        .order_by("pending_first", "-id")
    )

    if request.method == "POST":
        record_id = request.POST.get("record_id")
        action = request.POST.get("action")

        pub = get_object_or_404(StudentPublication, id=record_id)

        # ✅ Security: ensure mentor owns this student
        if not pub.student or pub.student.reg_no not in assigned_reg_nos:
            return render(request, "404.html", status=403)

        if action == "approve":
            pub.status = "Approved"
            pub.save(update_fields=["status"])
        elif action == "reject":
            pub.status = "Rejected"
            pub.save(update_fields=["status"])

        return redirect("mentor_publications_approval")

    grouped_activities = {}
    for act in publications:
        dept = getattr(act.department, "Department", "No Dept") if act.department else "No Dept"
        key = f"{dept} | Batch: {act.batch or '-'} | Year: {act.year or '-'} | Sec: {act.section or '-'}"
        grouped_activities.setdefault(key, []).append(act)

    context = {"faculty": faculty, "grouped_activities": grouped_activities}
    return render(request, "student_management/faculty/mentor_publications_approval.html", context)



from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Case, When, IntegerField

from faculty_management.models import general_information
from user_accounts.models import StudentDetails
from student_management.models import StudentProjects


def mentor_projects_approval(request):
    emp_id = request.user.Employee_id
    faculty = get_object_or_404(general_information, faculty_id=emp_id)

    assigned_students = StudentDetails.objects.filter(mentor=faculty)
    assigned_reg_nos = set(assigned_students.values_list("reg_no", flat=True))

    projects = (
        StudentProjects.objects.filter(students__student__in=assigned_students)
        .distinct()
        .prefetch_related("students__student", "students__department")
        .annotate(
            pending_first=Case(
                When(approval_status="Pending", then=0),
                default=1,
                output_field=IntegerField(),
            )
        )
        .order_by("pending_first", "-id")
    )

    if request.method == "POST":
        record_id = request.POST.get("record_id")
        action = request.POST.get("action")

        project = get_object_or_404(StudentProjects, id=record_id)

        # Security: ensure at least one student is assigned to this mentor
        allowed = project.students.filter(student__reg_no__in=assigned_reg_nos).exists()
        if not allowed:
            return render(request, "404.html", status=403)

        if action == "approve":
            project.approval_status = "Approved"
            project.save(update_fields=["approval_status"])
        elif action == "reject":
            project.approval_status = "Rejected"
            project.save(update_fields=["approval_status"])

        return redirect("mentor_projects_approval")

    grouped_activities = {}
    for proj in projects:
        first_sn = proj.students.select_related("department", "student").first()

        if first_sn:
            dept = getattr(first_sn.department, "Department", "No Dept") if first_sn.department else "No Dept"
            batch = first_sn.batch or "-"
            year = first_sn.year or "-"
            sec = first_sn.section or "-"
        else:
            dept, batch, year, sec = "No Dept", "-", "-", "-"

        key = f"{dept} | Batch: {batch} | Year: {year} | Sec: {sec}"
        grouped_activities.setdefault(key, []).append(proj)

    context = {"faculty": faculty, "grouped_activities": grouped_activities}
    return render(request, "student_management/faculty/mentor_projects_approval.html", context)

    
# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Case, When, IntegerField

from faculty_management.models import general_information
from user_accounts.models import StudentDetails
from student_management.models import StudentAchievements


def mentor_achievements_approval(request):
    emp_id = request.user.Employee_id
    faculty = get_object_or_404(general_information, faculty_id=emp_id)

    assigned_students = StudentDetails.objects.filter(mentor=faculty)
    assigned_reg_nos = set(assigned_students.values_list("reg_no", flat=True))

    achievements = (
        StudentAchievements.objects.filter(student__in=assigned_students)
        .select_related("student", "department")
        .annotate(
            pending_first=Case(
                When(status="Pending", then=0),
                default=1,
                output_field=IntegerField(),
            )
        )
        .order_by("pending_first", "-id")
    )

    if request.method == "POST":
        record_id = request.POST.get("record_id")
        action = request.POST.get("action")

        achievement = get_object_or_404(StudentAchievements, id=record_id)

        # ✅ Security
        if not achievement.student or achievement.student.reg_no not in assigned_reg_nos:
            return render(request, "404.html", status=403)

        if action == "approve":
            achievement.status = "Approved"
            achievement.save(update_fields=["status"])
        elif action == "reject":
            achievement.status = "Rejected"
            achievement.save(update_fields=["status"])

        return redirect("mentor_achievements_approval")

    grouped_activities = {}
    for ach in achievements:
        dept = getattr(ach.department, "Department", None) if ach.department else None
        dept = dept or getattr(getattr(ach.student, "Department", None), "Department", None) or "No Dept"

        batch = ach.batch or getattr(ach.student, "batch", None) or "-"
        year = ach.year or getattr(ach.student, "year", None) or "-"
        sec = ach.section or getattr(ach.student, "section", None) or "-"

        key = f"{dept} | Batch: {batch} | Year: {year} | Sec: {sec}"
        grouped_activities.setdefault(key, []).append(ach)

    context = {"faculty": faculty, "grouped_activities": grouped_activities}
    return render(request, "student_management/faculty/mentor_achievements_approval.html", context)

 
 
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Case, When, IntegerField

from faculty_management.models import general_information
from user_accounts.models import StudentDetails
from student_management.models import StudentCO_EX_Curricular


def mentor_coex_approval(request):
    emp_id = request.user.Employee_id
    faculty = get_object_or_404(general_information, faculty_id=emp_id)

    assigned_students = StudentDetails.objects.filter(mentor=faculty)
    assigned_reg_nos = set(assigned_students.values_list("reg_no", flat=True))

    activities = (
        StudentCO_EX_Curricular.objects.filter(student__in=assigned_students)
        .select_related("student", "department")
        .annotate(
            pending_first=Case(
                When(status="Pending", then=0),
                default=1,
                output_field=IntegerField(),
            )
        )
        .order_by("pending_first", "-id")
    )

    if request.method == "POST":
        record_id = request.POST.get("record_id")
        action = request.POST.get("action")

        activity = get_object_or_404(StudentCO_EX_Curricular, id=record_id)

        # ✅ Security: mentor can act only on assigned student
        if not activity.student or activity.student.reg_no not in assigned_reg_nos:
            return render(request, "404.html", status=403)

        if action == "approve":
            activity.status = "Approved"
            activity.save(update_fields=["status"])
        elif action == "reject":
            activity.status = "Rejected"
            activity.save(update_fields=["status"])

        return redirect("mentor_coex_approval")

    grouped_activities = {}
    for act in activities:
        dept = getattr(act.department, "Department", None) if act.department else None
        dept = dept or getattr(getattr(act.student, "Department", None), "Department", None) or "No Dept"

        batch = act.batch or getattr(act.student, "batch", None) or "-"
        year = act.year or getattr(act.student, "year", None) or "-"
        sec = act.section or getattr(act.student, "section", None) or "-"

        key = f"{dept} | Batch: {batch} | Year: {year} | Sec: {sec}"
        grouped_activities.setdefault(key, []).append(act)

    context = {
        "faculty": faculty,
        "grouped_activities": grouped_activities,
    }
    return render(
        request,
        "student_management/faculty/mentor_co_ex_curricular_approval.html",
        context,
    )

# views.py (FULL) — mentor_professional_approval (logic unchanged, only optimized to fetch student dept)
# student_management/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Case, When, IntegerField

from faculty_management.models import general_information
from user_accounts.models import StudentDetails
from student_management.models import StudentProfessionl


def mentor_professional_approval(request):
    emp_id = request.user.Employee_id
    faculty = get_object_or_404(general_information, faculty_id=emp_id)

    assigned_students = StudentDetails.objects.filter(mentor=faculty)
    assigned_reg_nos = set(assigned_students.values_list("reg_no", flat=True))

    professional = (
        StudentProfessionl.objects.filter(student__in=assigned_students)
        .select_related("student", "student__department", "department")
        .annotate(
            pending_first=Case(
                When(status="Pending", then=0),
                default=1,
                output_field=IntegerField(),
            )
        )
        .order_by("pending_first", "-id")
    )

    if request.method == "POST":
        record_id = request.POST.get("record_id")
        action = request.POST.get("action")

        prof = get_object_or_404(StudentProfessionl, id=record_id)

        # ✅ Security
        if not prof.student or prof.student.reg_no not in assigned_reg_nos:
            return render(request, "404.html", status=403)

        if action == "approve":
            prof.status = "Approved"
            prof.save(update_fields=["status"])
        elif action == "reject":
            prof.status = "Rejected"
            prof.save(update_fields=["status"])

        return redirect("mentor_professional_approval")

    grouped_activities = {}
    for p in professional:
        dept = (
            getattr(p.department, "Department", None)
            or getattr(getattr(p.student, "department", None), "Department", None)
            or "No Dept"
        )

        batch = getattr(p.student, "batch", None) or "-"
        year = p.year or getattr(p.student, "year", None) or "-"
        sec = p.section or getattr(p.student, "section", None) or "-"

        key = f"{dept} | Batch: {batch} | Year: {year} | Sec: {sec}"
        grouped_activities.setdefault(key, []).append(p)

    context = {
        "faculty": faculty,
        "grouped_activities": grouped_activities,
    }
    return render(
        request,
        "student_management/faculty/mentor_professional_approval.html",
        context,
    )
