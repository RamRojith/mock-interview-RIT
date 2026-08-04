from django.shortcuts import render,redirect,get_object_or_404
from user_accounts.decorators import no_cache,is_super_user
from django.contrib import messages
from course_management.models import PeriodAllocation, CourseHours, CourseEnrollment, AssignSubjectFaculty

from django.shortcuts import render
from datetime import datetime
from user_accounts.decorators import no_cache, check_permission
from faculty_management.models import FacultyCategory, general_information, DesignationMaster, StaffCategoryAssignment
from course_management.models import Course_category
from faculty_management.services import employee_upload
from user_accounts.models import Add_Department




def faculty_general_information(request):
    faculty = request.user
    employee_id = faculty.Employee_id
    username = faculty.username
    department_name = getattr(faculty.Department, "Department", None)
    college_email = faculty.email

    # Get department safely
    department = Add_Department.objects.filter(
        Department__iexact=department_name, is_active=True
    ).first()

    if not department:
        messages.error(request, "Department not found or inactive.")
        return redirect("faculty_dashboard")

    designations = DesignationMaster.objects.all()
    categories = FacultyCategory.objects.filter(is_active=True).order_by("category_name")
    info = general_information.objects.filter(faculty_id=employee_id).first()

    # Category fixed by the admin during pre-authorization (if any). When set,
    # the staff member cannot change it on this form.
    preset_assignment = (
        StaffCategoryAssignment.objects.filter(employee_id=employee_id)
        .select_related("category")
        .first()
    )
    preset_category = preset_assignment.category if preset_assignment else None

    # Read-only category label shown on the form: the admin preset takes
    # precedence, otherwise the previously stored category, otherwise a placeholder.
    if preset_category:
        category_display = preset_category.category_name
    elif info and info.category:
        category_display = info.category.category_name
    else:
        category_display = "Not assigned"

    if request.method == "POST":
        # Basic info
        name = request.POST.get("name")
        designation_id = request.POST.get("designation")
        designation = DesignationMaster.objects.filter(id=designation_id).first() if designation_id else None
        # Category is read-only for the staff member. It is fixed by the admin
        # during pre-authorization; otherwise the previously stored value is kept.
        if preset_category:
            category = preset_category
        elif info:
            category = info.category
        else:
            category = None
        dob = request.POST.get("dob")
        address = request.POST.get("address")
        personal_email = request.POST.get("personal_email")
        college_email = request.POST.get("college_email")
        phone = request.POST.get("phone")
        blood_group = request.POST.get("blood_group")
        community = request.POST.get("community")
        caste = request.POST.get("caste")
        religion = request.POST.get("religion")
        # Date of joining is read-only for the staff member and is managed by the
        # administration only. It is never taken from the submitted form.

        # IDs
        apaar_id = request.POST.get("apaar_id")
        anu_id = request.POST.get("anu_id")
        aicte_id = request.POST.get("aicte_id")
        annauniversity_affiliation_id = request.POST.get("annauniversity_affiliation_id")
        PAN_number = request.POST.get("PAN_number")
        Aadhar_number = request.POST.get("Aadhar_number")

        # File uploads
        PAN_certificate = request.FILES.get("PAN_certificate")
        Aadhar_certificate = request.FILES.get("Aadhar_certificate")

        # Employment details
        appointment_type = request.POST.get("appointment_type")
        basic_pay = request.POST.get("basic_pay")
        agp = request.POST.get("agp")
        allowances = request.POST.get("allowances")
        pay_scale_notes = request.POST.get("pay_scale_notes")
        recruitment_mode = request.POST.get("recruitment_mode")
        nature_of_duties = request.POST.get("nature_of_duties")
        confirmation_date = request.POST.get("confirmation_date")
        probation_period_months = request.POST.get("probation_period_months")
        probation_confirmation_reference = request.POST.get("probation_confirmation_reference")
        probation_confirmation_document = request.FILES.get("probation_confirmation_document")
        # print("ffsjfj => ",probation_confirmation_document)
        # Create or Update record
        if info:
            info.name = name
            info.department = department
            info.designation = designation
            info.category = category
            info.dob = dob or None
            info.address = address
            info.personal_email = personal_email
            info.college_email = college_email
            info.phone = phone or None
            info.blood_group = blood_group
            info.community = community
            info.caste = caste
            info.religion = religion
            # doj intentionally not updated here (admin-managed, read-only).
            info.apaar_id = apaar_id
            info.anu_id = anu_id
            info.aicte_id = aicte_id
            info.annauniversity_affiliation_id = annauniversity_affiliation_id
            info.PAN_number = PAN_number
            info.Aadhar_number = Aadhar_number
            info.appointment_type = appointment_type
            info.basic_pay = basic_pay or None
            info.agp = agp or None
            info.allowances = allowances or None
            info.pay_scale_notes = pay_scale_notes
            info.recruitment_mode = recruitment_mode
            info.nature_of_duties = nature_of_duties
            info.confirmation_date = confirmation_date or None
            info.probation_period_months = probation_period_months or None
            info.probation_confirmation_reference = probation_confirmation_reference

            if PAN_certificate:
                info.PAN_certificate = PAN_certificate
            if Aadhar_certificate:
                info.Aadhar_certificate = Aadhar_certificate
            if probation_confirmation_document:
                info.probation_confirmation_document = probation_confirmation_document

            info.save()
            messages.success(request, "Faculty information updated successfully!")
        else:
            general_information.objects.create(
                faculty_id=employee_id,
                name=name,
                department=department,
                designation=designation,
                category=category,
                dob=dob or None,
                address=address,
                personal_email=personal_email,
                college_email=college_email,
                phone=phone or None,
                blood_group=blood_group,
                community=community,
                caste=caste,
                religion=religion,
                doj=None,
                apaar_id=apaar_id,
                anu_id=anu_id,
                aicte_id=aicte_id,
                annauniversity_affiliation_id=annauniversity_affiliation_id,
                PAN_number=PAN_number,
                Aadhar_number=Aadhar_number,
                PAN_certificate=PAN_certificate,
                Aadhar_certificate=Aadhar_certificate,
                appointment_type=appointment_type,
                basic_pay=basic_pay or None,
                agp=agp or None,
                allowances=allowances or None,
                pay_scale_notes=pay_scale_notes,
                recruitment_mode=recruitment_mode,
                nature_of_duties=nature_of_duties,
                confirmation_date=confirmation_date or None,
                probation_period_months=probation_period_months or None,
                probation_confirmation_reference=probation_confirmation_reference,
                probation_confirmation_document=probation_confirmation_document,
            )
            messages.success(request, "Faculty information added successfully!")

        return redirect("faculty_dashboard")

    # Context
    context = {
        "info": info,
        "username": username,
        "employee_id": employee_id,
        "role": getattr(faculty.role, "role", "") if getattr(faculty, "role", None) else "",
        "department": department,
        "college_email": college_email,
        "designations": designations,
        "categories": categories,
        "preset_category": preset_category,
        "category_display": category_display,
        "category_ids": list(categories.values_list("id", flat=True)),
        "appointment_choices": general_information.APPOINTMENT_TYPE_CHOICES,
        "recruitment_choices": general_information.RECRUITMENT_MODE_CHOICES,
        "duties_choices": general_information.DUTIES_CHOICES,
    }

    return render(request, "faculty_management/faculty/faculty_general_information.html", context)

