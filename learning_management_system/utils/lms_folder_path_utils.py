import os
from datetime import date

def get_academic_year():
    """
    Dynamically returns academic year string.
    Example:
      If current month >= June → '2025-2026'
      Else (Jan–May) → '2024-2025'
    """
    today = date.today()
    current_year = today.year
    if today.month >= 6:  # June or later
        return f"{current_year}-{current_year + 1}"
    else:  # Before June → part of previous cycle
        return f"{current_year - 1}-{current_year}"
    
def faculty_document_path(instance, filename):
    folder = instance.folder

    # ✅ correct faculty field
    faculty = getattr(folder, "faculty", None)
    faculty_name = faculty.name if faculty else "no_faculty"

    # ✅ correct course access (FK)
    course_obj = getattr(folder, "course", None)
    course = f"{course_obj.course_code} - {course_obj.title}" if course_obj else "no_course"
    department = f"{course_obj.department.degree.degree_code} - {course_obj.department.Department}" if course_obj and course_obj.department else "no_department"
    year = folder.year or "no_year"
    semester = folder.semester or "no_sem"
    batch = getattr(folder, "batch", None) or "no_batch"
    academic_year = get_academic_year()

    filename = os.path.basename(filename)

    return f"faculty_lms_documents/{department}/{academic_year}/{faculty_name}/{course}/batch_{batch}/Year - {year}_Semester - {semester}/{filename}"