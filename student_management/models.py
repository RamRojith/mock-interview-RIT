from django.db import models
from django.dispatch import receiver# Create your models here.
from django.db.models.signals import pre_save, post_save
from django.core.validators import FileExtensionValidator
from course_management.models import Regulations
from user_accounts.models import *
import os
from django.conf import settings
from student_management.utils.upload_paths import *




class HSC_Marks(models.Model):
    personal = models.ForeignKey(PersonalDetails, on_delete=models.CASCADE)
    admissionNo = models.CharField(max_length=20)
    Eleventh_Std_School_Name = models.CharField(max_length=100)
    other_Eleventh_Std_School_Name = models.CharField(max_length=100,blank=True,null=True)

    Eleventh_Std_Year_of_Passing = models.IntegerField()
    Eleventh_Std_Place_of_School = models.CharField(max_length=100)
    Eleventh_Std_Medium_of_Study = models.CharField(max_length=50)
    Eleventh_Std_Category = models.CharField(max_length=50)

    Twelfth_Std_School_Name = models.CharField(max_length=100)
    other_Twelfth_Std_School_Name = models.CharField(max_length=100,blank=True,null=True)

    Twelfth_Std_Year_of_Passing = models.IntegerField()
    Twelfth_Std_Place_of_School = models.CharField(max_length=100)
    Twelfth_Std_Medium_of_Study = models.CharField(max_length=50)
    Twelfth_Std_Category = models.CharField(max_length=50)
    
    Twelfth_Std_Register_No = models.CharField(max_length=20)
    Twelfth_Std_Marksheet_No = models.CharField(max_length=20)
    Twelfth_Std_studied_in = models.CharField(max_length=50)
    Twelfth_Std_Education_Qualified = models.CharField(max_length=50)
    Twelfth_Std_Roll_No = models.CharField(max_length=20,blank=True,null=True)

    Twelfth_Std_aca_Language_Mark = models.CharField(max_length=100,blank=True,null=True)
    Twelfth_Std_aca_English_Mark = models.CharField(max_length=100,blank=True,null=True)
    Twelfth_Std_aca_Mathematics_Mark = models.CharField(max_length=100,blank=True,null=True)
    Twelfth_Std_aca_Physics_Mark = models.CharField(max_length=100,blank=True,null=True)
    Twelfth_Std_aca_Chemistry_Mark = models.CharField(max_length=100,blank=True,null=True)
    Twelfth_Std_aca_Elective_Name = models.CharField(max_length=100,blank=True,null=True)
    Twelfth_Std_aca_Elective_Mark = models.CharField(max_length=50,blank=True,null=True)
    Twelfth_Std_aca_Total_Marks = models.CharField(max_length=50,blank=True,null=True)
    Twelfth_Std_aca_CUT_OFF_Mark = models.CharField(max_length=50,blank=True,null=True)
    Twelfth_Std_aca_PCM_Average = models.CharField(max_length=50,blank=True,null=True)

    Twelfth_Std_voc_Language_Mark = models.CharField(max_length=50,blank=True,null=True)
    Twelfth_Std_voc_English_Mark = models.CharField(max_length=50,blank=True,null=True)
    Twelfth_Std_voc_chemistry_Mark = models.CharField(max_length=50,blank=True,null=True)
    Twelfth_Std_voc_Mathematics_or_Physics_Name = models.CharField(max_length=50,blank=True,null=True)
    Twelfth_Std_voc_Mathematics_or_Physics_Mark = models.CharField(max_length=50,blank=True,null=True)
    Twelfth_Std_voc_Vocational_Theory_Name = models.CharField(max_length=50,blank=True,null=True)
    Twelfth_Std_voc_Vocational_Theory_Mark = models.CharField(max_length=50,blank=True,null=True)
    Twelfth_Std_voc_Practical_Mark = models.CharField(max_length=50,blank=True,null=True)

    Twelfth_Std_voc_Total_Marks = models.CharField(max_length=50,blank=True,null=True)
    Twelfth_Std_voc_CUT_OFF_Mark = models.CharField(max_length=50,blank=True,null=True)
    Twelfth_Std_voc_PCM_Average = models.CharField(max_length=50,blank=True,null=True)

    def __str__(self):
        return self.admissionNo
    
    class Meta:
        managed = False
        db_table = "application_hsc_marks"



