
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Count
from django.db import connection
from datetime import date, datetime
import pandas as pd

from django.contrib.auth.decorators import login_required
from datetime import date

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from course_management.models import AssignSubjectFaculty, Course, CourseEnrollment, Regulations
from datetime import date

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from user_accounts.decorators import check_permission
from datetime import date
from collections import defaultdict

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from datetime import date
from collections import defaultdict


from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from user_accounts.models import USER  ,Add_Department 
from faculty_management.models import general_information, Open_Elective_Offer, Open_Elective_OfferToDept
from student_management.models import StudentDetails
from datetime import date

from user_accounts.decorators import check_permission, no_cache, faculty_login_required



from course_management.models import CourseHours
from django.db import models


def get_academic_year():
    today = date.today()
    if today.month >= 6:
        return f"{today.year}-{today.year + 1}"
    return f"{today.year - 1}-{today.year}"


from datetime import date
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

@check_permission("courses")
def student_courses(request):
    user = request.user
    reg_no = user.Employee_id

    try:
        student = StudentDetails.objects.select_related("department").get(reg_no=reg_no)
    except StudentDetails.DoesNotExist:
        messages.error(request, "Student record not found.")
        return render(
            request,
            "student_management/student/student_courses.html",
            {
                "all_courses": [],
                "academic_year": get_academic_year(),
            },
        )

    batch = student.batch
    current_sem = str(student.semester)
    regulation_year = student.regulation
    department = student.department
    academic_year = get_academic_year()
    current_year = str(student.year) if hasattr(student, "year") else None

    def semester_sort_value(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return 999

    def build_course_payload(
        course_obj,
        faculty_obj,
        skilled_faculty_obj=None,
        enrollment_obj=None,
        category_name="Core",
        category_description="Core Subjects",
        is_open_elective=False,
        course_hours_obj=None,
    ):
        return {
            "enrollment_id": enrollment_obj.id if enrollment_obj else None,
            "course_id": course_obj.id,
            "course_code": course_obj.course_code,
            "title": course_obj.title,
            "semester": str(course_obj.semester),
            "year": current_year,
            "academic_year": academic_year,
            "category": category_name,
            "category_description": category_description,
            "faculty_name": faculty_obj.name if faculty_obj else "Not Assigned",
            "faculty_id": faculty_obj.faculty_id if faculty_obj else "",
            "skilled_faculty_name": skilled_faculty_obj.name if skilled_faculty_obj else "",
            "skilled_faculty_id": skilled_faculty_obj.faculty_id if skilled_faculty_obj else "",
            "credits": getattr(course_hours_obj, "credits", "N/A") if course_hours_obj else "N/A",
            "total_hours": getattr(course_hours_obj, "total_hours", "N/A") if course_hours_obj else "N/A",
            "department_id": department.id if department else None,
            "batch": batch,
            "section": student.section,
            "regulation": regulation_year,
            "enrollment_date": enrollment_obj.enrollment_date if enrollment_obj else None,
            "is_open_elective": is_open_elective,
            "enrolled": bool(enrollment_obj.enroll) if enrollment_obj else False,
            "can_modify": str(course_obj.semester) == current_sem,
        }

    assigned = (
        AssignSubjectFaculty.objects
        .filter(
            batch=batch,
            regulation__year=regulation_year,
            department=department,
            section=student.section,
            is_active=True,
            academic_year=academic_year,
        )
        .select_related("course", "faculty", "skilled_faculty", "course__elective")
    )
    assigned = list(assigned)

    all_enrollments = (
        CourseEnrollment.objects.filter(
            student=student,
            batch=batch,
            regulation__year=regulation_year,
        )
        .select_related("course")
        .order_by("-id")
    )

    enrolled_map = {}
    for enrollment in all_enrollments:
        if enrollment.course_id not in enrolled_map:
            enrolled_map[enrollment.course_id] = enrollment

    offers = (
        Open_Elective_Offer.objects
        .filter(
            regulation__year=regulation_year,
            batch=batch,
            to_departments__offered_to_dept=department,
        )
        .select_related("course", "faculty", "course__elective")
        .distinct()
    )
    offers = list(offers)

    course_hours_map = {
        ch.course_id: ch
        for ch in CourseHours.objects.filter(
            course_id__in={
                assignment.course_id for assignment in assigned
            } | {
                offer.course_id for offer in offers
            }
        )
    }

    all_courses = []
    added_course_ids = set()

    for assignment in assigned:
        course_obj = assignment.course
        enrollment_obj = enrolled_map.get(course_obj.id)
        added_course_ids.add(course_obj.id)
        all_courses.append(
            build_course_payload(
                course_obj=course_obj,
                faculty_obj=assignment.faculty,
                skilled_faculty_obj=assignment.skilled_faculty,
                enrollment_obj=enrollment_obj,
                category_name=course_obj.elective.Course_category_name if course_obj.elective else "Core",
                category_description=course_obj.elective.category_description if course_obj.elective else "Core Subjects",
                is_open_elective=bool(enrollment_obj.is_open_elective) if enrollment_obj else False,
                course_hours_obj=course_hours_map.get(course_obj.id),
            )
        )

    for oe in offers:
        c = oe.course

        if c.id in added_course_ids:
            continue

        e = enrolled_map.get(c.id)
        if e and not bool(getattr(e, "is_open_elective", False)):
            e = None

        all_courses.append(
            build_course_payload(
                course_obj=c,
                faculty_obj=oe.faculty,
                enrollment_obj=e,
                category_name=c.elective.Course_category_name if c.elective else "Open Elective",
                category_description=c.elective.category_description if c.elective else "Open Elective Courses",
                is_open_elective=True,
                course_hours_obj=course_hours_map.get(c.id),
            )
        )

    all_courses.sort(
        key=lambda course: (
            0 if course["semester"] == current_sem else 1,
            -semester_sort_value(course["semester"]) if course["semester"] != current_sem else 0,
            course["course_code"].lower(),
            course["title"].lower(),
        )
    )

    semester_course_map = defaultdict(list)
    for course in all_courses:
        semester_course_map[course["semester"]].append(course)

    semester_groups = []
    for semester_key in sorted(
        semester_course_map.keys(),
        key=lambda sem: (
            0 if str(sem) == current_sem else 1,
            -semester_sort_value(sem) if str(sem) != current_sem else 0,
        ),
    ):
        semester_courses = sorted(
            semester_course_map[semester_key],
            key=lambda course: (
                0 if course["enrolled"] else 1,
                course["course_code"].lower(),
                course["title"].lower(),
            ),
        )

        semester_groups.append(
            {
                "semester": str(semester_key),
                "is_current": str(semester_key) == current_sem,
                "course_count": len(semester_courses),
                "enrolled_count": sum(1 for course in semester_courses if course["enrolled"]),
                "courses": semester_courses,
            }
        )

    current_semester_courses = next(
        (group for group in semester_groups if group["is_current"]),
        None,
    )
    current_semester_total_courses = (
        current_semester_courses["course_count"] if current_semester_courses else 0
    )
    current_semester_enrolled_courses = (
        current_semester_courses["enrolled_count"] if current_semester_courses else 0
    )

    if request.method == "POST":
        course = get_object_or_404(Course, id=request.POST.get("course_id"))
        faculty = get_object_or_404(
            general_information,
            faculty_id=request.POST.get("faculty_id"),
        )
        regulation_obj = get_object_or_404(Regulations, year=regulation_year)

        academic_year = get_academic_year()
        current_year = str(student.year) if getattr(student, "year", None) else None
        current_semester = str(student.semester) if getattr(student, "semester", None) else None
        is_open_elective = request.POST.get("is_open_elective") == "true"
        action_enroll = request.POST.get("action") == "enroll"

        # First try to update an old row with null values
        enrollment = (
            CourseEnrollment.objects.filter(
                student=student,
                course=course,
                regulation=regulation_obj,
            )
            .filter(
                Q(batch__isnull=True) |
                Q(year__isnull=True) |
                Q(academic_year__isnull=True) |
                Q(semester__isnull=True) |
                Q(section__isnull=True)
            )
            .first()
        )

        if enrollment:
            enrollment.department = department
            enrollment.faculty = faculty
            enrollment.batch = batch
            enrollment.section = student.section
            enrollment.regulation = regulation_obj
            enrollment.academic_year = academic_year
            enrollment.year = current_year
            enrollment.semester = current_semester
            enrollment.enroll = action_enroll
            enrollment.is_open_elective = is_open_elective
            enrollment.enrollment_date = date.today()
            enrollment.save()

        else:
            enrollment, created = CourseEnrollment.objects.update_or_create(
                student=student,
                course=course,
                batch=batch,
                regulation=regulation_obj,
                academic_year=academic_year,
                year=current_year,
                semester=current_semester,
                defaults={
                    "department": department,
                    "faculty": faculty,
                    "section": student.section,
                    "enroll": action_enroll,
                    "is_open_elective": is_open_elective,
                    "enrollment_date": date.today(),
                },
            )

        messages.success(request, f"{course.title} updated successfully.")
        return redirect("courses")

    return render(
        request,
        "student_management/student/student_courses.html",
        {
            "all_courses": all_courses,
            "semester_groups": semester_groups,
            "current_semester_courses": current_semester_courses,
            "semester": current_sem,
            "year": current_year,              # added
            "batch": batch,
            "regulation": regulation_year,
            "academic_year": academic_year,
            "student": student,
            "total_courses": current_semester_total_courses,
            "enrolled_courses": current_semester_enrolled_courses,
        },
    )



from student_management.models import AcademicCalendar





from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import os
from student_management.models import Student_cgpa, PersonalDetails
from user_accounts.models import StudentDetails



def upload_calendar(request):
    if request.method == 'POST':
        batch = request.POST.get('year')
        # print("batch => ", batch)
        semester = request.POST.get('semester')
        file = request.FILES.get('file')
        
        if not batch or not semester or not file:
            messages.error(request, 'All fields are required.')
            return redirect('upload_calendar')
        
        # ✅ Removed file type restriction (now accepts any file)
        
        # Check if calendar with same year and semester already exists
        try:
            existing_calendar = AcademicCalendar.objects.get(batch=batch, semester=semester)
            # Update existing calendar
            if existing_calendar.file and os.path.isfile(existing_calendar.file.path):
                try:
                    os.remove(existing_calendar.file.path)
                except OSError as e:
                    print()
            
            existing_calendar.file = file
            existing_calendar.save()
            messages.success(request, 'Calendar updated successfully.')
        except AcademicCalendar.DoesNotExist:
            # Create new calendar
            calendar = AcademicCalendar(batch=batch, semester=semester, file=file)
            calendar.save()
            messages.success(request, 'Calendar uploaded successfully.')
        
        return redirect('upload_calendar')
    
    # Get semesters 1-8
    semesters = range(1, 9)
    calendars = AcademicCalendar.objects.all().order_by('-batch', 'semester')
    batches = StudentDetails.objects.values_list("batch", flat=True).distinct()
    
    return render(request, 'student_management/admin/academic_calender.html', {
        'semesters': semesters,
        'calendars': calendars,
        "batches": batches,
    })



def delete_calendar(request, calendar_id):
    if request.method == 'POST':
        try:
            calendar = get_object_or_404(AcademicCalendar, id=calendar_id)
            
            # Store info for response
            calendar_info = f"Year {calendar.batch}, Semester {calendar.semester}"
            
            # Delete file from filesystem
            if calendar.file:
                try:
                    if os.path.isfile(calendar.file.path):
                        os.remove(calendar.file.path)
                except OSError as e:
                    print()
            
            # Delete from database
            calendar.delete()
            
            return JsonResponse({
                'success': True, 
                'message': f'Calendar {calendar_info} deleted successfully.'
            })
            
        except AcademicCalendar.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'error': 'Calendar not found.'
            }, status=404)
            
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'error': str(e)
            }, status=500)
            
    return JsonResponse({
        'success': False, 
        'error': 'Invalid request method. Only POST allowed.'
    }, status=405)


from user_accounts.models import StudentDetails
from faculty_management.models import general_information

from django.db.models import Q
from django.shortcuts import render
from user_accounts.decorators import check_permission

from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render

from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render

@check_permission("our_students")
def our_students(request):
    faculty_id = request.user.Employee_id
    faculty = general_information.objects.get(faculty_id=faculty_id)

    base_qs = StudentDetails.objects.filter(
        department=faculty.department
    ).select_related("mentor", "ca")

    batches = base_qs.values_list("batch", flat=True).distinct().order_by("batch")
    sections = base_qs.values_list("section", flat=True).distinct().order_by("section")

    mentor_ids = base_qs.exclude(mentor__isnull=True).values_list("mentor_id", flat=True).distinct()
    ca_ids = base_qs.exclude(ca__isnull=True).values_list("ca_id", flat=True).distinct()

    mentor_options = general_information.objects.filter(id__in=mentor_ids).order_by("name")
    ca_options = general_information.objects.filter(id__in=ca_ids).order_by("name")

    context = {
        "batches": batches,
        "sections": sections,
        "mentor_options": mentor_options,
        "ca_options": ca_options,
    }

    return render(request, "student_management/student/our_students.html", context)


@check_permission("our_students")
def our_students_data(request):
    faculty_id = request.user.Employee_id
    faculty = general_information.objects.get(faculty_id=faculty_id)

    students = StudentDetails.objects.filter(
        department=faculty.department
    ).select_related("mentor", "ca")

    batch = request.GET.get("batch")
    section = request.GET.get("section")
    mentor = request.GET.get("mentor")
    ca = request.GET.get("ca")
    search = request.GET.get("search")
    page = request.GET.get("page", 1)
    per_page = request.GET.get("per_page", 50)

    if batch:
        students = students.filter(batch=batch)

    if section:
        students = students.filter(section=section)

    if mentor:
        students = students.filter(mentor_id=mentor)

    if ca:
        students = students.filter(ca_id=ca)

    if search:
        students = students.filter(
            Q(reg_no__icontains=search) |
            Q(name__icontains=search) |
            Q(email__icontains=search)
        )

    students = students.order_by("reg_no", "is_active")

    try:
        per_page = int(per_page)
    except (TypeError, ValueError):
        per_page = 10

    paginator = Paginator(students, per_page)
    page_obj = paginator.get_page(page)

    data = []
    for s in page_obj:
        data.append({
            "id": s.id,
            "reg_no": s.reg_no,
            "name": s.name,
            "email": s.email,
            "batch": s.batch,
            "section": s.section,
            "mode": s.mode or "",
            "mentor": s.mentor.name if s.mentor else "",
            "ca": s.ca.name if s.ca else "",
            "profile_img": s.profile_img.url if s.profile_img else "",
            "status": "Active" if getattr(s, "is_active", True) else "Inactive"
        })

    return JsonResponse({
        "students": data,
        "pagination": {
            "current_page": page_obj.number,
            "total_pages": paginator.num_pages,
            "total_students": paginator.count,
            "has_previous": page_obj.has_previous(),
            "has_next": page_obj.has_next(),
            "previous_page": page_obj.previous_page_number() if page_obj.has_previous() else None,
            "next_page": page_obj.next_page_number() if page_obj.has_next() else None,
            "start_index": page_obj.start_index() if paginator.count else 0,
            "end_index": page_obj.end_index() if paginator.count else 0,
            "per_page": per_page,
        }
    })

