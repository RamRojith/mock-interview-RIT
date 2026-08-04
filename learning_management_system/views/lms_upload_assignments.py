# from collections import defaultdict
# from django.http import HttpResponseRedirect
# from django.shortcuts import render, redirect
# from canva.models import Folder, FacultyDocument
# from control_room.models import USER, Department, Program
# from django.contrib.auth.decorators import login_required
# from django.urls import reverse




# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib import messages
# from django.contrib.auth.decorators import login_required
# from control_room.models import Department, Program
# from faculty_management.models import Faculty
# from course_management.models import Year, Semester
# from canva.models import Folder

# from course_management.models import FacultyCourseMapping, course_enrolement  # Adjust import according to your models

# from django.contrib.auth.decorators import login_required
# from django.shortcuts import render, redirect
# from canva.models import Folder, CanvaAssignment
# from faculty_management.models import Faculty



# def canva_assignments(request):
#     emp_id = request.user.Employee_id  # Logged-in faculty ID
#     course_mappings = FacultyCourseMapping.objects.filter(faculty=emp_id)

#     program_assignment_map = defaultdict(list)

#     for mapping in course_mappings:
#         program_code = mapping.program_code

#         # Split intake_batch like "January - 2025"
#         intake_batch_raw = mapping.intake_batch or ''
#         intake, batch = '', ''
#         if ' - ' in intake_batch_raw:
#             parts = intake_batch_raw.split(' - ')
#             if len(parts) == 2:
#                 intake = parts[0].strip()
#                 batch = parts[1].strip()

#         program_assignment_map[program_code].append({
#             'course_code': mapping.course_code,
#             'course_title': mapping.course_title,
#             'intake': intake,
#             'batch': batch,
#         })

#     # Save processed data to session (optional)
#     # print("Program Assignment Map:", program_assignment_map)
#     request.session['program_assignment_map'] = dict(program_assignment_map)

#     return render(request, 'canva/faculty/canva_assignments.html', {
#         'program_assignment_map': dict(program_assignment_map)
#     })


# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib import messages
# from django.contrib.auth.decorators import login_required




# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib import messages
# from django.contrib.auth.decorators import login_required
# from canva.models import Folder
# from faculty_management.models import Faculty



# @login_required
# def assignment_folders(request, course_code):
#     # Get the logged-in user's employee ID
#     emp_id = request.user.Employee_id
#     intake = request.GET.get('intake')
#     batch = request.GET.get('batch')

#     # Ensure that both intake and batch are provided
#     if not intake or not batch:
#         messages.error(request, "Both Intake and Batch are required to view or create assignment folders.")
#         return redirect('some_default_page')  # Replace with a valid URL or redirect to a relevant page

#     # Fetch the faculty details based on the logged-in user
#     faculty = get_object_or_404(Faculty, employee_id=emp_id)

#     # Fetch existing assignment folders based on the provided criteria
#     existing_folders = Folder.objects.filter(
#         created_by=faculty,
#         course_code=course_code,
#         intake=intake,
#         batch=batch,
#         folder_type='assignment'  # Only retrieve folders marked as assignment
#     )

#     # Handle the folder creation logic if the request method is POST
#     if request.method == 'POST':
#         folder_name = request.POST.get('folder_name')

#         # Ensure the folder name is not empty
#         if folder_name:
#             # Check if folder name already exists for the specific course, intake, and batch
#             if existing_folders.filter(name=folder_name).exists():
#                 messages.error(request, f"Folder '{folder_name}' already exists.")
#             else:
#                 Folder.objects.create(
#                     name=folder_name,
#                     created_by=faculty,
#                     intake=intake,
#                     batch=batch,
#                     course_code=course_code,
#                     folder_type='assignment'  # Ensure this folder is for assignments
#                 )
#                 messages.success(request, f"Assignment folder '{folder_name}' created successfully.")
#         else:
#             messages.error(request, "Folder name cannot be empty.")

#         # Redirect back to the current page (useful to stay on the same page after POST)
#         return redirect(request.META.get('HTTP_REFERER', request.path))