class Diplomo(models.Model):
    personal = models.ForeignKey(PersonalDetails, on_delete=models.CASCADE)
    admissionNo = models.CharField(max_length=20)
    Name_of_the_Polytechnic_College= models.CharField(max_length=100)
    Polytechnic_College_place= models.CharField(max_length=100)
    Diploma_apply_for=models.CharField(max_length=50)
    medium_of_study = models.CharField(max_length=50)
    year_of_passing = models.CharField(max_length=50)
    diploma_register_no = models.CharField(max_length=50)
    diploma_certificate_no = models.CharField(max_length=50)
    diploma_studied_in = models.CharField(max_length=50, )
    sem1_total_mark = models.CharField(max_length=15)
    sem1_obtain_mark = models.CharField(max_length=15)
    sem2_total_mark = models.CharField(max_length=15)
    sem2_obtain_mark = models.CharField(max_length=15)
    sem3_total_mark = models.CharField(max_length=15)
    sem3_obtain_mark = models.CharField(max_length=5)
    sem4_total_mark = models.CharField(max_length=5)
    sem4_obtain_mark = models.CharField(max_length=15)
    sem5_total_mark = models.CharField(max_length=15)
    sem5_obtain_mark = models.CharField(max_length=15)
    sem6_total_mark = models.CharField(max_length=15)
    sem6_obtain_mark = models.CharField(max_length=5)
    total_percentages = models.CharField(max_length=100)
    diploma_total_mark = models.CharField(max_length=5)
    diploma_obtain_mark = models.CharField(max_length=100)

    def __str__(self):
        return self.admissionNo
    
    class Meta:
        managed = False
        db_table = "application_diplomo"



class aca(models.Model):
    admissionNo = models.CharField(max_length=25, db_column='admissionNo')
    apply_for = models.CharField(max_length=25, db_column='applyfor')
    hsc_register_no = models.CharField(max_length=25, db_column='hscregno')
    hsc_marksheet_no = models.CharField(max_length=25, db_column='hscmarkno')
    hsc_studied_in = models.CharField(max_length=25, db_column='hscin')
    category = models.CharField(max_length=25, db_column='category')
    subject1_mark = models.IntegerField(db_column='acasub1')
    subject2_mark = models.IntegerField(db_column='acasub2')
    subject3_mark = models.IntegerField(db_column='acasub3')
    subject4_mark = models.IntegerField(db_column='acasub4')
    subject5_mark = models.IntegerField(db_column='acasub5')
    subject6_name = models.CharField(max_length=25, db_column='acasub6n')
    subject6_mark = models.IntegerField(db_column='acasub6')
    total_marks = models.IntegerField(db_column='acatot')
    pcm_average = models.FloatField(db_column='acapcm')
    cutoff_mark = models.FloatField(null=True, blank=True, db_column='acacutoff')

    class Meta:
        db_table = 'hsc_aca'
        managed = False

class dip_aca(models.Model):
    admissionNo = models.CharField(max_length=25, db_column='admissionNo')
    apply_for = models.CharField(max_length=25, db_column='applyfor')
    hsc_register_no = models.CharField(max_length=25, db_column='hscregno')
    hsc_marksheet_no = models.CharField(max_length=25, db_column='hscmarkno')
    hsc_studied_in = models.CharField(max_length=25, db_column='hscin')
    hsc_mark = models.CharField(max_length=25, db_column='hscmark')
    category = models.CharField(max_length=25, db_column='category')
    subject1_mark = models.IntegerField(db_column='acasub1')
    subject2_mark = models.IntegerField(db_column='acasub2')
    subject3_mark = models.IntegerField(db_column='acasub3')
    subject4_mark = models.IntegerField(db_column='acasub4')
    subject5_mark = models.IntegerField(db_column='acasub5')
    subject6_mark = models.IntegerField(db_column='acasub6')
    total_marks = models.IntegerField(db_column='acatot')
    cutoff_mark = models.CharField(max_length=10, db_column='acacutoff')
    pcm_average = models.CharField(max_length=10, db_column='acapcm')
    subject6_name = models.CharField(max_length=30, db_column='acasub6n')
    diploma_name = models.CharField(max_length=25, db_column='diploman')
    medium_of_study_diploma = models.CharField(max_length=25, db_column='mosinDip')
    year_diploma = models.CharField(max_length=25, db_column='yearDip')
    diploma_register_no = models.CharField(max_length=25, db_column='dipregno')
    diploma_certificate_no = models.CharField(max_length=25, db_column='dipcerno')
    diploma_institution = models.CharField(max_length=25, db_column='dipin')
    education_qualification_diploma = models.CharField(max_length=25, db_column='eduqualdip')
    semester1_mark = models.IntegerField(db_column='sem1')
    semester1_average = models.CharField(max_length=10, db_column='avg1')
    semester2_mark = models.IntegerField(db_column='sem2')
    semester2_average = models.CharField(max_length=10, db_column='avg2')
    semester3_mark = models.IntegerField(db_column='sem3')
    semester3_average = models.CharField(max_length=10, db_column='avg3')
    semester4_mark = models.IntegerField(db_column='sem4')
    semester4_average = models.CharField(max_length=10, db_column='avg4')
    semester5_mark = models.IntegerField(db_column='sem5')
    semester5_average = models.CharField(max_length=10, db_column='avg5')
    semester6_mark = models.IntegerField(db_column='sem6')
    semester6_average = models.CharField(max_length=10, db_column='avg6')
    diploma_obtained_marks = models.CharField(max_length=11, db_column='dipobtain')
    diploma_total_marks = models.CharField(max_length=11, db_column='diptotal')
    diploma_average = models.CharField(max_length=11, db_column='dipavg')

    class Meta:
        db_table = 'hsc_dip_aca'
        managed = False