from django.contrib import messages

def edit_our_student(request, student_id):

    faculty_data = general_information.objects.get(
        faculty_id=request.user.Employee_id
    )

    student = get_object_or_404(StudentDetails, id=student_id)
    old_reg_no = student.reg_no

    departments = Add_Department.objects.all()
    faculty = general_information.objects.filter(
        department=faculty_data.department
    )

    if request.method == "POST":

        student.name = request.POST.get("name")
        student.reg_no = request.POST.get("reg_no")
        student.aadhar_number = request.POST.get("aadhar_number")
        student.batch = request.POST.get("batch")
        student.section = request.POST.get("section")
        student.year = request.POST.get("year")
        student.semester = request.POST.get("semester")
        student.regulation = request.POST.get("regulation")
        student.mobile_no = request.POST.get("mobile_no")
        student.email = request.POST.get("email")
        student.umis_id = request.POST.get("umis_id")
        student.date_of_birth = request.POST.get("date_of_birth")
        student.gender = request.POST.get("gender")
        student.mode = request.POST.get("mode") or None
        student.year_of_admission = request.POST.get("year_of_admission")
        student.semester_of_admission = request.POST.get("semester_of_admission")

        dept_id = request.POST.get("department")
        if dept_id:
            student.department_id = dept_id

        mentor_id = request.POST.get("mentor")
        if mentor_id:
            student.mentor_id = mentor_id

        ca_id = request.POST.get("ca")
        if ca_id:
            student.ca_id = ca_id

        if request.FILES.get("profile_img"):
            student.profile_img = request.FILES.get("profile_img")

        student.save()

        new_reg_no = student.reg_no

        # Case 1: Register number changed
        if old_reg_no != new_reg_no:

            USER.objects.using("rit_approval_system").filter(
                reg_no=old_reg_no
            ).update(reg_no=new_reg_no)

            PersonalDetails.objects.using("admissionform1").filter(
                Register_Number=old_reg_no
            ).update(Register_Number=new_reg_no)

            messages.success(
                request,
                f"Student '{student.name}' updated successfully. "
                f"Register Number changed from '{old_reg_no}' to '{new_reg_no}'. "
                f"All related systems were synchronized."
            )

        # Case 2: Only student details updated
        else:

            messages.info(
                request,
                f"Student '{student.name}' details updated successfully. "
                f"No Register Number change detected."
            )

        return redirect("our_students")

    context = {
        "student": student,
        "departments": departments,
        "faculty": faculty
    }

    return render(
        request,
        "student_management/student/edit_our_student.html",
        context
    )
 
@check_permission("mentees")
def mentees(request):
    faculty_id = request.user.Employee_id
    try:
        faculty = general_information.objects.get(faculty_id=faculty_id)
        # # print("Faculty found:", faculty.name)
    except general_information.DoesNotExist:
        return render(request, "student_management/student/mentees.html", {
            "mentees": [],
            "batches": [],
            "selected_batch": None,
            "error": "Faculty record not found."
        })


    mentees_qs = StudentDetails.objects.filter(mentor=faculty, is_active=True).order_by("reg_no")
    # print("Initial mentees count:", mentees_qs.count())
    # Batch filter
    batches = mentees_qs.values_list('batch', flat=True).distinct()
    selected_batch = request.GET.get('batch')
    if selected_batch:
        mentees_qs = mentees_qs.filter(batch=selected_batch)

    context = {
        "mentees": mentees_qs,
        "batches": batches,
        "selected_batch": selected_batch,
    }
    return render(request, "student_management/student/mentees.html", context)





from django.shortcuts import render, redirect
from django.db import transaction,IntegrityError
from django.contrib import messages
from user_accounts.models import StudentDetails, Add_Department
from student_management.models import PersonalDetails  # adjust if needed
from django.db.models.functions import Lower, Replace
from django.db.models import Value

@check_permission("generate_register_no")
def generate_register_no(request):

    faculty = general_information.objects.get(faculty_id=request.user.Employee_id)

    batches = StudentDetails.objects.values_list(
        'batch', flat=True
    ).distinct().order_by('batch')

    students = None
    selected_batch = None
    selected_department = None
    generated_data = []

    if request.method == 'POST':
        selected_batch = request.POST.get('batch')
        selected_department = request.POST.get('department')

        if not selected_batch or not selected_department:
            messages.error(
                request,
                "Please select both Batch and Department before generating register numbers."
            )
        else:
            department = Add_Department.objects.get(id=selected_department)

            batch_suffix = str(selected_batch)[-2:]

            # Use department_code field
            dept_code = str(department.Department_code).strip().upper()

            # A -> 0A
            if len(dept_code) == 1:
                dept_code = f"0{dept_code}"

            prefix = f"{batch_suffix}{dept_code}"

            students = StudentDetails.objects.filter(
                batch=selected_batch,
                department_id=selected_department
            ).annotate(
                cleaned=Lower('name')
            ).annotate(
                cleaned=Replace('cleaned', Value(' '), Value(''))
            ).annotate(
                cleaned=Replace('cleaned', Value('.'), Value(''))
            ).annotate(
                cleaned=Replace('cleaned', Value('-'), Value(''))
            ).annotate(
                cleaned=Replace('cleaned', Value(','), Value(''))
            ).order_by('cleaned')

            if not students.exists():
                messages.warning(
                    request,
                    f"No students found for Batch {selected_batch} - Department {department.Department}."
                )
            else:
                count = 1
                for student in students:
                    reg_no = f"{prefix}{count:03d}"

                    generated_data.append({
                        'id': student.id,
                        'name': student.name,
                        'department': department.Department,
                        'old_reg_no': student.reg_no,
                        'reg_no': reg_no,
                    })

                    count += 1

                if 'save_btn' in request.POST:
                    try:
                        with transaction.atomic():
                            StudentDetails.objects.filter(
                                batch=selected_batch,
                                department_id=selected_department
                            ).update(reg_no=None)

                            count = 1
                            for student in students:
                                reg_no = f"{prefix}{count:03d}"
                                student.reg_no = reg_no
                                student.save(update_fields=['reg_no'])

                                if student.aadhar_number:
                                    PersonalDetails.objects.using("admissionform1").filter(
                                        Aadhaar_Number=student.aadhar_number
                                    ).update(registration_no=reg_no)

                                count += 1

                        students = StudentDetails.objects.filter(
                            batch=selected_batch,
                            department_id=selected_department
                        ).annotate(
                            cleaned=Lower('name')
                        ).annotate(
                            cleaned=Replace('cleaned', Value(' '), Value(''))
                        ).annotate(
                            cleaned=Replace('cleaned', Value('.'), Value(''))
                        ).annotate(
                            cleaned=Replace('cleaned', Value('-'), Value(''))
                        ).annotate(
                            cleaned=Replace('cleaned', Value(','), Value(''))
                        ).order_by('cleaned')

                        generated_data = []

                        count = 1
                        for student in students:
                            reg_no = f"{prefix}{count:03d}"

                            generated_data.append({
                                'id': student.id,
                                'name': student.name,
                                'department': department.Department,
                                'old_reg_no': student.reg_no,
                                'reg_no': reg_no,
                            })

                            count += 1

                        messages.success(
                            request,
                            f"Register numbers generated & saved for Batch {selected_batch} - {department.Department}."
                        )

                    except Exception as e:
                        messages.error(request, f"Error: {str(e)}")

    context = {
        'faculty_department': faculty.department,
        'batches': batches,
        'students': students,
        'generated_data': generated_data,
        'selected_batch': selected_batch,
        'selected_department': selected_department,
    }

    return render(
        request,
        'student_management/admin/generate_register_no.html',
        context
    )



from django.shortcuts import render
from django.contrib import messages
from django.db.models import Sum
from decimal import Decimal

from user_accounts.models import StudentDetails, PersonalDetails, AdmissionRecords, Add_Department, TransportDetails
from fee_management.models import FeeEntry, TransportFee
from student_management.models import FeeReceipt, ManualFeeEntry


@check_permission("student_fee_view")
def student_fee_view(request):

    # ----------------------------
    # 1) Find student (local DB)
    # ----------------------------
    student = None
    if getattr(request.user, "email", None):
        student = StudentDetails.objects.filter(email=request.user.email).first()

    if not student and getattr(request.user, "Employee_id", None):
        student = StudentDetails.objects.filter(reg_no=request.user.Employee_id).first()

    if not student:
        messages.error(request, "Student record not found.")
        return render(request, "student_management/fee/student_fee_view.html", {
            "fee_entries": [],
            "context_info": {}
        })

    aadhar = (student.aadhar_number or "").strip()
    if not aadhar:
        messages.error(request, "Aadhaar number missing in your profile.")
        return render(request, "student_management/fee/student_fee_view.html", {
            "fee_entries": [],
            "context_info": {"student": student}
        })

    # ---------------------------------------
    # 2) Personal record (admissionform1 DB)
    # ---------------------------------------
    personal = PersonalDetails.objects.using("admissionform1").filter(
        Aadhaar_Number=aadhar
    ).first()

    if not personal:
        messages.error(request, "No admission personal record found.")
        return render(request, "student_management/fee/student_fee_view.html", {
            "fee_entries": [],
            "context_info": {"student": student}
        })

    # ---------------------------------------
    # 3) Admission record (admissionform1 DB)
    # ---------------------------------------
    admission = AdmissionRecords.objects.using("admissionform1").filter(
        PersonalDetailsId=personal
    ).first()

    if not admission:
        messages.error(request, "No admission record found.")
        return render(request, "student_management/fee/student_fee_view.html", {
            "fee_entries": [],
            "context_info": {"student": student}
        })

    dept_name = (admission.Department or "").strip()
    quota = (admission.Quota or "").strip()
    mode = (admission.Mode or "").strip().lower()

    # ------------------------------------------------
    # 3.5) TransportDetails -> bus_stop (admissionform1)
    # ------------------------------------------------
    # Your model: TransportDetails.admission_records_id -> PersonalDetails (to_field='id')
    transport = TransportDetails.objects.using("admissionform1").filter(
        admission_records_id=personal
    ).only("bus_stop", "bus_route", "bus_no", "bus_time").first()

    bus_stop = (transport.bus_stop or "").strip() if transport else ""

    # ---------------------------------------
    # 4) Map department (local DB)
    # ---------------------------------------
    department = None
    if dept_name:
        department = (
            Add_Department.objects.filter(Department__iexact=dept_name).first()
            or Add_Department.objects.filter(department_label__iexact=dept_name).first()
            or Add_Department.objects.filter(degree_department__icontains=dept_name).first()
        )

    if not department and student.department:
        department = student.department

    if not department:
        messages.error(request, "Unable to map your department.")
        return render(request, "student_management/fee/student_fee_view.html", {
            "fee_entries": [],
            "context_info": {"student": student}
        })

    # ---------------------------------------
    # 5) Mess / Hostel logic
    # ---------------------------------------
    selected_keyword = "Mess" if "transport" in mode else "Hostel"

    # ---------------------------------------
    # 6) Base fee queryset (local DB)
    # ---------------------------------------
    base_qs = FeeEntry.objects.select_related("fee_category", "degree").filter(
        department_id=str(department.id)
    )

    if quota:
        base_qs = base_qs.filter(quota=quota)

    if department.degree_id:
        base_qs = base_qs.filter(degree_id=department.degree_id)

    special_qs = base_qs.filter(fee_category__name__icontains=selected_keyword)
    tuition_qs = base_qs.filter(fee_category__name__icontains="Tuition")
    common_qs = base_qs.exclude(
        fee_category__name__icontains="Mess"
    ).exclude(
        fee_category__name__icontains="Hostel"
    ).exclude(
        fee_category__name__icontains="Tuition"
    )

    fee_qs = (special_qs | tuition_qs | common_qs).distinct()

    # ---------------------------------------
    # 7) Academic year from semester
    # ---------------------------------------
    try:
        semester = int(student.semester)
        year_index = min((semester + 1) // 2, 4)
    except Exception:
        year_index = 1

    # ---------------------------------------
    # 8) Fee calculation (local DB)
    # ---------------------------------------
    rows = []
    total_current_year = Decimal("0.00")

    for fee in fee_qs:
        amt = getattr(fee, f"year_{year_index}", None) or Decimal("0.00")
        amt = Decimal(amt)

        rows.append({
            "entry": fee,
            "label": None,
            "current_amount": amt,
            "amount_per_year": amt,  # ✅ for display (same as current year amount here)
        })
        total_current_year += amt

    # ---------------------------------------
    # 9) Transport Fee (ONLY if mode=transport)
    #    Match TransportFee.bus_stop == the student's admission bus stop
    # ---------------------------------------
    transport_amount_per_year = Decimal("0.00")

    if "transport" in mode:
        try:
            if bus_stop:
                transport_fee = TransportFee.objects.filter(
                    bus_stop__iexact=bus_stop
                ).first()

                if transport_fee:
                    transport_amount_per_year = Decimal(transport_fee.amount_per_year or 0)

                    rows.append({
                        "entry": None,
                        "label": f"Transport Fee - {bus_stop}",
                        "current_amount": transport_amount_per_year,
                        "amount_per_year": transport_amount_per_year,  # ✅ explicitly per-year
                    })
                    total_current_year += transport_amount_per_year
        except Exception:
            pass

    # ---------------------------------------
    # 10) Paid & Pending (local DB)
    # ---------------------------------------
    sem_map = {1: [1, 2], 2: [3, 4], 3: [5, 6], 4: [7, 8]}
    sem_pair = sem_map.get(year_index, [1, 2])

    paid = ManualFeeEntry.objects.filter(
        fee_receipt__student=student,
        fee_receipt__semester__in=sem_pair
    ).aggregate(total=Sum("entered_fee"))["total"] or Decimal("0.00")

    pending = total_current_year - paid
    if pending < 0:
        pending = Decimal("0.00")

    manual_entries = ManualFeeEntry.objects.filter(
        fee_receipt__student=student,
        fee_receipt__semester__in=sem_pair
    ).select_related("fee_receipt").order_by("-fee_receipt__uploaded_at")

    # ---------------------------------------
    # Context
    # ---------------------------------------
    context = {
        "fee_entries": rows,
        "context_info": {
            "student": student,
            "department": department,
            "quota": quota,
            "mode": admission.Mode,
            "bus_stop": bus_stop,
            "transport_amount_per_year": transport_amount_per_year,  # ✅ show separately if needed
        },
        "selected_fee_label": selected_keyword,
        "current_year_index": year_index,
        "total_current_year": total_current_year,
        "entered_total": paid,
        "pending_total": pending,
        "manual_entries": manual_entries,
    }

    return render(request, "student_management/fee/student_fee_view.html", context)
 
from collections import OrderedDict
from datetime import datetime
from decimal import Decimal
import io
import os

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Sum, Q
from django.http import HttpResponse, FileResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.contrib.staticfiles import finders

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Table, TableStyle, Paragraph, Spacer, KeepTogether
)

