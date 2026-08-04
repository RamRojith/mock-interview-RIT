# from django.contrib.auth.decorators import login_required
# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib import messages  # Import the messages framework
# from django.db.models import Q  # Import Q for query filtering
# from user_accounts.models import Department, Program
# from faculty_management.models import Faculty
# from course_management.models import Year, Semester
# from canva.models import Folder, FacultyDocument, CanvaAssignment, StudentCanvaAssignmentSubmission  # Adjust import according to your models
# from user_accounts.models import USER  # Assuming USER is the model for users
# from student_management.models import studentdetails  # Assuming you have a StudentProfile model
# from course_management.models import FacultyCourseMapping, course_enrolement  # Adjust import according to your models

# @login_required
# def view_assignment_documents(request):
#     # Get the logged-in student's registration number
#     student_reg_no = request.user.Employee_id  # Assuming username is student_reg_no; adjust if different

#     # Fetch all enrollments for the student
#     enrollments = course_enrolement.objects.filter(student_reg_no=student_reg_no)

#     # Group enrollments by program code
#     programs = {}
#     for enrollment in enrollments:
#         program_code = enrollment.Program_code
#         if program_code not in programs:
#             programs[program_code] = {
#                 'Programme_of_study': enrollment.Programme_of_study,
#                 'Department_code': enrollment.Department_code,
#                 'batch': enrollment.batch,  # Assuming batch is a field in course_enrolement
#                 'intake': enrollment.Intake,  # Assuming intake is a field in course_enrolement
#                 'courses': []
#             }
#         programs[program_code]['courses'].append(enrollment)

#     # Fetch course details from FacultyCourseMapping
#     program_data = []
#     for program_code, data in programs.items():
#         course_codes = [course.course_code for course in data['courses']]
#         course_mappings = FacultyCourseMapping.objects.filter(course_code__in=course_codes)
#         course_details = {
#             course.course_code: {
#                 'course_title': course.course_title,
#                 'faculty': course.faculty
#             } for course in course_mappings
#         }
#         program_data.append({
#             'program_code': program_code,
#             'programme_of_study': data['Programme_of_study'],
#             'department_code': data['Department_code'],
#             'batch': data['batch'],
#             'intake': data['intake'],
#             'courses': [
#                 {
#                     'course_code': course.course_code,
#                     'course_title': course_details.get(course.course_code, {}).get('course_title', 'N/A'),
#                     'faculty': course_details.get(course.course_code, {}).get('faculty', 'N/A'),
#                     'semester': course.semester
#                 } for course in data['courses']
#             ]
#         })

#     return render(request, 'canva/student/view_assignment_documents.html', {
#         'programs': program_data
#     })
    
    
    
# @login_required
# def view_uploaded_assignment_documents(request, course_code):
#     # Get intake, batch, and filter query from query parameters
#     intake = request.GET.get('intake')
#     batch = request.GET.get('batch')
#     filter_query = request.GET.get('filter', '')
#     # print("intake-->", intake)
#     # print("batch-->", batch)
#     # print("Course code-->", course_code)
#     # Fetch Canva assignments for the specific course, intake, and batch
#     assignments = CanvaAssignment.objects.filter(
#         course_code=course_code,
#         intake=intake,
#         batch=batch
#     )
    
#     # print("assignments-->", assignments)
    
#     # Apply filter if query is provided
#     if filter_query:
#         assignments = assignments.filter(Q(title__icontains=filter_query))

#     # Optimize query with prefetch_related for student submissions
#     assignments = assignments.prefetch_related('submissions')

#     return render(request, 'canva/student/view_uploaded_assignment_documents.html', {
#         'assignments': assignments,
#         'course_code': course_code
#     })



# from django.shortcuts import render, get_object_or_404, redirect
# from django.contrib import messages
# from django.contrib.auth.decorators import login_required
# from canva.models import CanvaAssignment, StudentCanvaAssignmentSubmission
# from student_management.models import studentdetails
# from django.utils import timezone



# @login_required
# def submit_canva_assignment(request, assignment_id):
#     # Get assignment_id from URL or form data
#     assignment_id = assignment_id or request.POST.get('assignment_id')
    
#     if not assignment_id:
#         messages.error(request, "No assignment specified")
#         return redirect(request.META.get('HTTP_REFERER', '/'))

#     # print("Assignment ID:", assignment_id)
#     emp_id = request.user.Employee_id
#     assignment = get_object_or_404(CanvaAssignment, id=assignment_id)
#     student = get_object_or_404(studentdetails, reg_number=emp_id)
    
#     # print("Student:", student)
#     # print("Assignment:", assignment)

#     existing_submission = StudentCanvaAssignmentSubmission.objects.filter(
#         assignment=assignment, 
#         student=student
#     ).first()
    
#     if request.method == 'POST':
#         submitted_file = request.FILES.get('submitted_file')

#         if not submitted_file:
#             messages.error(request, "Submission failed: No file was uploaded.")
#             return redirect(request.META.get('HTTP_REFERER', '/'))

#         if existing_submission:
#             # Update existing submission instead of creating new one
#             existing_submission.submitted_file = submitted_file
#             existing_submission.submission_date = timezone.now()
#             existing_submission.status = 'pending'
#             existing_submission.save()
#             messages.success(request, "Your submission has been updated!")
#         else:
#             StudentCanvaAssignmentSubmission.objects.create(
#                 assignment=assignment,
#                 student=student,
#                 submitted_file=submitted_file,
#                 status='pending'
#             )
#             messages.success(request, f"Assignment '{assignment.title}' submitted successfully!")
        
#         return redirect(request.META.get('HTTP_REFERER', '/'))

#     messages.error(request, "Invalid request method for submission.")
#     return redirect(request.META.get('HTTP_REFERER', '/'))






