from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password

from user_accounts.models import PersonalDetails, Student, StudentDetails
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.db import transaction
from django.contrib.auth.hashers import make_password
from course_management.models import Add_Department
from user_accounts.models import *


def check_aadhar(request):
    if request.method == "POST":
        aadhar = request.POST.get("aadhar")

        # Check Aadhaar in PersonalDetails (admissionform DB)
        personal = (
            PersonalDetails.objects.using("admissionform1")
            .filter(Aadhaar_Number=aadhar)
            .first()
        )
        # print("personal", personal)

        if personal:
            # Fetch admission record to get Department
            admission = (
                AdmissionRecords.objects.using("admissionform1")
                .filter(PersonalDetailsId=personal.id)
                .first()
            )
            if not admission:
                messages.error(request, "No admission record found for this Aadhaar.")
                return redirect("check_aadhar")

            # department_code = admission.Department if admission.Department and len(admission.Department.split()) > 1 else None
            department = Add_Department.objects.get(
                Department__iexact=admission.Department,
                degree__degree_code=admission.degree,
                is_active=True,
            )
            department_name = department.Department

            if not department_name:
                messages.error(
                    request,
                    "Invalid department format in admission records. Please contact admin.",
                )
                return redirect("check_aadhar")

            # Store Aadhaar in session and go to signup page
            request.session["aadhar"] = aadhar
            request.session["department_name"] = department_name
            messages.info(
                request,
                f"Aadhaar verified for {personal.name}. Please enter Roll Number and set your password.",
            )
            return redirect("student_sign_up")
        else:
            messages.error(request, "Aadhaar number not registered.")
            return redirect("check_aadhar")

    return render(request, "student_authentication/check_aadhar.html")


from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.hashers import make_password


from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth import login
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

# At the top of the file or in settings
DEPT_DICT = {
    "CSE": "CS",
    "IT": "IT",
    "EEE": "EE",
    "CSBS": "CB",
    "AIML": "AL",
    "MECH": "ME",
    "ECE": "EC",
    "CIVIL": "CE",
    "AD": "AD",
}


