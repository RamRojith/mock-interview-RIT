import json
import re
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.db.models.deletion import ProtectedError

from user_accounts.decorators import check_permission, is_super_user, no_cache
from user_accounts.models import Role, Add_Department
from faculty_management.models import general_information

from stock_management.decorators import stock_management
from stock_management.models import (
    Stock_Permission, Lab, StockRegister, StockEntry, StockItem,
    TransferRequest, VerificationAssignment,
)
from stock_management.views.stock_common import (
    get_logged_in_faculty, current_financial_year,
)

logger = logging.getLogger(__name__)
APPROVAL_DB = "rit_approval_system"


# ------------------------------------------------------------------
# Permission assignment (same mechanism as the other apps)
# ------------------------------------------------------------------
@no_cache
@is_super_user('stock_management')
def stock_assign_permission(request):
    if request.method == 'POST':
        for role_name, role_permissions in request.POST.items():
            if role_name.startswith('permissions'):
                try:
                    extract_data = list(re.findall(r'\[([^\]]+)\]', role_name))
                    if len(extract_data) < 2:
                        messages.warning(request, f"Invalid format in role_name: {role_name}. Skipping.")
                        continue
                    extract_data.append(role_permissions)
                    try:
                        role = Role.objects.using("rit_approval_system").get(role=extract_data[0])
                    except Role.DoesNotExist:
                        messages.error(request, f"Role '{extract_data[0]}' does not exist. Skipping this entry.")
                        continue
                    if isinstance(role_permissions, list):
                        role_permissions = role_permissions[0]
                    permission = extract_data[2] == 'true'
                    obj = Stock_Permission.objects.filter(role=role, function=extract_data[1]).first()
                    if obj:
                        obj.permission = permission
                        obj.save()
                    else:
                        Stock_Permission.objects.create(role=role, function=extract_data[1], permission=permission)
                except Exception as e:
                    messages.error(request, f"An error occurred while processing '{role_name}': {str(e)}")
    messages.success(request, "The permission changes have been successfully applied.")
    return redirect('stock_management')


# ------------------------------------------------------------------
# Module entry + hello
# ------------------------------------------------------------------
@stock_management
def stock_home(request):
    request.session['current_page'] = 'stock_home'
    return redirect('home')


@stock_management
@check_permission("stock_hello")
def stock_hello(request):
    return render(request, "stock_hello.html")


# ------------------------------------------------------------------
# Dashboard (role-filtered KPIs)
# ------------------------------------------------------------------
@stock_management
@check_permission("stock_dashboard")
def stock_dashboard(request):
    faculty = get_logged_in_faculty(request)

    context = {
        "total_labs": Lab.objects.count(),
        "total_items": StockItem.objects.count(),
        "total_entries": StockEntry.objects.count(),
        "pending_entries": StockEntry.objects.exclude(
            entry_status__in=[StockEntry.Status.APPROVED_PRINCIPAL, StockEntry.Status.REJECTED]
        ).count(),
        "open_transfers": TransferRequest.objects.exclude(
            status__in=[TransferRequest.Status.COMPLETED, TransferRequest.Status.REJECTED]
        ).count(),
        "open_verifications": VerificationAssignment.objects.exclude(
            status=VerificationAssignment.Status.APPROVED
        ).count(),
        "my_verifications": (
            VerificationAssignment.objects.filter(assigned_faculty=faculty).count()
            if faculty else 0
        ),
        "recent_entries": (
            StockEntry.objects.select_related("register", "register__lab")
            .order_by("-id")[:10]
        ),
        "condemned_items": StockItem.objects.filter(
            condition=StockItem.Condition.CONDEMNED
        ).count(),
    }
    return render(request, "stock_management/dashboard/stock_dashboard.html", context)


# ------------------------------------------------------------------
# Master data - Labs
# ------------------------------------------------------------------
@stock_management
@check_permission("lab_management")
def lab_management(request):
    labs = Lab.objects.select_related("department", "incharge").order_by("lab_code")
    departments = Add_Department.objects.all()
    # Employees from this system's own staff table (main DB), including
    # non-teaching staff (technicians, JAs, etc.), tagged with their department.
    incharges = (
        general_information.objects
        .select_related("designation", "department")
        .order_by("name")
    )
    return render(request, "stock_management/master/lab_management.html", {
        "labs": labs,
        "departments": departments,
        "incharges": incharges,
    })


