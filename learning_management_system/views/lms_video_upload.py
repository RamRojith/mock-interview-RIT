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