def student_sign_up(request):
    # 🔹 Retrieve session values
    aadhar = request.session.get("aadhar")
    department_name = request.session.get("department_name")
    # # print("DEBUG: Aadhaar from session ->", aadhar, "| Dept code from session ->", department_name)

    # 🔹 Session validation
    if not aadhar:
        messages.error(request, "Session expired. Please verify Aadhaar again.")
        return redirect("check_aadhar")

    # 🔹 Get student details from admission DB
    personal = (
        PersonalDetails.objects.using("admissionform1")
        .filter(Aadhaar_Number=aadhar)
        .first()
    )
    admission = (
        AdmissionRecords.objects.using("admissionform1")
        .filter(PersonalDetailsId=personal.id)
        .first()
    )
    if not personal:
        messages.error(
            request, "Aadhaar not found in admission records. Please contact admin."
        )
        return redirect("check_aadhar")

    student_name = personal.name
    # print(department_name)
    # 🔹 Validate department mapping
    if not department_name:
        messages.error(request, "Invalid department. Please contact admin.")
        return redirect("check_aadhar")

    # 🔹 Fetch department object safely
    try:
        department_obj = Department.objects.using("rit_approval_system").get(
            Department__iexact=department_name
        )
        # print(department_obj)
        department = Add_Department.objects.get(
            Department__iexact=department_name,
            is_active=True,
            degree__degree_code=admission.degree,
        )
    except Department.DoesNotExist:
        messages.error(request, "Department not found. Please contact admin.")
        return redirect("check_aadhar")

    # 🔹 Handle POST request
    if request.method == "POST":
        roll_no = request.POST.get("roll_no", "").strip().upper()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        

        # 🔹 Field validations
        if not all([roll_no, email, password, confirm_password]):
            messages.error(request, "All fields are required.")
            return redirect("student_sign_up")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("student_sign_up")

        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Invalid email format.")
            return redirect("student_sign_up")

        # 🔹 Duplicate user checks
        user_qs = USER.objects.using("rit_approval_system")
        if user_qs.filter(unique_id=aadhar).exists():
            messages.error(request, "User already registered with this Aadhaar.")
            return redirect("student_sign_up")
        if user_qs.filter(Employee_id=roll_no).exists():
            messages.error(request, "Roll Number already registered.")
            return redirect("student_sign_up")
        if user_qs.filter(email=email).exists():
            messages.error(request, "Email already registered.")
            return redirect("student_sign_up")

        # 🔹 Academic link fetching with safe fallbacks
        try:
            personal_record = AdmissionRecords.objects.using("admissionform1").get(
                PersonalDetailsId=personal.id
            )
            # academic = AcademicDetails.objects.using("admissionform1").get(id=personal_record.AcademicDetailsId)
            academic = personal_record.AcademicDetailsId
        except Exception as e:
            # print("DEBUG: Admission/Academic fetch error ->", e)
            messages.error(request, "Admission record not found. Please contact admin.")
            return redirect("student_sign_up")

        # 🔹 Create user + student atomically
        try:
            with transaction.atomic(using="rit_approval_system"):
                student_role = (
                    Role.objects.using("rit_approval_system")
                    .filter(role="Student")
                    .first()
                )
                if not student_role:
                    messages.error(
                        request, "Student role not found. Please contact admin."
                    )
                    return redirect("student_sign_up")

                # ✅ Create user record
                user = USER.objects.using("rit_approval_system").create(
                    username=student_name,
                    Employee_id=roll_no,
                    role=student_role,
                    unique_id=aadhar,
                    email=email,
                    password=make_password(password),
                    Department=department_obj,
                    is_student=True,
                    is_staff=False,
                    is_superuser=False,
                    last_login=timezone.now(),
                )

                # ✅ Create linked student record in local DB
                StudentDetails.objects.create(
                    name=student_name,
                    reg_no=roll_no,
                    aadhar_number=aadhar,
                    email=email,
                    year="1",
                    semester="1",
                    department=department,
                    mobile_no=personal.personal_mobile_no,
                    date_of_birth=personal.date_of_birth,
                    gender=personal.gender,
                    age=personal.age,
                    batch=academic.AcademicYear,
                )
                personal.registration_no = roll_no
                personal.save(using="admissionform1")

            messages.success(request, "Account created successfully. Please login.")
            return redirect("student_login")

        except Exception as e:
            # print("DEBUG: Error while creating user/student ->", e)
            messages.error(request, f"Error creating account: {e}")
            return redirect("student_sign_up")

    # 🔹 Render sign-up page
    return render(request, "student_authentication/student_sign_up.html")


# from django.shortcuts import render, redirect
# from django.contrib import messages
# from django.contrib.auth import authenticate, login

# old student login
# def student_login(request):
#     if request.method == "POST":
#         login_id = request.POST.get("login_id")  # Student's Roll/Employee ID
#         password = request.POST.get("password")
        
#         # ✅ Check empty fields
#         if not login_id or not password:
#             messages.error(request, "All fields are required.")
#             return redirect("student_login")

#         # ✅ Authenticate
#         user = authenticate(request, Employee_id=login_id, password=password)

#         if user is None:
#             messages.error(request, "Invalid ID or password.")
#             return redirect("student_login")

#         # ❌ Block staff & superusers
#         if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
#             messages.error(request, "Staff and Admins cannot log in here.")
#             return redirect("student_login")

#         # ✅ Restrict only students
#         if not getattr(user, "is_student", False):
#             messages.error(request, "Only students can log in here.")
#             return redirect("student_login")

#         # ❌ If user is inactive
#         if hasattr(user, "is_active") and not user.is_active:
#             messages.error(request, "Your account is inactive. Contact admin.")
#             return redirect("student_login")

#         # ✅ Login user
#         login(request, user)

#         # ✅ Success
#         messages.success(request, f"Welcome {user.username}!")
#         return redirect("student_dashboard")