@stock_management
@check_permission("lab_management")
def lab_create(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        lab_code = request.POST.get("lab_code", "").strip()
        department_id = request.POST.get("department") or None
        incharge_id = request.POST.get("incharge") or None
        location = request.POST.get("location", "").strip()

        if not name or not lab_code or not department_id:
            messages.error(request, "Name, lab code and department are required.")
        elif Lab.objects.filter(lab_code__iexact=lab_code).exists():
            messages.error(request, "A lab with this code already exists.")
        else:
            Lab.objects.create(
                name=name, lab_code=lab_code, department_id=department_id,
                incharge_id=incharge_id or None, location=location or None,
            )
            messages.success(request, "Lab added successfully.")
    return redirect("lab_management")


@stock_management
@check_permission("lab_management")
def lab_edit(request, pk):
    lab = get_object_or_404(Lab.objects.select_related("department", "incharge"), pk=pk)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        lab_code = request.POST.get("lab_code", "").strip()
        department_id = request.POST.get("department") or None
        incharge_id = request.POST.get("incharge") or None
        location = request.POST.get("location", "").strip()
        is_active = request.POST.get("is_active") == "on"

        if not name or not lab_code or not department_id:
            messages.error(request, "Name, lab code and department are required.")
        elif Lab.objects.filter(lab_code__iexact=lab_code).exclude(pk=lab.pk).exists():
            messages.error(request, "Another lab with this code already exists.")
        else:
            lab.name = name
            lab.lab_code = lab_code
            lab.department_id = department_id
            lab.incharge_id = incharge_id or None
            lab.location = location or None
            lab.is_active = is_active
            lab.save()
            messages.success(request, "Lab updated successfully.")
            return redirect("lab_management")

    departments = Add_Department.objects.all()
    incharges = (
        general_information.objects
        .select_related("designation", "department")
        .order_by("name")
    )
    return render(request, "stock_management/master/lab_edit.html", {
        "lab": lab,
        "departments": departments,
        "incharges": incharges,
    })


@stock_management
@check_permission("lab_management")
def lab_delete(request, pk):
    lab = get_object_or_404(Lab, pk=pk)
    if request.method == "POST":
        # Block deletion when it would cascade away stock data.
        if StockRegister.objects.filter(lab=lab).exists():
            messages.error(
                request,
                "Cannot delete this lab — it has a stock register (and possibly entries/assets). "
                "Deactivate it instead."
            )
            return redirect("lab_management")
        try:
            lab.delete()
            messages.success(request, "Lab deleted successfully.")
        except ProtectedError:
            messages.error(
                request,
                "Cannot delete this lab — it is referenced by transfers or verification records. "
                "Deactivate it instead."
            )
    return redirect("lab_management")


# ------------------------------------------------------------------
# Master data - Stock Registers
# ------------------------------------------------------------------
@stock_management
@check_permission("stock_register")
def stock_register(request):
    registers = StockRegister.objects.select_related("lab").order_by("register_number")
    labs_without_register = Lab.objects.filter(register__isnull=True, is_active=True)
    return render(request, "stock_management/master/stock_register.html", {
        "registers": registers,
        "labs": labs_without_register,
        "current_fy": current_financial_year(),
    })


@stock_management
@check_permission("stock_register")
def register_create(request):
    if request.method == "POST":
        lab_id = request.POST.get("lab") or None
        register_number = request.POST.get("register_number", "").strip()
        financial_year = request.POST.get("financial_year", "").strip() or current_financial_year()

        if not lab_id or not register_number:
            messages.error(request, "Lab and register number are required.")
        elif StockRegister.objects.filter(register_number__iexact=register_number).exists():
            messages.error(request, "This register number already exists.")
        elif StockRegister.objects.filter(lab_id=lab_id).exists():
            messages.error(request, "This lab already has a register.")
        else:
            StockRegister.objects.create(
                lab_id=lab_id, register_number=register_number, financial_year=financial_year,
            )
            messages.success(request, "Stock register created successfully.")
    return redirect("stock_register")
