from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from user_accounts.decorators import faculty_login_required, is_super_user, no_cache
from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from user_accounts.decorators import faculty_login_required, is_super_user, no_cache
from user_accounts.models import StudentDetails
from faculty_management.models import general_information

# @faculty_login_required
# def home(request):
#     request.session['current_page']='home'
#     app = request.session.get('app_name', None)
#     request.session["faculty_dashboard"]=True
#     # if app and app == "Library":
#     #     request.session["faculty_dashboard"]=False
#     #     return redirect('library_management_home')


# @faculty_login_required
def home(request):
    request.session['current_page'] = 'home'
    # # print("current page => ", request.session['current_page'])
    app = request.session.get('app_name', None)
    # # print("Current App => ", app)
    request.session["faculty_dashboard"] = True

    # Example: different redirection based on app
    # if app and app == "Library":
    #     request.session["faculty_dashboard"] = False
    #     return redirect('library_management_home')

    # Default: render a template
    return render(request, "home.html")


def index(request):
    return render(request, "index.html")


from django.views.decorators.cache import never_cache
from django.core.cache import cache
from django.utils.timezone import now
from django.contrib import messages
from datetime import date
from django.shortcuts import render
from datetime import datetime, timedelta
from faculty_management.models import general_information, Vision, Mission, Program_Educational_Objective, Program_specific_Outcomes

@never_cache
def faculty_dashboard(request):
    emp_id = getattr(request.user, "Employee_id", None)
    if not emp_id:
        messages.error(request, "Employee ID not found. Please re-login.")
        return render(request, "faculty_dashboard.html", {"error": "User data missing."})

    # ✅ Create a unique cache key per user (not including popup logic)
    cache_key = f"faculty_dashboard_data_{emp_id}"
    data_context = cache.get(cache_key)

    # ✅ Handle popup logic independently of cached data
    show_popup = not request.session.get("faculty_dashboard_popup_shown", False)
    if show_popup:
        request.session["faculty_dashboard_popup_shown"] = True  # show only once per login

    # ✅ If cached (reuse + merge popup logic)
    if data_context:
        data_context["show_popup"] = show_popup
        return render(request, "faculty_dashboard.html", data_context)

    # ------------------- DB Fetch Starts -------------------
    try:
        department = (
            Add_Department.objects.select_related("degree")
            .filter(Department__iexact=request.user.Department.Department, is_active=True)
            .first()
        )
        if not department:
            messages.warning(request, "Department not found or inactive.")
            department = None

        faculty = (
            general_information.objects
            .select_related("department", "department__degree")
            .filter(
                faculty_id=emp_id,
                department=department,
                department__degree=getattr(department, "degree", None)
            )
            .first()
        )
        if not faculty:
            messages.warning(request, "Faculty record not found.")
    except Exception as e:
        messages.error(request, f"Error loading faculty data: {str(e)}")
        faculty = department = None

    faculty_department = getattr(faculty, "department", None)

    # ✅ Vision, Mission, PEO, PSO fetch
    try:
        vision = (
            Vision.objects.filter(department=faculty_department, is_active=True)
            .only("vision_statement", "year")
            .order_by("-year")
            .first()
        )
        mission = (
            Mission.objects.filter(department=faculty_department, is_active=True)
            .only("mission_statement", "year")
            .order_by("-year")
            .first()
        )
        peos = (
            Program_Educational_Objective.objects.filter(department=faculty_department, is_active=True)
            .only("peo_statement", "year")
            .order_by("-year")
        )
        psos = (
            Program_specific_Outcomes.objects.filter(department=faculty_department, is_active=True)
            .only("pso_statement", "year")
            .order_by("-year")
        )

        # print("Vision Data => ", vision)
        # print("Mission Data => ", mission)
        # print(f"PEOs Count => {peos.count()}")
        # print(f"PSOs Count => {psos.count()}")

    except Exception as e:
        vision = mission = None
        peos = psos = []
        messages.warning(request, f"Unable to load department objectives: {str(e)}")

    # ✅ Birthday check (safe)
    dob = getattr(faculty, "dob", None)
    is_birthday = False
    try:
        today = now().date()
        if dob and (dob.month, dob.day) == (today.month, today.day):
            is_birthday = True
    except Exception:
        pass  # not critical

    # ✅ Combine data for caching
    data_context = {
        "is_birthday": is_birthday,
        "vision": vision,
        "mission": mission,
        "peos": peos,
        "psos": psos,
        "faculty": faculty,
        "department": faculty_department,
    }

    # ✅ Cache data only (no popup state)
    cache.set(cache_key, data_context, timeout=300)

    # ✅ Final render context (includes popup flag)
    final_context = {**data_context, "show_popup": show_popup}
    return render(request, "faculty_dashboard.html", final_context)