#     # GET → render login page
#     return render(request, "student_authentication/student_login.html")


from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils import timezone


def student_login(request):
    if request.method == "POST":
        login_id = request.POST.get("login_id", "").strip()
        password = request.POST.get("password")
        print("login id => ", login_id)
        print("password => ", password)
        print("hashed password => ", check_password(password,make_password(password)))
        
        # 🔹 Empty field check
        if not login_id or not password:
            messages.error(request, "All fields are required.")
            return redirect("student_login")

        # 🔹 Authenticate user
        user = authenticate(request, Employee_id=login_id, password=password)
        print("user => ", user)
        # print("User => ", user)
        if user is None:
            messages.error(request, "Invalid ID or password.")
            return redirect("student_login")

        # 🔹 Block staff & superusers
        if user.is_staff or user.is_superuser:
            messages.error(request, "Staff and Admins cannot log in here.")
            return redirect("student_login")

        # 🔹 Allow only students
        if not getattr(user, "is_student", False):
            messages.error(request, "Only students can log in here.")
            return redirect("student_login")

        # 🔹 Inactive check
        if not user.is_active:
            messages.error(request, "Your account is inactive. Contact admin.")
            return redirect("student_login")

        # ======================================================
        # 🔹 SYNC REGISTRATION NUMBER INTO ADMISSION DB
        # ======================================================
        try:
            # 1️⃣ Get student details using reg_no
            student = StudentDetails.objects.filter(reg_no=login_id).first()

            if student and student.aadhar_number:
                # 2️⃣ Fetch personal details from admission DB
                personal = (
                    PersonalDetails.objects.using("admissionform1")
                    .filter(Aadhaar_Number=student.aadhar_number)
                    .first()
                )

                # 3️⃣ Save reg_no only if not already present
                if personal and not personal.registration_no:
                    personal.registration_no = login_id
                    personal.save(using="admissionform1")

        except Exception as e:
            pass  # Fail silently; this is a non-critical sync

        # 🔐 Force password change for students still on the default password (123)
        if check_password("123", user.password):
            request.session["force_pw_change_employee_id"] = login_id
            request.session["force_pw_change_redirect"] = "student_login"
            return redirect("set_new_password")

        login(request, user)

        messages.success(request, f"Welcome {user.username}!")
        return redirect("student_dashboard")

    # GET request
    return render(request, "student_authentication/student_login.html")
 


from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth import authenticate, login, get_user_model

from student_management.models import PersonalDetails, StudentDetails

# def student_login(request):
#     if request.method == "POST":
#         login_id = (request.POST.get("login_id") or "").strip()
#         password = (request.POST.get("password") or "").strip()

#         # ✅ Required fields
#         if not login_id or not password:
#             messages.error(request, "All fields are required.")
#             return redirect("student_login")

#         # ✅ Use the actual USERNAME_FIELD of your custom user model
#         # User = get_user_model()
#         # login_kwargs = {User.USERNAME_FIELD: login_id, "password": password}

#         # user = authenticate(request, **login_kwargs)
#         user = authenticate(request, Employee_id=login_id, password=password)
#         # ✅ Invalid creds
#         if user is None:
#             messages.error(request, "Invalid ID or password.")
#             return redirect("student_login")

#         # ❌ Block staff & superusers
#         if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
#             messages.error(request, "Staff and Admins cannot log in here.")
#             return redirect("student_login")

#         # ✅ Restrict only students
#         if not getattr(user, "is_student", False):
#             messages.error(request, "Only students can log in here.")
#             return redirect("student_login")

#         # ❌ Inactive users
#         if hasattr(user, "is_active") and not user.is_active:
#             messages.error(request, "Your account is inactive. Contact admin.")
#             return redirect("student_login")

#         # ✅ At this point, the user is allowed. Now resolve external records and create StudentDetails.
#         #    Use transaction to avoid partial writes. Guard every external dependency.

