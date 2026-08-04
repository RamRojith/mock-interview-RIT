# from django.core.mail import EmailMessage
# from django.conf import settings
# import os
# from student_management.models import Enquiry
# from django.db.models.signals import post_save
# from django.dispatch import receiver

# @receiver(post_save, sender=Enquiry)
# def send_docx_email_view(sender, instance, created,**kwargs):
#     if created:
#         # print("Signal triggered for Enquiry instance:", instance)

#         file_path = os.path.join(settings.BASE_DIR,'media', 'email_docx', 'Enquiry response letter_TM.docx')

#         email = EmailMessage(
#             subject='Your Enquiry – University of Edenberg Programs',
#             body="""
#             Subject: Your Enquiry – University of Edenberg Programs
#         Dear Prospective Student,
#         Thank you for your interest in the programs offered at the University of Edenberg. Our programs at both bachelor’s and master’s levels are open for registration.
#         To register, please use the following link: ------------------------------------------------------------------
#         We look forward to welcoming you to the University of Edenberg—an institution committed to academic excellence and shaping future leaders across Africa and beyond.
#         Warm regards,
#         Admissions Office
#         University of Edenberg
# """, 
#             from_email=settings.EMAIL_HOST_USER,
#             to=[instance.email],
#         )

#         try:
#             # email.attach_file(file_path)
#             email.send()
#             # print("Email sent successfully.")
#         except Exception as e:
#             # print(f"Error sending email: {str(e)}")