from user_accounts.models import StudentDetails, PersonalDetails, AdmissionRecords, Add_Department, TransportDetails, GlobalUsers
from fee_management.models import FeeEntry, TransportFee
from student_management.models import ManualFeeEntry
from faculty_management.models import general_information
from course_management.models import SectionMaster, Degree


def _is_global_fee_user(user):
    """
    'Global user' access (all-college, not department-scoped) is granted via
    the Create Global Users admin screen (GlobalUsers.global_user). This is
    granted per (employee, role), not per employee — the same person can
    hold multiple accounts under different roles (e.g. HOD on one, Vice
    Principal on another), and global access on one role must not leak into
    the others. Only the role the viewer is actually logged in as is checked.
    """
    emp_id = str(getattr(user, "Employee_id", "") or "").strip()
    role_id = getattr(user, "role_id", None)
    if not emp_id or role_id is None:
        return False
    return GlobalUsers.objects.filter(
        employee_id=emp_id, role_id=str(role_id), global_user=True
    ).exists()


# ============================================================
# Batched fee-computation helpers
#
# The naive per-student loop (used previously) issued ~4 DB queries per
# student (admission lookup, transport lookup, fee-entry lookup, paid-total
# aggregate) — for a few thousand students that's thousands of round trips
# and is the main reason the Fee View page/summary/chart felt slow. These
# helpers fetch everything for the whole batch in a handful of queries and
# do the matching in Python instead.
# ============================================================

def _fee_safe_str(v):
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    return str(v).strip()


def _fee_year_index_from_sem(student):
    sem_raw = _fee_safe_str(getattr(student, "semester", ""))
    try:
        sem_i = int(sem_raw)
        yi = (sem_i + 1) // 2 if sem_i > 0 else 1
    except Exception:
        yi = 1
    return min(max(yi, 1), 4)


def _fee_sem_pair_for_year(yi):
    return {1: [1, 2], 2: [3, 4], 3: [5, 6], 4: [7, 8]}.get(yi, [1, 2])


def _batch_fee_entries_by_department(dept_ids):
    dept_ids = [d for d in dept_ids if d]
    if not dept_ids:
        return {}
    out = {}
    for entry in FeeEntry.objects.select_related("fee_category").filter(department_id__in=dept_ids):
        out.setdefault(entry.department_id, []).append(entry)
    return out


def _batch_admission_data(students):
    """Returns {student.id: (quota, mode_str, bus_stop)} in ~3 queries total."""
    aadhar_to_ids = {}
    for st in students:
        a = _fee_safe_str(getattr(st, "aadhar_number", ""))
        if a:
            aadhar_to_ids.setdefault(a, []).append(st.id)

    result = {}
    if not aadhar_to_ids:
        return result

    personals = list(
        PersonalDetails.objects.using("admissionform1")
        .filter(Aadhaar_Number__in=list(aadhar_to_ids.keys()))
        .only("id", "Aadhaar_Number")
    )
    personal_id_by_aadhar = {p.Aadhaar_Number: p.id for p in personals}
    personal_ids = list(personal_id_by_aadhar.values())

    admissions = {
        a.PersonalDetailsId_id: a
        for a in AdmissionRecords.objects.using("admissionform1")
            .filter(PersonalDetailsId_id__in=personal_ids)
            .only("PersonalDetailsId_id", "Quota", "Mode")
    }
    transports = {
        t.admission_records_id_id: t
        for t in TransportDetails.objects.using("admissionform1")
            .filter(admission_records_id_id__in=personal_ids)
            .only("admission_records_id_id", "bus_stop")
    }

    for aadhar, student_ids in aadhar_to_ids.items():
        pid = personal_id_by_aadhar.get(aadhar)
        if pid is None:
            continue
        adm = admissions.get(pid)
        trn = transports.get(pid)
        quota = _fee_safe_str(getattr(adm, "Quota", "")) if adm else ""
        mode_str = _fee_safe_str(getattr(adm, "Mode", "")) if adm else ""
        bus_stop = _fee_safe_str(getattr(trn, "bus_stop", "")) if trn else ""
        for sid in student_ids:
            result[sid] = (quota, mode_str, bus_stop)

    return result


def _batch_paid_by_student_semester(student_ids):
    """Returns {(student_id, semester): total_paid} in 1 query."""
    if not student_ids:
        return {}
    rows = (
        ManualFeeEntry.objects.filter(fee_receipt__student_id__in=student_ids)
        .values("fee_receipt__student_id", "fee_receipt__semester")
        .annotate(total=Sum("entered_fee"))
    )
    return {
        (r["fee_receipt__student_id"], r["fee_receipt__semester"]): (r["total"] or Decimal("0.00"))
        for r in rows
    }


_transport_amount_cache = {}


def _batch_transport_amounts(bus_stops):
    """Returns {bus_stop: amount_per_year} for the given unique bus stops."""
    needed = [b for b in set(bus_stops) if b and b not in _transport_amount_cache]
    if needed:
        fees = {
            f.bus_stop: f for f in TransportFee.objects.filter(bus_stop__in=needed)
        }
        for bus_stop in needed:
            fee = fees.get(bus_stop)
            try:
                _transport_amount_cache[bus_stop] = Decimal(str(fee.amount_per_year or 0)) if fee else Decimal("0.00")
            except Exception:
                _transport_amount_cache[bus_stop] = Decimal("0.00")
    return _transport_amount_cache


def _pick_fee_entries(entries, quota, mode_str):
    """Pure-Python equivalent of the old per-student select_fee_qs() DB query."""
    mode_lc = _fee_safe_str(mode_str).lower()
    selected_keyword = "mess" if "transport" in mode_lc else "hostel"
    quota_lc = _fee_safe_str(quota).lower()

    pool = entries
    if quota_lc:
        matched = [e for e in entries if _fee_safe_str(getattr(e, "quota", "")).lower() == quota_lc]
        if matched:
            pool = matched

    out = []
    for e in pool:
        name_lc = _fee_safe_str(getattr(e.fee_category, "name", "")).lower()
        if selected_keyword in name_lc:
            out.append(e)
        elif "tuition" in name_lc:
            out.append(e)
        elif "mess" not in name_lc and "hostel" not in name_lc:
            out.append(e)
    return out


def _compute_fee_rows_batched(students, force_dept=None):
    """
    Batched replacement for the old per-student compute_student_fee_row() loop.
    Returns a list of {department, year_index, section, total_current_year,
    paid_total, pending_total} dicts, computed with a fixed, small number of
    queries regardless of how many students are passed in.
    """
    students = list(students)
    if not students:
        return []

    prelim = []
    dept_ids = set()
    for st in students:
        yi = _fee_year_index_from_sem(st)
        sem_pair = _fee_sem_pair_for_year(yi)
        dept = force_dept or getattr(st, "department", None)
        if not dept and getattr(st, "department_id", None):
            dept = Add_Department.objects.filter(id=st.department_id).first()
        if dept:
            dept_ids.add(dept.id)
        prelim.append({"student": st, "year_index": yi, "sem_pair": sem_pair, "department": dept})

    fee_entries_by_dept = _batch_fee_entries_by_department(dept_ids)
    admission_by_student = _batch_admission_data(students)
    paid_by_student_sem = _batch_paid_by_student_semester([st.id for st in students])

    bus_stops = [v[2] for v in admission_by_student.values() if v[2]]
    transport_amounts = _batch_transport_amounts(bus_stops)

    rows = []
    for r in prelim:
        st = r["student"]
        dept = r["department"]
        yi = r["year_index"]
        sem_pair = r["sem_pair"]

        quota, mode_str, bus_stop = admission_by_student.get(st.id, ("", "", ""))

        total_current_year = Decimal("0.00")
        if dept:
            entries = fee_entries_by_dept.get(dept.id, [])
            for e in _pick_fee_entries(entries, quota, mode_str):
                total_current_year += Decimal(str(getattr(e, f"year_{yi}", 0) or 0))

        if "transport" in mode_str.lower() and bus_stop:
            total_current_year += transport_amounts.get(bus_stop, Decimal("0.00"))

        paid_total = Decimal("0.00")
        for sem in sem_pair:
            paid_total += paid_by_student_sem.get((st.id, sem), Decimal("0.00"))

        pending_total = total_current_year - paid_total
        if pending_total < 0:
            pending_total = Decimal("0.00")

        rows.append({
            "student": st,
            "department": dept,
            "year_index": yi,
            "section": _fee_safe_str(getattr(st, "section", "")) or "Unassigned",
            "total_current_year": total_current_year,
            "paid_total": paid_total,
            "pending_total": pending_total,
        })

    return rows


