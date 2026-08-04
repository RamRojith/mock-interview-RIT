import os
import time
from datetime import datetime


def sanitize_upload_path(instance, filename, folder_name):
    """
    Utility function to create safe upload paths for certificates.
    Creates directory structure:
    department/academic_year/faculty_id/folder_name/
    """
    from faculty_management.models import general_information
    from user_accounts.models import USER
    # print("Instance :", instance)
    # print("Filename :", filename)
    # Faculty ID
    faculty_id = getattr(instance.faculty, 'faculty_id', 'unknown')

    # print("Faculty ID :", faculty_id)
    # Academic Year
    current_year = datetime.now().year
    academic_year = f"{current_year - 1}-{current_year}"

    # Department
    department_name = "unknown"
    try:
        gen_info = general_information.objects.filter(id=faculty_id).first()
        # print("General Info :", gen_info)
        if gen_info and getattr(gen_info.department, "Department", None):
            department_name = gen_info.department.Department
        else:
            user = USER.objects.using("rit_approval_system").filter(Employee_id=faculty_id).first()
            if user and getattr(user.Department, "Department", None):
                department_name = user.Department.Department
    except Exception as e:
         return (f"Error getting department for faculty_id {faculty_id}: {e}")

    # Sanitize to strings
    department_name = str(department_name).replace("/", "_").strip() or "unknown"
    academic_year = str(academic_year).replace("/", "_").strip() or "unknown"
    faculty_id = str(faculty_id).strip() or "unknown"
    # print("Department Name :", department_name)
    # print("Academic Year :", academic_year)
    # print("Faculty ID :", faculty_id)

    # Build upload directory
    upload_path = f"{department_name}/{academic_year}/{faculty_id}/{folder_name}/"

    # Safe filename with timestamp
    name, ext = os.path.splitext(filename)
    short_name = name[:20] if len(name) > 20 else name
    timestamp = int(time.time())
    safe_filename = f"{short_name}_{timestamp}{ext}"

    return upload_path + safe_filename


def PAN_certificate_upload_path(instance, filename):
    """Upload path for PAN certificate"""
    return sanitize_upload_path(instance, filename, "PAN")


def Aadhar_certificate_upload_path(instance, filename):
    """Upload path for Aadhar certificate"""
    return sanitize_upload_path(instance, filename, "Aadhar")


def probation_confirmation_upload_path(instance, filename):
    """Upload path for Probation Confirmation Document"""
    return sanitize_upload_path(instance, filename, "Probation")




def sslc_certificate_upload_path(instance, filename):
    """Generate upload path for publication certificates"""
    return sanitize_upload_path(instance, filename, 'Academic_Background')



def hsc_certificate_upload_path(instance, filename):
    """Generate upload path for publication certificates"""
    return sanitize_upload_path(instance, filename, 'Academic_Background')

def ug_certificate_upload_path(instance, filename):
    """Generate upload path for publication certificates"""
    return sanitize_upload_path(instance, filename, 'Academic_Background')

def pg_certificate_upload_path(instance, filename):
    """Generate upload path for publication certificates"""
    return sanitize_upload_path(instance, filename, 'Academic_Background')

def phd_certificate_upload_path(instance, filename):
    """Generate upload path for publication certificates"""
    return sanitize_upload_path(instance, filename, 'Academic_Background')

def mphil_certificate_upload_path(instance, filename):
    """Generate upload path for publication certificates"""
    return sanitize_upload_path(instance, filename, 'Academic_Background')

def postDoc_certificate_upload_path(instance, filename):
    """Generate upload path for publication certificates"""
    return sanitize_upload_path(instance, filename, 'Academic_Background')



def academic_experience_certificate_upload_path(instance, filename):
    """Generate upload path for academic experience certificates"""
    return sanitize_upload_path(instance, filename, 'experience_certificates/academic')  


def industry_experience_certificate_upload_path(instance, filename):
    """Generate upload path for Industry certificates"""
    return sanitize_upload_path(instance, filename, 'experience_certificates/industry')  


def research_experience_certificate_upload_path(instance, filename):
    """Generate upload path for Research certificates"""
    return sanitize_upload_path(instance, filename, 'experience_certificates/research')  



def industry_experience_relieving_certificate_upload_path(instance, filename):
    """Generate upload path for Industry relieving certificates"""
    return sanitize_upload_path(instance, filename, 'experience_certificates/relieving/industry')  

def academic_experience_relieving_certificate_upload_path(instance, filename):
    """Generate upload path for Academic relieving certificates"""
    return sanitize_upload_path(instance, filename, 'experience_certificates/relieving/academic')  

def research_experience_relieving_certificate_upload_path(instance, filename):
    """Generate upload path for Research relieving certificates"""
    return sanitize_upload_path(instance, filename, 'experience_certificates/relieving/research')  

from datetime import date
from dateutil.relativedelta import relativedelta

def industry_experience_certificate_upload_path(instance, filename):
    """Generate upload path for industry experience certificates"""
    import os
    from django.utils import timezone
    
    # Get faculty ID or use 'unknown' if not available
    faculty_id = str(instance.faculty_id) if instance.faculty_id else 'unknown'
    
    # Get current academic year
    current_year = timezone.now().year
    academic_year = f"{current_year}-{current_year + 1}"
    
    # Create safe filename
    safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
    
    return f"{academic_year}/{faculty_id}/experience_certificates/industry/{safe_filename}"

def research_experience_certificate_upload_path(instance, filename):
    """Generate upload path for research experience certificates"""
    import os
    from django.utils import timezone
    
    # Get faculty ID or use 'unknown' if not available
    faculty_id = str(instance.faculty_id) if instance.faculty_id else 'unknown'
    
    # Get current academic year
    current_year = timezone.now().year
    academic_year = f"{current_year}-{current_year + 1}"
    
    # Create safe filename
    safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
    
    return f"{academic_year}/{faculty_id}/experience_certificates/research/{safe_filename}"


def academic_result_certificate_upload_path(instance, filename):
    """Generate upload path for publication certificates"""
    # Get faculty info to create directory structure
    faculty_id = instance.faculty_id or 'unknown'
    
    # Get department from faculty info (you may need to adjust this based on your data structure)
    department = getattr(instance, 'department', 'unknown')
    
    # Get academic year (you may need to adjust this based on your data structure)
    academic_year = getattr(instance, 'academic_year', 'unknown')
    
    # Create directory structure: department/academic_year/faculty_id/publications/
    upload_path = f'{department}/{academic_year}/{faculty_id}/academic_result/'
    
    # Ensure filename is unique
    name, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(os.path.join('media', upload_path, filename)):
        filename = f"{name}_{counter}{ext}"
        counter += 1
    
    return upload_path + filename       
        




