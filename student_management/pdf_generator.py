# from reportlab.lib.pagesizes import letter
# from reportlab.pdfgen import canvas
# from datetime import date
# from django.http import HttpResponse
# from django.template.loader import render_to_string
# from django.shortcuts import get_object_or_404
# import pdfkit
# from student_management.models import StudentApplicant
# import os
# from PyPDF2 import PdfMerger, PdfReader
# from PyPDF2.errors import PdfReadError
# from PIL import Image
# import os
# from io import BytesIO
# from django.conf import settings
# from reportlab.lib.pagesizes import A4

# from django.http import HttpResponse
# from django.conf import settings
# from django.shortcuts import get_object_or_404
# from reportlab.pdfgen import canvas
# from reportlab.lib.pagesizes import A4, letter
# from PyPDF2 import PdfMerger, PdfReader
# from PIL import Image
# import os
# from io import BytesIO
# from control_room.models import Program


# def generate_student_pdf(request, student_id):
#     student = get_object_or_404(StudentApplicant, id=student_id)
    
#     # Create a buffer for the main PDF content
#     main_pdf_buffer = BytesIO()
    
#     try:
#         # Create canvas with the buffer (not response)
#         c = canvas.Canvas(main_pdf_buffer, pagesize=letter)
#         width, height = letter  # Changed from A4 to letter for consistency
        
#         # --- ALL YOUR EXISTING CONTENT GENERATION CODE ---
#         # (Keep everything exactly as is, just indented one level)
        
#         logo_path = os.path.join(settings.BASE_DIR, 'static', 'image', 'Edenberg.png')
#         profile_img_path = os.path.join(settings.MEDIA_ROOT, str(student.passport_size_photo)) if student.passport_size_photo else None

#         if os.path.exists(logo_path):
#             c.saveState()
#             c.translate(width / 2, height / 2)
#             c.rotate(0)  
#             c.setFillAlpha(0.2)
#             c.drawImage(logo_path, -100, -100, width=220, height=200)
#             c.restoreState()
        
#         y_position = height - 150  # Starting position for the first line
    
#         c.setFont("Helvetica-Bold", 14)
#         c.drawString(230, height - 50, "University of Edenberg")
#         c.drawString(250, height - 65, "Student Form")
        
#         if os.path.exists(logo_path):
#             c.drawImage(logo_path, 150, height - 80, width=80, height=60)
            
#         if profile_img_path and os.path.exists(profile_img_path):
#             c.drawImage(profile_img_path, 450, height - 220, width=100, height=100)
#         else:
#             c.drawString(450, height - 230, "No Photo Available")
           
#         c.setFont("Helvetica", 10)
#         x_label = 50
#         x_value = 180
#         y_position = 700  
#         line_spacing = 15
#         program = Program.objects.filter(program_code=student.first_choice).first()
#         program = program.program_name
#         details = [
#             ("Programme of Study", student.programme_of_study),
#             ("First Choice", program),
#             ("Second Choice", student.second_choice),
#             ("Certificate Program", student.certificate_program),
#             ("Intake", student.Intake),
#             ("Mode of Study", student.mode_of_study),
#             ("First Name", student.title),
#             ("Surname", student.surname),
#             ("Other Names", student.other_names),
#             ("Gender", student.gender),
#             ("Date of Birth", student.date_of_birth),
#             ("Marital Status", student.marital_status),
#             ("NRC Number", student.nrc_number),
#             ("Mobile Number", student.mobile_number),
#             ("Email Address", student.email_address),
#             ("Postal Address", student.postal_address),
#             ("Has Disability", student.has_disability),
#             ("Disability Description", student.disability_description),
#             ("Next of Kin Name", student.next_of_kin_name),
#             ("Next of Kin Phone", student.next_of_kin_phone),
#             ("Next of Kin Email", student.next_of_kin_email),

#             ("O-Level Examination Body", student.o_level_examination_body),
#             ("A-Level Examination Body", student.a_level_examination_body),
#             ("Applicant Form", student.applicant_form),
#         ]
        
#         # ... (keep all your existing drawing commands exactly as they are)
        
#         c.drawString(250, 655, 'Year:')
#         c.drawString(300, 655, str(int(student.year)))
        
#         c.drawString(200, 625, student.first_name)
        
#         # c.drawString(250, 565, 'Age:')
#         # c.drawString(300, 565, str(int(student.age)))
        
#         # c.drawString(250, 550, 'Are You Employed?:')
#         # c.drawString(360, 550, str(int(student.employee_status or 0)))
        