@check_permission("fee_view")
def fee_view(request):
    TEMPLATE = "student_management/fee/fee_view.html"

    # ----------------------------
    # Helpers
    # ----------------------------
    def safe_str(v):
        if v is None:
            return ""
        if isinstance(v, str):
            return v.strip()
        return str(v).strip()

    def _field_exists(model, name: str) -> bool:
        try:
            model._meta.get_field(name)
            return True
        except Exception:
            return False

    def _role_to_text(role_value) -> str:
        # Fix: 'Role' object has no attribute 'lower'
        if role_value is None:
            return ""
        if isinstance(role_value, str):
            return role_value.strip().lower()

        # control_room_role has field: role (CharField)
        if hasattr(role_value, "role"):
            vv = getattr(role_value, "role", None)
            if isinstance(vv, str) and vv.strip():
                return vv.strip().lower()

        for attr in ("name", "role_name", "Role_name", "title", "code", "slug"):
            if hasattr(role_value, attr):
                vv = getattr(role_value, attr, None)
                if isinstance(vv, str) and vv.strip():
                    return vv.strip().lower()

        try:
            return str(role_value).strip().lower()
        except Exception:
            return ""

    def get_user_role_id(user):
        # control_room_user.role is FK to control_room_role
        v = getattr(user, "role", None)
        if v is not None and hasattr(v, "id"):
            try:
                return int(v.id)
            except Exception:
                pass

        # fallback (older patterns)
        for attr in ("role_id", "Role_id", "role", "Role"):
            vv = getattr(user, attr, None)
            if vv is None:
                continue
            if hasattr(vv, "id"):
                try:
                    return int(vv.id)
                except Exception:
                    pass
            try:
                return int(str(vv).strip())
            except Exception:
                continue
        return None

    def get_user_role_text(user) -> str:
        # prefers user.role.role (control_room_role.role)
        if hasattr(user, "role"):
            return _role_to_text(getattr(user, "role", None))
        # fallback
        for attr in ("role", "Role", "role_id", "Role_id"):
            if hasattr(user, attr):
                txt = _role_to_text(getattr(user, attr, None))
                if txt:
                    return txt
        return ""

    def is_hod_user(user) -> bool:
        rt = get_user_role_text(user)
        if not rt:
            return False
        return (rt == "hod") or rt.startswith("hod") or ("head of department" in rt)

    def resolve_faculty_and_hod_dept(user):
        """
        Faculty is found by Employee_id (from login), matched to faculty_management.general_information.faculty_id.
        Department for HOD is taken from that faculty record.
        """
        fac_emp_id = getattr(user, "Employee_id", None)
        faculty = (
            general_information.objects
            .filter(faculty_id=fac_emp_id)
            .select_related("department")
            .first()
            if fac_emp_id else None
        )

        hod_dept = None
        if faculty and getattr(faculty, "department", None):
            hod_dept = faculty.department

        # fallback by user.email
        if not hod_dept:
            user_email = getattr(user, "email", None)
            if user_email:
                fac_by_email = (
                    general_information.objects
                    .filter(Q(college_email__iexact=user_email) | Q(personal_email__iexact=user_email))
                    .select_related("department")
                    .first()
                )
                if fac_by_email and getattr(fac_by_email, "department", None):
                    faculty = faculty or fac_by_email
                    hod_dept = fac_by_email.department

        # fallback by user.Department FK (control_room_user.Department)
        if not hod_dept and hasattr(user, "Department"):
            ud = getattr(user, "Department", None)
            if ud is not None:
                dept_id = getattr(ud, "id", None)
                if dept_id is not None:
                    hod_dept = Add_Department.objects.filter(id=dept_id).first()

        return faculty, hod_dept

    def hod_students_queryset(hod_dept):
        """
        Matches students in HOD department, robust across FK + ids + code/name.
        """
        if not hod_dept:
            return StudentDetails.objects.none()

        qs = StudentDetails.objects.all().select_related("department")

        dept_id = getattr(hod_dept, "id", None)
        dept_code = safe_str(getattr(hod_dept, "Department_code", ""))
        dept_name = safe_str(getattr(hod_dept, "Department", ""))
        dept_label = safe_str(getattr(hod_dept, "department_label", ""))

        cond = Q()

        # FK match
        try:
            cond |= Q(department=hod_dept)
        except Exception:
            pass

        # department_id match
        if dept_id is not None:
            cond |= Q(department_id=dept_id)

        # by related fields
        if dept_code:
            cond |= Q(department__Department_code__iexact=dept_code)
        if dept_name:
            cond |= Q(department__Department__iexact=dept_name)
        if dept_label:
            cond |= Q(department__department_label__iexact=dept_label)

        # StudentDetails may have string department fields
        for f in ("Department", "department_name", "dept_name", "department_label", "Department_code", "dept_code", "department_code"):
            if _field_exists(StudentDetails, f):
                if dept_code:
                    cond |= Q(**{f"{f}__iexact": dept_code})
                if dept_name:
                    cond |= Q(**{f"{f}__iexact": dept_name})
                if dept_label:
                    cond |= Q(**{f"{f}__iexact": dept_label})

        return qs.filter(cond).distinct().order_by("name")

    def year_index_from_sem(student):
        sem_raw = safe_str(getattr(student, "semester", ""))
        try:
            sem_i = int(sem_raw)
            yi = (sem_i + 1) // 2 if sem_i > 0 else 1
        except Exception:
            yi = 1
        return min(max(yi, 1), 4)

    def sem_pair_for_year(yi):
        return {1: [1, 2], 2: [3, 4], 3: [5, 6], 4: [7, 8]}.get(yi, [1, 2])

    def get_admission(student):
        aadhar = safe_str(getattr(student, "aadhar_number", ""))
        personal = None
        admission = None
        bus_stop = ""
        if aadhar:
            personal = PersonalDetails.objects.using("admissionform1").filter(Aadhaar_Number=aadhar).first()
            if personal:
                admission = AdmissionRecords.objects.using("admissionform1").filter(PersonalDetailsId=personal).first()
                transport = TransportDetails.objects.using("admissionform1").filter(
                    admission_records_id=personal
                ).only("bus_stop").first()
                bus_stop = safe_str(getattr(transport, "bus_stop", "")) if transport else ""
        quota = safe_str(getattr(admission, "Quota", "")) if admission else ""
        mode_str = safe_str(getattr(admission, "Mode", "")) if admission else ""
        return admission, quota, mode_str, bus_stop

    def map_department(student, admission, force_dept=None):
        """
        Use StudentDetails.department_id -> Add_Department.
        If force_dept is given (HOD / filtered dept), use it.
        """
        if force_dept:
            return force_dept

        # direct FK
        if getattr(student, "department", None):
            return student.department

        # department_id fallback
        dept_id = getattr(student, "department_id", None)
        if dept_id:
            return Add_Department.objects.filter(id=dept_id).first()

        # admission dept name fallback
        dept_name = safe_str(getattr(admission, "Department", "")) if admission else ""
        if dept_name:
            return (
                Add_Department.objects.filter(Department__iexact=dept_name).first()
                or Add_Department.objects.filter(department_label__iexact=dept_name).first()
                or Add_Department.objects.filter(degree_department__icontains=dept_name).first()
            )

        return None

    # ---- per-request caches (reduces repeated DB hits) ----
    dept_fee_cache = {}
    transport_cache = {}

    def feeentry_for_department(add_dept):
        if not add_dept:
            return FeeEntry.objects.none()

        dept_id = getattr(add_dept, "id", None)
        if dept_id in dept_fee_cache:
            return dept_fee_cache[dept_id]

        qs = FeeEntry.objects.select_related("fee_category", "degree")
        out = FeeEntry.objects.none()

        # try FK
        try:
            q1 = qs.filter(department=add_dept)
            if q1.exists():
                out = q1
        except Exception:
            pass

        # try id
        if out is None or out.count() == 0:
            if dept_id is not None:
                try:
                    q2 = qs.filter(department_id=dept_id)
                    if q2.exists():
                        out = q2
                except Exception:
                    pass

        dept_fee_cache[dept_id] = out
        return out

    def select_fee_qs(add_dept, quota, mode_str):
        mode_lc = safe_str(mode_str).lower()
        selected_keyword = "Mess" if "transport" in mode_lc else "Hostel"
        base_qs = feeentry_for_department(add_dept)

        if quota:
            q_quota = base_qs.filter(quota__iexact=quota)
            if q_quota.exists():
                base_qs = q_quota

        special_qs = base_qs.filter(fee_category__name__icontains=selected_keyword)
        tuition_qs = base_qs.filter(fee_category__name__icontains="Tuition")
        common_qs = (
            base_qs.exclude(fee_category__name__icontains="Mess")
                   .exclude(fee_category__name__icontains="Hostel")
                   .exclude(fee_category__name__icontains="Tuition")
        )
        return (special_qs | tuition_qs | common_qs).distinct()

    def transport_amount(mode_str, bus_stop):
        if "transport" not in safe_str(mode_str).lower():
            return Decimal("0.00")

        raw = safe_str(bus_stop)
        if not raw:
            return Decimal("0.00")

        if raw in transport_cache:
            return transport_cache[raw]

        t_fee = TransportFee.objects.filter(bus_stop__iexact=raw).first()
        if not t_fee:
            transport_cache[raw] = Decimal("0.00")
            return transport_cache[raw]

        try:
            transport_cache[raw] = Decimal(str(t_fee.amount_per_year or 0))
        except Exception:
            transport_cache[raw] = Decimal("0.00")
        return transport_cache[raw]

    def paid_pending(student, sem_pair, total_current_year):
        paid_total = (
            ManualFeeEntry.objects.filter(
                fee_receipt__student=student,
                fee_receipt__semester__in=sem_pair
            )
            .aggregate(total_paid=Sum("entered_fee"))
            .get("total_paid")
            or Decimal("0.00")
        )

        pending_total = total_current_year - paid_total
        if pending_total < 0:
            pending_total = Decimal("0.00")
        return paid_total, pending_total

    def compute_student_fee_row(st, force_dept=None):
        admission, quota, mode_str, bus_stop = get_admission(st)
        add_dept = map_department(st, admission, force_dept=force_dept)

        yi = year_index_from_sem(st)
        sem_pair = sem_pair_for_year(yi)

        total_current_year = Decimal("0.00")
        if add_dept:
            fee_qs = select_fee_qs(add_dept, quota, mode_str)
            for entry in fee_qs:
                total_current_year += Decimal(str(getattr(entry, f"year_{yi}", 0) or 0))

        total_current_year += transport_amount(mode_str, bus_stop)
        paid_total, pending_total = paid_pending(st, sem_pair, total_current_year)

        return {
            "student": st,
            "department": add_dept,
            "year_index": yi,
            "section": safe_str(getattr(st, "section", "")) or "Unassigned",
            "total_current_year": total_current_year,
            "paid_total": paid_total,
            "pending_total": pending_total,
        }

    def make_empty_bucket():
        return {"total": Decimal("0.00"), "paid": Decimal("0.00"), "pending": Decimal("0.00"), "count": 0}

    def add_to_bucket(bucket, r):
        bucket["total"] += r["total_current_year"]
        bucket["paid"] += r["paid_total"]
        bucket["pending"] += r["pending_total"]
        bucket["count"] += 1

    def make_empty_year_summary():
        return {1: make_empty_bucket(), 2: make_empty_bucket(), 3: make_empty_bucket(), 4: make_empty_bucket()}

    def build_summaries(rows):
        overall = make_empty_bucket()
        year_wise = make_empty_year_summary()
        section_wise = OrderedDict()
        year_section_wise = OrderedDict()
        dept_wise = OrderedDict()
        dept_year_wise = OrderedDict()

        def dept_label(d):
            if not d:
                return "Unknown"
            code = safe_str(getattr(d, "Department_code", ""))
            nm = safe_str(getattr(d, "Department", ""))
            return f"{nm}{(' ('+code+')') if code else ''}".strip() or "Unknown"

        for r in rows:
            dept = r["department"]
            dept_key = str(getattr(dept, "id", "UNKNOWN") or "UNKNOWN")
            yi = int(r["year_index"] or 1)
            sec = r.get("section") or "Unassigned"

            add_to_bucket(overall, r)
            add_to_bucket(year_wise[yi], r)

            if sec not in section_wise:
                section_wise[sec] = make_empty_bucket()
            add_to_bucket(section_wise[sec], r)

            if yi not in year_section_wise:
                year_section_wise[yi] = OrderedDict()
            if sec not in year_section_wise[yi]:
                year_section_wise[yi][sec] = make_empty_bucket()
            add_to_bucket(year_section_wise[yi][sec], r)

            if dept_key not in dept_wise:
                dept_wise[dept_key] = {"label": dept_label(dept), **make_empty_bucket()}
            add_to_bucket(dept_wise[dept_key], r)

            if dept_key not in dept_year_wise:
                dept_year_wise[dept_key] = {"label": dept_label(dept), "years": make_empty_year_summary()}
            add_to_bucket(dept_year_wise[dept_key]["years"][yi], r)

        section_wise = OrderedDict(sorted(section_wise.items(), key=lambda kv: (kv[0] == "Unassigned", kv[0])))
        year_section_wise = OrderedDict(sorted(year_section_wise.items(), key=lambda kv: kv[0]))
        for yi in year_section_wise:
            year_section_wise[yi] = OrderedDict(
                sorted(year_section_wise[yi].items(), key=lambda kv: (kv[0] == "Unassigned", kv[0]))
            )

        return overall, year_wise, dept_wise, dept_year_wise, section_wise, year_section_wise

    # ----------------------------
    # Mode: page access itself is already gated by @check_permission("fee_view").
    # "Global user" access (Create Global Users) decides all-college vs department scope.
    # ----------------------------
    faculty, hod_dept = resolve_faculty_and_hod_dept(request.user)

    if _is_global_fee_user(request.user):
        mode = "principal"
    else:
        mode = "hod" if (is_hod_user(request.user) or hod_dept) else ("faculty" if faculty else "hod")

    # ----------------------------
    # Modal subviews (AJAX) - still inside fee_view (sub-view)
    # ----------------------------
    if request.GET.get("modal") and request.headers.get("X-Requested-With") == "XMLHttpRequest":
        modal = safe_str(request.GET.get("modal"))
        sid = safe_str(request.GET.get("student_id"))
        st = StudentDetails.objects.filter(id=sid).first()
        if not st:
            return HttpResponse("<div class='p-3 text-danger fw-bold'>Student not found.</div>")

        MODAL_TEMPLATE = {
            "fee_entry_view": "student_management/fee/fee_entry_view.html",
            "fee_receipt_view": "student_management/fee/fee_receipt_view.html",
        }
        tpl = MODAL_TEMPLATE.get(modal)
        if not tpl:
            return HttpResponse("<div class='p-3 text-danger fw-bold'>Invalid modal.</div>")

        html = render_to_string(tpl, {"student": st}, request=request)
        return HttpResponse(html)

    # ----------------------------
    # Filters (used only to set dropdowns + defaults; list itself comes from API)
    # ----------------------------
    selected_degree_id = safe_str(request.GET.get("degree"))
    selected_dept_id = safe_str(request.GET.get("department"))
    selected_year = safe_str(request.GET.get("year"))
    selected_section = safe_str(request.GET.get("section"))
    q = safe_str(request.GET.get("q"))

    # section options
    sm_sections = list(
        SectionMaster.objects.exclude(section__isnull=True).exclude(section__exact="")
        .values_list("section", flat=True).order_by("section")
    )
    stu_sections = list(
        StudentDetails.objects.exclude(section__isnull=True).exclude(section__exact="")
        .values_list("section", flat=True).distinct()
    )
    section_options = sorted(set(sm_sections) | set(stu_sections))

    # degree dropdown (principal only)
    degree_options = []
    if mode == "principal":
        for d in Degree.objects.filter(is_active=True).order_by("degree"):
            degree_options.append({
                "id": str(d.id),
                "code": safe_str(getattr(d, "degree_code", "")),
                "label": safe_str(getattr(d, "degree", "")) or str(d),
            })

    # dept dropdown depends on selected degree (principal)
    if mode == "principal" and selected_degree_id:
        dept_options = Add_Department.objects.filter(is_active=True, degree_id=selected_degree_id).order_by("Department")
    else:
        dept_options = Add_Department.objects.filter(is_active=True).order_by("Department")

    # ------------------------------------------------------------
    # Summary is loaded client-side via the api_fee_summary AJAX call
    # (see loadSummary() in fee_view.html) instead of being computed here.
    # Computing it synchronously on every page load was the main reason the
    # page felt slow (it iterated every matching student with several DB
    # queries each, then threw the result away the moment the same data
    # loaded again over AJAX). The initial context below just gives the
    # template zeroed placeholders so it renders instantly.
    # ------------------------------------------------------------
    overall_summary = make_empty_bucket()
    year_wise_summary = make_empty_year_summary()
    dept_wise_summary = OrderedDict()
    dept_year_wise_summary = OrderedDict()
    section_wise_summary = OrderedDict()
    year_section_wise_summary = OrderedDict()

    context = {
        "mode": mode,
        "faculty": faculty,
        "hod_dept": hod_dept,

        "degree_options": degree_options,
        "dept_options": dept_options,
        "section_options": section_options,

        "selected_degree_id": selected_degree_id,
        "selected_dept_id": selected_dept_id,
        "selected_year": selected_year,
        "selected_section": selected_section,
        "q": q,

        "overall_summary": overall_summary,
        "year_wise_summary": year_wise_summary,
        "dept_wise_summary": dept_wise_summary,
        "dept_year_wise_summary": dept_year_wise_summary,
        "section_wise_summary": section_wise_summary,
        "year_section_wise_summary": year_section_wise_summary,
    }
    return render(request, TEMPLATE, context)



def api_degree_departments(request):
    degree_id = (request.GET.get("degree") or "").strip()

    qs = Add_Department.objects.filter(is_active=True)
    if degree_id:
        qs = qs.filter(degree_id=degree_id)

    qs = qs.order_by("Department")

    data = {
        "ok": True,
        "departments": [
            {
                "id": str(d.id),
                "Department": d.Department or "",
                "Department_code": d.Department_code or "",
            }
            for d in qs
        ]
    }
    return JsonResponse(data)



