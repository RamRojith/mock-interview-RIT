from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse


from django.shortcuts import render

# Create your views here.
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import logout

from user_accounts.forms import EmployeeLoginForm

from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls.resolvers import get_resolver, URLPattern

from user_accounts.urls import admin_urls


def admin_view_names():
    from django.contrib import admin
    # admin_urls = admin.site.urls
    resolver = get_resolver(admin_urls)
    view_names = []

    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLPattern):
            view_names.append(pattern.name)              
    return view_names


def login_view(request):
    if request.method == 'POST':
        form = EmployeeLoginForm(request.POST)
        if form.is_valid():
            employee_id = form.cleaned_data['Employee_id']
            password = form.cleaned_data['password']

            user = authenticate(request, Employee_id=employee_id, password=password)

            if user:
                # ❌ Block students
                if hasattr(user, "is_student") and user.is_student:
                    form.add_error(None, "Students are not allowed to login here.")
                    return render(request, 'login.html', {'form': form})

                # 🔐 Force password change for users still on the default password (123)
                from django.contrib.auth.hashers import check_password
                if check_password("123", user.password):
                    request.session["force_pw_change_employee_id"] = employee_id
                    request.session["force_pw_change_redirect"] = "login_view"
                    return redirect("set_new_password")

                # ✅ Staff / Superuser login
                login(request, user)
                request.session["employee_id"] = employee_id  # store for custom checks
                # print("Login successful")
                # print("Password => ", password)

                # ✅ Admin login
                if employee_id == "0000" or user.is_superuser:
                    request.session['app_name'] = "Admin Portal"
                    request.session['pages'] = list(
                        sorted(
                            {
                                word.replace('_', ' ').title(): word
                                for word in set(admin_view_names())
                            }.items(),
                            key=lambda item: len(item[0]),
                            reverse=False
                        )
                    )
                    # print("Admin logged in")
                    messages.success(request, "Authentication successful. Welcome to Admin Portal.")
                    return redirect('home')

                # ✅ Faculty login — redirect to profile form if not yet filled
                from faculty_management.models import general_information as FM_GeneralInfo
                if not FM_GeneralInfo.objects.filter(faculty_id=employee_id).exists():
                    messages.info(request, "Please complete your profile to continue.")
                    return redirect('faculty_general_information')
                return redirect('faculty_dashboard')

            else:
                form.add_error(None, "Invalid Employee ID or Password")
    else:
        form = EmployeeLoginForm()

    return render(request, 'login.html', {'form': form})
  
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError, transaction

from user_accounts.models import USER, NewUserAdder, Department, Role


def faculty_sign_up(request):
    request.session.flush()

    departments = Department.objects.using("rit_approval_system").all().order_by("Department")
    roles = Role.objects.using("rit_approval_system").all().order_by("role")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        employee_id = request.POST.get("Employee_id", "").strip()
        department_id = request.POST.get("Department", "").strip()
        role_id = request.POST.get("role", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not all([username, employee_id, department_id, role_id, email, password, confirm_password]):
            messages.error(request, "All fields are required.")
            return render(request, "faculty_sign_up.html", {"departments": departments, "roles": roles})

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "faculty_sign_up.html", {"departments": departments, "roles": roles})

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return render(request, "faculty_sign_up.html", {"departments": departments, "roles": roles})

        try:
            dept = Department.objects.using("rit_approval_system").get(id=department_id)
            role = Role.objects.using("rit_approval_system").get(id=role_id)
        except (Department.DoesNotExist, Role.DoesNotExist):
            messages.error(request, "Invalid department or role selected.")
            return render(request, "faculty_sign_up.html", {"departments": departments, "roles": roles})

        verify = NewUserAdder.objects.using("rit_approval_system").filter(
            Employee_id=employee_id, role=role, Department=dept
        ).first()

        if not verify:
            messages.error(request, "Invalid credentials. Employee ID, department, or role not pre-authorized. Please contact admin.")
            return render(request, "faculty_sign_up.html", {"departments": departments, "roles": roles})

        unique_id = f"{dept.Department_code}{employee_id}{role.role}"

        try:
            with transaction.atomic(using="rit_approval_system"):
                USER.objects.using("rit_approval_system").create(
                    username=username,
                    Employee_id=employee_id,
                    role=role,
                    Department=dept,
                    unique_id=unique_id,
                    email=email,
                    password=make_password(password),
                    is_student=False,
                    is_parent=False,
                    is_staff=True,
                    is_active=True,
                )

            user = authenticate(request, Employee_id=employee_id, password=password)
            if user:
                login(request, user)
                request.session["employee_id"] = employee_id
                messages.success(request, f"Account created successfully! Welcome, {username}. Please complete your profile.")
                return redirect("faculty_general_information")

            messages.success(request, "Account created successfully! Please login.")
            return redirect("login_view")

        except IntegrityError as e:
            if "unique_id" in str(e):
                messages.error(request, "An account already exists with this Employee ID, department, and role.")
            elif "email" in str(e):
                messages.error(request, "This email address is already registered.")
            else:
                messages.error(request, f"An error occurred: {e}")

    return render(request, "faculty_sign_up.html", {"departments": departments, "roles": roles})