#         c.drawString(250, 520, 'Alternate Mobile Number:')
#         try:
#             alt_number = int(student.alternate_mobile_number)
#             c.drawString(365,520,str(alt_number))
#         except (TypeError, ValueError):
#             c.drawString(365,520,"N/A")
        
#         c.setFont("Helvetica", 10)
#         for label, value in details:
#             if value:
#                 c.drawString(x_label, y_position, f"{label}:")
#                 c.drawString(x_value, y_position, str(value))
#                 y_position -= line_spacing
        
#         # **Educational Details Table**
#         c.setFont("Helvetica-Bold", 10)
#         c.drawString(50, y_position - 10, "Educational Details")
#         y_position -= 40
        
#         table_x = 30
#         col_widths = [150, 150, 120, 120]  
#         row_height = 20
#         headers = ["Institute/University", "Qualification", "From Year", "To Year"]
        
#         c.setFont("Helvetica-Bold", 10)
#         x = table_x
#         for i, header in enumerate(headers):
#             c.drawString(x + 5, y_position + 5, header)
#             c.rect(x, y_position, col_widths[i], row_height)
#             x += col_widths[i]
#         y_position -= row_height
        
#         c.setFont("Helvetica", 10)
#         education_details = student.student_educational_details.all()
        
#         for edu in education_details:
#             x = table_x
#             row_data = [edu.institute_university, edu.qualification_obtained, str(edu.from_year), str(edu.to_year)]
            
#             for i, data in enumerate(row_data):
#                 c.drawString(x + 5, y_position + 5, data)
#                 c.rect(x, y_position, col_widths[i], row_height)
#                 x += col_widths[i]
            
#             y_position -= row_height
        
#         c.setFont("Helvetica-Bold", 10)
#         c.drawString(50, y_position - 10, "Post Graduate Educational Details")
#         y_position -= 40
        
#         c.setFont("Helvetica-Bold", 10)
#         x = table_x
#         for i, header in enumerate(headers):
#             c.drawString(x + 5, y_position + 5, header)
#             c.rect(x, y_position, col_widths[i], row_height)
#             x += col_widths[i]
#         y_position -= row_height
        
#         c.setFont("Helvetica", 10)
#         post_graduate_details = student.post_graduate_educational_details.all()
        
#         for pg_edu in post_graduate_details:
#             x = table_x
#             row_data = [pg_edu.institute_university, pg_edu.qualification_obtained, str(pg_edu.from_year), str(pg_edu.to_year)]
            
#             for i, data in enumerate(row_data):
#                 c.drawString(x + 5, y_position + 5, data)
#                 c.rect(x, y_position, col_widths[i], row_height)
#                 x += col_widths[i]
            
#             y_position -= row_height
        
#         c.showPage()
#         c.save()
        
#     except Exception as e:
#         # print(f"Error generating main PDF: {str(e)}")
#         # Create simple error PDF
#         main_pdf_buffer = BytesIO()
#         c = canvas.Canvas(main_pdf_buffer, pagesize=letter)
#         c.drawString(100, 500, "Error generating student details")
#         c.showPage()
#         c.save()
    
#     main_pdf_buffer.seek(0)
    
#     # Prepare final PDF with attachments
#     final_buffer = BytesIO()
#     merger = PdfMerger()
    
#     try:
#         # Add main content
#         merger.append(PdfReader(main_pdf_buffer))
        
#         # Add attachments
#         def convert_image_to_pdf(image_path):
#             img = Image.open(image_path).convert("RGB")
#             img_buffer = BytesIO()
#             img.save(img_buffer, format="PDF")
#             img_buffer.seek(0)
#             return img_buffer

#         attachments = [
#             student.applicant_form,
#             student.certificate12,
#             student.card_or_license,
#             student.deposit_slip,
#             student.ug_certificate,
#         ]

#         for attachment in attachments:
#             if not attachment:
#                 continue

#             file_path = os.path.join(settings.MEDIA_ROOT, str(attachment))
            
#             try:
#                 if not os.path.exists(file_path):
#                     continue

#                 if file_path.lower().endswith('.pdf'):
#                     merger.append(file_path)
#                 elif file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
#                     img_pdf = convert_image_to_pdf(file_path)
#                     merger.append(img_pdf)
                    
#             except Exception as e:
#                 # print(f"Failed to append attachment: {str(e)}")
#                 continue
        
#         merger.write(final_buffer)
        
#     except Exception as e:
#         # print(f"Error merging PDFs: {str(e)}")
#         # Fallback to just the main content
#         final_buffer = main_pdf_buffer
    
#     final_buffer.seek(0)
    
#     # Create response
#     response = HttpResponse(content_type='application/pdf')
#     response['Content-Disposition'] = f'inline; filename="{student.id}_details.pdf"'
#     response.write(final_buffer.read())
    