@check_permission("fee_view")
def api_fee_summary(request):
    # reuse same core helper logic as in fee_view
    def safe_str(v):
        if v is None:
            return ""
        if isinstance(v, str):
            return v.strip()
        return str(v).strip()

    def _role_to_text(role_value) -> str:
        if role_value is None:
            return ""
        if isinstance(role_value, str):
            return role_value.strip().lower()
        if hasattr(role_value, "role"):
            vv = getattr(role_value, "role", None)
            if isinstance(vv, str) and vv.strip():
                return vv.strip().lower()
        try:
            return str(role_value).strip().lower()
        except Exception:
            return ""

    def get_user_role_id(user):
        v = getattr(user, "role", None)
        if v is not None and hasattr(v, "id"):
            try:
                return int(v.id)
            except Exception:
                pass
        return None

    def get_user_role_text(user) -> str:
        return _role_to_text(getattr(user, "role", None))

    def is_hod_user(user) -> bool:
        rt = get_user_role_text(user)
        return (rt == "hod") or rt.startswith("hod") or ("head of department" in rt)

    def resolve_faculty_and_hod_dept(user):
        fac_emp_id = getattr(user, "Employee_id", None)
        faculty = (
            general_information.objects
            .filter(faculty_id=fac_emp_id)
            .select_related("department")
            .first()
            if fac_emp_id else None
        )
        hod_dept = getattr(faculty, "department", None) if faculty else None
        return faculty, hod_dept

    def hod_students_queryset(hod_dept):
        if not hod_dept:
            return StudentDetails.objects.none()
        return StudentDetails.objects.filter(department_id=getattr(hod_dept, "id", None)).select_related("department").order_by("name")

    # Row computation (admission/transport/fee-entry/paid-total lookups) is
    # done in bulk by _compute_fee_rows_batched() below instead of per-student
    # queries — see the batched helpers defined above fee_view().

    def make_empty_bucket():
        return {"total": Decimal("0.00"), "paid": Decimal("0.00"), "pending": Decimal("0.00"), "count": 0}

    def add_to_bucket(bucket, r):
        bucket["total"] += r["total_current_year"]
        bucket["paid"] += r["paid_total"]
        bucket["pending"] += r["pending_total"]
        bucket["count"] += 1

    def make_empty_year_summary():
        return {1: make_empty_bucket(), 2: make_empty_bucket(), 3: make_empty_bucket(), 4: make_empty_bucket()}

    def build_summaries(rows):
        overall = make_empty_bucket()
        year_wise = make_empty_year_summary()
        section_wise = OrderedDict()
        year_section_wise = OrderedDict()
        dept_wise = OrderedDict()
        dept_year_wise = OrderedDict()

        def dept_label(d):
            if not d:
                return "Unknown"
            code = safe_str(getattr(d, "Department_code", ""))
            nm = safe_str(getattr(d, "Department", ""))
            return f"{nm}{(' ('+code+')') if code else ''}".strip() or "Unknown"

        for r in rows:
            dept = r["department"]
            dept_key = str(getattr(dept, "id", "UNKNOWN") or "UNKNOWN")
            yi = int(r["year_index"] or 1)
            sec = r.get("section") or "Unassigned"

            add_to_bucket(overall, r)
            add_to_bucket(year_wise[yi], r)

            if sec not in section_wise:
                section_wise[sec] = make_empty_bucket()
            add_to_bucket(section_wise[sec], r)

            if yi not in year_section_wise:
                year_section_wise[yi] = OrderedDict()
            if sec not in year_section_wise[yi]:
                year_section_wise[yi][sec] = make_empty_bucket()
            add_to_bucket(year_section_wise[yi][sec], r)

            if dept_key not in dept_wise:
                dept_wise[dept_key] = {"label": dept_label(dept), **make_empty_bucket()}
            add_to_bucket(dept_wise[dept_key], r)

            if dept_key not in dept_year_wise:
                dept_year_wise[dept_key] = {"label": dept_label(dept), "years": make_empty_year_summary()}
            add_to_bucket(dept_year_wise[dept_key]["years"][yi], r)

        section_wise = OrderedDict(sorted(section_wise.items(), key=lambda kv: (kv[0] == "Unassigned", kv[0])))
        year_section_wise = OrderedDict(sorted(year_section_wise.items(), key=lambda kv: kv[0]))
        for yi in year_section_wise:
            year_section_wise[yi] = OrderedDict(
                sorted(year_section_wise[yi].items(), key=lambda kv: (kv[0] == "Unassigned", kv[0]))
            )

        return overall, year_wise, dept_wise, dept_year_wise, section_wise, year_section_wise

    # ----------------------------
    # Permissions + mode (same gate as fee_view)
    # ----------------------------
    faculty, hod_dept = resolve_faculty_and_hod_dept(request.user)
    if _is_global_fee_user(request.user):
        mode = "principal"
    else:
        mode = "hod" if (is_hod_user(request.user) or hod_dept) else ("faculty" if faculty else "hod")

    # ---- filters (shared) ----
    degree_id = safe_str(request.GET.get("degree"))
    dept_id = safe_str(request.GET.get("department"))
    year_param = safe_str(request.GET.get("year"))
    section = safe_str(request.GET.get("section"))
    q = safe_str(request.GET.get("q"))
    scope = safe_str(request.GET.get("scope")).lower()

    sem_map = {1: ["1", "2", 1, 2], 2: ["3", "4", 3, 4], 3: ["5", "6", 5, 6], 4: ["7", "8", 7, 8]}

    if mode == "hod":
        qs = hod_students_queryset(hod_dept)
        if section:
            qs = qs.filter(section=section)
        if year_param.isdigit():
            yi = max(1, min(4, int(year_param)))
            qs = qs.filter(semester__in=sem_map[yi])
        if q:
            qs = qs.filter(Q(reg_no__icontains=q) | Q(name__icontains=q) | Q(section__icontains=q))

        rows = _compute_fee_rows_batched(qs, force_dept=hod_dept)
        overall, year_wise, dept_wise, dept_year_wise, section_wise, year_section_wise = build_summaries(rows)

        def money(x):
            try:
                return f"{Decimal(x):.2f}"
            except Exception:
                return safe_str(x)

        out = {
            "ok": True,
            "mode": mode,
            "overall_summary": {
                "count": overall["count"], "total": money(overall["total"]),
                "paid": money(overall["paid"]), "pending": money(overall["pending"]),
            },
            "year_wise_summary": {
                str(k): {
                    "count": v["count"], "total": money(v["total"]),
                    "paid": money(v["paid"]), "pending": money(v["pending"]),
                } for k, v in year_wise.items()
            },
            "section_wise_summary": {
                str(k): {
                    "count": v["count"], "total": money(v["total"]),
                    "paid": money(v["paid"]), "pending": money(v["pending"]),
                } for k, v in section_wise.items()
            },
            "year_section_wise_summary": {
                str(y): {
                    str(sec): {
                        "count": vv["count"], "total": money(vv["total"]),
                        "paid": money(vv["paid"]), "pending": money(vv["pending"]),
                    } for sec, vv in secs.items()
                } for y, secs in year_section_wise.items()
            },
        }
        return JsonResponse(out)

    if mode == "faculty":
        if not faculty:
            return JsonResponse({"ok": False, "error": "Faculty profile not found"}, status=404)
        if scope == "ca":
            qs = StudentDetails.objects.filter(ca=faculty).select_related("department").order_by("name")
        else:
            qs = StudentDetails.objects.filter(mentor=faculty).select_related("department").order_by("name")
        if q:
            qs = qs.filter(Q(reg_no__icontains=q) | Q(name__icontains=q) | Q(section__icontains=q))

        rows = _compute_fee_rows_batched(qs)
        overall, year_wise, dept_wise, dept_year_wise, section_wise, year_section_wise = build_summaries(rows)

        def money(x):
            try:
                return f"{Decimal(x):.2f}"
            except Exception:
                return safe_str(x)

        out = {
            "ok": True,
            "mode": mode,
            "overall_summary": {
                "count": overall["count"], "total": money(overall["total"]),
                "paid": money(overall["paid"]), "pending": money(overall["pending"]),
            },
            "year_wise_summary": {
                str(k): {
                    "count": v["count"], "total": money(v["total"]),
                    "paid": money(v["paid"]), "pending": money(v["pending"]),
                } for k, v in year_wise.items()
            },
            "section_wise_summary": {
                str(k): {
                    "count": v["count"], "total": money(v["total"]),
                    "paid": money(v["paid"]), "pending": money(v["pending"]),
                } for k, v in section_wise.items()
            },
        }
        return JsonResponse(out)

    # ---- principal filters ----
    qs = StudentDetails.objects.all().select_related("department").order_by("name")

    has_any_filter = bool(degree_id or dept_id or year_param or section or q)

    if has_any_filter:
        if degree_id:
            qs = qs.filter(department__degree_id=degree_id)
        if dept_id:
            qs = qs.filter(department_id=dept_id)
        if section:
            qs = qs.filter(section=section)
        if year_param.isdigit():
            yi = max(1, min(4, int(year_param)))
            sem_map = {1: ["1", "2", 1, 2], 2: ["3", "4", 3, 4], 3: ["5", "6", 5, 6], 4: ["7", "8", 7, 8]}
            qs = qs.filter(semester__in=sem_map[yi])
        if q:
            qs = qs.filter(Q(reg_no__icontains=q) | Q(name__icontains=q) | Q(section__icontains=q))

    rows = _compute_fee_rows_batched(qs)
    overall, year_wise, dept_wise, dept_year_wise, section_wise, year_section_wise = build_summaries(rows)

    def money(x):
        try:
            return f"{Decimal(x):.2f}"
        except Exception:
            return safe_str(x)

    # JSON serializable conversion
    out = {
        "ok": True,
        "mode": mode,
        "overall_summary": {
            "count": overall["count"],
            "total": money(overall["total"]),
            "paid": money(overall["paid"]),
            "pending": money(overall["pending"]),
        },
        "year_wise_summary": {
            str(k): {
                "count": v["count"],
                "total": money(v["total"]),
                "paid": money(v["paid"]),
                "pending": money(v["pending"]),
            } for k, v in year_wise.items()
        },
        "section_wise_summary": {
            str(k): {
                "count": v["count"],
                "total": money(v["total"]),
                "paid": money(v["paid"]),
                "pending": money(v["pending"]),
            } for k, v in section_wise.items()
        },
        "dept_wise_summary": {
            str(k): {
                "label": v["label"],
                "count": v["count"],
                "total": money(v["total"]),
                "paid": money(v["paid"]),
                "pending": money(v["pending"]),
            } for k, v in dept_wise.items()
        },
        "dept_year_wise_summary": {
            str(k): {
                "label": v["label"],
                "years": {
                    str(y): {
                        "count": yy["count"],
                        "total": money(yy["total"]),
                        "paid": money(yy["paid"]),
                        "pending": money(yy["pending"]),
                    } for y, yy in v["years"].items()
                }
            } for k, v in dept_year_wise.items()
        },
        "year_section_wise_summary": {
            str(y): {
                str(sec): {
                    "count": vv["count"],
                    "total": money(vv["total"]),
                    "paid": money(vv["paid"]),
                    "pending": money(vv["pending"]),
                } for sec, vv in secs.items()
            } for y, secs in year_section_wise.items()
        },
    }
    return JsonResponse(out)