#     # Render the template with existing folders and data
#     return render(request, 'canva/faculty/assignment_folders.html', {
#         'folders': existing_folders,
#         'course_code': course_code,
#         'intake': intake,
#         'batch': batch,
#     })



# from django.shortcuts import render, redirect, get_object_or_404
# from django.contrib import messages
# from django.contrib.auth.decorators import login_required
# from django.urls import reverse
# from django.http import HttpResponseRedirect
# from canva.models import Folder, CanvaAssignment
# from faculty_management.models import Faculty


# @login_required
# def canva_upload_assignments(request, course_code, folder_id):
#     faculty = get_object_or_404(Faculty, employee_id=request.user.Employee_id)
#     folder = get_object_or_404(Folder, id=folder_id, created_by=faculty, course_code=course_code)

#     # Initialize variables for edit mode
#     edit_assignment = None
#     edit_mode = False

#     # Check if we're in edit mode
#     if 'edit' in request.GET:
#         try:
#             edit_assignment = CanvaAssignment.objects.get(
#                 id=request.GET['edit'],
#                 folder=folder,
#                 faculty=faculty
#             )
#             edit_mode = True
#         except CanvaAssignment.DoesNotExist:
#             messages.error(request, "Assignment not found or you don't have permission to edit it")

#     if request.method == 'POST':
#         # Handle assignment update
#         if 'update_assignment' in request.POST and edit_mode:
#             title = request.POST.get('title', '').strip()
#             description = request.POST.get('description', '').strip()
#             due_date = request.POST.get('due_date')
#             total_marks = request.POST.get('total_marks', '').strip()
#             file = request.FILES.get('assignment_file')

#             # Update fields
#             edit_assignment.title = title or "Untitled Assignment"
#             edit_assignment.description = description
#             edit_assignment.due_date = due_date
#             edit_assignment.total_marks = total_marks if total_marks else 100.0
#             if file:
#                 edit_assignment.assignment_file = file
#             edit_assignment.save()

#             messages.success(request, f"Assignment '{edit_assignment.title}' updated successfully")
#             return redirect('canva_upload_assignments', course_code=course_code, folder_id=folder.id)

#         # Handle assignment delete
#         elif 'delete_assignment' in request.POST:
#             try:
#                 assignment = CanvaAssignment.objects.get(
#                     id=request.POST['delete_assignment'],
#                     folder=folder,
#                     faculty=faculty
#                 )
#                 assignment_title = assignment.title
#                 assignment.delete()
#                 messages.success(request, f"Assignment '{assignment_title}' deleted successfully")
#                 return redirect('canva_upload_assignments', course_code=course_code, folder_id=folder.id)
#             except CanvaAssignment.DoesNotExist:
#                 messages.error(request, "Assignment not found or you don't have permission to delete it")

#         # Handle new assignment upload
#         else:
#             title = request.POST.get('title', '').strip()
#             description = request.POST.get('description', '').strip()
#             due_date = request.POST.get('due_date')
#             total_marks = request.POST.get('total_marks', '').strip()
#             file = request.FILES.get('assignment_file')

#             if not file:
#                 messages.error(request, "No file was uploaded. Please choose a file.")
#             else:
#                 CanvaAssignment.objects.create(
#                     folder=folder,
#                     title=title or "Untitled Assignment",
#                     description=description,
#                     due_date=due_date,
#                     total_marks=total_marks if total_marks else 100.0,
#                     assignment_file=file,
#                     faculty=faculty,
#                     course_code=course_code,
#                     intake=request.GET.get('intake'),  # Assuming intake and batch are passed as query params
#                     batch=request.GET.get('batch')  # Same for batch
#                 )
#                 messages.success(request, f"Assignment '{title or 'Untitled'}' uploaded successfully.")
#                 return redirect('canva_upload_assignments', course_code=course_code, folder_id=folder.id)

#     # Fetch all assignments for the specific folder
#     assignments = CanvaAssignment.objects.filter(folder=folder, faculty=faculty)