#     return response

# # def generate_student_pdf(request, student_id):
# #     try:
# #         student = get_object_or_404(StudentApplicant, id=student_id)
        
# #         # Create main PDF buffer
# #         main_pdf_buffer = BytesIO()
        
# #         # 1. Generate main content PDF
# #         c = canvas.Canvas(response, pagesize=letter)
# #         width, height = A4  # Get page size

# #         logo_path = os.path.join(settings.BASE_DIR, 'static', 'image', 'Edenberg.png')
# #         # Convert relative image path to absolute path
# #         profile_img_path = os.path.join(settings.MEDIA_ROOT, str(student.passport_size_photo)) if student.passport_size_photo else None

# #         if os.path.exists(logo_path):
# #             c.saveState()
# #             c.translate(width / 2, height / 2)
# #             c.rotate(0)  
# #             c.setFillAlpha(0.2)  # Set transparency (0 = invisible, 1 = opaque)
# #             c.drawImage(logo_path, -100, -100, width=220, height=200)  # Centered watermark
# #             c.restoreState()
        
# #         y_position = height - 150  # Starting position for the first line
        
# #         c.setFont("Helvetica-Bold", 14)
# #         c.drawString(200, height - 90, "University of Edenberg")
# #         c.drawString(220, height - 105, "Student Form")
        
# #         if os.path.exists(logo_path):
# #             c.drawImage(logo_path, 120, height - 120, width=80, height=60)  # Adjust position and size
            
# #         if profile_img_path and os.path.exists(profile_img_path):
# #             c.drawImage(profile_img_path, 450, height - 220, width=100, height=100)
# #         else:
# #             c.drawString(450, height - 230, "No Photo Available")
# #     # Show text if image missing
        
# #         c.setFont("Helvetica", 10)
# #         x_label = 50  # Position for labels
# #         x_value = 180  # Position for values
# #         y_position = 700  
# #         line_spacing = 15  # Space between lines
        
# #         details = [
# #             ("Programme of Study", student.programme_of_study),
# #             ("First Choice", student.first_choice),
# #             ("Second Choice", student.second_choice),
# #             ("Certificate Program", student.certificate_program),
# #             ("Intake", student.Intake),
# #             ("Mode of Study", student.mode_of_study),
# #             ("First Name", student.title),
# #             ("Surname", student.surname),
# #             ("Other Names", student.other_names),
# #             ("Gender", student.gender),
# #             ("Date of Birth", student.date_of_birth),
# #             ("Marital Status", student.marital_status),
# #             ("NRC Number", student.nrc_number),
# #             ("Mobile Number", student.mobile_number),
# #             ("Email Address", student.email_address),
# #             ("Postal Address", student.postal_address),
# #             ("Has Disability", student.has_disability),
# #             ("Disability Description", student.disability_description),
# #             ("Next of Kin Name", student.next_of_kin_name),
# #             ("Next of Kin Phone", student.next_of_kin_phone),
# #             ("Next of Kin Email", student.next_of_kin_email),

# #             ("O-Level Examination Body", student.o_level_examination_body),
# #             ("A-Level Examination Body", student.a_level_examination_body),
# #             ("Applicant Form", student.applicant_form),
            
# #         ]
# #         c.drawString(250, 655, 'Year:')
# #         c.drawString(300, 655, str(int(student.year)))
        
# #         c.drawString(200, 625, student.first_name)
        
# #         # c.drawString(250, 565, 'Age:')
# #         # c.drawString(300, 565, str(int(student.age)))
        
# #         # c.drawString(250, 550, 'Are You Employed?:')
# #         # c.drawString(360, 550, str(int(student.employee_status or 0)))
        
# #         c.drawString(250, 520, 'Alternate Mobile Number:')
# #         try:
# #             alt_number = int(student.alternate_mobile_number)
# #             c.drawString(365,520,str(alt_number))
# #         except (TypeError, ValueError):
# #             c.drawString(365,520,"N/A")
        
# #         c.setFont("Helvetica", 10)
# #         for label, value in details:
# #             if value:
# #                 c.drawString(x_label, y_position, f"{label}:")
# #                 c.drawString(x_value, y_position, str(value))
# #                 y_position -= line_spacing
        
# #         # **Educational Details Table**
# #         c.setFont("Helvetica-Bold", 10)
# #         c.drawString(50, y_position - 10, "Educational Details")
# #         y_position -= 40
        
# #         table_x = 30
# #         col_widths = [150, 150, 120, 120]  
# #         row_height = 20
# #         headers = ["Institute/University", "Qualification", "From Year", "To Year"]
        