class dip_voc(models.Model):
    admissionNo = models.CharField(max_length=25, db_column='admissionNo')
    apply_for = models.CharField(max_length=25, db_column='applyfor')
    hsc_register_no = models.CharField(max_length=25, db_column='hscregno')
    hsc_marksheet_no = models.CharField(max_length=25, db_column='hscmarkno')
    hsc_studied_in = models.CharField(max_length=25, db_column='hscin')
    hsc_mark = models.CharField(max_length=25, db_column='hscmark')
    category = models.CharField(max_length=25, db_column='category')
    vocational_subject1_mark = models.IntegerField(db_column='vocsub1')
    vocational_subject2_mark = models.IntegerField(db_column='vocsub2')
    vocational_subject3_name = models.CharField(max_length=30, db_column='vocsub3n')
    vocational_subject3_mark = models.IntegerField(db_column='vocsub3')
    vocational_subject4_mark = models.IntegerField(db_column='vocsub4')
    vocational_subject5_name = models.CharField(max_length=30, db_column='vocsub5n')
    vocational_subject5_mark = models.IntegerField(db_column='vocsub5')
    vocational_subject6_name = models.CharField(max_length=30, db_column='vocsub6n')
    vocational_subject6_mark = models.IntegerField(db_column='vocsub6')
    vocational_total_marks = models.IntegerField(db_column='voctot')
    vocational_cutoff_mark = models.CharField(max_length=10, db_column='voccutoff')
    vocational_pcm_average = models.CharField(max_length=10, db_column='vocpcm')
    diploma_name = models.CharField(max_length=25, db_column='diploman')
    medium_of_study_diploma = models.CharField(max_length=25, db_column='mosinDip')
    year_diploma = models.CharField(max_length=25, db_column='yearDip')
    diploma_register_no = models.CharField(max_length=25, db_column='dipregno')
    diploma_certificate_no = models.CharField(max_length=25, db_column='dipcerno')
    diploma_institution = models.CharField(max_length=25, db_column='dipin')
    education_qualification_diploma = models.CharField(max_length=25, db_column='eduqualdip')
    semester1_mark = models.IntegerField(db_column='sem1')
    semester1_average = models.CharField(max_length=10, db_column='avg1')
    semester2_mark = models.IntegerField(db_column='sem2')
    semester2_average = models.CharField(max_length=10, db_column='avg2')
    semester3_mark = models.IntegerField(db_column='sem3')
    semester3_average = models.CharField(max_length=10, db_column='avg3')
    semester4_mark = models.IntegerField(db_column='sem4')
    semester4_average = models.CharField(max_length=10, db_column='avg4')
    semester5_mark = models.IntegerField(db_column='sem5')
    semester5_average = models.CharField(max_length=10, db_column='avg5')
    semester6_mark = models.IntegerField(db_column='sem6')
    semester6_average = models.CharField(max_length=10, db_column='avg6')
    diploma_obtained_marks = models.CharField(max_length=11, db_column='dipobtain')
    diploma_total_marks = models.CharField(max_length=11, db_column='diptotal')
    diploma_average = models.CharField(max_length=11, db_column='dipavg')

    class Meta:
        db_table = 'hsc_dip_voc'
        managed = False

class voc(models.Model):
    admissionNo = models.CharField(max_length=25, db_column='admissionNo')
    apply_for = models.CharField(max_length=25, db_column='applyfor')
    hsc_register_no = models.CharField(max_length=25, db_column='hscregno')
    hsc_marksheet_no = models.CharField(max_length=25, db_column='hscmarkno')
    hsc_studied_in = models.CharField(max_length=25, db_column='hscin')
    category = models.CharField(max_length=25, db_column='category')
    vocational_subject1_mark = models.IntegerField(db_column='vocsub1')
    vocational_subject2_mark = models.IntegerField(db_column='vocsub2')
    vocational_subject3_name = models.CharField(max_length=25, db_column='vocsub3n')
    vocational_subject3_mark = models.IntegerField(db_column='vocsub3')
    vocational_subject4_mark = models.IntegerField(db_column='vocsub4')
    vocational_subject5_name = models.CharField(max_length=25, db_column='vocsub5n')
    vocational_subject5_mark = models.IntegerField(db_column='vocsub5')
    vocational_subject6_name = models.CharField(max_length=25, db_column='vocsub6n')
    vocational_subject6_mark = models.IntegerField(db_column='vocsub6')
    vocational_total_marks = models.IntegerField(db_column='voctot')
    vocational_cutoff_mark = models.FloatField(db_column='voccutoff')
    vocational_pcm_average = models.FloatField(db_column='vocpcm')

    class Meta:
        db_table = 'hsc_voc'
        managed = False