@never_cache
def student_dashboard(request):
    reg_no = getattr(request.user, "Employee_id", None)
    if not reg_no:
        messages.error(request, "Student ID not found. Please re-login.")
        return render(request, "student_dashboard.html", {"error": "User data missing."})

    # ✅ Create cache key per student
    cache_key = f"student_dashboard_data_{reg_no}"
    data_context = cache.get(cache_key)

    # ✅ Handle popup once per login
    show_popup = not request.session.get("student_dashboard_popup_shown", False)
    if show_popup:
        request.session["student_dashboard_popup_shown"] = True

    # ✅ If cached, reuse data (merge popup logic)
    if data_context:
        data_context["show_popup"] = show_popup
        return render(request, "student_dashboard.html", data_context)

    # ------------------- DB Fetch Starts -------------------
    try:
        student = (
            StudentDetails.objects
            .select_related("department", "department__degree")
            .filter(reg_no=reg_no)
            .first()
        )

        if not student:
            messages.warning(request, "Student record not found.")
            department = None
        else:
            department = getattr(student, "department", None)

    except Exception as e:
        messages.error(request, f"Error loading student data: {str(e)}")
        student = department = None

    # ✅ Vision, Mission, PEO, PSO — all filtered by department
    try:
        vision = (
            Vision.objects.filter(department=department, is_active=True)
            .only("vision_statement", "year")
            .order_by("-year")
            .first()
        )
        mission = (
            Mission.objects.filter(department=department, is_active=True)
            .only("mission_statement", "year")
            .order_by("-year")
            .first()
        )

        peos = (
            Program_Educational_Objective.objects.filter(department=department, is_active=True)
            .only("peo_statement", "year")
            .order_by("-year")
        )

        psos = (
            Program_specific_Outcomes.objects.filter(department=department, is_active=True)
            .only("pso_statement", "year")
            .order_by("-year")
        )

        # print(f"Vision => {vision}")
        # print(f"Mission => {mission}")
        # print(f"PEOs => {peos.count()}")
        # print(f"PSOs => {psos.count()}")

    except Exception as e:
        vision = mission = None
        peos = psos = []
        messages.warning(request, f"Unable to load department objectives: {str(e)}")

    # ✅ Birthday check (safe)
    is_birthday = False
    dob = getattr(student, "date_of_birth", None)
    try:
        today = now().date()
        if dob and (dob.month, dob.day) == (today.month, today.day):
            is_birthday = True
    except Exception:
        pass  # Don't break page

    # ✅ Module access based on the student's role permissions.
    # Each module app keeps its own per-role permission table; a card is shown
    # only if the student's role has at least one enabled permission there.
    from course_management.models import CourseandexaminationFunction
    from student_management.models import StudentManagementPermissions
    from fee_management.models import FeePerimissonFunction
    from feedback_management.models import FeedbackPermission
    from library_management.models import Library_Permissions
    from data_center_management.models import Data_Center_Permission
    from faculty_management.models import FacultyFunction

    role_id = getattr(request.user, "role_id", None)

    def _role_has_access(model):
        # Filter by role_id to avoid cross-database FK resolution against the default DB.
        try:
            return model.objects.filter(role_id=role_id, permission=True).exists()
        except Exception:
            return False

    module_access = {
        "courses": _role_has_access(CourseandexaminationFunction),
        "academic": _role_has_access(StudentManagementPermissions),
        "fee": _role_has_access(FeePerimissonFunction),
        "feedback": _role_has_access(FeedbackPermission),
        "library": _role_has_access(Library_Permissions),
        "data_center": _role_has_access(Data_Center_Permission),
        "support": _role_has_access(FacultyFunction),
    }

    # ✅ Cache data
    data_context = {
        "is_birthday": is_birthday,
        "vision": vision,
        "mission": mission,
        "peos": peos,
        "psos": psos,
        "student": student,
        "department": department,
        "module_access": module_access,
    }

    cache.set(cache_key, data_context, timeout=300)

    final_context = {**data_context, "show_popup": show_popup}
    return render(request, "student_dashboard.html", final_context)


@no_cache
def parent_dashboard(request):
    return render(request, "parent_dashboard.html")