#         # You appear to rely on user.unique_id (Aadhaar link) and user.Department.Department.
#         # Validate presence before using.
#         if not hasattr(user, "unique_id") or not user.unique_id:
#             messages.error(request, "Your profile is missing a required identifier. Contact admin.")
#             return redirect("student_login")

#         # Department name (case-insensitive match in Add_Department)
#         department_name = None
#         # If user.Department is a FK with field 'Department', guard access
#         if hasattr(user, "Department") and user.Department:
#             department_name = getattr(user.Department, "Department", None)

#         if not department_name:
#             messages.error(request, "Your profile is missing a department. Contact admin.")
#             return redirect("student_login")

#         try:
#             dept_obj = Add_Department.objects.get(Department__iexact=department_name, is_active=True)
#         except Add_Department.DoesNotExist:
#             messages.error(request, "Department is not active or not found. Contact admin.")
#             return redirect("student_login")

#         # 🔒 Cross-database lookups
#         personal = PersonalDetails.objects.using("admissionform1").filter(
#             Aadhaar_Number=user.unique_id
#         ).first()
#         if not personal:
#             messages.error(request, "No personal record found for your Aadhaar. Contact admin.")
#             return redirect("student_login")

#         admission = AdmissionRecords.objects.using("admissionform1").filter(
#             PersonalDetailsId=personal.id
#         ).first()
#         if not admission:
#             messages.error(request, "No admission record found. Contact admin.")
#             return redirect("student_login")

#         academic = getattr(admission, "AcademicDetailsId", None)
#         batch = getattr(academic, "AcademicYear", None)

#         # Some of your fields assume certain naming; guard them
#         name = getattr(personal, "name", None) or getattr(personal, "full_name", None) or ""
#         reg_no = getattr(user, "Employee_id", None) or getattr(user, "employee_id", None) or login_id
#         aadhar_number = getattr(personal, "Aadhaar_Number", None) or user.unique_id
#         email = getattr(user, "email", "") or ""

#         mobile_no = getattr(personal, "personal_mobile_no", None) or getattr(personal, "mobile_no", None)
#         date_of_birth = getattr(personal, "date_of_birth", None)
#         age = getattr(personal, "age", None)
#         gender = getattr(personal, "gender", None)

#         # ✅ Create or reuse StudentDetails atomically
#         try:
#             with transaction.atomic():
#                 student_obj, created = StudentDetails.objects.get_or_create(
#                     reg_no=reg_no,  # assume reg_no is unique for a student
#                     defaults={
#                         "name": name,
#                         "aadhar_number": aadhar_number,
#                         "email": email,
#                         "year": "1",
#                         "semester": "1",
#                         "department": dept_obj,
#                         "mobile_no": mobile_no,
#                         "date_of_birth": date_of_birth,
#                         "batch": batch,
#                         "gender": gender,
#                         "age": age,

#                     },
#                 )

#                 # If the record exists, you might still want to sync some fields
#                 if not created:
#                     # Light, safe updates (avoid clobbering user-changed data)
#                     updated = False
#                     if not student_obj.aadhar_number and aadhar_number:
#                         student_obj.aadhar_number = aadhar_number
#                         updated = True
#                     if not student_obj.department_id and dept_obj:
#                         student_obj.department = dept_obj
#                         updated = True
#                     if not student_obj.batch and batch:
#                         student_obj.batch = batch
#                         updated = True
#                     if updated:
#                         student_obj.save()

#         except Exception as e:
#             messages.error(request, f"Could not create student profile: {e}")
#             return redirect("student_login")

#         # ✅ Finally log the user in
#         login(request, user)

#         messages.success(request, f"Welcome {getattr(user, 'username', login_id)}!")
#         return redirect("student_dashboard")

#     # GET → render login page
#     return render(request, "student_authentication/student_login.html")


def student_logout(request):
    # Clear all session data
    request.session.flush()

    # Optional: message
    messages.success(request, "You have been logged out successfully.")

    # Redirect to login page
    return redirect("student_login")