class dip_cgpa(models.Model):
    admissionNo = models.CharField(max_length=25, db_column='admissionNo')
    apply_for = models.CharField(max_length=25, db_column='applyfor')
    diploma_name = models.CharField(max_length=30, db_column='diploman')
    medium_of_study_diploma = models.CharField(max_length=25, db_column='mosinDip')
    year_diploma = models.CharField(max_length=25, db_column='yearDip')
    diploma_register_no = models.CharField(max_length=25, db_column='dipregno')
    diploma_certificate_no = models.CharField(max_length=25, db_column='dipcerno')
    diploma_institution = models.CharField(max_length=25, db_column='dipin')
    education_qualification_diploma = models.CharField(max_length=25, db_column='eduqualdip')
    semester1_mark = models.IntegerField(db_column='sem1')
    semester1_average = models.CharField(max_length=10, db_column='avg1')
    semester2_mark = models.IntegerField(db_column='sem2')
    semester2_average = models.CharField(max_length=10, db_column='avg2')
    semester3_mark = models.IntegerField(db_column='sem3')
    semester3_average = models.CharField(max_length=10, db_column='avg3')
    semester4_mark = models.IntegerField(db_column='sem4')
    semester4_average = models.CharField(max_length=10, db_column='avg4')
    semester5_mark = models.IntegerField(db_column='sem5')
    semester5_average = models.CharField(max_length=10, db_column='avg5')
    semester6_mark = models.IntegerField(db_column='sem6')
    semester6_average = models.CharField(max_length=10, db_column='avg6')
    diploma_obtained_marks = models.CharField(max_length=11, db_column='dipobtain')
    diploma_total_marks = models.CharField(max_length=11, db_column='diptotal')
    diploma_average = models.CharField(max_length=11, db_column='dipavg')

    class Meta:
        db_table = 'dip'
        managed = False

class aca_details(models.Model):
    admissionNo = models.CharField(max_length=25, db_column='admissionNo')
    emis_id = models.CharField(max_length=40, db_column='emis')
    counselling_number = models.CharField(max_length=25, null=True, blank=True, db_column='counselNo')
    counselling_rank = models.CharField(max_length=15, null=True, blank=True, db_column='counselRank')
    gq_seat = models.CharField(max_length=100, null=True, blank=True, db_column='GQseat')
    tenth_school_name = models.CharField(max_length=100, db_column='schoolName10')
    tenth_year_of_passing = models.IntegerField(db_column='yearOfPassing10')
    tenth_place = models.CharField(max_length=25, db_column='place10')
    tenth_medium_of_study = models.CharField(max_length=20, db_column='mosin10')
    tenth_school_type = models.CharField(max_length=20, db_column='schooltype10')
    eleventh_school_name = models.CharField(max_length=100, db_column='schoolName11')
    eleventh_year_of_passing = models.IntegerField(db_column='yearOfPassing11')
    eleventh_place = models.CharField(max_length=25, db_column='place11')
    eleventh_medium_of_study = models.CharField(max_length=15, db_column='mosin11')
    eleventh_school_type = models.CharField(max_length=15, db_column='schooltype11')
    twelfth_school_name = models.CharField(max_length=100, db_column='schoolName12')
    twelfth_year_of_passing = models.IntegerField(db_column='yearOfPassing12')
    twelfth_place = models.CharField(max_length=25, db_column='place12')
    twelfth_medium_of_study = models.CharField(max_length=15, db_column='mosin12')
    twelfth_school_type = models.CharField(max_length=15, db_column='schooltype12')
    sslc_register_no = models.CharField(max_length=25, db_column='sslcregno')
    sslc_exam_no = models.CharField(max_length=25, db_column='sslcexamno')
    sslc_marksheet_no = models.CharField(max_length=25, db_column='sslcmarkno')
    sslc_studied_in = models.CharField(max_length=25, db_column='sslcin')
    Tenth_Std_Tamil_Name = models.CharField(max_length=20, db_column='sslcsub1')
    sslc_subject1_mark = models.IntegerField(db_column='sslcsubm1')
    Tenth_Std_Tamil_Obtain_Mark = models.IntegerField(db_column='sslcout1')
    Tenth_Std_English_Name = models.CharField(max_length=20, db_column='sslcsub2')
    sslc_subject2_mark = models.IntegerField(db_column='sslcsubm2')
    Tenth_Std_English_Obtain_Mark = models.IntegerField(db_column='sslcout2')
    Tenth_Std_Maths_Name = models.CharField(max_length=20, db_column='sslcsub3')
    sslc_subject3_mark = models.IntegerField(db_column='sslcsubm3')
    Tenth_Std_Maths_Obtain_Mark = models.IntegerField(db_column='sslcout3')
    Tenth_Std_Science_Name = models.CharField(max_length=20, db_column='sslcsub4')
    sslc_subject4_mark = models.IntegerField(db_column='sslcsubm4')
    Tenth_Std_Science_Obtain_Mark = models.IntegerField(db_column='sslcout4')
    Tenth_Std_SocialScience_Name = models.CharField(max_length=20, db_column='sslcsub5')
    sslc_subject5_mark = models.IntegerField(db_column='sslcsubm5')
    Tenth_Std_SocialScience_Obtain_Mark = models.IntegerField(db_column='sslcout5')
    Tenth_Std_Others_Name = models.CharField(max_length=20, null=True, blank=True, db_column='sslcsub6')
    sslc_subject6_mark = models.IntegerField(null=True, blank=True, default=0, db_column='sslcsubm6')
    Tenth_Std_Others_Obtain_Mark = models.IntegerField(null=True, blank=True, default=100, db_column='sslcout6')
    sslc_total_marks = models.IntegerField(db_column='sscltot')
    Tenth_Std_Obtain_Mark = models.IntegerField(db_column='sslcout')

    class Meta:
        db_table = 'admission_details'
        managed = False