@check_permission("fee_view")
def api_fee_students(request):
    def safe_str(v):
        if v is None:
            return ""
        if isinstance(v, str):
            return v.strip()
        return str(v).strip()

    def _role_to_text(role_value) -> str:
        if role_value is None:
            return ""
        if isinstance(role_value, str):
            return role_value.strip().lower()
        if hasattr(role_value, "role"):
            vv = getattr(role_value, "role", None)
            if isinstance(vv, str) and vv.strip():
                return vv.strip().lower()
        try:
            return str(role_value).strip().lower()
        except Exception:
            return ""

    def get_user_role_id(user):
        v = getattr(user, "role", None)
        if v is not None and hasattr(v, "id"):
            try:
                return int(v.id)
            except Exception:
                pass
        return None

    def get_user_role_text(user) -> str:
        return _role_to_text(getattr(user, "role", None))

    def is_hod_user(user) -> bool:
        rt = get_user_role_text(user)
        return (rt == "hod") or rt.startswith("hod") or ("head of department" in rt)

    def resolve_faculty_and_hod_dept(user):
        fac_emp_id = getattr(user, "Employee_id", None)
        faculty = (
            general_information.objects
            .filter(faculty_id=fac_emp_id)
            .select_related("department")
            .first()
            if fac_emp_id else None
        )
        hod_dept = getattr(faculty, "department", None) if faculty else None
        return faculty, hod_dept

    def hod_students_queryset(hod_dept):
        if not hod_dept:
            return StudentDetails.objects.none()
        return StudentDetails.objects.filter(department_id=getattr(hod_dept, "id", None)).select_related("department").order_by("name")

    def year_index_from_sem(student):
        sem_raw = safe_str(getattr(student, "semester", ""))
        try:
            sem_i = int(sem_raw)
            yi = (sem_i + 1) // 2 if sem_i > 0 else 1
        except Exception:
            yi = 1
        return min(max(yi, 1), 4)

    def sem_pair_for_year(yi):
        return {1: [1, 2], 2: [3, 4], 3: [5, 6], 4: [7, 8]}.get(yi, [1, 2])

    # Row computation is done in bulk by _compute_fee_rows_batched() below
    # instead of per-student queries — see the batched helpers above fee_view().

    # ----------------------------
    # mode permission
    # ----------------------------
    faculty, hod_dept = resolve_faculty_and_hod_dept(request.user)
    if _is_global_fee_user(request.user):
        mode = "principal"
    else:
        mode = "hod" if (is_hod_user(request.user) or hod_dept) else ("faculty" if faculty else "hod")

    # ----------------------------
    # filters
    # ----------------------------
    degree_id = safe_str(request.GET.get("degree"))
    dept_id = safe_str(request.GET.get("department"))
    year_param = safe_str(request.GET.get("year"))
    section = safe_str(request.GET.get("section"))
    q = safe_str(request.GET.get("q"))
    scope = safe_str(request.GET.get("scope")).lower()  # faculty only: mentor/ca

    page = int(safe_str(request.GET.get("page") or "1") or 1)
    page_size = int(safe_str(request.GET.get("page_size") or "50") or 50)
    page_size = max(1, min(200, page_size))

    sem_map = {1: ["1", "2", 1, 2], 2: ["3", "4", 3, 4], 3: ["5", "6", 5, 6], 4: ["7", "8", 7, 8]}

    # principal requires at least one filter to show students
    filter_applied = True
    if mode == "principal":
        filter_applied = bool(degree_id or dept_id or year_param or section or q)

    # base queryset per mode
    if mode == "principal":
        qs = StudentDetails.objects.all().select_related("department").order_by("name")
        if filter_applied:
            if degree_id:
                qs = qs.filter(department__degree_id=degree_id)
            if dept_id:
                qs = qs.filter(department_id=dept_id)
            if section:
                qs = qs.filter(section=section)
            if year_param.isdigit():
                yi = max(1, min(4, int(year_param)))
                qs = qs.filter(semester__in=sem_map[yi])
            if q:
                qs = qs.filter(Q(reg_no__icontains=q) | Q(name__icontains=q) | Q(section__icontains=q))
        else:
            qs = StudentDetails.objects.none()

    elif mode == "hod":
        qs = hod_students_queryset(hod_dept)
        if section:
            qs = qs.filter(section=section)
        if year_param.isdigit():
            yi = max(1, min(4, int(year_param)))
            qs = qs.filter(semester__in=sem_map[yi])
        if q:
            qs = qs.filter(Q(reg_no__icontains=q) | Q(name__icontains=q) | Q(section__icontains=q))
        filter_applied = True

    else:  # faculty
        if not faculty:
            return JsonResponse({"ok": False, "error": "Faculty profile not found"}, status=404)

        if scope == "ca":
            qs = StudentDetails.objects.filter(ca=faculty).select_related("department").order_by("name")
        else:
            qs = StudentDetails.objects.filter(mentor=faculty).select_related("department").order_by("name")

        if q:
            qs = qs.filter(Q(reg_no__icontains=q) | Q(name__icontains=q) | Q(section__icontains=q))
        filter_applied = True

    # pagination
    paginator = Paginator(qs, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # compute rows for this page (batched: a handful of queries regardless of page size)
    results = []
    total_sum = Decimal("0.00")
    paid_sum = Decimal("0.00")
    pending_sum = Decimal("0.00")

    force_dept = hod_dept if mode == "hod" else None

    for r in _compute_fee_rows_batched(page_obj.object_list, force_dept=force_dept):
        total_sum += r["total_current_year"]
        paid_sum += r["paid_total"]
        pending_sum += r["pending_total"]
        st = r["student"]
        dept = r["department"]
        results.append({
            "student_id": st.id,
            "reg_no": safe_str(getattr(st, "reg_no", "")),
            "name": safe_str(getattr(st, "name", "")),
            "section": safe_str(getattr(st, "section", "")) or "-",
            "year_index": r["year_index"],
            "department": safe_str(getattr(dept, "Department", "")) if dept else "-",
            "total_current_year": f"{r['total_current_year']:.2f}",
            "paid_total": f"{r['paid_total']:.2f}",
            "pending_total": f"{r['pending_total']:.2f}",
        })

    return JsonResponse({
        "ok": True,
        "mode": mode,
        "filter_applied": filter_applied,
        "count": paginator.count,
        "page": page_obj.number,
        "num_pages": paginator.num_pages,
        "page_size": page_size,
        "results": results,
        "totals": {
            "total": f"{total_sum:.2f}",
            "paid": f"{paid_sum:.2f}",
            "pending": f"{pending_sum:.2f}",
        }
    })


@check_permission("fee_view")
def download_fee_summary_pdf(request):
    def safe_str(v):
        if v is None:
            return ""
        if isinstance(v, str):
            return v.strip()
        return str(v).strip()

    def _role_to_text(role_value) -> str:
        if role_value is None:
            return ""
        if isinstance(role_value, str):
            return role_value.strip().lower()
        if hasattr(role_value, "role"):
            vv = getattr(role_value, "role", None)
            if isinstance(vv, str) and vv.strip():
                return vv.strip().lower()
        try:
            return str(role_value).strip().lower()
        except Exception:
            return ""

    def get_user_role_id(user):
        for attr in ("role_id", "Role_id", "role", "Role"):
            v = getattr(user, attr, None)
            if v is None:
                continue
            if hasattr(v, "id"):
                try:
                    return int(v.id)
                except Exception:
                    pass
            try:
                return int(str(v).strip())
            except Exception:
                continue
        return None

    def get_user_role_text(user) -> str:
        for attr in ("role", "Role", "role_id", "Role_id"):
            if hasattr(user, attr):
                txt = _role_to_text(getattr(user, attr, None))
                if txt:
                    return txt
        return ""

    def is_hod_user(user) -> bool:
        rt = get_user_role_text(user)
        if not rt:
            return False
        return (rt == "hod") or rt.startswith("hod") or ("head of department" in rt)

    def resolve_faculty_and_hod_dept(user):
        fac_emp_id = getattr(user, "Employee_id", None)
        faculty = general_information.objects.filter(faculty_id=fac_emp_id).select_related("department").first() if fac_emp_id else None

        hod_dept = None
        if faculty and getattr(faculty, "department", None):
            hod_dept = faculty.department

        if not hod_dept:
            user_email = getattr(user, "email", None)
            if user_email:
                fac_by_email = general_information.objects.filter(
                    Q(college_email__iexact=user_email) | Q(personal_email__iexact=user_email)
                ).select_related("department").first()
                if fac_by_email and getattr(fac_by_email, "department", None):
                    faculty = faculty or fac_by_email
                    hod_dept = fac_by_email.department

        return faculty, hod_dept

    def hod_students_queryset(hod_dept):
        if not hod_dept:
            return StudentDetails.objects.none()
        qs = StudentDetails.objects.all().select_related("department", "department__degree")

        dept_id = getattr(hod_dept, "id", None)
        dept_code = safe_str(getattr(hod_dept, "Department_code", ""))
        dept_name = safe_str(getattr(hod_dept, "Department", ""))
        dept_label = safe_str(getattr(hod_dept, "department_label", ""))

        cond = Q()
        try:
            cond |= Q(department=hod_dept)
        except Exception:
            pass
        if dept_id is not None:
            cond |= Q(department_id=dept_id)
        if dept_code:
            cond |= Q(department__Department_code__iexact=dept_code)
        if dept_name:
            cond |= Q(department__Department__iexact=dept_name)
        if dept_label:
            cond |= Q(department__department_label__iexact=dept_label)

        return qs.filter(cond).distinct().order_by("name")

    # fee compute helpers
    def year_index_from_sem(student):
        sem_raw = safe_str(getattr(student, "semester", ""))
        try:
            sem_i = int(sem_raw)
            yi = (sem_i + 1) // 2 if sem_i > 0 else 1
        except Exception:
            yi = 1
        return min(max(yi, 1), 4)

    def sem_pair_for_year(yi):
        return {1: [1, 2], 2: [3, 4], 3: [5, 6], 4: [7, 8]}.get(yi, [1, 2])

    def get_admission(student):
        aadhar = safe_str(getattr(student, "aadhar_number", ""))
        personal = None
        admission = None
        bus_stop = ""
        if aadhar:
            personal = PersonalDetails.objects.using("admissionform1").filter(Aadhaar_Number=aadhar).first()
            if personal:
                admission = AdmissionRecords.objects.using("admissionform1").filter(PersonalDetailsId=personal).first()
                transport = TransportDetails.objects.using("admissionform1").filter(
                    admission_records_id=personal
                ).only("bus_stop").first()
                bus_stop = safe_str(getattr(transport, "bus_stop", "")) if transport else ""
        quota = safe_str(getattr(admission, "Quota", "")) if admission else ""
        mode_str = safe_str(getattr(admission, "Mode", "")) if admission else ""
        return admission, quota, mode_str, bus_stop

    def map_department(student, admission, force_dept=None):
        if force_dept:
            return force_dept
        if getattr(student, "department", None):
            return student.department
        dept_name = safe_str(getattr(admission, "Department", "")) if admission else ""
        add_dept = None
        if dept_name:
            add_dept = (
                Add_Department.objects.filter(Department__iexact=dept_name).first()
                or Add_Department.objects.filter(department_label__iexact=dept_name).first()
                or Add_Department.objects.filter(degree_department__icontains=dept_name).first()
                or Add_Department.objects.filter(degree_department_label__icontains=dept_name).first()
            )
        return add_dept

    def feeentry_for_department(add_dept):
        qs = FeeEntry.objects.select_related("fee_category", "degree")
        if not add_dept:
            return FeeEntry.objects.none()
        try:
            q1 = qs.filter(department=add_dept)
            if q1.exists():
                return q1
        except Exception:
            pass
        dept_id = getattr(add_dept, "id", None)
        if dept_id is not None:
            try:
                q2 = qs.filter(department_id=dept_id)
                if q2.exists():
                    return q2
            except Exception:
                pass
        return FeeEntry.objects.none()

    def select_fee_qs(add_dept, quota, mode_str):
        mode_lc = safe_str(mode_str).lower()
        selected_keyword = "Mess" if "transport" in mode_lc else "Hostel"
        base_qs = feeentry_for_department(add_dept)
        if quota:
            q_quota = base_qs.filter(quota__iexact=quota)
            if q_quota.exists():
                base_qs = q_quota
        special_qs = base_qs.filter(fee_category__name__icontains=selected_keyword)
        tuition_qs = base_qs.filter(fee_category__name__icontains="Tuition")
        common_qs = base_qs.exclude(fee_category__name__icontains="Mess") \
                          .exclude(fee_category__name__icontains="Hostel") \
                          .exclude(fee_category__name__icontains="Tuition")
        return (special_qs | tuition_qs | common_qs).distinct()

    def transport_amount(mode_str, bus_stop):
        if "transport" not in safe_str(mode_str).lower():
            return Decimal("0.00")
        raw = safe_str(bus_stop)
        if not raw:
            return Decimal("0.00")
        t_fee = TransportFee.objects.filter(bus_stop__iexact=raw).first()
        if not t_fee:
            return Decimal("0.00")
        try:
            return Decimal(str(t_fee.amount_per_year or 0))
        except Exception:
            return Decimal("0.00")

    def paid_pending(student, sem_pair, total_current_year):
        paid_total = ManualFeeEntry.objects.filter(
            fee_receipt__student=student,
            fee_receipt__semester__in=sem_pair
        ).aggregate(total_paid=Sum("entered_fee")).get("total_paid") or Decimal("0.00")
        pending_total = total_current_year - paid_total
        if pending_total < 0:
            pending_total = Decimal("0.00")
        return paid_total, pending_total

    def compute_student_fee_row(st, force_dept=None):
        admission, quota, mode_str, bus_stop = get_admission(st)
        add_dept = map_department(st, admission, force_dept=force_dept)

        yi = year_index_from_sem(st)
        sem_pair = sem_pair_for_year(yi)

        total_current_year = Decimal("0.00")
        if add_dept:
            fee_qs = select_fee_qs(add_dept, quota, mode_str)
            for entry in fee_qs:
                total_current_year += Decimal(str(getattr(entry, f"year_{yi}", 0) or 0))
        total_current_year += transport_amount(mode_str, bus_stop)

        paid_total, pending_total = paid_pending(st, sem_pair, total_current_year)

        return {
            "student": st,
            "department": add_dept,
            "year_index": yi,
            "total_current_year": total_current_year,
            "paid_total": paid_total,
            "pending_total": pending_total,
        }

    def make_empty_year_summary():
        return {
            1: {"total": Decimal("0.00"), "paid": Decimal("0.00"), "pending": Decimal("0.00"), "count": 0},
            2: {"total": Decimal("0.00"), "paid": Decimal("0.00"), "pending": Decimal("0.00"), "count": 0},
            3: {"total": Decimal("0.00"), "paid": Decimal("0.00"), "pending": Decimal("0.00"), "count": 0},
            4: {"total": Decimal("0.00"), "paid": Decimal("0.00"), "pending": Decimal("0.00"), "count": 0},
        }

    def build_summaries(rows):
        overall = {"total": Decimal("0.00"), "paid": Decimal("0.00"), "pending": Decimal("0.00"), "count": 0}
        year_wise = make_empty_year_summary()
        dept_wise = OrderedDict()
        dept_year_wise = OrderedDict()

        def dept_label(d):
            if not d:
                return "Unknown"
            code = safe_str(getattr(d, "Department_code", ""))
            nm = safe_str(getattr(d, "Department", ""))
            return f"{nm}{(' ('+code+')') if code else ''}".strip() or "Unknown"

        for r in rows:
            dept = r["department"]
            dept_key = str(getattr(dept, "id", "UNKNOWN") or "UNKNOWN")
            yi = int(r["year_index"] or 1)

            overall["total"] += r["total_current_year"]
            overall["paid"] += r["paid_total"]
            overall["pending"] += r["pending_total"]
            overall["count"] += 1

            year_wise[yi]["total"] += r["total_current_year"]
            year_wise[yi]["paid"] += r["paid_total"]
            year_wise[yi]["pending"] += r["pending_total"]
            year_wise[yi]["count"] += 1

            if dept_key not in dept_wise:
                dept_wise[dept_key] = {"label": dept_label(dept), "total": Decimal("0.00"), "paid": Decimal("0.00"), "pending": Decimal("0.00"), "count": 0}
            dept_wise[dept_key]["total"] += r["total_current_year"]
            dept_wise[dept_key]["paid"] += r["paid_total"]
            dept_wise[dept_key]["pending"] += r["pending_total"]
            dept_wise[dept_key]["count"] += 1

            if dept_key not in dept_year_wise:
                dept_year_wise[dept_key] = {"label": dept_label(dept), "years": make_empty_year_summary()}
            dept_year_wise[dept_key]["years"][yi]["total"] += r["total_current_year"]
            dept_year_wise[dept_key]["years"][yi]["paid"] += r["paid_total"]
            dept_year_wise[dept_key]["years"][yi]["pending"] += r["pending_total"]
            dept_year_wise[dept_key]["years"][yi]["count"] += r["year_index"] and 1 or 0

        return overall, year_wise, dept_wise, dept_year_wise

    def group_principal_dept_year(rows):
        grouped = OrderedDict()
        for r in rows:
            dept = r["department"]
            dept_name = safe_str(getattr(dept, "Department", "")) or "Unknown"
            yi = int(r["year_index"] or 1)
            grouped.setdefault(dept_name, {1: [], 2: [], 3: [], 4: []})
            grouped[dept_name][yi].append(r)
        for d in grouped:
            for yi in (1, 2, 3, 4):
                grouped[d][yi].sort(key=lambda x: safe_str(getattr(x["student"], "reg_no", "")))
        return grouped

    def group_by_year(rows):
        grouped = {1: [], 2: [], 3: [], 4: []}
        for r in rows:
            grouped[int(r["year_index"] or 1)].append(r)
        for yi in (1, 2, 3, 4):
            grouped[yi].sort(key=lambda x: safe_str(getattr(x["student"], "reg_no", "")))
        return grouped

    def apply_search(qs, q_param: str):
        q_param = safe_str(q_param)
        if not q_param:
            return qs
        return qs.filter(
            Q(name__icontains=q_param) |
            Q(reg_no__icontains=q_param) |
            Q(section__icontains=q_param)
        )

    # ----------------------------
    # Permissions / mode
    # ----------------------------
    faculty, hod_dept = resolve_faculty_and_hod_dept(request.user)

    if _is_global_fee_user(request.user):
        mode = "principal"
    else:
        mode = "hod" if is_hod_user(request.user) else ("faculty" if faculty else "hod")

    # filters
    degree_id_param = safe_str(request.GET.get("degree"))
    dept_id_param = safe_str(request.GET.get("department"))
    year_param = safe_str(request.GET.get("year"))
    section_param = safe_str(request.GET.get("section"))
    q_param = safe_str(request.GET.get("q"))
    scope = safe_str(request.GET.get("scope")).lower()  # mentor/ca

    sem_map = {1: ["1", "2", 1, 2], 2: ["3", "4", 3, 4], 3: ["5", "6", 5, 6], 4: ["7", "8", 7, 8]}

    filename = "Fee_Summary.pdf"
    report_title = "FEE SUMMARY REPORT"

    # ===========================
    # SELECT STUDENTS
    # ===========================
    if mode == "principal":
        qs = StudentDetails.objects.all().select_related("department", "department__degree").order_by("name")

        if safe_str(degree_id_param).isdigit():
            qs = qs.filter(department__degree_id=int(degree_id_param))
        if dept_id_param:
            qs = qs.filter(department_id=dept_id_param)
        if section_param:
            qs = qs.filter(section=section_param)
        if year_param.isdigit():
            yi = max(1, min(4, int(year_param)))
            qs = qs.filter(semester__in=sem_map[yi])

        qs = apply_search(qs, q_param)

        rows = [compute_student_fee_row(st) for st in qs]
        overall, year_wise, dept_wise, dept_year_wise = build_summaries(rows)
        grouped = group_principal_dept_year(rows)
        filename = "Fee_Summary_Principal.pdf"

    elif mode == "hod":
        qs = hod_students_queryset(hod_dept)

        if section_param:
            qs = qs.filter(section=section_param)
        if year_param.isdigit():
            yi = max(1, min(4, int(year_param)))
            qs = qs.filter(semester__in=sem_map[yi])

        qs = apply_search(qs, q_param)

        rows = [compute_student_fee_row(st, force_dept=hod_dept) for st in qs]
        overall = {
            "count": len(rows),
            "total": sum((r["total_current_year"] for r in rows), Decimal("0.00")),
            "paid": sum((r["paid_total"] for r in rows), Decimal("0.00")),
            "pending": sum((r["pending_total"] for r in rows), Decimal("0.00")),
        }
        grouped_year = group_by_year(rows)
        filename = "Fee_Summary_HOD.pdf"

    else:
        if not faculty:
            return HttpResponse("Faculty profile not found.", status=404)

        if scope == "ca":
            qs = StudentDetails.objects.filter(ca=faculty).select_related("department", "department__degree").order_by("name")
            filename = "Fee_Summary_Faculty_CA.pdf"
        else:
            qs = StudentDetails.objects.filter(mentor=faculty).select_related("department", "department__degree").order_by("name")
            filename = "Fee_Summary_Faculty_Mentor.pdf"

        qs = apply_search(qs, q_param)

        rows = [compute_student_fee_row(st) for st in qs]
        rows.sort(key=lambda x: safe_str(getattr(x["student"], "reg_no", "")))

    # ============================================================
    # PDF DESIGN (compact, good looking, same header/footer)
    # ============================================================
    styles = getSampleStyleSheet()

    PRIMARY_BLUE = colors.HexColor("#0f2f57")
    SECONDARY_BLUE = colors.HexColor("#1a4b8c")
    ACCENT_RED = colors.HexColor("#b91c1c")
    DARK_GRAY = colors.HexColor("#111827")
    MEDIUM_GRAY = colors.HexColor("#4b5563")
    LIGHT_GRAY = colors.HexColor("#9ca3af")
    BG_GRAY = colors.HexColor("#f8fafc")
    BORDER_GRAY = colors.HexColor("#e5e7eb")

    title_style = ParagraphStyle(
        "title_style", parent=styles["Heading1"],
        fontSize=14.5, textColor=PRIMARY_BLUE, alignment=TA_CENTER,
        spaceAfter=4, fontName="Helvetica-Bold", leading=16
    )
    sub_style = ParagraphStyle(
        "sub_style", parent=styles["Normal"],
        fontSize=9.2, textColor=MEDIUM_GRAY, alignment=TA_CENTER,
        spaceAfter=6
    )
    section_style = ParagraphStyle(
        "section_style", parent=styles["Heading2"],
        fontSize=11.2, textColor=PRIMARY_BLUE, alignment=TA_LEFT,
        spaceBefore=6, spaceAfter=4, fontName="Helvetica-Bold", leading=14
    )
    cell = ParagraphStyle(
        "cell", parent=styles["Normal"],
        fontSize=8.7, textColor=DARK_GRAY, alignment=TA_LEFT,
        leading=10.5, wordWrap="CJK"
    )
    cell_center = ParagraphStyle("cell_center", parent=cell, alignment=TA_CENTER)
    th = ParagraphStyle(
        "th", parent=styles["Normal"],
        fontSize=8.7, textColor=colors.white, alignment=TA_CENTER,
        fontName="Helvetica-Bold", leading=10.5
    )

    def money(x):
        try:
            return f"{Decimal(x):.2f}"
        except Exception:
            return safe_str(x)

    def create_table(data, col_widths, header_bg=SECONDARY_BLUE, zebra=True):
        t = Table(data, repeatRows=1, colWidths=col_widths)
        style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), header_bg),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8.7),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.45, BORDER_GRAY),
            ("FONTSIZE", (0, 1), (-1, -1), 8.7),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
        if zebra and len(data) > 1:
            style.add("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG_GRAY])
        t.setStyle(style)
        return t

    HEADER_HEIGHT = 36 * mm

    def draw_header_footer(canvas, doc_):
        canvas.saveState()
        page_w, page_h = A4
        left = doc_.leftMargin
        right = page_w - doc_.rightMargin
        center_x = (left + right) / 2
        top_y = page_h - 8 * mm

        logo_rel = "images/ritlogo.png"
        logo_path = finders.find(logo_rel)
        if not logo_path:
            static_root = getattr(settings, "STATIC_ROOT", "")
            if static_root:
                cand = os.path.join(static_root, logo_rel)
                if os.path.exists(cand):
                    logo_path = cand

        if logo_path and os.path.exists(logo_path):
            canvas.drawImage(
                ImageReader(logo_path),
                left, top_y - 20 * mm,
                width=30 * mm, height=18 * mm,
                preserveAspectRatio=True, mask="auto"
            )

        canvas.setFillColor(PRIMARY_BLUE)
        canvas.setFont("Helvetica-Bold", 14)
        canvas.drawCentredString(center_x, top_y - 6 * mm, "RAMCO INSTITUTE OF TECHNOLOGY")

        canvas.setFillColor(ACCENT_RED)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawCentredString(center_x, top_y - 13 * mm, "An Autonomous Institution")

        canvas.setFillColor(MEDIUM_GRAY)
        canvas.setFont("Helvetica", 8.2)
        canvas.drawCentredString(center_x, top_y - 18.5 * mm, "Approved by AICTE, New Delhi")
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(center_x, top_y - 23 * mm, "Accredited by NAAC & ISO 9001:2015 Certified Institution")
        canvas.drawCentredString(center_x, top_y - 27.5 * mm, "NBA Accredited UG Programs: CSE, EEE, ECE and MECH")

        footer_y = 18 * mm
        canvas.setStrokeColor(BORDER_GRAY)
        canvas.setLineWidth(0.8)
        canvas.line(left, footer_y + 7 * mm, right, footer_y + 7 * mm)

        canvas.setFillColor(LIGHT_GRAY)
        canvas.setFont("Helvetica", 8)
        gen_time = datetime.now().strftime("%d %b %Y, %I:%M %p")
        canvas.drawString(left, footer_y, f"Generated: {gen_time}")

        if mode == "principal":
            canvas.drawCentredString(center_x, footer_y, "Fee Summary - Principal")
        elif mode == "hod":
            canvas.drawCentredString(center_x, footer_y, f"Fee Summary - {safe_str(getattr(hod_dept,'Department','HOD'))}")
        else:
            canvas.drawCentredString(center_x, footer_y, f"Fee Summary - {safe_str(faculty)} ({(scope or 'mentor').upper()})")

        canvas.drawRightString(right, footer_y, f"Page {doc_.page}")
        canvas.restoreState()

    buffer = io.BytesIO()
    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        showBoundary=0
    )

    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin + 6 * mm,
        doc.width,
        doc.height - HEADER_HEIGHT + 8 * mm,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        id="normal"
    )
    doc.addPageTemplates([PageTemplate(id="All", frames=[frame], onPage=draw_header_footer)])

    elements = []
    elements.append(Spacer(1, 4 * mm))
    elements.append(Paragraph(report_title, title_style))

    meta = []
    if mode == "principal":
        meta.append("Mode: Principal")
        if safe_str(degree_id_param).isdigit():
            deg = Degree.objects.filter(id=int(degree_id_param)).first()
            if deg:
                meta.append(f"Degree: {safe_str(deg.degree)} ({safe_str(deg.degree_code)})")
    elif mode == "hod":
        meta.append(f"Mode: HOD | Dept: {safe_str(getattr(hod_dept,'Department','')) or 'N/A'}")
    else:
        meta.append(f"Mode: Faculty | Scope: {(scope or 'mentor').upper()} | {safe_str(faculty)}")
    if year_param:
        meta.append(f"Year: {year_param}")
    if section_param:
        meta.append(f"Section: {section_param}")
    if q_param:
        meta.append(f"Search: {q_param}")

    elements.append(Paragraph(" | ".join(meta), sub_style))

    # Overall summary (principal + hod only)
    if mode in ("principal", "hod"):
        elements.append(Paragraph("Overall Summary", section_style))
        data = [
            [Paragraph("Students", th), Paragraph("Total", th), Paragraph("Paid", th), Paragraph("Pending", th)],
            [
                Paragraph(str(overall["count"]), cell_center),
                Paragraph(money(overall["total"]), cell_center),
                Paragraph(money(overall["paid"]), cell_center),
                Paragraph(money(overall["pending"]), cell_center),
            ],
        ]
        elements.append(create_table(
            data,
            [doc.width * 0.18, doc.width * 0.27, doc.width * 0.27, doc.width * 0.28],
            header_bg=SECONDARY_BLUE
        ))
        elements.append(Spacer(1, 3 * mm))

    # Principal full blocks + student details (Dept -> Year)
    if mode == "principal":
        elements.append(Paragraph("Year-wise Summary", section_style))
        ydata = [[Paragraph("Year", th), Paragraph("Students", th), Paragraph("Total", th), Paragraph("Paid", th), Paragraph("Pending", th)]]
        for y, info in year_wise.items():
            ydata.append([
                Paragraph(f"Year {y}", cell_center),
                Paragraph(str(info["count"]), cell_center),
                Paragraph(money(info["total"]), cell_center),
                Paragraph(money(info["paid"]), cell_center),
                Paragraph(money(info["pending"]), cell_center),
            ])
        elements.append(create_table(ydata, [doc.width*0.16, doc.width*0.16, doc.width*0.22, doc.width*0.22, doc.width*0.24], header_bg=SECONDARY_BLUE))
        elements.append(Spacer(1, 3 * mm))

        elements.append(Paragraph("Department-wise Summary", section_style))
        ddata = [[Paragraph("Department", th), Paragraph("Students", th), Paragraph("Total", th), Paragraph("Paid", th), Paragraph("Pending", th)]]
        for d in dept_wise.values():
            ddata.append([
                Paragraph(safe_str(d["label"]), cell),
                Paragraph(str(d["count"]), cell_center),
                Paragraph(money(d["total"]), cell_center),
                Paragraph(money(d["paid"]), cell_center),
                Paragraph(money(d["pending"]), cell_center),
            ])
        elements.append(create_table(ddata, [doc.width*0.36, doc.width*0.12, doc.width*0.17, doc.width*0.17, doc.width*0.18], header_bg=PRIMARY_BLUE))
        elements.append(Spacer(1, 4 * mm))

        elements.append(Paragraph("Student Details (Department → Year)", section_style))
        for dept_name, years in grouped.items():
            blocks = [Paragraph(f"<b>Department:</b> {dept_name}",
                                ParagraphStyle("dept", parent=cell, fontName="Helvetica-Bold", spaceAfter=2))]
            for yi in (1, 2, 3, 4):
                if not years[yi]:
                    continue
                blocks.append(Paragraph(f"<b>Year {yi}</b>",
                                        ParagraphStyle("y", parent=cell, fontName="Helvetica-Bold",
                                                       textColor=SECONDARY_BLUE, spaceBefore=2, spaceAfter=2)))

                sdata = [[Paragraph("Reg No", th), Paragraph("Name", th), Paragraph("Sec", th),
                          Paragraph("Total", th), Paragraph("Paid", th), Paragraph("Pending", th)]]
                for r in years[yi]:
                    st = r["student"]
                    sdata.append([
                        Paragraph(safe_str(getattr(st, "reg_no", "")), cell_center),
                        Paragraph(safe_str(getattr(st, "name", "")), cell),
                        Paragraph(safe_str(getattr(st, "section", "")) or "-", cell_center),
                        Paragraph(money(r["total_current_year"]), cell_center),
                        Paragraph(money(r["paid_total"]), cell_center),
                        Paragraph(money(r["pending_total"]), cell_center),
                    ])

                blocks.append(create_table(
                    sdata,
                    [doc.width*0.16, doc.width*0.34, doc.width*0.08, doc.width*0.14, doc.width*0.14, doc.width*0.14],
                    header_bg=colors.HexColor("#334155"),
                    zebra=True
                ))
                blocks.append(Spacer(1, 2 * mm))
            elements.append(KeepTogether(blocks))

    # HOD: year-wise student list
    if mode == "hod":
        elements.append(Paragraph("Student Details (Year-wise)", section_style))
        for yi in (1, 2, 3, 4):
            if not grouped_year[yi]:
                continue
            elements.append(Paragraph(f"<b>Year {yi}</b>", ParagraphStyle("y2", parent=cell, fontName="Helvetica-Bold", textColor=SECONDARY_BLUE, spaceAfter=2)))

            sdata = [[Paragraph("Reg No", th), Paragraph("Name", th), Paragraph("Sec", th),
                      Paragraph("Total", th), Paragraph("Paid", th), Paragraph("Pending", th)]]
            for r in grouped_year[yi]:
                st = r["student"]
                sdata.append([
                    Paragraph(safe_str(getattr(st, "reg_no", "")), cell_center),
                    Paragraph(safe_str(getattr(st, "name", "")), cell),
                    Paragraph(safe_str(getattr(st, "section", "")) or "-", cell_center),
                    Paragraph(money(r["total_current_year"]), cell_center),
                    Paragraph(money(r["paid_total"]), cell_center),
                    Paragraph(money(r["pending_total"]), cell_center),
                ])

            elements.append(create_table(
                sdata,
                [doc.width*0.16, doc.width*0.36, doc.width*0.08, doc.width*0.13, doc.width*0.13, doc.width*0.14],
                header_bg=SECONDARY_BLUE
            ))
            elements.append(Spacer(1, 3 * mm))

    # Faculty: only student list
    if mode == "faculty":
        elements.append(Paragraph("Student Details", section_style))
        sdata = [[Paragraph("Reg No", th), Paragraph("Name", th), Paragraph("Dept", th), Paragraph("Year", th),
                  Paragraph("Total", th), Paragraph("Paid", th), Paragraph("Pending", th)]]
        for r in rows:
            st = r["student"]
            dept = r["department"]
            sdata.append([
                Paragraph(safe_str(getattr(st, "reg_no", "")), cell_center),
                Paragraph(safe_str(getattr(st, "name", "")), cell),
                Paragraph(safe_str(getattr(dept, "Department", "")) or "-", cell),
                Paragraph(str(r["year_index"] or ""), cell_center),
                Paragraph(money(r["total_current_year"]), cell_center),
                Paragraph(money(r["paid_total"]), cell_center),
                Paragraph(money(r["pending_total"]), cell_center),
            ])

        elements.append(create_table(
            sdata,
            [doc.width*0.14, doc.width*0.28, doc.width*0.20, doc.width*0.07, doc.width*0.10, doc.width*0.10, doc.width*0.11],
            header_bg=colors.HexColor("#0f766e")
        ))

    try:
        doc.build(elements)
    except Exception as e:
        # print("PDF build error:", e)
        return HttpResponse("PDF generation failed.", status=500)

    buffer.seek(0)

    # ✅ inline so it opens in browser tab
    response = FileResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response
  
 
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from user_accounts.decorators import check_permission

