from django.urls import path
from examination_management.views import result_views
urlpatterns = [
    path("assign_result_permission/", result_views.assign_result_permission, name="assign_result_permission"),
    path("result_detail/<int:student_id>/<int:year>/<int:semester>/", result_views.result_detail, name="result_detail"),
     path(
        "results/data/",
        result_views.results_data,
        name="results_data"
    ),
    path("get_result_departments/", result_views.get_result_departments, name="get_result_departments"),
    path("get_result_degree_structure/", result_views.get_result_degree_structure, name="get_result_degree_structure"),
    path(
"export_result_analysis/",
result_views.export_result_analysis,
name="export_result_analysis"
)
]


