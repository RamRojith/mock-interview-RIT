from django.shortcuts import redirect, render ,get_object_or_404
from django.contrib import messages
from nba.models import *
from user_accounts.decorators import check_permission
from user_accounts.models import Degree, Add_Department
from django.http import JsonResponse


def nba_outcome_based_curriculum_1(request):
    return render(request, "nba_management/nba_outcome_based_curriculum.html")


def  nba_outcome_based_teaching_learning_2(request):
    return render(request, "nba_management/nba_outcome_based_teaching_learning.html")

def nba_outcome_based_assessment_3(request):
    return render(request, "nba_management/nba_outcome_based_assessment.html")

@check_permission("nba_students_performance")
def nba_students_performance_4(request):
    return render(request, "nba_management/nba_students_performance.html")

def nba_faculty_information_5(request):
    return render(request, "nba_management/nba_faculty_information.html")

def  nba_faculty_contribution_6(request):
    return render(request, "nba_management/nba_faculty_contribution.html")

def nba_faculty_and_technical_support_7(request):
    return render(request, "nba_management/nba_faculty_and_technical_support.html")

def nba_continuous_improvement_8(request):
    return render(request, "nba_management/nba_continuous_improvement.html")

def nba_student_support_system_and_governance_9(request):
    return render(request, "nba_management/nba_student_support_system_and_governance.html")




