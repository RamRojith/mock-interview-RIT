import datetime
from django.shortcuts import render, redirect
# from learning_management_system.models import Folder, FacultyDocument
from user_accounts.models import USER, Department, Role
from django.contrib.auth.decorators import login_required
from faculty_management.models import general_information




from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from user_accounts.models import Department
from faculty_management.models import general_information
from learning_management_system.models import Folder


from course_management.models import CourseEnrollment

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from learning_management_system.models import *
from user_accounts.decorators import check_permission




from django.shortcuts import render
from collections import defaultdict

from django.shortcuts import render
from collections import defaultdict

from collections import defaultdict
# from course_management.models import CourseEnrollment

from collections import defaultdict
from django.shortcuts import render, get_object_or_404
from faculty_management.models import general_information
from course_management.models import CourseEnrollment, AssignSubjectFaculty


from collections import defaultdict
from django.shortcuts import render, get_object_or_404

from django.shortcuts import render, get_object_or_404
from django.db.models import Q


@check_permission("lms_subjects")
def lms_subjects(request):
    emp_id = request.user.Employee_id

    faculty = get_object_or_404(
        general_information,
        faculty_id=emp_id
    )

    # Get assigned courses, and group them by semester
    assigned_courses = (
        AssignSubjectFaculty.objects
        .select_related("course", "department", "regulation")
        .filter(
            faculty=faculty,
            is_active=True,
            course__is_active=True
        )
        .order_by("course__semester", "-id")  # Group by semester and order by course code
    )

    # Grouping courses by semester
    # semester -> section -> courses
    semesters = {}

    for assignment in assigned_courses:
        semester = assignment.course.semester
        section = assignment.section or "No Section"

        if semester not in semesters:
            semesters[semester] = {}

        if section not in semesters[semester]:
            semesters[semester][section] = []

        semesters[semester][section].append(assignment)

    return render(
        request,
        "learning_management_system/faculty/lms_subjects.html",
        {
            "faculty": faculty,
            "semesters": semesters,
            "assigned_courses": assigned_courses
        }
    )

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

# @login_required
def course_folders(request, course_id, batch, academic_year, section=None):
    emp_id = request.user.Employee_id

    if not batch:
        messages.error(request, "Batch is required.")
        return redirect('lms_subjects')

    faculty = get_object_or_404(general_information, faculty_id=emp_id)
    course = get_object_or_404(Course, id=course_id)

    assignment_filters = {
        "course": course,
        "batch": batch,
        "is_active": True,
    }
    if section:
        assignment_filters["section"] = section

    assigned_subject = get_object_or_404(
        AssignSubjectFaculty,
        Q(faculty=faculty) | Q(skilled_faculty=faculty),
        **assignment_filters
    )
    section = section or assigned_subject.section

    folders = Folder.objects.filter(
        faculty=faculty,
        course=course,
        year=course.year,
        semester=course.semester,
        regulation=course.regulation,
        folder_type='subject',
        batch=batch,
        academic_year=academic_year,
        section=section
    )

    if request.method == 'POST':
        action = request.POST.get('action')

        # CREATE
        if action == 'create':
            folder_name = request.POST.get('folder_name', '').strip()
            if not folder_name:
                messages.error(request, "Folder name cannot be empty.")
            else:
                Folder.objects.create(
                    folder_name=folder_name,
                    faculty=faculty,
                    course=course,
                    year=course.year,
                    semester=course.semester,
                    regulation=course.regulation,
                    folder_type='subject',
                    batch=batch,
                    academic_year=academic_year,
                    section=section
                )
                messages.success(request, "Folder created successfully.")

        # EDIT
        elif action == 'edit':
            folder_id = request.POST.get('folder_id')
            new_name = request.POST.get('folder_name', '').strip()

            folder = get_object_or_404(Folder, id=folder_id, faculty=faculty)

            if not new_name:
                messages.error(request, "Folder name cannot be empty.")
            else:
                folder.folder_name = new_name
                folder.save()
                messages.success(request, "Folder updated successfully.")

        # DELETE
        elif action == 'delete':
            folder_id = request.POST.get('folder_id')
            folder = get_object_or_404(Folder, id=folder_id, faculty=faculty)
            folder.delete()
            messages.success(request, "Folder deleted successfully.")

        return redirect(request.path)

    return render(request, 'learning_management_system/faculty/course_folders.html', {
        'folders': folders,
        'academic_year': academic_year,
        'batch': batch,
        'course': course
    })





