import os
import time
from datetime import datetime


        
from django.db import models

def certificate_dir(instance, filename):
    """
    Store certificates inside achievements/<register_no>/<filename>
    """
    return os.path.join("achievements", instance.student.reg_no, filename)
    
        
def publication_certificate_upload_path(instance, filename):
    """Generate upload path for publication certificates"""
    # Get faculty info to create directory structure
    faculty_id = instance.faculty_id or 'unknown'
    
    # Get department from faculty info (you may need to adjust this based on your data structure)
    department = getattr(instance, 'department', 'unknown')
    
    # Get academic year (you may need to adjust this based on your data structure)
    academic_year = getattr(instance, 'academic_year', 'unknown')
    
    # Create directory structure: department/academic_year/faculty_id/publications/
    upload_path = f'{department}/{academic_year}/{faculty_id}/publications/'
    
    # Ensure filename is unique
    name, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(os.path.join('media', upload_path, filename)):
        filename = f"{name}_{counter}{ext}"
        counter += 1
    
    return upload_path + filename