# #         c.setFont("Helvetica-Bold", 10)
# #         x = table_x
# #         for i, header in enumerate(headers):
# #             c.drawString(x + 5, y_position + 5, header)
# #             c.rect(x, y_position, col_widths[i], row_height)
# #             x += col_widths[i]
# #         y_position -= row_height
        
# #         c.setFont("Helvetica", 10)
# #         education_details = student.student_educational_details.all()
        
# #         for edu in education_details:
# #             x = table_x
# #             row_data = [edu.institute_university, edu.qualification_obtained, str(edu.from_year), str(edu.to_year)]
            
# #             for i, data in enumerate(row_data):
# #                 c.drawString(x + 5, y_position + 5, data)
# #                 c.rect(x, y_position, col_widths[i], row_height)
# #                 x += col_widths[i]
            
# #             y_position -= row_height
        
# #         c.setFont("Helvetica-Bold", 10)
# #         c.drawString(50, y_position - 10, "Post Graduate Educational Details")
# #         y_position -= 40
        
# #         c.setFont("Helvetica-Bold", 10)
# #         x = table_x
# #         for i, header in enumerate(headers):
# #             c.drawString(x + 5, y_position + 5, header)
# #             c.rect(x, y_position, col_widths[i], row_height)
# #             x += col_widths[i]
# #         y_position -= row_height
        
# #         c.setFont("Helvetica", 10)
# #         post_graduate_details = student.post_graduate_educational_details.all()
        
# #         for pg_edu in post_graduate_details:
# #             x = table_x
# #             row_data = [pg_edu.institute_university, pg_edu.qualification_obtained, str(pg_edu.from_year), str(pg_edu.to_year)]
            
# #             for i, data in enumerate(row_data):
# #                 c.drawString(x + 5, y_position + 5, data)
# #                 c.rect(x, y_position, col_widths[i], row_height)
# #                 x += col_widths[i]
            
# #             y_position -= row_height
# #         try:
# #             c = canvas.Canvas(main_pdf_buffer, pagesize=letter)
# #             width, height = letter  # Use letter instead of A4 for consistency
            
# #             # Your content generation code here...
# #             # (Keep all your existing drawing commands)
            
# #             c.showPage()
# #             c.save()
            
# #         except Exception as e:
# #             # print(f"Content generation failed: {str(e)}")
# #             main_pdf_buffer = BytesIO()
# #             c = canvas.Canvas(main_pdf_buffer, pagesize=letter)
# #             c.drawString(100, 500, "Error in main content generation")
# #             c.showPage()
# #             c.save()

# #         main_pdf_buffer.seek(0)
        
# #         # 2. Create merged PDF
# #         final_buffer = BytesIO()
# #         merger = PdfMerger()
        
# #         try:
# #             # Add main content
# #             merger.append(PdfReader(main_pdf_buffer))
            
# #             # Add attachments
# #             attachments = [
# #                 student.certificate12,
# #                 student.card_or_license,
# #                 student.deposit_slip,
# #                 student.ug_certificate,
# #             ]
            
# #             for attachment in attachments:
# #                 if not attachment:
# #                     continue
                    
# #                 file_path = os.path.join(settings.MEDIA_ROOT, str(attachment))
                
# #                 if not os.path.exists(file_path):
# #                     continue
                    
# #                 try:
# #                     if file_path.lower().endswith('.pdf'):
# #                         merger.append(file_path)
# #                     elif file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
# #                         img_pdf = convert_image_to_pdf(file_path)
# #                         merger.append(img_pdf)
# #                 except Exception as e:
# #                     # print(f"Failed to append {file_path}: {str(e)}")
                    
# #             merger.write(final_buffer)
            
# #         except Exception as e:
# #             # print(f"Merging failed: {str(e)}")
# #             final_buffer = BytesIO()
# #             c = canvas.Canvas(final_buffer, pagesize=letter)
# #             c.drawString(100, 500, "Error during PDF merging")
# #             c.showPage()
# #             c.save()
            
# #         final_buffer.seek(0)
        
# #         # Prepare response
# #         response = HttpResponse(
# #             final_buffer.getvalue(),
# #             content_type='application/pdf'
# #         )
# #         response['Content-Disposition'] = f'inline; filename="{student.id}_details.pdf"'
# #         return response
        
# #     except Exception as e:
# #         # print(f"Fatal error: {str(e)}")
# #         buffer = BytesIO()
# #         c = canvas.Canvas(buffer, pagesize=letter)
# #         c.drawString(100, 500, "Failed to generate PDF")
# #         c.showPage()
# #         c.save()
# #         buffer.seek(0)
# #         return HttpResponse(buffer.getvalue(), content_type='application/pdf')