@no_cache
@is_super_user('admin_management')
def admin_management(request):
    return render(request,"admin_dashboards/admin_management.html")

# @faculty_login_required

from user_accounts.models import Department
from course_management.models import Course, CourseHours, Add_Department

@no_cache
@is_super_user('course_management')
def course_management(request):
    # Fetch all departments
    departments = Add_Department.objects.filter(is_active=True)
    department_stats = {}

    for dept in departments:
        # All courses for this department
        courses = Course.objects.filter(department=dept)
        course_ids = courses.values_list('id', flat=True)

        # All semester/course hours for the courses
        semester_courses = CourseHours.objects.filter(course_id__in=course_ids)

        # Initialize stats
        stats = {
            'total_credits': 0,
            'integrated_credits': 0,  # Lecture + Lab
            'theory_credits': 0,      # Only lecture
            'laboratory_credits': 0,  # Only lab
            'hsmc_credits': 0,
            'bsc_credits': 0,
            'eec_credits': 0,
            'pcc_credits': 0,
            'mc_credits': 0,
            'oec_credits': 0,
            'pec_credits': 0,
        }

        for sc in semester_courses:
            try:
                # Safe conversion to float
                credits = float(sc.credits or 0)
                lecture_hours = float(sc.leture_hpwk or 0)
                lab_hours = float(sc.laboratory_hpwk or 0)

                # Add to total credits
                stats['total_credits'] += credits

                # Categorize by lecture/lab
                if lecture_hours > 0 and lab_hours > 0:
                    stats['integrated_credits'] += credits
                elif lecture_hours > 0:
                    stats['theory_credits'] += credits
                elif lab_hours > 0:
                    stats['laboratory_credits'] += credits

                # Elective categories
                elective_type = (sc.course.elective or "").strip().upper()
                if elective_type in stats:
                    stats[f'{elective_type.lower()}_credits'] += credits

            except (ValueError, TypeError, AttributeError):
                # Skip problematic entries
                continue

        # Round all stats to 1 decimal and save
        department_stats[dept.id] = {
            'name': dept.Department,
            **{k: round(v, 1) for k, v in stats.items()}
        }

    return render(request, "admin_dashboards/admin_course_management.html", {
        'department_stats': department_stats
    })

@no_cache
@is_super_user('examination_management')
def examination_management(request):
    return render(request, "admin_dashboards/admin_examination_management.html")



@no_cache
@is_super_user('student_management')
def student_management(request):
    return render(request, "admin_dashboards/admin_student_management.html")


@no_cache
@is_super_user('faculty_management')
def faculty_management(request):
    return render(request, "admin_dashboards/admin_faculty_management.html")



@no_cache
@is_super_user('fee_management')
def fee_management(request):
    from fee_management.models import FeeType, ScholarshipType

    fee_types = FeeType.objects.all().order_by('name')
    scholarship_types = ScholarshipType.objects.all().order_by('name')
    open_modal = request.GET.get("open_modal")

    return render(
        request,
        "admin_dashboards/admin_fee_management.html",
        {
            "fee_types": fee_types,
            "scholarship_types": scholarship_types,
            "open_modal": open_modal,
        },
    )

@no_cache
@is_super_user('nba_management')
def nba_management(request):
    return render(request, "admin_dashboards/admin_nba_management.html")




@no_cache
@is_super_user('approval_management')
def approval_management(request):
    return render(request, "admin_dashboards/admin_approval_management.html")



@no_cache
@is_super_user('faculty_leave_management')
def faculty_leave_management(request):
    return render(request, "admin_dashboards/admin_faculty_leave_management.html")




@no_cache
@is_super_user('feedback_management')
def feedback_management(request):
    return render(request, "admin_dashboards/admin_feedback_management.html")





# @no_cache
# @is_super_user('feedback_management')
# def feedback_management(request):
#     return render(request, "admin_dashboards/admin_feedback_management.html")



@no_cache
@is_super_user('lms_management')
def lms_management(request):
    return render(request, "admin_dashboards/admin_lms_management.html")


@no_cache
@is_super_user('data_center_management')
def data_center_management(request):
    return render(request, "admin_dashboards/admin_data_center_management.html")



@no_cache
@is_super_user('library_management')
def library_management(request):
    return render(request, "admin_dashboards/admin_library_management.html")


@no_cache
@is_super_user('stock_management')
def stock_management(request):
    return render(request, "admin_dashboards/admin_stock_management.html")