#     return render(request, 'canva/faculty/canva_upload_assignments.html', {
#         'folder': folder,
#         'assignments': assignments,
#         'edit_assignment': edit_assignment,
#         'edit_mode': edit_mode,
#     })
    



# from django.shortcuts import render, get_object_or_404, redirect
# from django.contrib.auth.decorators import login_required
# from django.contrib import messages
# from canva.models import CanvaAssignment, StudentCanvaAssignmentSubmission, Faculty
# from student_management.models import studentdetails
# from django.utils import timezone

# @login_required
# def canva_view_submissions(request, course_code, assignment_id):
#     faculty = get_object_or_404(Faculty, employee_id=request.user.Employee_id)
#     assignment = get_object_or_404(CanvaAssignment, id=assignment_id, course_code=course_code, faculty=faculty)
    
#     # Get all enrolled students for this course (using intake and batch from assignment)
#     enrolled_students = course_enrolement.objects.filter(
#         course_code=course_code,
#         Intake=assignment.intake,
#         batch=assignment.batch
#     )

#     # Get all submissions for this assignment (no select_related due to model structure)
#     submissions = StudentCanvaAssignmentSubmission.objects.filter(assignment=assignment)
    
#     # Create a dictionary of submissions by student reg number for quick lookup
#     submissions_dict = {sub.student.reg_number: sub for sub in submissions}

#     # Prepare the data for template
#     student_submissions = []
#     for enrollment in enrolled_students:
#         student = studentdetails.objects.filter(reg_number=enrollment.student_reg_no).first()
#         submission = submissions_dict.get(enrollment.student_reg_no)
        
#         student_data = {
#             'student': student,
#             'enrollment': enrollment,
#             'submission': submission,
#             'status': submission.status if submission else 'not_completed',
#             'submitted_at': submission.submitted_at if submission else None,
#             'marks_obtained': submission.marks_obtained if submission else None
#         }
#         student_submissions.append(student_data)

#     if request.method == 'POST':
#         submission_id = request.POST.get('submission_id')
#         marks_obtained = request.POST.get('marks')
#         student_reg_no = request.POST.get('student_reg_no')

#         try:
#             marks_obtained = float(marks_obtained) if marks_obtained else None
#             if marks_obtained is not None and (marks_obtained < 0 or marks_obtained > assignment.total_marks):
#                 messages.error(request, f"Marks must be between 0 and {assignment.total_marks}.")
#                 return redirect('canva_view_submissions', course_code=course_code, assignment_id=assignment.id)
#         except (TypeError, ValueError):
#             messages.error(request, "Please enter a valid number for marks.")
#             return redirect('canva_view_submissions', course_code=course_code, assignment_id=assignment.id)

#         # Find or create submission
#         if student_reg_no:
#             student = get_object_or_404(studentdetails, reg_number=student_reg_no)
#             submission, created = StudentCanvaAssignmentSubmission.objects.get_or_create(
#                 assignment=assignment,
#                 student=student,  # Use reg number directly
#                 defaults={
#                     'marks_obtained': marks_obtained,
#                     'status': 'marked' if marks_obtained is not None else 'completed'
#                 }
#             )
            
#             if not created:
#                 submission.marks_obtained = marks_obtained
#                 submission.status = 'marked' if marks_obtained is not None else submission.status
#                 submission.save()

#             messages.success(request, f"Updated {student.first_name} {student.surname}'s submission.")
#             return redirect('canva_view_submissions', course_code=course_code, assignment_id=assignment.id)

#     # Calculate submission statistics
#     total_students = enrolled_students.count()
#     submitted_count = submissions.count()
#     marked_count = submissions.filter(status='marked').count()
#     pending_count = submissions.filter(status='pending').count()

#     return render(request, 'canva/faculty/canva_assignment_submissions.html', {
#         'assignment': assignment,
#         'student_submissions': student_submissions,
#         'total_students': total_students,
#         'submitted_count': submitted_count,
#         'marked_count': marked_count,
#         'pending_count': pending_count,
#         'now': timezone.now()
#     })













