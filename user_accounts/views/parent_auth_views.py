from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password

from user_accounts.models import PersonalDetails, Student
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.db import transaction
from django.contrib.auth.hashers import make_password

from user_accounts.models import *

def parent_check_aadhar(request):
    if request.method == "POST":
        aadhar = request.POST.get("aadhar")

        # Check Aadhaar in PersonalDetails (admissionform DB)
        personal = PersonalDetails.objects.using('admissionform1').filter(Aadhaar_Number=aadhar).first()
        # print("personal", personal)

        if personal:
            # Fetch admission record to get Department
            admission = AdmissionRecords.objects.using('admissionform1').filter(PersonalDetailsId=personal.id).first()
            if not admission:
                messages.error(request, "No admission record found for this Aadhaar.")
                return redirect("parent_check_aadhar")

            # Debug the Department field
            # print(f"DEBUG: Admission record found - Department: {admission.Department}")
            # department_code = admission.Department if admission.Department and len(admission.Department.split()) > 1 else None
            department = Add_Department.objects.get(Department__contains=admission.Department, is_active=True)
            department_code = department.Department
            if not department_code:
                messages.error(request, "Invalid department format in admission records. Please contact admin.")
                return redirect("parent_check_aadhar")

            # Store Aadhaar in session and go to signup page
            request.session["aadhar"] = aadhar
            request.session["department_code"] = department_code
            # print('request.session["department_code"] => ', request.session["department_code"])
            messages.info(request, f"Aadhaar verified for {personal.name}. Please enter Roll Number and set your password.")
            return redirect("parent_sign_up")
        else:
            messages.error(request, "Aadhaar number not registered.")
            return redirect("parent_check_aadhar")

    return render(request, "parent_authentication/parent_check_aadhar.html")




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
    "AD": "AD"
}


def parent_sign_up(request):
    aadhar = request.session.get("aadhar")
    department_code = request.session.get("department_code")
    # print("DEBUG: Aadhaar from session ->", aadhar, "Dept code from session ->", department_code)

    if not aadhar:
        messages.error(request, "Session expired. Please verify Aadhaar again.")
        return redirect("parent_check_aadhar")

    # 🔹 Get student details from admission DB
    personal = PersonalDetails.objects.using('admissionform1').filter(Aadhaar_Number=aadhar).first()
    # print("personal details => ", personal)
    if not personal:
        messages.error(request, "Aadhaar not found in admission records. Please contact admin.")
        return redirect("parent_check_aadhar")

    student_name = personal.name
    parent_name = personal.father_name

    # 🔹 Resolve department
    if not department_code:
        # print(f"DEBUG: Department code {department_code} not found in DEPT_DICT: {DEPT_DICT}")
        messages.error(request, "Invalid department. Please contact admin.")
        return redirect("parent_check_aadhar")

    try:
        department_obj = Department.objects.using("rit_approval_system").get(Department__iexact=department_code)
        department_id = department_obj.id
    except Department.DoesNotExist:
        messages.error(request, "Department not found. Please contact admin.")
        return redirect("parent_check_aadhar")

    if request.method == "POST":
        roll_no = request.POST.get("roll_no", "").strip().upper()
        email = request.POST.get("email", "").strip().lower()
        role = request.POST.get("role", "").strip()
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        

        # 🔹 Validation
        if not roll_no or not email or not password or not confirm_password:
            messages.error(request, "All fields are required.")
            return redirect("parent_sign_up")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("parent_sign_up")

        # 🔹 Validate email format
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Invalid email format.")
            return redirect("parent_sign_up")

        unique_aadhar = f"parent_{aadhar}"

        # 🔹 Duplicate checks
        if USER.objects.using("rit_approval_system").filter(unique_id=unique_aadhar).exists():
            # print("Aadhar ===> ", USER.objects.using("rit_approval_system").filter(unique_id=unique_aadhar, is_parent=True).exists())
            messages.error(request, "User already registered with this Aadhaar.")
            return redirect("parent_sign_up")

        
        if USER.objects.using("rit_approval_system").filter(role_id=role).exists():
            messages.error(request, "Role already registered.")
            return redirect("parent_sign_up")

        if USER.objects.using("rit_approval_system").filter(email=email, is_parent=True).exists():
            messages.error(request, "Email already registered.")
            return redirect("parent_sign_up")

        try:
            with transaction.atomic(using="rit_approval_system"):
                # 🔹 Get parent role
                try:
                    parent_role = Role.objects.using("rit_approval_system").get(id=role)
                except Role.DoesNotExist:
                    messages.error(request, "Parent role not found. Please contact admin.")
                    return redirect("parent_sign_up")

                # 🔹 Create parent user
                USER.objects.using("rit_approval_system").create(
                    username=f"{parent_name}",   # ✅ unique username
                    Employee_id=roll_no,
                    role=parent_role,
                    unique_id=unique_aadhar,
                    email=email,
                    password=make_password(password),
                    Department_id=department_id,
                    is_student=False,
                    is_parent=True,
                    is_staff=False,
                    is_superuser=False,
                )

            messages.success(request, "Parent account created successfully. Please login.")
            return redirect("parent_login")

        except Exception as e:
            # print("DEBUG: Error while creating parent user ->", str(e))
            messages.error(request, f"Error creating account: {e}")
            return redirect("parent_sign_up")

    roles = Role.objects.using("rit_approval_system").filter(role__in=["Parent", "Guardian"])

    return render(request, "parent_authentication/parent_sign_up.html", {"roles": roles})



from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login

def parent_login(request):
    if request.method == "POST":
        login_id = request.POST.get("login_id")
        password = request.POST.get("password")

        if not login_id or not password:
            messages.error(request, "All fields are required.")
            return redirect("parent_login")

        # 🔹 Fetch all parent accounts with this login_id
        parent_users = USER.objects.using("rit_approval_system").filter(Employee_id=login_id, is_parent=True)

        # 🔹 Verify password manually (since passwords are hashed)
        user_authenticated = None
        for user in parent_users:
            if check_password(password, user.password):
                user_authenticated = user
                break

        if not user_authenticated:
            messages.error(request, "Invalid ID or password.")
            return redirect("parent_login")

        user = user_authenticated

        # ❌ Block staff & superusers
        if user.is_staff or user.is_superuser:
            messages.error(request, "Staff and Admins cannot log in here.")
            return redirect("parent_login")

        # ❌ Students cannot login here
        if user.is_student:
            messages.error(request, "Students cannot log in here.")
            return redirect("parent_login")

        # ❌ If user is inactive
        if not user.is_active:
            messages.error(request, "Your account is inactive. Contact admin.")
            return redirect("parent_login")

        # 🔐 Force password change for parents still on the default password (123)
        if check_password("123", user.password):
            request.session["force_pw_change_employee_id"] = login_id
            request.session["force_pw_change_redirect"] = "parent_login"
            return redirect("set_new_password")

        # 🔹 Set backend manually
        from django.contrib.auth import get_backends
        backend = get_backends()[0]  # Use the first configured backend
        user.backend = f"{backend.__module__}.{backend.__class__.__name__}"

        # ✅ Login user
        login(request, user)

        messages.success(request, f"Welcome {user.username}!")
        return redirect("parent_dashboard")

    # GET → render login page
    return render(request, "parent_authentication/parent_login.html")



def parent_logout(request):
    # Clear all session data
    request.session.flush()

    # Optional: message
    messages.success(request, "You have been logged out successfully.")

    # Redirect to login page
    return redirect("parent_login")