from faculty_management.models import general_information, Academic_Background, AcademicExperience, IndustryExperience, ResearchExperience
from django.http import JsonResponse

DEGREE_CHOICES = Academic_Background.DEGREE_CHOICES

def faculty_academic_background(request):
    
    # faculty_id = request.user.Employee_id
    
    
    faculty = request.user
    employee_id = faculty.Employee_id
    username = faculty.username
    department_name = getattr(faculty.Department, "Department", None)
    college_email = faculty.email
    username = faculty.username
    # Get department safely

    staff = general_information.objects.filter(faculty_id=employee_id).first()

    academic_records = Academic_Background.objects.filter(faculty=staff)
    department_name = getattr(staff.department, "department", None)

    department = Add_Department.objects.filter(
        Department__iexact=department_name, is_active=True
    ).first()
    # Handle AJAX edit fetch
    edit_id = request.GET.get('edit_id')
    if edit_id:
        record = get_object_or_404(Academic_Background, id=edit_id, faculty=staff)
        certificate_url = None
        if record.degree == 'SSLC' and record.sslc_certificate:
            certificate_url = record.sslc_certificate.url
        elif record.degree == 'High School' and record.hsc_certificate:
            certificate_url = record.hsc_certificate.url
        elif record.degree == 'Graduation' and record.ug_certificate:
            certificate_url = record.ug_certificate.url
        elif record.degree == 'Post-Graduation' and record.pg_certificate:
            certificate_url = record.pg_certificate.url
        elif record.degree == 'MPhil' and record.mphil_certificate:
            certificate_url = record.mphil_certificate.url
        elif record.degree == 'PhD' and record.phd_certificate:
            certificate_url = record.phd_certificate.url
        elif record.degree == 'PostDoc' and record.postDoc_certificate:
            certificate_url = record.postDoc_certificate.url

        return JsonResponse({
            'id': record.id,
            'degree': record.degree,
            'title': record.title,
            'board_university': record.board_university,
            'year_of_passing': record.year_of_passing,
            'marks_percentage': record.marks_percentage,
            'certificate_url': certificate_url
        })

    # Handle POST (Add/Edit/Delete)
    if request.method == "POST":
        action = request.POST.get('action')
        record_id = request.POST.get('record_id')

        if action == 'delete' and record_id:
            record = get_object_or_404(Academic_Background, id=record_id, faculty=staff)
            record.delete()
            return redirect('faculty_academic_background')

        # Add/Edit logic
        degree = request.POST.get('degree')
        title = request.POST.get('title')
        board_university = request.POST.get('board_university')
        year_of_passing = request.POST.get('year_of_passing') or None
        marks_percentage = request.POST.get('marks_percentage') or None

        if record_id:
            record = get_object_or_404(Academic_Background, id=record_id, faculty=staff)
        else:
            record = Academic_Background(faculty=staff)

        record.degree = degree
        record.title = title
        record.board_university = board_university
        record.year_of_passing = year_of_passing
        record.marks_percentage = marks_percentage

        # âœ… FIX: Get file dynamically based on degree
        file_field_map = {
            'SSLC': 'sslc_certificate',
            'High School': 'hsc_certificate',
            'Graduation': 'ug_certificate',
            'Post-Graduation': 'pg_certificate',
            'MPhil': 'mphil_certificate',
            'PhD': 'phd_certificate',
            'PostDoc': 'postDoc_certificate'
        }

        certificate_field = file_field_map.get(degree)
        if certificate_field and certificate_field in request.FILES:
            uploaded_file = request.FILES[certificate_field]
            setattr(record, certificate_field, uploaded_file)

        record.save()
        return redirect('faculty_academic_background')

    return render(request, "faculty_management/faculty/faculty_academic_background.html", {
        'academic_records': academic_records,
        'DEGREE_CHOICES': Academic_Background.DEGREE_CHOICES,
        "username": username,
        "department": department,
        
    })