class StudentManagementPermissions(models.Model):
    role = models.ForeignKey(
        "user_accounts.Role",       # Role from external DB
        on_delete=models.DO_NOTHING, 
        db_constraint=False         # 🚨 disables DB-level FK
    )
    function = models.CharField(max_length=500)
    permission = models.BooleanField()


class Student_cgpa(models.Model):
    reg_no = models.CharField(max_length=20, primary_key=True)
    batch = models.CharField(max_length=100)
    Name = models.CharField(max_length=100, db_column='student_name')
    department = models.CharField(max_length=100)
    section = models.CharField(max_length=100)
    cgpa = models.FloatField()
    Tenth_Std_Obtain_Mark = models.FloatField(db_column = 'sslc')
    Twelfth_Std_aca_Total_Marks = models.CharField(max_length=20, blank=True, null=True , db_column = 'hsc')
    total_percentages = models.CharField(max_length=20, blank=True, null=True ,  db_column = 'diploma')
    bag_of_log = models.IntegerField()
    history_of_arrear = models.IntegerField()
    admission_type = models.CharField(max_length=100, blank=True, null=True)
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    semester1 = models.CharField(max_length=20, blank=True, null=True)
    semester2 = models.CharField(max_length=20, blank=True, null=True)
    semester3 = models.CharField(max_length=20, blank=True, null=True)
    semester4 = models.CharField(max_length=20, blank=True, null=True)
    semester5 = models.CharField(max_length=20, blank=True, null=True)
    semester6 = models.CharField(max_length=20, blank=True, null=True)
    semester7 = models.CharField(max_length=20, blank=True, null=True)
    semester8 = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        db_table = "application_student"
        managed = False

