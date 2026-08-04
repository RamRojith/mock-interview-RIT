
# @login_required
# @course_management
# @check_permission('Student_Semester_Mark_Dashboard')

# def fetch_students_for_mark(request):
#     # print("Entered fetch_students_for_mark function")
    
#     department_id = request.GET.get("department")
#     program_id = request.GET.get("program")
#     semester = request.GET.get("semester")
#     year = request.GET.get("year")
#     assessment = request.GET.get("assessment")  # Get assessment type

#     # Get department and program details
#     department = Department.objects.get(id=department_id)
#     program = Program.objects.get(id=program_id)

#     department_code = department.Department_code
#     program_code = program.program_code

#     # Fetch students based on the program, department, and semester
#     students = studentdetails.objects.filter(
#         department_code=department_code,
#         program_code=program_code,
#         semester=semester
#     ).values("id", "first_name", "surname", "reg_number")

#     # Fetch courses based on program, year, and semester
#     courses = Course.objects.filter(
#         program_id=program_id, 
#         year=year, 
#         semester=semester
#     ).values("id", "course_code", "title")

#     # Fetch existing marks
#     student_marks = StudentMark.objects.filter(
#         semester=semester,
#         assessment=assessment
#     ).values("student_id", "course_code", "grade")

#     # Convert student marks into a dictionary for easy lookup
#     student_marks_dict = {}
#     for mark in student_marks:
#         key = f"{mark['student_id']}_{mark['course_code']}"
#         student_marks_dict[key] = mark["grade"]

#     # Add grades to students if they exist
#     students_list = []
#     for student in students:
#         student_data = dict(student)
#         student_data["grades"] = {}
        
#         for course in courses:
#             key = f"{student['id']}_{course['course_code']}"
#             student_data["grades"][course["course_code"]] = student_marks_dict.get(key, "")

#         students_list.append(student_data)

#     return JsonResponse({"students": students_list, "courses": list(courses)})



# from django.http import HttpResponse
# from reportlab.lib.pagesizes import letter
# from reportlab.pdfgen import canvas
# from django.template.loader import render_to_string
# from course_management.models import result, Program, Course, StudentMark
# @login_required
# @course_management
# @check_permission('Student_Semester_Mark_Dashboard')

# def Student_Semester_Mark_Dashboard(request):
#     semesters = range(1, 9)  # Semesters 1 to 8
#     return render(request, "course_management/student_mark.html", {"semesters": semesters})



# @login_required
# @course_management
# @check_permission('Student_Semester_Mark_Dashboard')
# def fetch_student_marks(request):
#     if request.method == "GET":
#         employee_id = request.user.Employee_id  
#         semester = request.GET.get("semester")  # Get semester value
        
#         res = result.objects.filter(student_reg_no=employee_id, semester=semester)

#         try:
#             # Fetch student details
#             student = studentdetails.objects.get(reg_number=employee_id)
            
#             program_code = student.program_code  
#             program = Program.objects.get(program_code=program_code)
#             program_id = program.id
            
#             # Fetch courses for this program & semester
#             courses = Course.objects.filter(semester=semester)
#             course_codes = courses.values_list("course_code", flat=True)
            
#             # Fetch student marks
#             marks = StudentMark.objects.filter(
#                 student_reg_no=student.reg_number,
#                 semester=semester,
#                 course_code__in=course_codes
#             )
            
#             data = [
#                 {
#                     "student_name": mark.student_name,
#                     "student_reg_no": mark.student_reg_no,
#                     "course_name": mark.course_code,
#                     "assessment": mark.assessment,
#                     "mark": mark.mark, 
#                     "grade": mark.grade
#                 }
#                 for mark in marks
#             ]
            
#             return JsonResponse({"data": data}, safe=False)
        
#         except studentdetails.DoesNotExist:
#             return JsonResponse({"error": "Student details not found"}, status=404)
#         except Program.DoesNotExist:
#             return JsonResponse({"error": "Program not found"}, status=404)
#         except Exception as e:
#             return JsonResponse({"error": str(e)}, status=500)