def faculty_academic_experience(request):
    employee_id = request.user.Employee_id
    faculty = general_information.objects.filter(faculty_id=employee_id).first()

    if not faculty:
        messages.error(request, "Faculty information not found.")
        return redirect('home')

    if request.method == 'POST':
        action = request.POST.get('action')
        experience_id = request.POST.get('experience_id')

        # DELETE
        if action == 'delete' and experience_id:
            experience = get_object_or_404(AcademicExperience, id=experience_id, faculty=faculty)
            experience.delete()
            messages.success(request, "Academic experience deleted successfully.")
            return redirect('faculty_academic_experience')

        # CREATE / EDIT
        if action in ['create', 'edit']:
            if action == 'edit' and experience_id:
                experience = get_object_or_404(AcademicExperience, id=experience_id, faculty=faculty)
            else:
                experience = AcademicExperience(faculty=faculty)

            experience.institute_name = request.POST.get('institute_name')
            experience.designation = request.POST.get('designation')
            experience.from_date = request.POST.get('from_date') or None
            experience.to_date = request.POST.get('to_date') or None

            if request.FILES.get('certificate'):
                experience.certificate = request.FILES['certificate']

            try:
                experience.full_clean()
                experience.save()
                messages.success(request, f"Academic experience {'updated' if action=='edit' else 'created'} successfully.")
            except Exception as e:
                messages.error(request, f"Error: {e}")

            return redirect('faculty_academic_experience')

    experiences = AcademicExperience.objects.filter(faculty=faculty).order_by('-from_date')
    context = {'experiences': experiences, 'faculty': faculty}
    return render(request, "faculty_management/faculty/faculty_academic_experience.html", context)