class StudentCO_EX_Curricular(models.Model):
    
    ACTIVITY_CHOICES = [
        ('Co-curricular', 'Co-curricular'),
        ('Extra-curricular', 'Extra-curricular'),
    ]

    LEVEL_CHOICES = [
        ('College', 'College'),
        ('State', 'State'),
        ('National', 'National'),
        ('International', 'International'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    mentor = models.ForeignKey(
        "faculty_management.general_information",
        on_delete=models.CASCADE,
        null=True, blank=True
    )
    batch = models.CharField(max_length=100, null=True, blank=True)
    semester = models.CharField(max_length=100, null=True, blank=True)
    section = models.CharField(max_length=100, null=True, blank=True)
    year = models.CharField(max_length=100, null=True, blank=True)
    academic_year = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    student = models.ForeignKey(
        "user_accounts.StudentDetails",
        on_delete=models.CASCADE,
        null=True, blank=True
    )
    department = models.ForeignKey(
        "user_accounts.Add_Department",
        on_delete=models.CASCADE,
        null=True, blank=True
    )

    activity_type = models.CharField(
        max_length=20,
        choices=ACTIVITY_CHOICES,
        null=True, blank=True
    )
    event_name = models.CharField(max_length=255, null=True, blank=True)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    from_date = models.DateField(null=True, blank=True)
    to_date = models.DateField(null=True, blank=True)
    total_days = models.PositiveIntegerField(null=True, blank=True)

    certificate = models.FileField(
        upload_to=certificate_dir,
        null=True, blank=True
    )

    # ✅ NEW FIELD
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )

    def __str__(self):
        return f"{self.student} - {self.event_name} ({self.status})"

   
from django.db import models

class StudentAchievements(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]

    student = models.ForeignKey("user_accounts.StudentDetails", on_delete=models.CASCADE, null=True, blank=True)
    mentor = models.ForeignKey("faculty_management.general_information", on_delete=models.CASCADE, null=True, blank=True)
    department = models.ForeignKey("user_accounts.Add_Department", on_delete=models.CASCADE, null=True, blank=True)

    batch = models.CharField(max_length=100, null=True, blank=True)
    semester = models.CharField(max_length=100, null=True, blank=True)
    section = models.CharField(max_length=100, null=True, blank=True)
    year = models.CharField(max_length=100, null=True, blank=True)
    academic_year = models.CharField(max_length=100, null=True, blank=True)

    date = models.DateField(null=True, blank=True)
    award_name = models.CharField(max_length=200, null=True, blank=True)
    contest = models.CharField(max_length=200, null=True, blank=True)
    given_by = models.CharField(max_length=200, null=True, blank=True)

    event_type = models.CharField(max_length=50, default="achievements", null=True, blank=True)
    certificate = models.FileField(upload_to=certificate_dir, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    # ✅ NEW (replaces is_verified)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")

    def __str__(self):
        # guard if student is null
        student_name = getattr(self.student, "name", "Unknown Student")
        return f"{student_name} - {self.award_name}"


from django.db import models

class StudentPublication(models.Model):
    PRESENTATION_CHOICES = [
        ("Presented", "Presented"),
        ("Not Presented", "Not Presented"),
    ]

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]

    mentor = models.ForeignKey("faculty_management.general_information", on_delete=models.CASCADE, null=True, blank=True)
    student = models.ForeignKey("user_accounts.StudentDetails", on_delete=models.CASCADE, null=True, blank=True)
    department = models.ForeignKey("user_accounts.Add_Department", on_delete=models.CASCADE, null=True, blank=True)
    batch = models.CharField(max_length=100, null=True, blank=True)
    semester = models.CharField(max_length=100, null=True, blank=True)
    section = models.CharField(max_length=100, null=True, blank=True)
    year = models.CharField(max_length=100, null=True, blank=True)
    academic_year = models.CharField(max_length=100, null=True, blank=True)

    authors = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    program_name = models.CharField(max_length=255)
    publication_date = models.DateField()
    volume = models.CharField(max_length=100, blank=True, null=True)
    presented = models.CharField(max_length=20, choices=PRESENTATION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    # ✅ NEW FIELD (replaces is_verified)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")

    def __str__(self):
        return f"{self.title} by {self.authors}"


# student_management/models.py

from django.db import models

class StudentProfessionl(models.Model):
    VALIDITY_CHOICES = [
        ("lifetime", "Lifetime"),
        ("period", "Validity Period"),
    ]

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]

    mentor = models.ForeignKey(
        "faculty_management.general_information",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    student = models.ForeignKey(
        "user_accounts.StudentDetails",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    department = models.ForeignKey(
        "user_accounts.Add_Department",
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    semester = models.CharField(max_length=100, null=True, blank=True)
    section = models.CharField(max_length=100, null=True, blank=True)
    year = models.CharField(max_length=100, null=True, blank=True)
    academic_year = models.CharField(max_length=100, null=True, blank=True)

    bodyName = models.CharField(max_length=200)
    validity = models.CharField(max_length=50, choices=VALIDITY_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    # ✅ NEW (replaces is_verified)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")

    def __str__(self):
        if self.student:
            return f"{self.student.name} ({self.student.reg_no}) - {self.status}"
        return "Professional Record"

from django.db import models

class StudentProjects(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("on going", "On Going"),
        ("completed", "Completed"),
    ]
    ACTIVITY_CHOICES = [
        ("college", "College"),
        ("hackathon", "Hackathon"),
    ]
    APPROVAL_STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]

    # ✅ Student info (merged from StudentName)
    student = models.ForeignKey(
        "user_accounts.StudentDetails",
        on_delete=models.CASCADE,
        null=True, blank=True
    )
    department = models.ForeignKey(
        "user_accounts.Add_Department",
        on_delete=models.CASCADE,
        null=True, blank=True
    )
    semester = models.CharField(max_length=100, null=True, blank=True)
    section = models.CharField(max_length=100, null=True, blank=True)
    year = models.CharField(max_length=100, null=True, blank=True)
    batch = models.CharField(max_length=100, null=True, blank=True)

    # ✅ Project info
    title = models.CharField(max_length=200, null=True, blank=True)
    mentor = models.ForeignKey(
        "faculty_management.general_information",
        on_delete=models.CASCADE,
        null=True, blank=True
    )
    domain = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    activity_name = models.CharField(max_length=100, choices=ACTIVITY_CHOICES)
    organisation = models.CharField(max_length=100, null=True, blank=True)
    place = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    academic_year = models.CharField(max_length=100, null=True, blank=True)

    approval_status = models.CharField(
        max_length=10,
        choices=APPROVAL_STATUS_CHOICES,
        default="Pending"
    )

    def __str__(self):
        student_name = getattr(self.student, "name", "Unknown Student")
        return f"{self.title or 'Project'} - {student_name}"
 


class Subject_Assignment(models.Model):
    department = models.ForeignKey("user_accounts.Add_Department", on_delete=models.CASCADE, null=True, blank=True)
    batch = models.CharField(max_length=20, null=True, blank=True)
    section = models.CharField(max_length=10, null=True, blank=True)
    subject = models.CharField(max_length=100, null=True, blank=True)
    course_code = models.CharField(max_length=100, null=True, blank=True)
    faculty_id = models.IntegerField()



    
class Daily_Attendance(models.Model):
    faculty = models.ForeignKey(
        "faculty_management.general_information",
        on_delete=models.CASCADE,
        null=True, blank=True
    )
    student = models.ForeignKey(
        "user_accounts.StudentDetails",
        on_delete=models.CASCADE,
        null=True, blank=True
    )
    year = models.CharField(max_length=20, null=True, blank=True)
    semester = models.CharField(max_length=20, null=True, blank=True)
    section = models.CharField(max_length=10, null=True, blank=True)
    academic_year = models.CharField(max_length=20, null=True, blank=True)

    date = models.DateField(null=True, blank=True)  # Remove auto_now_add=True

    # Half-day statuses
    morning_status = models.CharField(
        max_length=10,
        choices=[('Present', 'Present'), ('Absent', 'Absent'), ('On Duty', 'On Duty')],
        null=True, blank=True
    )
    afternoon_status = models.CharField(
        max_length=10,
        choices=[('Present', 'Present'), ('Absent', 'Absent'), ('On Duty', 'On Duty')],
        null=True, blank=True
    )

    # Computed or manually entered summary (optional)
    full_day_status = models.CharField(
        max_length=10,
        choices=[
            ('Present', 'Present'),
            ('Absent', 'Absent'),
            ('Half Day', 'Half Day'),
            ('On Duty', 'On Duty')
        ],
        null=True, blank=True
    )

    remarks = models.TextField(null=True, blank=True)

    marked_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    marked_by = models.ForeignKey(
       "faculty_management.general_information",
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="attendance_marked"
    )
    updated_by = models.ForeignKey(
        "faculty_management.general_information",
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="attendance_updated"
    )
 
 




class HourAttendance(models.Model):
    faculty = models.ForeignKey(
        "faculty_management.general_information",
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="hour_attendance_faculty"
    )

    department = models.ForeignKey(
        "user_accounts.Add_Department",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="hour_attendance_department"
    )

    batch = models.CharField(max_length=20, null=True, blank=True)
    section = models.CharField(max_length=10, null=True, blank=True)
    academic_year = models.CharField(max_length=20, null=True, blank=True)
    semester = models.CharField(max_length=20, null=True, blank=True)
    year = models.CharField(max_length=20, null=True, blank=True)

    course = models.ForeignKey(
        "course_management.Course",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="hour_attendance_course"
    )

    course_plan = models.ForeignKey(
        "course_management.CoursePlan",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="hour_attendance_course_plan"
    )

    period = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Period number (1, 2, 3, ...)"
    )

    date = models.DateField(default=timezone.now, null=True, blank=True)

    student = models.ForeignKey(
        "user_accounts.StudentDetails",
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="hour_attendance_student"
    )

    status = models.CharField(
        max_length=10,
        choices=[('Present', 'Present'), ('Absent', 'Absent'), ('On Duty', 'On Duty')],
        default='Present',
        null=True,
        blank=True
    )

    remarks = models.TextField(null=True, blank=True)
    marked_at = models.DateTimeField(default=timezone.now, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)



class FeeReceipt(models.Model):

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        VERIFIED = 'VERIFIED', 'Verified'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
    student = models.ForeignKey("user_accounts.StudentDetails", on_delete=models.CASCADE, null=True, blank=True)
    # register_no = models.CharField(max_length=20, null=True, blank=True)
    # student_name = models.CharField(max_length=100)
    department = models.ForeignKey(
        "user_accounts.Add_Department", on_delete=models.CASCADE, null=True, blank=True
    )
    batch = models.CharField(max_length=50, null=True, blank=True)
    section = models.CharField(max_length=5, null=True, blank=True)
    semester = models.IntegerField(null=True, blank=True)
    fee_receipt = models.FileField(upload_to='fee_receipts/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )


    def __str__(self):
        return f"{self.student} - {self.student.reg_no}"
 



class AcademicCalendar(models.Model):
    SEMESTER_CHOICES = [(i, f"Semester {i}") for i in range(1, 9)]
    
    batch = models.CharField(max_length=100,null=True, blank=True)
    semester = models.IntegerField(choices=SEMESTER_CHOICES)
    file = models.FileField(upload_to="academic_calenders/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('batch', 'semester')  # Ensure only one calendar per year+sem

    def __str__(self):
        return f"{self.batch} - Semester {self.semester} Calendar"




class ManualFeeEntry(models.Model):
    fee_receipt = models.OneToOneField(
        'student_management.FeeReceipt',
        on_delete=models.CASCADE,
        related_name='fee_entry'
    )
    entered_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    transaction_id = models.CharField(max_length=50, unique=True, null=True, blank=True)  # ✅ enforce unique
    entered_by = models.CharField(max_length=100, null=True, blank=True)
    entered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    academic_year = models.CharField(max_length=20, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.fee_receipt.status != self.fee_receipt.Status.VERIFIED:
            self.fee_receipt.status = self.fee_receipt.Status.VERIFIED
            self.fee_receipt.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.fee_receipt.student} - {self.transaction_id}"
  




class AssignApproval(models.Model):
    class DefaultApprover(models.TextChoices):
        YES = "YES", "Yes"
        NO = "NO", "No"

    creator_role = models.ForeignKey(
        "user_accounts.Role",
        on_delete=models.SET_NULL,db_constraint=False,
        related_name='assignments_created', null=True, blank=True
    )
    approver_role = models.ForeignKey(
        "user_accounts.Role",
        on_delete=models.SET_NULL,db_constraint=False,
        related_name='assignments_as_approver', null=True, blank=True
    )
    approver_level = models.PositiveIntegerField()
    is_cross_department_approver = models.CharField(
        max_length=3,
        choices=DefaultApprover.choices,
        default=DefaultApprover.NO, null=True, blank=True
    )
    approver_department = models.ForeignKey(
        "user_accounts.Add_Department",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        help_text="Required when is_cross_department_approver is YES"
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        ordering = ['creator_role', 'approver_level']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(approver_level__gt=0),
                name="check_assignapproval_level_positive"
            )
        ]


    def __str__(self):
        return f"{self.creator_role} -> {self.approver_role} (Level {self.approver_level})"

    def save(self, *args, **kwargs):
        if self.is_cross_department_approver == "YES" and not self.approver_department:
            raise ValueError("Approver department must be specified when approver is cross-department.")
        super().save(*args, **kwargs)





from user_accounts.models import StudentDetails,PersonalDetails


class BonafideApplication(models.Model):


    student = models.ForeignKey(
        StudentDetails,
        on_delete=models.CASCADE,null=True, blank=True,
        related_name="bonafide_applications"
    )
    department = models.ForeignKey(Add_Department, on_delete=models.SET_NULL, null=True, blank=True)
    regulation = models.CharField(max_length=10, null=True, blank=True)
    year = models.CharField(max_length=10, null=True, blank=True)
    batch = models.CharField(max_length=10, null=True, blank=True)

    semester = models.CharField(max_length=10, null=True, blank=True)
    academic_year = models.CharField(max_length=9, null=True, blank=True)  # e.g., 2024-2025
    subject = models.CharField(max_length=255, blank=True, null=True)
    other_reason = models.TextField(blank=True, null=True)

    father_name = models.CharField(max_length=255, blank=True, null=True)
    # department_name = models.CharField(max_length=255, blank=True, null=True)
    year_display = models.CharField(max_length=50, blank=True, null=True)

    # Metadata
    applied_on = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True, null=True, blank=True)

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="Pending"
    )

    def __str__(self):
        return f"{self.student.reg_no} - {self.subject or 'Bonafide'} ({self.status})"






class BonafideApprovalFlow(models.Model):
    application = models.ForeignKey(
       'BonafideApplication',
        on_delete=models.CASCADE,
        related_name='approval_flow', null=True, blank=True
    )
    approver_role_id = models.IntegerField(null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)

    approver_department = models.ForeignKey("user_accounts.Add_Department", on_delete=models.CASCADE, null=True, blank=True)
    approver_level = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, default="Pending")  
    acted_on = models.DateTimeField(auto_now=True)
    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Flow: {self.application.student.reg_no} - Level {self.approver_level} ({self.status})"




class Student_LeaveApprovers(models.Model):

    class DefaultApprover(models.TextChoices):
        YES = "YES", "Yes"
        NO = "NO", "No"

    class ApplicantMode(models.TextChoices):
        DEFAULT = "DEFAULT", "Default"
        TRANSPORT = "TRANSPORT", "Transport"
        HOSTEL = "HOSTEL", "Hostel"

    class ApplicantGender(models.TextChoices):
        ANY = "ANY", "Any"
        MALE = "MALE", "Male"
        FEMALE = "FEMALE", "Female"

    creator_role_id = models.IntegerField(
        null=True,
        blank=True
    )

    applicant_mode = models.CharField(
        max_length=20,
        choices=ApplicantMode.choices,
        default=ApplicantMode.DEFAULT,
        blank=True,
        null=True,
    )

    applicant_gender = models.CharField(
        max_length=20,
        choices=ApplicantGender.choices,
        default=ApplicantGender.ANY,
        blank=True,
        null=True,
    )

    approver_role_id = models.IntegerField(
        null=True,
        blank=True
    )

    approver_level = models.PositiveIntegerField()

    is_cross_department_approver = models.CharField(
        max_length=3,
        choices=DefaultApprover.choices,
        default=DefaultApprover.NO,
        blank=True,
        null=True
    )

    approver_department = models.ForeignKey(
        Add_Department,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )

    def __str__(self):

        return (
            f"Level {self.approver_level} "
            f"(Creator Role: {self.creator_role_id}, "
            f"{self.applicant_mode}/{self.applicant_gender})"
        )


class Student_LeaveApproversData(models.Model):

    class Status(models.TextChoices):

        APPROVED = "APPROVED", "Approved"

        PENDING = "PENDING", "Pending"

        REJECTED = "REJECTED", "Rejected"

    leave_application = models.ForeignKey(
        "course_management.StudentLeaveOdApplication",
        on_delete=models.CASCADE,
        related_name="approval_entries",
        blank=True,
        null=True
    )

    # IMPORTANT
    # db_constraint=False avoids cross DB FK issue
    approver_id = models.ForeignKey(
        "user_accounts.USER",
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="student_leave_approver_entries",
        db_constraint=False,
    )

    creator_id = models.ForeignKey(
        "user_accounts.StudentDetails",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="student_leave_creator_entries"
    )

    reason = models.CharField(
        max_length=225,
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        blank=True,
        null=True
    )

    approver_level = models.PositiveIntegerField(
        blank=True,
        null=True
    )

    approved_date = models.DateTimeField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True
    )

    def __str__(self):

        approver = (
            getattr(
                self.approver_id,
                "username",
                None
            ) or "N/A"
        )

        leave_id = (
            self.leave_application_id
            or "N/A"
        )

        return (
            f"Leave #{leave_id} - "
            f"{approver} ({self.status})"
        )






