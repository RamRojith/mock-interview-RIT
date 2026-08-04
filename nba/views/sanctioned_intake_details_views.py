from django.shortcuts import redirect, render ,get_object_or_404
from django.contrib import messages
from nba.models import *
from user_accounts.models import Degree, Add_Department
from django.http import JsonResponse


def add_sanctioned_intake(request):
    degrees = Degree.objects.filter(is_active=True)
    
    if request.method == "POST":
        intake_id = request.POST.get("intake_id")  # For edit
        degree_id = request.POST.get("degree")
        department_id = request.POST.get("department")
        year = request.POST.get("year")
        sanctioned_intake = request.POST.get("sanctioned_intake")

        if not (degree_id and department_id and year and sanctioned_intake):
            messages.error(request, "All fields are required.")
        else:
            degree = Degree.objects.get(id=degree_id)
            department = Add_Department.objects.get(id=department_id)

            if intake_id:  # Edit existing
                obj = SanctionedIntake.objects.get(id=intake_id)
                obj.degree = degree
                obj.department = department
                obj.year = year
                obj.sanctioned_intake = sanctioned_intake
                obj.save()
                messages.success(request, "Sanctioned intake updated successfully.")
            else:  # Add new
                obj, created = SanctionedIntake.objects.update_or_create(
                    degree=degree,
                    department=department,
                    year=year,
                    defaults={"sanctioned_intake": sanctioned_intake},
                )
                if created:
                    messages.success(request, "Sanctioned intake added successfully.")
                else:
                    messages.info(request, "Existing intake updated successfully.")

            return redirect("add_sanctioned_intake")

    intake_list = SanctionedIntake.objects.select_related("degree", "department").order_by("degree__degree", "department__Department")
    context = {"degrees": degrees, "intake_list": intake_list}
    return render(request, "nba_management/add_sanctioned_intake.html", context)


def get_departments_by_degree(request):
    degree_id = request.GET.get("degree_id")
    if degree_id:
        departments = Add_Department.objects.filter(degree_id=degree_id, is_active=True).values("id", "Department")
        data = [{"id": dept["id"], "name": dept["Department"]} for dept in departments]
        return JsonResponse(data, safe=False)
    return JsonResponse([], safe=False)


def edit_sanctioned_intake(request, id):
    intake = get_object_or_404(SanctionedIntake, id=id)
    degrees = Degree.objects.filter(is_active=True)
    intake_list = SanctionedIntake.objects.select_related("degree", "department").order_by("degree__degree", "department__Department")

    if request.method == "POST":
        degree_id = request.POST.get("degree")
        department_id = request.POST.get("department")
        year = request.POST.get("year")
        sanctioned_intake = request.POST.get("sanctioned_intake")

        if not (degree_id and department_id and year and sanctioned_intake):
            messages.error(request, "All fields are required.")
        else:
            degree = Degree.objects.get(id=degree_id)
            department = Add_Department.objects.get(id=department_id)

            # Update the existing intake using update_or_create
            obj, created = SanctionedIntake.objects.update_or_create(
                id=int(id),
                defaults={
                    "degree": degree,
                    "department": department,
                    "year": year,
                    "sanctioned_intake": sanctioned_intake
                }
            )
            messages.success(request, "Sanctioned intake updated successfully.")
            return redirect("add_sanctioned_intake")  # redirect to list page

    context = {
        "degrees": degrees,
        "intake_list": intake_list,
        "edit_intake": intake
    }
    return render(request, "nba_management/add_sanctioned_intake.html", context)

def delete_sanctioned_intake(request, id):
    intake = get_object_or_404(SanctionedIntake, id=id)
    intake.delete()
    messages.success(request, "Sanctioned intake deleted successfully.")
    return redirect("add_sanctioned_intake")
