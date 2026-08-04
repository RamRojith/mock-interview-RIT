import json
from collections import defaultdict, OrderedDict

from django.contrib import messages
from django.db import transaction
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import render, redirect

from course_management.models import Regulations

from student_management.models import StudentDetails
from course_management.models import Course, CourseEnrollment, CourseHours
from user_accounts.models import Add_Department, Degree
import pandas as pd
from django.shortcuts import render
from django.contrib import messages
from examination_management.models import Result, Regular_Course_Grade_Master



REQUIRED_COLUMNS = [
    'degree',
    'department',
    'reg_no',
    'batch',
    'academic_year',
    'regulation',
    'year',
    'semester',
    'course_code',
    'course_name',
    'grade',
]

REQUIRED_COLUMNS = [
    'degree',
    'department',
    'reg_no',
    'batch',
    'academic_year',
    'regulation',
    'year',
    'semester',
    'course_code',
    'course_name',
    'grade',
]
import pandas as pd
from django.shortcuts import render
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from decimal import Decimal

def upload_student_results(request):
    preview_data = []
    error_logs = []

    if request.method == "POST":
        excel_file = request.FILES.get('excel_file')

        if not excel_file:
            messages.error(request, "No file uploaded")
            return render(request, 'examination_management/admin/upload_student_results.html')

        try:
            # ==============================
            # 1️⃣ READ FIRST 9 SHEETS
            # ==============================
            xls = pd.ExcelFile(excel_file)
            sheet_names = xls.sheet_names  # First 9 sheets

            df_list = []
            for sheet in sheet_names:
                df_temp = pd.read_excel(xls, sheet_name=sheet)
                df_temp["sheet"] = sheet
                df_list.append(df_temp)

            if not df_list:
                messages.error(request, "No sheets found")
                return render(request, 'examination_management/admin/upPDF Generation Error:load_student_results.html')

            df = pd.concat(df_list, ignore_index=True)

            # ==============================
            # 2️⃣ CLEAN & VALIDATE
            # ==============================
            df.columns = df.columns.str.strip().str.lower()

            missing_columns = set(REQUIRED_COLUMNS) - set(df.columns)
            if missing_columns:
                messages.error(request, f"Missing columns: {', '.join(missing_columns)}")
                return render(request, 'examination_management/admin/upload_student_results.html')

            rows = df[REQUIRED_COLUMNS + ["sheet"]].to_dict(orient="records")

            created_count = updated_count = skipped_count = error_count = 0

            # ==============================
            # 3️⃣ PROCESS DATA
            # ==============================
            with transaction.atomic():
                for i, row in enumerate(rows, start=1):
                    row_status = {
                        **row,
                        "status": "",
                        "message": ""
                    }

                    try:
                        student = StudentDetails.objects.get(reg_no=row['reg_no'])
                        regulation = Regulations.objects.get(year=row['regulation'])

                        course = Course.objects.filter(
    course_code=row['sheet'],
    regulation=regulation
).first()

                        if not course:
                            raise ObjectDoesNotExist("Course not found")

                        grade_master = Regular_Course_Grade_Master.objects.get(
                            degree=student.department.degree,
                            regulation=regulation,
                            letter_grade=row['grade']
                        )

                        course_hour = CourseHours.objects.get(course=course)

                        credit = Decimal(course_hour.credits)
                        grade_points = Decimal(grade_master.grade_points)

                        grade_total = credit * grade_points

                        result, created = Result.objects.update_or_create(
                            student=student,
                            course=course,
                            semester=row['semester'],
                            academic_year=row['academic_year'],
                            defaults={
                                'degree': student.department.degree,
                                'department': student.department,
                                'regulation': regulation,
                                'grade': row['grade'],
                                'grade_total': grade_total,
                                'year': row['year'],
                                'batch': student.batch,
                                'credit': credit,
                            }
                        )

                        if created:
                            created_count += 1
                            row_status["status"] = "CREATED"
                            row_status["message"] = "New result inserted"
                        else:
                            updated_count += 1
                            row_status["status"] = "UPDATED"
                            row_status["message"] = "Existing result updated"

                    except ObjectDoesNotExist as e:
                        skipped_count += 1
                        row_status["status"] = "SKIPPED"
                        row_status["message"] = str(e)

                    except Exception as e:
                        error_count += 1
                        row_status["status"] = "ERROR"
                        row_status["message"] = str(e)

                    preview_data.append(row_status)

            messages.success(
                request,
                f"Completed → Created: {created_count}, Updated: {updated_count}, "
                f"Skipped: {skipped_count}, Errors: {error_count}"
            )

        except Exception as e:
            messages.error(request, f"Excel failed: {e}")

    return render(
        request,
        'examination_management/admin/upload_student_results.html',
        {
            'data': preview_data
        }
    )