def faculty_industry_experience(request):
    employee_id = request.user.Employee_id
    faculty = general_information.objects.filter(faculty_id=employee_id).first()

    if not faculty:
        messages.error(request, "Faculty information not found.")
        return redirect('home')

    if request.method == 'POST':
        action = request.POST.get('action')
        experience_id = request.POST.get('experience_id')

        # DELETE
        if action == 'delete' and experience_id:
            experience = get_object_or_404(IndustryExperience, id=experience_id, faculty=faculty)
            experience.delete()
            messages.success(request, "Industry experience deleted successfully.")
            return redirect('faculty_industry_experience')

        # CREATE / EDIT
        if action in ['create', 'edit']:
            if action == 'edit' and experience_id:
                experience = get_object_or_404(IndustryExperience, id=experience_id, faculty=faculty)
            else:
                experience = IndustryExperience(faculty=faculty)

            experience.company_name = request.POST.get('company_name')

            # Get designation from DesignationMaster
            designation_id = request.POST.get('designation')
            if designation_id:
                experience.designation = get_object_or_404(DesignationMaster, id=designation_id)
            else:
                experience.designation = None

            experience.from_date = request.POST.get('from_date') or None
            experience.to_date = request.POST.get('to_date') or None

            if request.FILES.get('certificate'):
                experience.certificate = request.FILES['certificate']

            try:
                experience.full_clean()
                experience.save()
                messages.success(request, f"Industry experience {'updated' if action=='edit' else 'created'} successfully.")
            except Exception as e:
                messages.error(request, f"Error: {e}")

            return redirect('faculty_industry_experience')

    experiences = IndustryExperience.objects.filter(faculty=faculty).order_by('-from_date')
    designations = DesignationMaster.objects.all()
    context = {'experiences': experiences, 'faculty': faculty, 'designations': designations}
    return render(request, "faculty_management/faculty/faculty_industry_experience.html", context)


def faculty_research_experience(request):
    employee_id = request.user.Employee_id
    faculty = general_information.objects.filter(faculty_id=employee_id).first()

    if not faculty:
        messages.error(request, "Faculty information not found.")
        return redirect('home')

    if request.method == 'POST':
        action = request.POST.get('action')
        experience_id = request.POST.get('experience_id')

        # DELETE
        if action == 'delete' and experience_id:
            experience = get_object_or_404(ResearchExperience, id=experience_id, faculty=faculty)
            experience.delete()
            messages.success(request, "Research experience deleted successfully.")
            return redirect('faculty_research_experience')

        # CREATE / EDIT
        if action in ['create', 'edit']:
            if action == 'edit' and experience_id:
                experience = get_object_or_404(ResearchExperience, id=experience_id, faculty=faculty)
            else:
                experience = ResearchExperience(faculty=faculty)

            experience.research_area = request.POST.get('research_area')
            experience.institute = request.POST.get('institute')
            experience.from_date = request.POST.get('from_date') or None
            experience.to_date = request.POST.get('to_date') or None

            if request.FILES.get('certificate'):
                experience.certificate = request.FILES['certificate']

            try:
                experience.full_clean()
                experience.save()
                messages.success(
                    request,
                    f"Research experience {'updated' if action == 'edit' else 'added'} successfully."
                )
            except Exception as e:
                messages.error(request, f"Error saving data: {e}")

            return redirect('faculty_research_experience')

    experiences = ResearchExperience.objects.filter(faculty=faculty).order_by('-from_date')

    context = {
        'experiences': experiences,
        'faculty': faculty,
    }

    return render(request, "faculty_management/faculty/faculty_research_experience.html", context)



def employee_data_upload_template(request):
    return employee_upload.build_template_response()


def employee_date_upload(request):
    context = employee_upload.upload_context()

    if request.method != "POST":
        return render(request, "faculty_management/faculty/employee_date_upload.html", context)

    if request.POST.get("action") == "sync_departments":
        sync_summary = employee_upload.sync_department_tables()
        context["department_sync_summary"] = sync_summary
        if sync_summary["created_academic"] or sync_summary["created_control"]:
            messages.success(request, "Department tables synced successfully.")
        elif sync_summary["skipped"]:
            messages.warning(request, "Department sync completed with skipped records.")
        else:
            messages.info(request, "Both department tables already match by name.")
        return render(request, "faculty_management/faculty/employee_date_upload.html", context)

    if request.POST.get("action") == "export_missing_users":
        return employee_upload.build_missing_users_report()

    excel_file = request.FILES.get("excel_file")
    if not excel_file:
        messages.error(request, "Please choose an Excel file.")
        return render(request, "faculty_management/faculty/employee_date_upload.html", context)

    if not excel_file.name.lower().endswith(".xlsx"):
        messages.error(request, "Please upload a .xlsx file.")
        return render(request, "faculty_management/faculty/employee_date_upload.html", context)

    try:
        results, summary = employee_upload.process_upload_file(excel_file)
    except ValueError as exc:
        messages.error(request, str(exc))
        return render(request, "faculty_management/faculty/employee_date_upload.html", context)

    context = employee_upload.upload_context(results=results, summary=summary)
    if summary["created_general"] or summary["updated_general"] or summary["created_users"] or summary["updated_users"]:
        messages.success(request, "Employee upload completed.")
    elif summary["skipped"]:
        messages.warning(request, "No employees were saved. Please review the row errors.")
    else:
        messages.warning(request, "No employee rows were found after the header.")

    return render(request, "faculty_management/faculty/employee_date_upload.html", context)