# @login_required
# def upload_to_folder(request, course_id, folder_id):
#     faculty = get_object_or_404(general_information, faculty_id=request.user.Employee_id)
#     folder = get_object_or_404(Folder, id=folder_id, faculty=faculty, course_id=course_id)

#     # Initialize variables for edit mode
#     edit_document = None
#     edit_mode = False

#     # Check if we're in edit mode
#     if 'edit' in request.GET:
#         try:
#             edit_document = FacultyDocument.objects.get(
#                 id=request.GET['edit'],
#                 folder=folder,
#                 uploaded_by=faculty
#             )
#             edit_mode = True
#         except FacultyDocument.DoesNotExist:
#             messages.error(request, "Document not found or you don't have permission to edit it")

#     if request.method == 'POST':
#         # Handle document update
#         if 'update_document' in request.POST and edit_mode:
#             title = request.POST.get('title', '').strip()
#             description = request.POST.get('description', '').strip()
#             file = request.FILES.get('file')

#             edit_document.document_title = title or "Untitled Document"
#             edit_document.description = description
#             if file:
#                 edit_document.file = file
#             edit_document.save()

#             messages.success(request, f"Document '{edit_document.document_title}' updated successfully")
#             return redirect('upload_to_folder', course_id=course_id, folder_id=folder.id)

#         # Handle document delete
#         elif 'delete_document' in request.POST:
#             try:
#                 document = FacultyDocument.objects.get(
#                     id=request.POST['delete_document'],
#                     folder=folder,
#                     uploaded_by=faculty
#                 )
#                 document_title = document.document_title
#                 document.delete()
#                 messages.success(request, f"Document '{document_title}' deleted successfully")
#                 return redirect('upload_to_folder', course_id=course_id, folder_id=folder.id)
#             except FacultyDocument.DoesNotExist:
#                 messages.error(request, "Document not found or you don't have permission to delete it")

#         # Handle new document upload
#         else:
#             title = request.POST.get('title', '').strip()
#             description = request.POST.get('description', '').strip()
#             file = request.FILES.get('file')

#             if not file:
#                 messages.error(request, "No file was uploaded. Please choose a file.")
#             else:
#                 FacultyDocument.objects.create(
#                     folder=folder,
#                     document_title=title or "Untitled Document",
#                     description=description,
#                     file=file,
#                     uploaded_by=faculty,
#                     academic_year=folder.academic_year,
#                     year=folder.year,
#                     semester=folder.semester,
#                     uploaded_at=datetime.datetime.now()
                    
#                 )
#                 messages.success(request, f"Document '{title or 'Untitled'}' uploaded successfully.")
#                 return redirect('upload_to_folder', course_id=course_id, folder_id=folder.id)

#     documents = FacultyDocument.objects.filter(folder=folder, uploaded_by=faculty)
#     print("Documents in folder:", documents)

#     return render(request, 'learning_management_system/faculty/upload_file.html', {
#         'folder': folder,
#         'documents': documents,
#         'edit_document': edit_document,
#         'edit_mode': edit_mode
#     })


from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
import re
from .rag_utils import process_document_embedding, delete_document_embeddings


