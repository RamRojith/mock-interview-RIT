from django.shortcuts import render,redirect
from user_accounts.models import USER
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.contrib import messages
from faculty_leave_management.models import LeaveBalance,LeaveAllotment
from django.contrib.auth.forms import AuthenticationForm
from user_accounts.decorators import no_cache
from datetime import date
from django.urls import get_resolver,URLPattern
import datetime
from faculty_management.models import general_information
from faculty_leave_management.urls import flm_application,flm_control_urls
from faculty_leave_management.utils import leave_allotment_update
from django.contrib.auth.decorators import login_required
from faculty_leave_management.decorators import faculty_leave_management
# Example usage:

@no_cache
@login_required
@faculty_leave_management
def leave_management(request):
    check_leave_balance=LeaveBalance.objects.filter(user=request.user,
                start_date__lte= datetime.datetime.now(),
                end_date__gte=datetime.datetime.now())
    if check_leave_balance.exists():
        pass
    else:
        
        get_faculty=general_information.objects.filter(employee_id=request.user.Employee_id,department=request.user.Department).first()
      
        if get_faculty:
            now = datetime.datetime.now()

            role_allotments = LeaveAllotment.objects.filter(
                role=get_faculty.designation,
                start_date__lte=now,
                end_date__gte=now,
            )
            category_allotments = LeaveAllotment.objects.none()
            if get_faculty.category_id:
                category_allotments = LeaveAllotment.objects.filter(
                    category_id=get_faculty.category_id,
                    start_date__lte=now,
                    end_date__gte=now,
                )

            # Category-based allotment takes precedence over role-based for the
            # same academic year + leave type.
            merged = {}
            for leave in role_allotments:
                merged[(leave.academic_year, leave.leave_type_id)] = leave
            for leave in category_allotments:
                merged[(leave.academic_year, leave.leave_type_id)] = leave

            for leave in merged.values():
                obj, created = LeaveBalance.objects.update_or_create(
                        user=get_faculty,
                        designation=get_faculty.designation,
                        academic_year=leave.academic_year,
                        leave_type=leave.leave_type,
                        defaults={'available': leave_allotment_update(leave.start_date, leave.end_date, leave.default_allotment)},
                        start_date=leave.start_date,
                        end_date=leave.end_date
                )
        else:
            
            messages.error(request,"Please add your data in faculty profile.")
            return redirect('home') 

    return redirect('home')
            

        

def flm_view_names():
    
    resolver = get_resolver(flm_control_urls)
    view_names = []

    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLPattern):
            view_names.append(pattern.name)              
    return view_names