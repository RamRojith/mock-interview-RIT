# from django.http import HttpResponse
# from django.shortcuts import get_object_or_404
# from reportlab.lib.pagesizes import A4
# from reportlab.pdfgen import canvas
# from faculty_management.models import Faculty
# from reportlab.lib.utils import Image
# from django.shortcuts import get_object_or_404
# from reportlab.lib.utils import ImageReader  # Import ImageReader
# from io import BytesIO
# from reportlab.lib.utils import ImageReader
# from django.urls import reverse
# from control_room.models import USER
# import os
# from django.conf import settings
# from django.contrib.auth.decorators import login_required
# import textwrap



# @login_required
# def generate_faculty_pdf(request, faculty_id):
#     faculty = get_object_or_404(Faculty, id=faculty_id)
    
#     try:
#         user = USER.objects.filter(Employee_id=faculty.employee_id).first()
#         if user.profile_img:
#             profile_img_path = os.path.join(settings.MEDIA_ROOT, str(user.profile_img))
#         else:
#             profile_img_path = None
#     except USER.DoesNotExist:
#         profile_img_path = None
    
#     response = HttpResponse(content_type='application/pdf')
#     response['Content-Disposition'] = f'inline; filename="{faculty.name}_details.pdf"'
    
#     # Get the correct static path
#     logo_path = os.path.join(settings.BASE_DIR, 'static', 'image', 'Edenberg.png')

    
    

#     if not os.path.exists(logo_path):
#         # print("⚠️ Logo file not found:", logo_path)

#     # Draw the logo at the top
    

    
#     p = canvas.Canvas(response, pagesize=A4)
#     width, height = A4  # Get A4 page dimensions
    
#     if os.path.exists(logo_path):
#         p.saveState()
#         p.translate(width / 2, height / 2)
#         p.rotate(0)  
#         p.setFillAlpha(0.2)  # Set transparency (0 = invisible, 1 = opaque)
#         p.drawImage(logo_path, -100, -100, width=220, height=200)  # Centered watermark
#         p.restoreState()
        
#     y_position = height - 150  # Leave top 150px free for university name
    
#     # University Name Placeholder
#     p.setFont("Helvetica-Bold", 14)
#     p.drawString(200, height - 50, "University of Edenberg")
#     p.drawString(220, height - 65, "Student Form")
    
#     if os.path.exists(logo_path):
#         p.drawImage(logo_path, 120, height - 80, width=80, height=60)  # Adjust position and size
        
           
#     if profile_img_path and os.path.exists(profile_img_path):
#         p.drawImage(profile_img_path, 450, height - 220, width=100, height=100)
#     else:
#         p.drawString(450, height - 230, "No Photo Available")  # Show text if image missing
     

    
#     # Faculty Basic Details
#     p.setFont("Helvetica", 12)
#     x_label = 50  # Position for labels
#     x_value = 180  # Position for values
#     y_position = 700  # Starting position (adjust as needed)
#     line_spacing = 20  # Space between lines

#     # **List of Details**
#     details = [
#         ("Name", faculty.name),
#         ("Sure Name", faculty.sure_name),
#         ("Gender", faculty.gender),
#         ("Father/Husband Name", faculty.father_or_husband_name),
#         ("Date of Birth", faculty.date_of_birth),
#         ("Department", faculty.department),
#         ("Present Designation", faculty.present_designation),
#         ("Date of Joining", faculty.date_of_joining),
#         ("Aadhar/NRC Number", faculty.aadhar_nrc_number),
#         ("Mobile Number", faculty.mobile_number),
#         ("Personal Mail", faculty.personal_mail_id),
#         ("Address", faculty.present_address),
#     ]
    
#     p.drawString(330, 520, 'WhatsApp Number:')
#     p.drawString(440, 520, faculty.whatsapp_number)
    
#     p.drawString(330, 500, 'Official Mail:')
#     p.drawString(400, 500, faculty.official_mail_id)
    
#     p.drawString(330, 700, 'Faculty ID:')
#     p.drawString(400, 700, faculty.employee_id)

#     # **Draw Aligned Text**
#     for label, value in details:
#         p.drawString(x_label, y_position, f"{label}:")  # Ensure label is a string
#         p.drawString(x_value, y_position, str(value))  # Ensure value is a string
#         y_position -= line_spacing  # Move down

#     # **Educational Details Table with Borders**
#     p.setFont("Helvetica-Bold", 12)
#     p.drawString(50, y_position - 10, "Educational Details")
#     y_position -= 40

#     # **Table Column Headers**
#     p.setFont("Helvetica-Bold", 10)
#     table_x = 30  # Left margin for table
#     col_widths = [150, 150, 150, 90]  # Column widths: Degree, Specialization, University, Year
#     row_height = 20

#     headers = ["Degree", "Specialization", "Institute/University", "Year of Passing"]
    
#     # **Draw Table Headers**
#     x = table_x
#     for i, header in enumerate(headers):
#         p.drawString(x + 5, y_position + 5, header)  # Adding text inside boxes
#         p.rect(x, y_position, col_widths[i], row_height)  # Draw cell box
#         x += col_widths[i]

#     y_position -= row_height  # Move down for rows

#     # **Fetch & Display Education Data in Table**
#     p.setFont("Helvetica", 10)
#     education_details = faculty.educational_details.all()[:5]  

#     for edu in education_details:
#         x = table_x
#         row_data = [edu.degree, edu.branch_specialization, edu.institute_university, str(edu.year_of_passing)]
        
#         for i, data in enumerate(row_data):
#             p.drawString(x + 5, y_position + 5, data)  # Adding text inside boxes
#             p.rect(x, y_position, col_widths[i], row_height)  # Draw cell box
#             x += col_widths[i]

#         y_position -= row_height  # Move to next row
        
        
#    # **Experience Details Table**
#     p.setFont("Helvetica-Bold", 12)
#     p.drawString(50, y_position - 10, "Experience Details")
#     y_position -= 40

#     # **Table Column Headers**
#     p.setFont("Helvetica-Bold", 10)
#     table_x = 30  # Left margin for table
#     col_widths = [150, 150, 150, 100]  # Column widths: Designation, Department, Institution, Period
#     row_height = 20

#     headers = ["Designation", "Department", "Institution", "Period"]

#     # **Draw Table Headers**
#     x = table_x
#     for i, header in enumerate(headers):
#         p.drawString(x + 5, y_position + 5, header)  # Adding text inside boxes
#         p.rect(x, y_position, col_widths[i], row_height)  # Draw cell box
#         x += col_widths[i]

#     y_position -= row_height  # Move down for rows

#     # **Fetch & Display Experience Data in Table**
#     p.setFont("Helvetica", 10)
#     experience_details = faculty.experience_details.all()[:5]  # Limit to 5 entries

#     for exp in experience_details:
#         x = table_x
#         row_data = [exp.designation, exp.department, exp.institution_organization, f"{exp.period_from} - {exp.period_to}"]

#         for i, data in enumerate(row_data):
#             p.drawString(x + 5, y_position + 5, data)  # Adding text inside boxes
#             p.rect(x, y_position, col_widths[i], row_height)  # Draw cell box
#             x += col_widths[i]

#         y_position -= row_height  # Move to next row


    
#     p.showPage()
#     p.save()
#     return response