def upload_to_folder(request, course_id, folder_id):
    emp_id = request.user.Employee_id
    faculty = get_object_or_404(general_information, faculty_id=emp_id)
    folder = get_object_or_404(Folder, id=folder_id, faculty=faculty, course_id=course_id)

    if request.method == "POST":
        action = request.POST.get('action')
        edit_document_id = request.POST.get('edit_document_id')
        edit_video_id = request.POST.get('edit_video_id')

        # ──────────────── DOCUMENT HANDLING ────────────────
        if action in ['upload_document', 'update_document']:
            title = request.POST.get('title', '').strip() or "Untitled Document"
            desc = request.POST.get('description', '').strip()

            if action == 'update_document' and edit_document_id:
                try:
                    doc = FacultyDocument.objects.get(id=edit_document_id, folder=folder, uploaded_by=faculty)
                    doc.document_title = title
                    doc.description = desc
                    if 'file' in request.FILES:
                        doc.file = request.FILES['file']
                    doc.save()
                    messages.success(request, "Document updated successfully.")
                except FacultyDocument.DoesNotExist:
                    messages.error(request, "Document not found or no permission.")
            else:
                file = request.FILES.get('file')
                if not file:
                    messages.error(request, "Please select a file to upload.")
                else:
                    doc = FacultyDocument.objects.create(
                        folder=folder,
                        document_title=title,
                        description=desc,
                        file=file,
                        uploaded_by=faculty,
                        academic_year=folder.academic_year,
                        year=folder.year,
                        semester=folder.semester
                    )
                    process_document_embedding(doc)
                    messages.success(request, "Document uploaded successfully.")

        elif 'delete_document' in request.POST:
            try:
                doc = FacultyDocument.objects.get(id=request.POST['delete_document'], folder=folder, uploaded_by=faculty)
                doc.delete()
                delete_document_embeddings(doc.id)
                messages.success(request, "Document deleted.")
            except FacultyDocument.DoesNotExist:
                messages.error(request, "Document not found.")

        # ──────────────── VIDEO HANDLING ────────────────
        elif action in ['upload_video', 'update_video']:
            title = request.POST.get('title', '').strip() or "Untitled Video"
            url = request.POST.get('youtube_url', '').strip()
            desc = request.POST.get('description', '').strip()

            if not url:
                messages.error(request, "Please provide a YouTube URL.")
            else:
                if action == 'update_video' and edit_video_id:
                    try:
                        vid = FacultyVideo.objects.get(id=edit_video_id, folder=folder, uploaded_by=faculty)
                        vid.title = title
                        vid.youtube_url = url
                        vid.description = desc
                        vid.save()  # Triggers clean/save logic for video_id extraction
                        messages.success(request, "Video updated successfully.")
                    except FacultyVideo.DoesNotExist:
                        messages.error(request, "Video not found or no permission.")
                else:
                    FacultyVideo.objects.create(
                        folder=folder,
                        title=title,
                        youtube_url=url,
                        description=desc,
                        uploaded_by=faculty,
                        academic_year=folder.academic_year,
                        year=folder.year,
                        semester=folder.semester
                    )
                    messages.success(request, "Video added successfully.")

        elif 'delete_video' in request.POST:
            try:
                vid = FacultyVideo.objects.get(id=request.POST['delete_video'], folder=folder, uploaded_by=faculty)
                vid.delete()
                messages.success(request, "Video deleted.")
            except FacultyVideo.DoesNotExist:
                messages.error(request, "Video not found.")

        return redirect('upload_to_folder', course_id=course_id, folder_id=folder_id)

    # Query data for GET or after POST redirect
    documents = FacultyDocument.objects.filter(folder=folder, uploaded_by=faculty).order_by('-uploaded_at')
    videos = FacultyVideo.objects.filter(folder=folder, uploaded_by=faculty).order_by('-uploaded_at')

    context = {
        'folder': folder,
        'documents': documents,
        'videos': videos,
    }

    return render(request, 'learning_management_system/faculty/upload_file.html', context)




# def lms_upload_video(request, folder_id):
#     folder = get_object_or_404(Folder, id=folder_id)

#     if request.method == "POST":
#         title = request.POST.get('title')
#         youtube_url = request.POST.get('youtube_url')
#         description = request.POST.get('description')

#         FacultyVideo.objects.create(
#             folder=folder,
#             title=title,
#             youtube_url=youtube_url,
#             description=description,
#             uploaded_by=request.user.general_information
#         )
#         return redirect('video_list', folder_id=folder.id)

#     return render(request, 'lms/upload_video.html', {"folder": folder})


# @login_required
# def video_list(request, folder_id):
#     folder = get_object_or_404(Folder, id=folder_id)
#     videos = FacultyVideo.objects.filter(folder=folder)

#     return render(request, 'lms/video_list.html', {
#         "folder": folder,
#         "videos": videos
#     })