#     return JsonResponse({"error": "Invalid request"}, status=400)


# # PDF generation view using ReportLab
# from django.http import HttpResponse
# from reportlab.lib.pagesizes import letter
# from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
# from reportlab.lib.styles import getSampleStyleSheet
# from reportlab.lib import colors
# from io import BytesIO
# @login_required
# @course_management
# @check_permission('Student_Semester_Mark_Dashboard')
# def generate_pdf(request, semester):
#     if request.method == "POST":
#         employee_id = request.user.Employee_id
        
#         try:
#             # Fetch student details
#             student = studentdetails.objects.get(reg_number=employee_id)
            
#             # Fetch results for the student and semester
#             results = result.objects.filter(
#                 student_reg_no=employee_id,
#                 semester=semester
#             ).order_by('course_code')
            
#             if not results.exists():
#                 return HttpResponse("No results found for this semester", status=404)
            
#             # Create PDF buffer
#             buffer = BytesIO()
            
#             # Create PDF document
#             doc = SimpleDocTemplate(
#                 buffer,
#                 pagesize=letter,
#                 title=f"Semester {semester} Results - {student.reg_number}"
#             )
            
#             # Prepare data for the table
#             data = []
#             styles = getSampleStyleSheet()
            
#             # Add title
#             title = Paragraph(
#                 f"<b>Semester {semester} Academic Report</b>",
#                 styles['Heading1']
#             )
            
#             # Student information
#             student_info = [
#                 Paragraph(f"<b>Student Name:</b> {student.first_name}", styles['Normal']),
#                 Paragraph(f"<b>Registration No:</b> {student.reg_number}", styles['Normal']),
#                 Paragraph(f"<b>Program:</b> {student.program_code}", styles['Normal']),
#                 Paragraph(f"<b>Department:</b> {student.programme_of_study}", styles['Normal']),
#                 Paragraph(f"<b>Regulation:</b> {results[0].regulation if results else ''}", styles['Normal']),
#             ]
            
#             # Table header
#             table_header = [
#                 "Course Code",
#                 "Course Name",
                
#                 "Mark",
#                 "Grade"
#             ]
            
#             data.append(table_header)
            
#             # Add results to table
#             for res in results:
#                 data.append([
#                     res.course_code,
#                     res.programme_of_study,
                    
#                     str(res.mark) if res.mark is not None else "-",
#                     res.grade
#                 ])
            
#             # Create table
#             table = Table(data)
#             table.setStyle(TableStyle([
#                 ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
#                 ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
#                 ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
#                 ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#                 ('FONTSIZE', (0, 0), (-1, 0), 12),
#                 ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
#                 ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
#                 ('GRID', (0, 0), (-1, -1), 1, colors.black),
#                 ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
#             ]))
            
#             # Build PDF document
#             elements = [title]
#             elements.extend(student_info)
#             elements.append(Paragraph("<br/><b>Course Results:</b>", styles['Heading2']))
#             elements.append(table)
            
#             doc.build(elements)
            
#             # Get PDF value from buffer
#             pdf = buffer.getvalue()
#             buffer.close()
            
#             # Create HTTP response
#             response = HttpResponse(content_type='application/pdf')
#             response['Content-Disposition'] = f'inline; filename="Semester_{semester}_Results_{student.reg_number}.pdf"'
#             response.write(pdf)
#             return response
            
#         except studentdetails.DoesNotExist:
#             return HttpResponse("Student details not found", status=404)
#         except Exception as e:
#             return HttpResponse(f"Error generating PDF: {str(e)}", status=500)
    
#     return HttpResponse("Invalid request method", status=400)

# @login_required
# @course_management
# @check_permission('course_registration')
# def get_student_details(request):
#     student_reg_no = request.user.Employee_id  # Remove spaces
#     # print(f"Searching for student with reg_number: '{student_reg_no}'")

