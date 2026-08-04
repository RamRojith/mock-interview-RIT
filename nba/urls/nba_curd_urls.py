from django.urls import path
from nba.views.sanctioned_intake_details_views import *
from nba.views.module_4_views import *


urlpatterns = [
    path("nba/api/past_enrolments/", get_past_enrolments, name="get_past_enrolments"),
    path("nba/api/batches/", get_batches_by_department, name="get_batches_by_department"),
    path("nba/api/intake_snapshot/", get_intake_snapshot, name="get_intake_snapshot"),
    path('add_enrolment_ratio/', add_enrolment_ratio, name='add_enrolment_ratio'),
    path("add-success-rate-stipulated/", add_success_rate_stipulated, name="add_success_rate_stipulated"),
    path("get-past-success-rate-entries/", get_past_success_rate_entries, name="get_past_success_rate_entries"),
    path('api/first-year/add/', add_academic_performance_first_year, name='add_academic_performance_first_year'),
    path('api/first-year/past/', get_past_academic_api_entries, name='get_past_academic_api_entries'),
    path("api/second-year/add/",  add_academic_performance_second_year, name="add_academic_performance_second_year"),
    path("api/second-year/past/", get_past_academic_api2_entries,name="get_past_academic_api2_entries"),
    path("api/third-year/past/",get_past_academic_api_third_year_entries,name="get_past_academic_api_third_year_entries"),
    path("api/third-year/add/",add_academic_performance_third_year,name="add_academic_performance_third_year"),
    path("placements/add/",  add_placement_hs_entre, name="add_placement_hs_entre"),
    path("placements/past/", get_past_placement_entries, name="get_past_placement_entries"),
# ========================= Module 4.7.1 =========================
    path("pa/471/add/", add_societies, name="add_societies"),
    path("pa/471/past/", past_societies, name="past_societies"),

    # # ========================= Module 4.7.2 =========================
    path("pa/472/add/", add_student_events, name="add_student_events"),
    path("pa/472/past/", past_student_events, name="past_student_events"),

    # ========================= Module 4.7.3 =========================
    path("pa/473/add/", add_deptpubs, name="add_deptpubs"),
    path("pa/473/past/", past_deptpubs, name="past_deptpubs"),

    # ========================= Module 4.7.4 =========================
    path("pa/474/add/", add_studpubs, name="add_studpubs"),
    path("pa/474/past/", past_studpubs, name="past_studpubs"),

]      



