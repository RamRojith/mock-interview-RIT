from django.urls import path
from examination_management.views.result_views import *
from examination_management.views.admin_em import *
from examination_management.views.upload_excel_views import *


urlpatterns = [
    path(
        "result-permission/api/",
        result_permission_api,
        name="result_permission_api",
    ),

    path("ltp/export-excel/", export_ltp_excel, name="export_ltp_excel"),

    # path("api/results/", results_api, name="results_api"),

]