@require_http_methods(["GET"])
def get_payment_history(request, reg_no):
    """
    AJAX endpoint to get payment history for a specific student
    Works for both Principal and HOD users
    """
    # IMMEDIATE RETURN FOR TESTING
    return JsonResponse({
        'success': False,
        'error': 'Test endpoint reached successfully',
        'reg_no': reg_no,
        'user': str(request.user),
        'is_authenticated': request.user.is_authenticated
    })
    
    # Simple authentication check - allow any logged-in user
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    # Add debug logging
    # print(f"=== get_payment_history called ===")
    # print(f"User: {request.user}")
    # print(f"Reg No: {reg_no}")
    # print(f"Is authenticated: {request.user.is_authenticated}")
    
    try:
        from user_accounts.models import StudentDetails as UAStudentDetails, PersonalDetails as UAPersonalDetails, AdmissionRecords as UAAdmissionRecords
        from student_management.models import ManualFeeEntry, FeeReceipt
        from decimal import Decimal
        
        # Get student
        student = UAStudentDetails.objects.filter(reg_no=reg_no).select_related('department', 'department__degree').first()
        if not student:
            return JsonResponse({'error': 'Student not found'}, status=404)
        
        # Get admission details for additional info
        aadhar = (getattr(student, 'aadhar_number', '') or '').strip()
        personal = UAPersonalDetails.objects.using('admissionform1').filter(Aadhaar_Number=aadhar).first() if aadhar else None
        admission = UAAdmissionRecords.objects.using('admissionform1').filter(PersonalDetailsId=personal).first() if personal else None
        
        # Get manual payments (from fee receipts) grouped by year
        year_payments = {1: [], 2: [], 3: [], 4: []}
        year_totals = {1: Decimal('0.00'), 2: Decimal('0.00'), 3: Decimal('0.00'), 4: Decimal('0.00')}
        
        fee_entries = ManualFeeEntry.objects.filter(
            fee_receipt__student=student
        ).select_related('fee_receipt').order_by('-entered_at')
        
        online_total = Decimal('0.00')
        manual_total = Decimal('0.00')
        
        for entry in fee_entries:
            receipt = entry.fee_receipt
            amount = entry.entered_fee or Decimal('0.00')
            
            # Map semester to year
            semester = receipt.semester
            year = 1  # Default to year 1
            if semester:
                try:
                    sem_num = int(semester)
                    year = (sem_num + 1) // 2  # Sem 1,2 = Year 1, Sem 3,4 = Year 2, etc.
                    if year < 1:
                        year = 1
                    elif year > 4:
                        year = 4
                except (ValueError, TypeError):
                    year = 1
            
            payment_data = {
                'date': entry.entered_at.strftime('%d/%m/%Y'),
                'reference_no': entry.transaction_id or '-',
                'amount': str(amount),
                'semester': receipt.semester or '',
                'year': year,
                'status': receipt.status,
                'recorded_by': entry.entered_by or 'System',
                'receipt_url': receipt.fee_receipt.url if receipt.fee_receipt else None,
                'fee_type': 'Manual Entry'
            }
            
            # Add to appropriate year
            if year in year_payments:
                year_payments[year].append(payment_data)
                year_totals[year] += amount
            
            # For now, treating all as manual payments
            # You can add logic here to differentiate between online and manual
            if entry.transaction_id and len(entry.transaction_id) > 10:
                # Assume longer transaction IDs are online payments
                online_total += amount
            else:
                manual_total += amount
        
        # Get student program info with multiple fallbacks
        program_name = "Unknown Program"
        
        # Priority 1: Admission degree field
        if admission and admission.degree:
            program_name = admission.degree
        # Priority 2: Admission admissionFor field  
        elif admission and admission.admissionFor:
            program_name = admission.admissionFor
        # Priority 3: Department degree
        elif student.department and student.department.degree and student.department.degree.degree:
            program_name = student.department.degree.degree
        # Priority 4: Department degree_department field
        elif student.department and student.department.degree_department:
            program_name = student.department.degree_department
        # Priority 5: Use department name as fallback
        elif student.department and student.department.Department:
            program_name = f"Bachelor of Science in {student.department.Department}"
        
        department_name = student.department.Department if student.department else "Unknown Department"
        
        # Try to get intake information from admission
        intake = "January"  # Default
        if admission and hasattr(admission, 'intake'):
            intake = admission.intake or "January"
        
        batch = student.batch or "2025"
        mode_of_study = (admission.Mode or "Regular") if admission else "Regular"
        
        return JsonResponse({
            'success': True,
            'student_info': {
                'name': student.name,
                'reg_no': student.reg_no,
                'program': program_name,
                'department': department_name,
                'intake': intake,
                'batch': batch,
                'mode_of_study': mode_of_study
            },
            'year_payments': year_payments,
            'year_totals': {str(k): str(v) for k, v in year_totals.items()},
            'totals': {
                'online_total': str(online_total),
                'manual_total': str(manual_total),
                'grand_total': str(online_total + manual_total)
            }
        })
        
    except Exception as e:
        import traceback
        return JsonResponse({
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


@require_http_methods(["GET"])
def get_fee_structure(request, reg_no):
    """
    AJAX endpoint to get detailed fee structure breakdown for a specific student
    Works for both Principal and HOD users
    """
    # IMMEDIATE RETURN FOR TESTING
    return JsonResponse({
        'success': False,
        'error': 'Test endpoint reached successfully',
        'reg_no': reg_no,
        'user': str(request.user),
        'is_authenticated': request.user.is_authenticated
    })
    
    # Simple authentication check - allow any logged-in user
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    # Add debug logging
    # print(f"=== get_fee_structure called ===")
    # print(f"User: {request.user}")
    # print(f"Reg No: {reg_no}")
    # print(f"Is authenticated: {request.user.is_authenticated}")
    
    try:
        from user_accounts.models import StudentDetails as UAStudentDetails, PersonalDetails as UAPersonalDetails, AdmissionRecords as UAAdmissionRecords, Add_Department as UAAddDepartment
        from fee_management.models import FeeEntry as FMFeeEntry, ScholarshipDeduction
        from django.db.models import Q
        from decimal import Decimal
        
        # print("Imports successful")
        
        # Get parameters
        year_param = request.GET.get('year', '1')
        dept_id_param = request.GET.get('dept_id', '')
        # print(f"Parameters - year: {year_param}, dept_id: {dept_id_param}")
        
        # Get student
        student = UAStudentDetails.objects.filter(reg_no=reg_no).select_related('department', 'department__degree').first()
        if not student:
            # print(f"Student not found: {reg_no}")
            return JsonResponse({'error': 'Student not found'}, status=404)
        
        # print(f"Student found: {student.name}")
        
        # Get admission details
        aadhar = (getattr(student, 'aadhar_number', '') or '').strip()
        personal = UAPersonalDetails.objects.using('admissionform1').filter(Aadhaar_Number=aadhar).first() if aadhar else None
        admission = UAAdmissionRecords.objects.using('admissionform1').filter(PersonalDetailsId=personal).first() if personal else None
        
        # print(f"Admission found: {admission is not None}")
        
        # Determine department to use
        if dept_id_param:
            try:
                selected_dept = UAAddDepartment.objects.filter(id=int(dept_id_param)).first()
            except (ValueError, TypeError):
                selected_dept = student.department
        else:
            selected_dept = student.department
            
        if not selected_dept:
            return JsonResponse({'error': 'Department not found'}, status=404)
        
        quota = (admission.Quota or '').strip() if admission else ''
        mode = (admission.Mode or '').strip() if admission else ''
        batch = student.batch or '2025'
        
        # Build FeeEntry queryset to find matching fee structure
        dep_strings = [
            str(getattr(selected_dept, 'id', '') or ''),
            (getattr(selected_dept, 'Department_code', '') or '').strip(),
            (getattr(selected_dept, 'Department', '') or '').strip(),
            (getattr(selected_dept, 'department_label', '') or '').strip(),
            (getattr(selected_dept, 'degree_department', '') or '').strip(),
        ]
        dep_strings = [s for s in dep_strings if s]
        
        # Query FeeEntry with multiple matching strategies
        base_qs = FMFeeEntry.objects.select_related('fee_category', 'degree').filter(
            Q(department_id__in=dep_strings) | 
            Q(department_id__icontains=selected_dept.Department if selected_dept.Department else '')
        )
        
        # Filter by batch if available
        if batch:
            batch_qs = base_qs.filter(batch=batch)
            if batch_qs.exists():
                base_qs = batch_qs
        
        # Filter by degree if available
        if getattr(selected_dept, 'degree_id', None):
            degree_qs = base_qs.filter(degree_id=selected_dept.degree_id)
            if degree_qs.exists():
                base_qs = degree_qs
        
        # Filter by quota if available
        if quota:
            quota_qs = base_qs.filter(quota__icontains=quota)
            if quota_qs.exists():
                base_qs = quota_qs
        
        # Get all fee entries for this student
        fee_qs = base_qs.distinct()
        
        # Build year-wise detailed fee breakdown (4 years)
        year_fees = []
        total_fee = Decimal('0.00')
        
        # Get payment information to calculate paid amounts by year
        from student_management.models import ManualFeeEntry
        paid_by_year = {}
        fee_entries = ManualFeeEntry.objects.filter(
            fee_receipt__student=student
        ).select_related('fee_receipt')
        
        # Map semester payments to years
        for entry in fee_entries:
            semester = entry.fee_receipt.semester
            if semester:
                try:
                    sem_num = int(semester)
                    year_num = (sem_num + 1) // 2
                    if year_num < 1:
                        year_num = 1
                    elif year_num > 4:
                        year_num = 4
                        
                    if year_num not in paid_by_year:
                        paid_by_year[year_num] = Decimal('0.00')
                    paid_by_year[year_num] += entry.entered_fee or Decimal('0.00')
                except (ValueError, TypeError):
                    pass
        
        # Calculate fees for each year (4 years) with detailed breakdown
        for year in range(1, 5):
            # Initialize detailed fee categories
            fee_details = {
                'tuition': Decimal('0.00'),
                'academic': Decimal('0.00'),
                'hostel': Decimal('0.00'),
                'mess': Decimal('0.00'),
                'transport': Decimal('0.00'),
                'library': Decimal('0.00'),
                'lab': Decimal('0.00'),
                'exam': Decimal('0.00'),
                'development': Decimal('0.00'),
                'other': Decimal('0.00')
            }
            scholarship_reduction = Decimal('0.00')
            
            # Determine which fee components to include based on mode of study
            mode_lc = (mode or '').lower()
            is_hostel_student = any(keyword in mode_lc for keyword in ['hostel', 'residential'])
            is_transport_student = any(keyword in mode_lc for keyword in ['transport', 'day scholar', 'dayscholar'])
            
            # Calculate fee amounts for this year by category
            for entry in fee_qs:
                year_field = f"year_{year}"
                year_amount = getattr(entry, year_field, Decimal('0.00'))
                
                if year_amount > 0:  # Only process if there's an amount
                    # Categorize fees based on fee category name (flexible matching)
                    fee_category_name = entry.fee_category.name.lower()
                    
                    # Always include basic academic fees for all students
                    if any(keyword in fee_category_name for keyword in ['tuition', 'college', 'course']):
                        fee_details['tuition'] += year_amount
                    elif any(keyword in fee_category_name for keyword in ['academic', 'study', 'education']):
                        fee_details['academic'] += year_amount
                    elif any(keyword in fee_category_name for keyword in ['library', 'book']):
                        fee_details['library'] += year_amount
                    elif any(keyword in fee_category_name for keyword in ['lab', 'laboratory', 'practical']):
                        fee_details['lab'] += year_amount
                    elif any(keyword in fee_category_name for keyword in ['exam', 'test', 'assessment']):
                        fee_details['exam'] += year_amount
                    elif any(keyword in fee_category_name for keyword in ['development', 'infrastructure', 'building', 'facility']):
                        fee_details['development'] += year_amount
                    
                    # Mode-specific fees
                    elif any(keyword in fee_category_name for keyword in ['hostel', 'accommodation', 'room']):
                        if is_hostel_student:  # Only include hostel fees for hostel students
                            fee_details['hostel'] += year_amount
                    elif any(keyword in fee_category_name for keyword in ['mess', 'food', 'canteen', 'dining']):
                        if is_hostel_student:  # Only include mess fees for hostel students
                            fee_details['mess'] += year_amount
                    elif any(keyword in fee_category_name for keyword in ['transport', 'bus', 'travel']):
                        if is_transport_student:  # Only include transport fees for transport/day scholar students
                            fee_details['transport'] += year_amount
                    
                    else:
                        # Smart categorization for generic fees based on student mode
                        if year_amount >= 50000:  # Very large amounts likely tuition
                            fee_details['tuition'] += year_amount
                        elif year_amount >= 20000:  # Large amounts likely academic
                            fee_details['academic'] += year_amount
                        elif year_amount >= 10000:  # Medium amounts - mode specific
                            if is_hostel_student:
                                fee_details['hostel'] += year_amount  # Hostel students get hostel fees
                            elif is_transport_student:
                                fee_details['transport'] += year_amount  # Transport students get transport fees
                            else:
                                fee_details['academic'] += year_amount  # Regular students get academic fees
                        else:  # Small amounts go to other
                            fee_details['other'] += year_amount
            
            # Add specific transport fee if applicable and student is transport/day scholar
            if is_transport_student:
                try:
                    bus_stop = None
                    td = getattr(admission, 'TransportDetailsId', None)
                    if td:
                        bus_stop = getattr(td, 'bus_stop', None)

                    if bus_stop:
                        from fee_management.models import TransportFee
                        t_fee = TransportFee.objects.filter(bus_stop__iexact=bus_stop.strip()).first()
                        if t_fee:
                            yearly_transport = t_fee.amount_per_year or (Decimal(t_fee.amount_per_semester or 0) * 2)
                            fee_details['transport'] += yearly_transport
                except Exception:
                    pass
            
            # Get scholarship deductions for this year
            if quota and selected_dept:
                scholarship_deductions = ScholarshipDeduction.objects.filter(
                    Q(Department__icontains=selected_dept.Department) |
                    Q(Department__icontains=selected_dept.Department_code),
                    Q(Quota__icontains=quota)
                )
                for deduction in scholarship_deductions:
                    year_scholarship = deduction.scholarship_amount / 4
                    scholarship_reduction += year_scholarship
            
            # Calculate totals
            year_total = sum(fee_details.values()) - scholarship_reduction
            paid_amount = paid_by_year.get(year, Decimal('0.00'))
            balance = max(year_total - paid_amount, Decimal('0.00'))
            
            total_fee += year_total
            
            # Create detailed fee breakdown
            year_fees.append({
                'year': f'YEAR {year}',
                'fee_details': {
                    'tuition': f"{fee_details['tuition']:.2f}",
                    'academic': f"{fee_details['academic']:.2f}",
                    'hostel': f"{fee_details['hostel']:.2f}",
                    'mess': f"{fee_details['mess']:.2f}",
                    'transport': f"{fee_details['transport']:.2f}",
                    'library': f"{fee_details['library']:.2f}",
                    'lab': f"{fee_details['lab']:.2f}",
                    'exam': f"{fee_details['exam']:.2f}",
                    'development': f"{fee_details['development']:.2f}",
                    'other': f"{fee_details['other']:.2f}"
                },
                'scholarship_reduction': f"{scholarship_reduction:.2f}",
                'year_total': f"{year_total:.2f}",
                'paid': f"{paid_amount:.2f}",
                'balance': f"{balance:.2f}",
                'student_mode': {
                    'is_hostel': is_hostel_student,
                    'is_transport': is_transport_student,
                    'mode_text': mode
                }
            })
        
        # Calculate overall totals
        total_paid = sum(paid_by_year.values())
        total_balance = max(total_fee - total_paid, Decimal('0.00'))
        
        # Get student info with multiple fallbacks
        program_name = "Unknown Program"
        if admission and admission.degree:
            program_name = admission.degree
        elif admission and admission.admissionFor:
            program_name = admission.admissionFor
        elif student.department and student.department.degree and student.department.degree.degree:
            program_name = student.department.degree.degree
        elif student.department and student.department.degree_department:
            program_name = student.department.degree_department
        elif student.department and student.department.Department:
            program_name = f"Bachelor of Science in {student.department.Department}"
            
        department_name = selected_dept.Department if selected_dept else "Unknown Department"
        intake = "January"
        if admission and hasattr(admission, 'intake'):
            intake = admission.intake or "January"
        mode_of_study = mode or "Regular"
        
        return JsonResponse({
            'success': True,
            'student_info': {
                'name': student.name,
                'reg_no': student.reg_no,
                'program': program_name,
                'department': department_name,
                'intake': intake,
                'batch': batch,
                'mode_of_study': mode_of_study
            },
            'year_fees': year_fees,
            'summary': {
                'total_fee': f"{total_fee:.2f}",
                'total_paid': f"{total_paid:.2f}",
                'total_balance': f"{total_balance:.2f}"
            },
            'debug_info': {
                'fee_entries_found': fee_qs.count(),
                'department_strings': dep_strings,
                'quota': quota,
                'mode': mode,
                'batch': batch,
                'fee_categories': [entry.fee_category.name for entry in fee_qs],
                'format': 'detailed_breakdown'
            }
        })
        
    except Exception as e:
        import traceback
        return JsonResponse({
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)
