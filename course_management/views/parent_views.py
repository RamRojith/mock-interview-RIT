from django.shortcuts import redirect, render
from course_management.decorators import course_management
from user_accounts.decorators import faculty_login_required, check_permission
from student_management.models import *
from examination_management.models import *
from course_management.models import *
import json
from django.shortcuts import render
from django.db.models import Count, Q, Prefetch
from django.shortcuts import render, get_object_or_404


@check_permission('daily_attendance_report')
def daily_attendance_report(request):
    reg_no = request.user.Employee_id
    student_detail = get_object_or_404(StudentDetails, reg_no=reg_no)
    class_attendances = Daily_Attendance.objects.filter(reg_no=reg_no).order_by('date')

    total_days = class_attendances.count()
    present_days = class_attendances.filter(status='Present').count()
    absent_days = class_attendances.filter(status='Absent').count()
    od_days = class_attendances.filter(status='On Duty').count()
    percentage = round((present_days / total_days) * 100, 2) if total_days else 0

    # Group by Month for chart
    monthly_data = (
        class_attendances
        .values('date__month')
        .annotate(total=Count('id'), present=Count('id', filter=Q(status='Present')))
        .order_by('date__month')
    )

    months = [m['date__month'] for m in monthly_data]
    presents = [m['present'] for m in monthly_data]

    context = {
        "student_detail": student_detail,
        "class_attendances": class_attendances,
        "total_days": total_days,
        "present_days": present_days,
        "absent_days": absent_days,
        "od_days": od_days,
        "percentage": percentage,
        "months": json.dumps(months),
        "presents": json.dumps(presents),
    }
    return render(request, "course_management/parent/daily_attendance_report.html", context)



@check_permission('hour_attendance_report')
def hour_attendance_report(request):
    reg_no = request.user.Employee_id
    student_detail = get_object_or_404(StudentDetails, reg_no=reg_no)

    # Current year & semester
    current_year = student_detail.year
    current_semester = student_detail.semester

    # Filter hour attendance
    hour_attendances = HourAttendance.objects.filter(
        reg_no=reg_no,
        course__year=current_year,
        course__semester=current_semester
    ).order_by('date', 'period')

    total_hours = hour_attendances.count()
    present_hours = hour_attendances.filter(status='Present').count()
    absent_hours = hour_attendances.filter(status='Absent').count()
    percentage = round((present_hours / total_hours) * 100, 2) if total_hours else 0

    present_percentage = round((present_hours / total_hours) * 100, 2) if total_hours else 0
    absent_percentage = round((absent_hours / total_hours) * 100, 2) if total_hours else 0

    # Average hours per day
    daily_counts = hour_attendances.values('date').annotate(daily_total=Count('id'))
    average_daily_hours = round(sum(d['daily_total'] for d in daily_counts) / len(daily_counts), 2) if daily_counts else 0

    # Course-wise data for charts
    course_data = hour_attendances.values('course__course_code', 'course__title').annotate(
        present=Count('id', filter=Q(status='Present')),
        total=Count('id')
    )

    courses = [c['course__course_code'] for c in course_data]
    presents = [c['present'] for c in course_data]

    context = {
        'student_detail': student_detail,
        'hour_attendances': hour_attendances,
        'total_hours': total_hours,
        'present_hours': present_hours,
        'absent_hours': absent_hours,
        'percentage': percentage,
        'present_percentage': present_percentage,
        'absent_percentage': absent_percentage,
        'average_daily_hours': average_daily_hours,
        'courses': json.dumps(courses),
        'presents': json.dumps(presents),
        'current_year': current_year,
        'current_semester': current_semester,
        'course_data': course_data,
        'now': timezone.now(),
    }
    return render(request, "course_management/parent/hour_attendance_report.html", context)
 