#     students = studentdetails.objects.filter(reg_number=student_reg_no)
    
#     if students.exists():
#         # print("✅ Student found!")
#         return students.first()
#     else:
#         # print("❌ No matching student found!")
#         return None
    

# @login_required
# @course_management
# @check_permission('course_registration')
# def course_registration(request):
#     student_reg_no = request.user.Employee_id
#     # print(student_reg_no,"i am")
#     student = get_student_details(request)
#     # print(student,"hello")
#     # print(f"Student Program Code: {student.program_code}")
#     # print(f"Student Regulation: {student.regulation}")
#     # print(f"Student Year: {student.year}")
#     # print(f"Student Semester: {student.semester}")

#     if not student:
#         messages.error(request, "Student details not found. Please contact the admin.")
#         return render(request, 'course_management/course_registration.html', {'courses': [], 'student': None})

#     courses = Course.objects.filter(
#         program_code=student.program_code,
#         regulation=student.regulation,
#         year=student.year,
#         semester=student.semester
#     )
#     # print(courses,"hii")

#     registered_courses = course_enrolement.objects.filter(
#         student_reg_no=student_reg_no,
#         Program_code=student.program_code,
#         Regulation=student.regulation,
#         semester=student.semester
#     ).values_list('course_code', flat=True)

#     courses_to_register = courses.exclude(course_code__in=registered_courses)

#     context = {
#         'courses': courses_to_register,
#         'student': student
#     }
#     return render(request, 'course_management/course_registration.html', context)



# @login_required
# @course_management
# @require_POST
# @check_permission('course_registration')
# def register_course(request, course_code):
#     student_reg_no = request.user.Employee_id
#     student = get_student_details(request)

#     if not student:
#         messages.error(request, "Student details not found. Please contact the admin.")
#         return redirect('course_registration')

#     try:
#         course = Course.objects.get(course_code=course_code,
#                                     program_code=student.program_code,
#                                     regulation=student.regulation,
#                                     year=student.year,
#                                     semester=student.semester)
#     except Course.DoesNotExist:
#         messages.error(request, "Invalid course selection. Please try again.")
#         return redirect('course_registration')

#     # Create a new course_enrolement entry.
#     course_enrolement.objects.create(
#         student_reg_no=student_reg_no,
#         Regulation=student.regulation,
#         Programme_of_study=student.programme_of_study,
#         Department_code=student.department,  # Fill in or derive as necessary
#         Program_code=student.program_code,
#         semester=student.semester,
#         course_code=course.course_code,
#         batch=student.batch,
#         Intake=student.Intake,
#         registration="register"
#     )

#     messages.success(request, f"Successfully registered for {course.course_code} - {course.title}.")
#     return redirect('course_registration')



# def leave_form(request):
#     # Fetch student details using credentials
#     student = studentdetails.objects.filter(credentials=request.user).first()
#     # print(student)
#     # print(student.reg_number,"sssss")

#     if not student:
#         messages.error(request, "Student details not found.")
#         return redirect('dashboard')

#     if request.method == "POST":
#         form = StudentLeaveApplicationForm(request.POST)
#         if form.is_valid():
#             leave_application = form.save(commit=False)
#             leave_application.student = student
#             leave_application.reg_number = student.reg_number
#             leave_application.first_name = student.first_name
#             leave_application.email_address = student.email_address
#             leave_application.mobile_number = student.mobile_number
#             leave_application.mentor_id = student.mentor_id
#             leave_application.save()

#             messages.success(request, "Leave application submitted successfully!")
#             return redirect('leave_form')

#     else:
#         form = StudentLeaveApplicationForm()

#     leave_form = StudentLeaveApplication.objects.filter(student=student).order_by('-id')
#     # print(leave_form,"leave form")

#     return render(request, 'student_management/student_leave_application.html', {
#         'form': form,
#         'leave_form': leave_form,
#         'student_reg_number': student.reg_number
#     })