from django.shortcuts import render, redirect, get_object_or_404
from user_accounts.models import general_information as UA_GeneralInfo, Add_Department
from faculty_management.models import general_information as FM_GeneralInfo, DesignationMaster

# def login_view(request):
#     if request.method == 'POST':
#         form = EmployeeLoginForm(request.POST)
#         if form.is_valid():
#             employee_id = form.cleaned_data.get('Employee_id')
#             password = form.cleaned_data.get('password')

#             # 🔍 Authenticate user — ensure backend supports Employee_id
#             user = authenticate(request, Employee_id=employee_id, password=password)

#             if user is not None:
#                 # ❌ Block student login (if applicable)
#                 if getattr(user, "is_student", False):
#                     form.add_error(None, "Students are not allowed to login here.")
#                     return render(request, 'login.html', {'form': form})

#                 # ✅ Login success
#                 login(request, user)
#                 request.session["employee_id"] = employee_id

#                 # ✅ Admin login (for employee_id "0000" or superuser)
#                 if employee_id == "0000" or user.is_superuser:
#                     request.session['app_name'] = "Admin Portal"
#                     messages.success(request, "Authentication successful. Welcome to Admin Portal.")
#                     # print(f"🛠 Admin login detected for {employee_id}")
#                     return redirect('home')

#                 # ✅ Faculty login — data sync logic
#                 try:
#                     # Step 1: Get faculty data from user_accounts DB
#                     ua_data = (
#                         UA_GeneralInfo.objects.using('rit_academic_system')
#                         .filter(faculty_id=employee_id)
#                         .first()
#                     )

#                     if ua_data:
#                         # Step 2: Sync to faculty_management
#                         fm_data, created = FM_GeneralInfo.objects.get_or_create(
#                             faculty_id=employee_id
#                         )

#                         # Step 3: Map all relevant fields safely
#                         fm_data.name = ua_data.name or fm_data.name

#                         # 🔧 Handle Foreign Keys properly
#                         if ua_data.department:
#                             dept = Add_Department.objects.filter(
#                                 Department=ua_data.department
#                             ).first()
#                             if dept:
#                                 fm_data.department = dept

#                         if ua_data.designation:
#                             desig = DesignationMaster.objects.filter(
#                                 designation_name=ua_data.designation
#                             ).first()
#                             if desig:
#                                 fm_data.designation = desig

#                         # Copy simple fields
#                         fm_data.dob = ua_data.dob
#                         fm_data.address = ua_data.address
#                         fm_data.personal_email = ua_data.personal_email
#                         fm_data.college_email = ua_data.college_email
#                         fm_data.phone = ua_data.phone
#                         fm_data.blood_group = ua_data.blood_group
#                         fm_data.community = ua_data.community
#                         fm_data.caste = ua_data.caste
#                         fm_data.religion = ua_data.religion
#                         fm_data.doj = ua_data.doj
#                         fm_data.apaar_id = ua_data.apaar_id
#                         fm_data.anu_id = ua_data.anu_id
#                         fm_data.aicte_id = ua_data.aicte_id
#                         fm_data.annauniversity_affiliation_id = ua_data.annauniversity_affiliation_id
#                         fm_data.PAN_number = ua_data.PAN_number
#                         fm_data.Aadhar_number = ua_data.Aadhar_number
#                         fm_data.PAN_certificate = ua_data.PAN_certificate
#                         fm_data.Aadhar_certificate = ua_data.Aadhar_certificate
#                         fm_data.approval = ua_data.approval

#                         fm_data.save()

#                         if created:
#                             # print(f"✅ Faculty data inserted for {employee_id}")
#                         else:
#                             # print(f"🔄 Faculty data updated for {employee_id}")

#                 except Exception as e:
#                     # print(f"⚠️ Error syncing faculty data for {employee_id}: {e}")

#                 # Redirect after successful faculty login
#                 messages.success(request, f"Welcome back, {user.username}!")
#                 return redirect('faculty_dashboard')

#             # ❌ Authentication failed
#             else:
#                 form.add_error(None, "Invalid Employee ID or Password")
#     else:
#         form = EmployeeLoginForm()

#     return render(request, 'login.html', {'form': form})



def logout_view(request):
    if request.method == "POST":
        logout(request)
    return redirect('index')

def parent_login(request):
    logout(request)
    return redirect('http://172.16.11.3.249:9000/')