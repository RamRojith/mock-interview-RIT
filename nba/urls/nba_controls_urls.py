from django.urls import path
from nba.views.module_4_views import *

from nba.views.total_nba_modules_views import *

urlpatterns = [


    path('nba_outcome_based_curriculum', nba_outcome_based_curriculum_1, name='nba_outcome_based_curriculum'),
    path('nba_outcome_based_teaching_learning', nba_outcome_based_teaching_learning_2, name='nba_outcome_based_teaching_learning'),
    path('nba_outcome_based_assessment', nba_outcome_based_assessment_3, name='nba_outcome_based_assessment'),
    path('nba_students_performance/', nba_students_performance_4, name='nba_students_performance'),
    path('nba_faculty_information', nba_faculty_information_5, name='nba_faculty_information'),
    path('nba_faculty_contribution', nba_faculty_contribution_6, name='nba_faculty_contribution'),
    path('nba_faculty_and_technical_support', nba_faculty_and_technical_support_7, name='nba_faculty_and_technical_support'),
    path('nba_continuous_improvement', nba_continuous_improvement_8, name='nba_continuous_improvement'),
    path('nba_student_support_system_and_governance', nba_student_support_system_and_governance_9, name='nba_student_support_system_and_governance'),




]

