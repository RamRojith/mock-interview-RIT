from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.decorators import login_required
from user_accounts.models import USER
import random, datetime

# ---------------- STEP 1: Forgot Password ----------------
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


# ---------------- STEP 1: Forgot Password ----------------
def forgot_password(request):
    if request.method == "POST":
        employee_id = request.POST.get("employee_id")

        if not employee_id:
            messages.error(request, "Please enter your Employee ID.")
            return redirect("forgot_password")

        # Get first user for email (Employee may have multiple roles)
        user = USER.objects.using("rit_approval_system").filter(
            Employee_id=employee_id
        ).first()

        if not user:
            messages.error(request, "Invalid Employee ID.")
            return redirect("forgot_password")

        if not user.email:
            messages.error(request, "No email registered with this account.")
            return redirect("forgot_password")

        # Generate OTP
        otp = str(random.randint(100000, 999999))
        expiry = timezone.now() + datetime.timedelta(minutes=10)

        # Store OTP in session
        request.session["otp_code"] = otp
        request.session["otp_user_id"] = employee_id
        request.session["otp_expiry"] = expiry.isoformat()

        context = {
            "username": user.username,
            "otp": otp,
            "valid_minutes": 10,
        }

        subject = "Your OTP for Password Reset"
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [user.email]

        text_content = f"Your OTP for password reset is {otp}."
        html_content = render_to_string("emails/otp_email.html", context)

        try:
            msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
            msg.attach_alternative(html_content, "text/html")
            msg.send()

            messages.success(
                request, f"OTP sent to your registered email ({user.email})."
            )
            return redirect("verify_otp")

        except Exception:
            messages.error(request, "Error sending OTP email. Try again later.")
            return redirect("forgot_password")

    return render(request, "password/forgot_password.html")


# ---------------- STEP 2: Verify OTP ----------------
def verify_otp(request):
    if request.method == "POST":

        entered_otp = request.POST.get("otp")
        otp_code = request.session.get("otp_code")
        otp_user_id = request.session.get("otp_user_id")
        otp_expiry = request.session.get("otp_expiry")

        if not entered_otp:
            messages.error(request, "Please enter the OTP.")
            return redirect("verify_otp")

        if not otp_code or not otp_user_id or not otp_expiry:
            messages.error(request, "Session expired. Please request a new OTP.")
            return redirect("forgot_password")

        expiry_time = timezone.datetime.fromisoformat(otp_expiry)

        if timezone.now() > expiry_time:
            messages.error(request, "OTP expired. Request a new one.")
            return redirect("forgot_password")

        if entered_otp != otp_code:
            messages.error(request, "Invalid OTP. Please try again.")
            return redirect("verify_otp")

        # OTP verified
        request.session["otp_verified"] = True

        messages.success(request, "OTP verified successfully. Please set a new password.")
        return redirect("reset_password")

    return render(request, "password/verify_otp.html")


# ---------------- STEP 3: Reset Password ----------------
def reset_password(request):

    otp_verified = request.session.get("otp_verified")
    otp_user_id = request.session.get("otp_user_id")

    if not otp_verified or not otp_user_id:
        messages.error(request, "Unauthorized access. Please verify OTP first.")
        return redirect("forgot_password")

    if request.method == "POST":

        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if not new_password or not confirm_password:
            messages.error(request, "All fields are required.")
            return redirect("reset_password")

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("reset_password")

        users = USER.objects.using("rit_approval_system").filter(
            Employee_id=otp_user_id
        )

        if not users.exists():
            messages.error(request, "User not found.")
            return redirect("forgot_password")

        # Hash password
        hashed_password = make_password(new_password)

        # Update ALL records of that employee
        users.update(password=hashed_password)

        # Clear session
        for key in ["otp_code", "otp_user_id", "otp_expiry", "otp_verified"]:
            if key in request.session:
                del request.session[key]

        messages.success(request, "Password changed successfully! You can now log in.")
        return redirect("/")

    return render(request, "password/reset_password.html")


# ---------------- FORCE SET NEW PASSWORD (default 123 users only) ----------------
def set_new_password(request):
    # This flow is only reachable right after logging in with the default password (123)
    employee_id = request.session.get("force_pw_change_employee_id")

    if not employee_id:
        messages.error(request, "Unauthorized access. Please log in first.")
        return redirect("login_view")

    if request.method == "POST":
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if not new_password or not confirm_password:
            messages.error(request, "All fields are required.")
            return redirect("set_new_password")

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("set_new_password")

        if len(new_password) < 4:
            messages.error(request, "Password must be at least 4 characters.")
            return redirect("set_new_password")

        if new_password == "123":
            messages.error(request, "New password cannot be the default password.")
            return redirect("set_new_password")

        users = USER.objects.using("rit_approval_system").filter(
            Employee_id=employee_id
        )

        if not users.exists():
            messages.error(request, "User not found.")
            return redirect("login_view")

        # Hash and update ALL records of that employee (multiple roles)
        users.update(password=make_password(new_password))

        # Remember which login page to send them back to, then clear the flags
        login_redirect = request.session.get("force_pw_change_redirect", "login_view")
        del request.session["force_pw_change_employee_id"]
        if "force_pw_change_redirect" in request.session:
            del request.session["force_pw_change_redirect"]

        messages.success(request, "Password set successfully! Please log in with your new password.")
        return redirect(login_redirect)

    return render(request, "password/set_new_password.html")


@login_required
def change_logged_in_password(request):
    if request.method != "POST":
        return redirect(request.META.get("HTTP_REFERER") or "home")

    current_password = request.POST.get("current_password")
    new_password = request.POST.get("new_password")
    confirm_password = request.POST.get("confirm_password")
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "home"

    if not current_password or not new_password or not confirm_password:
        messages.error(request, "All password fields are required.")
        return redirect(next_url)

    if new_password != confirm_password:
        messages.error(request, "New passwords do not match.")
        return redirect(next_url)

    if len(new_password) < 4:
        messages.error(request, "Password must be at least 4 characters.")
        return redirect(next_url)

    if new_password == "123":
        messages.error(request, "New password cannot be the default password.")
        return redirect(next_url)

    employee_id = getattr(request.user, "Employee_id", None)
    if not employee_id:
        messages.error(request, "Unable to identify the logged-in user.")
        return redirect(next_url)

    users = USER.objects.using("rit_approval_system").filter(Employee_id=employee_id)
    current_user = users.filter(pk=getattr(request.user, "id", None)).first() or users.first()

    if not current_user:
        messages.error(request, "Logged-in user not found.")
        return redirect(next_url)

    if not check_password(current_password, current_user.password):
        messages.error(request, "Current password is incorrect.")
        return redirect(next_url)

    users.update(password=make_password(new_password))
    messages.success(request, "Password changed successfully.")
    return redirect(next_url)
