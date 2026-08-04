from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models
from django.utils import timezone
from django.db import models

class Degree(models.Model):
    degree_code = models.CharField(max_length=255, null=True, blank=True)
    degree = models.CharField(max_length=255, null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True, default=0)
    academic_type = models.CharField(max_length=255, null=True, blank=True)
    degree_graduate = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True ,null=True, blank=True)

    def __str__(self):
        return self.degree or "Unnamed Degree"

    @property
    def effective_duration(self) -> int:
        # Clamp duration to 0..4 without schema changes
        try:
            d = int(self.duration or 0)
        except (TypeError, ValueError):
            d = 0
        return max(0, min(d, 4))
 
 
class Add_Department(models.Model):
    Department = models.CharField(max_length=255, null=True, blank=True)
    Department_code = models.CharField(max_length=255, null=True, blank=True)
    degree = models.ForeignKey('Degree', on_delete=models.CASCADE, null=True, blank=True)
    degree_department = models.CharField(max_length=255, null=True, blank=True)
    department_label = models.CharField(max_length=255, null=True, blank=True)
    degree_department_label = models.CharField(max_length=255, null=True, blank=True)
    is_academic = models.BooleanField(default=False, null=True, blank=True)

    is_active = models.BooleanField(default=True, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)


    

    def __str__(self):
        return self.Department or "Unnamed Department"


class Department(models.Model):
    Department = models.CharField(max_length=255)
    Department_code = models.CharField(max_length=255)


    class Meta:
        managed = False
        db_table = 'control_room_department'
  


class Role(models.Model):
    role = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'control_room_role'


class NewUserAdder(models.Model):
    Employee_id = models.CharField(max_length=225)
    Department = models.ForeignKey(Department, on_delete=models.DO_NOTHING)
    role = models.ForeignKey(Role, on_delete=models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'control_room_new_user_adder'
 
class USER(models.Model):
    username = models.CharField(max_length=500)
    profile_img = models.ImageField(null=True, blank=True)
    Employee_id = models.CharField(max_length=225)
    Department = models.ForeignKey(Department, on_delete=models.DO_NOTHING)
    role = models.ForeignKey(Role, on_delete=models.DO_NOTHING)
    unique_id = models.CharField(max_length=100, unique=True, null=True)
    is_student = models.BooleanField(default=False)
    password = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    email = models.EmailField(max_length=255, unique=True, null=True)
    is_parent = models.BooleanField(default=False)
    profile_img = models.ImageField(null=True,blank=True)

    class Meta:
        managed = False
        db_table = 'control_room_user'

    def __str__(self):
        return self.username
  
    
    @property
    def is_authenticated(self):
        """
        Always return True for USER objects. This is a way to tell if
        the user has been authenticated in templates.
        """
        return True
    
    @property
    def is_anonymous(self):
        """
        Always return False for USER objects. This is a way to tell if
        the user is anonymous in templates.
        """
        return False
     
 
class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    roll_no = models.CharField(max_length=20, unique=True)
    aadhar = models.CharField(max_length=12, unique=True)

    def __str__(self):
        return f"{self.roll_no} - {self.name}"
    


class StudentDetails(models.Model):
    aadhar_number = models.CharField(
        max_length=12,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Aadhar Number"
    )
    name = models.CharField(max_length=255, null=True, blank=True)
    reg_no = models.CharField(max_length=255, unique=True, null=True, blank=True, verbose_name="Register Number")
    department = models.ForeignKey(Add_Department, on_delete=models.CASCADE, null=True, blank=True)
    regulation = models.CharField(max_length=50, null=True, blank=True)
    batch = models.CharField(max_length=50, null=True, blank=True)
    year = models.CharField(max_length=50, null=True, blank=True)
    semester = models.CharField(max_length=50, null=True, blank=True)
    umis_id = models.CharField(max_length=50, null=True, blank=True)
    section = models.CharField(max_length=10, null=True, blank=True)
    profile_img = models.ImageField(upload_to="student_profiles_photos/", null=True, blank=True)
    email = models.EmailField(max_length=255, unique=True, null=True, blank=True)
    mobile_no = models.CharField(max_length=15, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=50, null=True, blank=True, choices=[
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other')
    ])
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True) 
    last_updated = models.DateTimeField(null=True, blank=True)
    # mentor = models.CharField(max_length=255, null=True, blank=True)
    # ca = models.CharField(max_length=255, null=True, blank=True)
    mentor = models.ForeignKey(
        "faculty_management.general_information",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mentor_students"  # reverse relation from general_information
    )
    ca = models.ForeignKey(
    "faculty_management.general_information",
    on_delete=models.SET_NULL,
    null=True,
    auto_created=True,
    blank=True,
    related_name="ca_students"  # reverse relation from general_information
    )
    
    year_of_admission = models.CharField(max_length=10,default = "1", null=True, blank=True)
    semester_of_admission = models.CharField(max_length=10,default = "1", null=True, blank=True)
    mode = models.CharField(max_length=50, null=True, blank=True)
    is_active = models.BooleanField(default=True, null=True, blank=True)
    is_break_of_study = models.BooleanField(default=False, null=True, blank=True)
    date_of_admission = models.CharField(max_length=10, null=True, blank=True)
    is_discontinued = models.BooleanField(default=False, null=True, blank=True)


    
    # academic_status = models.CharField(max_length=100, null=True, blank=True)
    def __str__(self):
        return f"{self.name} ({self.reg_no})"
        
    
   

  




class PersonalDetails(models.Model):
    id=models.AutoField(primary_key=True, db_column='Id')
    created_at = models.DateTimeField(auto_now_add=True, db_column='CreatedAt')
    Aadhaar_Number = models.CharField(max_length=20, db_column='AadhaarNumber', unique=True)
    age = models.IntegerField(db_column='Age')
    caste = models.CharField(max_length=255, db_column='Caste')
    community = models.CharField(max_length=255, db_column='Community')
    community_no = models.CharField(max_length=50, db_column='CommunityNumber')
    date_of_birth = models.DateField(db_column='DateOfBirth')
    father_mobile_no = models.CharField(max_length=15, db_column='FatherMobileNo')
    father_name = models.CharField(max_length=100, db_column='FatherName')
    guardian_mobile_no = models.CharField(max_length=15, db_column='GuardianMobileNo')
    guardian_name = models.CharField(max_length=100, db_column='GuardianName')
    mother_mobile_no = models.CharField(max_length=15, db_column='MotherMobileNo')
    mother_name = models.CharField(max_length=100, db_column='MotherName')
    mother_tounge = models.CharField(max_length=50, db_column='MotherTongue')
    name = models.CharField(max_length=100, db_column='Name')
    nationality = models.CharField(max_length=50, db_column='Nationality')
    personal_email_id = models.CharField(max_length=100, db_column='PersonalEmailID')
    personal_mobile_no = models.CharField(max_length=15, db_column='PersonalMobileNo')
    registration_no = models.CharField(max_length=50, db_column='RegisterationNumber')
    religion = models.CharField(max_length=50, db_column='Religion')
    roll_no = models.CharField(max_length=20, db_column='RollNumber')
    EMIS_ID = models.CharField(max_length=100, blank=True, null=True, db_column='EMISID')
    gender = models.CharField(max_length=10, db_column='Gender')

    Permanent_Address_Door_No = models.CharField(max_length=20, db_column='PermanentAddressNo')
    Permanent_Address_Street_Name = models.CharField(max_length=100, db_column='PermanentAddressStreet')
    Permanent_Address_Location = models.CharField(max_length=100, db_column='PermanentAddressLocation')
    Permanent_Address_Pincode = models.CharField(max_length=10, db_column='PermanentAddressPincode')
    Permanent_Address_Taluk = models.CharField(max_length=50, db_column='PermanentAddressTaluk')
    Permanent_Address_District = models.CharField(max_length=50, db_column='PermanentAddressDistrict')
    Permanent_Address_State = models.CharField(max_length=50, db_column='PermanentAddressState')

    Communication_Address_Door_No = models.CharField(max_length=20, db_column='CommunicationAddressNo')
    Communication_Address_Street_Name = models.CharField(max_length=100, db_column='CommunicationAddressStreet')
    Communication_Address_Location = models.CharField(max_length=100, db_column='CommunicationAddressLocation')
    Communication_Address_Pincode = models.CharField(max_length=10, db_column='CommunicationAddressPincode')
    Communication_Address_Taluk = models.CharField(max_length=50, db_column='CommunicationAddressTaluk')
    Communication_Address_District = models.CharField(max_length=50, db_column='CommunicationAddressDistrict')
    Communication_Address_State = models.CharField(max_length=50, db_column='CommunicationAddressState')

    def __str__(self):
        return f"{self.name} ({self.registration_no})"

    class Meta:
        db_table = 'personaldetails'
        managed = False
     
 

class SSLCDetails(models.Model):
    Tenth_Std_School_Name = models.CharField(max_length=255, db_column='SchoolName')
    Tenth_Std_School_Type = models.CharField(max_length=255, db_column='SchoolType')
    Tenth_Std_Place_of_School = models.CharField(max_length=255, db_column='PlaceofSchool')
    Tenth_Std_School_Category = models.CharField(max_length=255, db_column='SchoolCategory')
    Tenth_Std_Medium_of_Study = models.CharField(max_length=255, db_column='SchoolMedium')
    Tenth_Std_Year_of_Passing = models.CharField(max_length=255, db_column='PassingYear')
    Tenth_Std_Roll_No = models.CharField(max_length=255, db_column='RollNumber')
    Tenth_Std_Register_No = models.CharField(max_length=255, db_column='RegisterNumber')
    Tenth_Std_Marksheet_No = models.CharField(max_length=255, db_column='MarkSheetNumber')
    Tenth_Std_Studied_In = models.CharField(max_length=255, db_column='StudiedIn', blank=True, null=True)

    Tenth_Std_Language_Name = models.CharField(max_length=255, db_column='Language', blank=True, null=True)
    Tenth_Std_Language_Mark = models.CharField(max_length=255, db_column='LanguageMarks', blank=True, null=True)
    Tenth_Std_Language_Obtained_Mark = models.CharField(max_length=255, db_column='LanguageObtainedMarks', blank=True, null=True)

    Tenth_Std_English_Name = models.CharField(max_length=255, db_column='English')
    Tenth_Std_English_Mark = models.CharField(max_length=255, db_column='EnglishMarks')
    Tenth_Std_English_Obtained_Mark = models.CharField(max_length=255, db_column='EnglishObtainedMarks')

    Tenth_Std_Maths_Name = models.CharField(max_length=255, db_column='Mathematics')
    Tenth_Std_Maths_Mark = models.CharField(max_length=255, db_column='MathematicsMarks')
    Tenth_Std_Maths_Obtained_Mark = models.CharField(max_length=255, db_column='MathematicsObtainedMarks')

    Tenth_Std_Science_Name = models.CharField(max_length=255, db_column='Science')
    Tenth_Std_Science_Mark = models.CharField(max_length=255, db_column='ScienceMarks')
    Tenth_Std_Science_Obtained_Mark = models.CharField(max_length=255, db_column='ScienceObtainedMarks')

    Tenth_Std_SocialScience_Name = models.CharField(max_length=255, db_column='SocialScience')
    Tenth_Std_SocialScience_Mark = models.CharField(max_length=255, db_column='SocialScienceMarks')
    Tenth_Std_SocialScience_Obtained_Mark = models.CharField(max_length=255, db_column='SocialScienceObtainedMarks')

    Tenth_Std_Other_Subject_Name = models.CharField(max_length=255, db_column='OtherSubject', blank=True, null=True)
    Tenth_Std_Other_Subject_Mark = models.CharField(max_length=255, db_column='OtherSubjectMarks', blank=True, null=True)
    Tenth_Std_Other_Subject_Obtained_Mark = models.CharField(max_length=255, db_column='OtherSubjectObtainedMarks', blank=True, null=True)

    Tenth_Std_Total_Marks = models.CharField(max_length=255, db_column='TotalMarks')
    Tenth_Std_Obtained_Marks = models.CharField(max_length=255, db_column='ObtainedMarks')

    SchoolDetailsId = models.IntegerField(db_column='SchoolDetailsId')

    def __str__(self):
        return self.Tenth_Std_Register_No

    class Meta:
        db_table = 'sslcdetails'
        managed = False

class HSCDetails(models.Model):
    id = models.AutoField(primary_key=True, db_column='ID')
    school_name_11th = models.CharField(max_length=255, blank=True, null=True, db_column='SchoolName11th')
    school_type_11th = models.CharField(max_length=255, blank=True, null=True, db_column='SchoolType11th')
    school_category_11th = models.CharField(max_length=255, blank=True, null=True, db_column='SchoolCategory11th')
    school_medium_11th = models.CharField(max_length=255, blank=True, null=True, db_column='SchoolMedium11th')
    passing_year_11th = models.CharField(max_length=255, blank=True, null=True, db_column='PassingYear11th')
    place_of_school_11th = models.CharField(max_length=255, blank=True, null=True, db_column='PlaceofSchool11th')
    school_name_12th = models.CharField(max_length=255, blank=True, null=True, db_column='SchoolName12th')
    school_type_12th = models.CharField(max_length=255, blank=True, null=True, db_column='SchoolType12th')
    school_category_12th = models.CharField(max_length=255, blank=True, null=True, db_column='SchoolCategory12th')
    school_medium_12th = models.CharField(max_length=255, blank=True, null=True, db_column='SchoolMedium12th')
    passing_year_12th = models.CharField(max_length=255, blank=True, null=True, db_column='PassingYear12th')
    place_of_school_12th = models.CharField(max_length=255, blank=True, null=True, db_column='PlaceofSchool12th')
    roll_number_12th = models.CharField(max_length=255, blank=True, null=True, db_column='RollNumber12th')
    register_number_12th = models.CharField(max_length=255, blank=True, null=True, db_column='RegisterNumber12th')
    sheet_number_12th = models.CharField(max_length=255, blank=True, null=True, db_column='MarkSheetNumber12th')
    education_qualification_12th = models.CharField(max_length=255, blank=True, null=True, db_column='EducationQualification12th')
    twelfth_std_aca_language_mark = models.CharField(max_length=255, blank=True, null=True, db_column='TwelfthStdAcaLanguageMark')
    twelfth_std_aca_english_mark = models.CharField(max_length=255, blank=True, null=True, db_column='TwelfthStdAcaEnglishMark')
    twelfth_std_aca_mathematics_mark = models.CharField(max_length=255, blank=True, null=True, db_column='TwelfthStdAcaMathematicsMark')
    twelfth_std_aca_physics_mark = models.CharField(max_length=255, blank=True, null=True, db_column='TwelfthStdAcaPhysicsMark')
    twelfth_std_aca_chemistry_mark = models.CharField(max_length=255, blank=True, null=True, db_column='TwelfthStdAcaChemistryMark')
    twelfth_std_aca_elective_mark = models.CharField(max_length=255, blank=True, null=True, db_column='TwelfthStdAcaElectiveMark')
    twelfth_std_aca_total_marks = models.CharField(max_length=255, blank=True, null=True, db_column='TwelfthStdAcaTotalMarks')
    twelfth_std_aca_cut_off_mark = models.CharField(max_length=255, blank=True, null=True, db_column='TwelfthStdAcaCutOffMark')
    twelfth_std_aca_pcm_average = models.CharField(max_length=255, blank=True, null=True, db_column='TwelfthStdAcaPCMAverage')
    twelfth_std_voc_language_mark = models.CharField(max_length=255, blank=True, null=True, db_column='TwelfthStdVocLanguageMark')
    twelfth_std_voc_english_mark = models.CharField(max_length=255, blank=True, null=True, db_column='TwelfthStdVocEnglishMark')
    twelfth_std_voc_mathematics_or_physics_name = models.CharField(max_length=255, blank=True, null=True, db_column='TwelfthStdVocMathematicsOrPhysicsName')
    twelfth_std_voc_mathematics_or_physics_mark = models.CharField(max_length=255, blank=True, null=True, db_column='TwelfthStdVocMathematicsOrPhysicsMark')
    twelfth_std_voc_vocational_theory_name = models.CharField(max_length=255, blank=True, null=True, db_column='TwelfthStdVocVocationalTheoryName')
    twelfth_std_voc_vocational_theory_mark = models.CharField(max_length=255, blank=True, null=True, db_column='TwelfthStdVocVocationalTheoryMark')
    twelfth_std_voc_practical_mark = models.CharField(max_length=255, blank=True, null=True, db_column='TwelfthStdVocPracticalMark')
    twelfth_std_voc_total_marks = models.CharField(max_length=255, blank=True, null=True, db_column='TwelfthStdVocTotalMarks')
    twelfth_std_voc_cut_off_mark = models.CharField(max_length=255, blank=True, null=True, db_column='TwelfthStdVocCutOffMark')
    twelfth_std_voc_pcm_average = models.CharField(max_length=255, blank=True, null=True, db_column='TwelfthStdVocPCMAverage')
    school_details_id = models.IntegerField(default=0, db_column='SchoolDetailsId')
    studied_in_12th = models.CharField(max_length=255, blank=True, null=True, db_column='Studiedin12th')

    def __str__(self):
        return f"{self.studied_in_12th} ({self.roll_number_12th})"

    class Meta:
        db_table = 'hscdetails'
        managed = False



class SchoolDetails(models.Model):
    # HSCDetailsId = models.IntegerField(null=True, blank=True)
    HSCDetailsId=models.ForeignKey(HSCDetails, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        db_table = 'schooldetails'
        managed = False



from django.db import models

class DiplomoDetails(models.Model):
    id = models.AutoField(primary_key=True, db_column='ID')
    name_of_the_polytechnic_college = models.CharField(max_length=255, blank=True, null=True, db_column='NameOfThePolytechnicCollege')
    polytechnic_college_place = models.CharField(max_length=255, blank=True, null=True, db_column='PolytechnicCollegePlace')
    medium_of_study = models.CharField(max_length=255, blank=True, null=True, db_column='MediumOfStudy')
    year_of_passing = models.CharField(max_length=255, blank=True, null=True, db_column='YearOfPassing')
    diploma_register_no = models.CharField(max_length=255, blank=True, null=True, db_column='DiplomaRegisterNo')
    diploma_certificate_no = models.CharField(max_length=255, blank=True, null=True, db_column='DiplomaCertificateNo')
    diploma_studied_in = models.CharField(max_length=255, blank=True, null=True, db_column='DiplomaStudiedIn')
    sem1_total_mark = models.CharField(max_length=255, blank=True, null=True, db_column='Sem1TotalMark')
    sem1_obtain_mark = models.CharField(max_length=255, blank=True, null=True, db_column='Sem1ObtainMark')
    sem2_total_mark = models.CharField(max_length=255, blank=True, null=True, db_column='Sem2TotalMark')
    sem2_obtain_mark = models.CharField(max_length=255, blank=True, null=True, db_column='Sem2ObtainMark')
    sem3_total_mark = models.CharField(max_length=255, blank=True, null=True, db_column='Sem3TotalMark')
    sem3_obtain_mark = models.CharField(max_length=255, blank=True, null=True, db_column='Sem3ObtainMark')
    sem4_total_mark = models.CharField(max_length=255, blank=True, null=True, db_column='Sem4TotalMark')
    sem4_obtain_mark = models.CharField(max_length=255, blank=True, null=True, db_column='Sem4ObtainMark')
    sem5_total_mark = models.CharField(max_length=255, blank=True, null=True, db_column='Sem5TotalMark')
    sem5_obtain_mark = models.CharField(max_length=255, blank=True, null=True, db_column='Sem5ObtainMark')
    sem6_total_mark = models.CharField(max_length=255, blank=True, null=True, db_column='Sem6TotalMark')
    sem6_obtain_mark = models.CharField(max_length=255, blank=True, null=True, db_column='Sem6ObtainMark')
    total_percentages = models.CharField(max_length=255, blank=True, null=True, db_column='TotalPercentages')
    diploma_total_mark = models.CharField(max_length=255, blank=True, null=True, db_column='DiplomaTotalMark')
    diploma_obtain_mark = models.CharField(max_length=255, blank=True, null=True, db_column='DiplomaObtainMark')
    school_details_id = models.IntegerField(db_column='SchoolDetailsId')

    class Meta:
        db_table = 'diplomodetails'
        managed = False



class TransportDetails(models.Model):
    id = models.AutoField(primary_key=True, db_column='id')
    bus_route = models.CharField(max_length=255, blank=True, null=True, db_column='BusRoute')
    bus_stop = models.CharField(max_length=255, blank=True, null=True, db_column='BusStop')
    bus_no = models.CharField(max_length=255, blank=True, null=True, db_column='BusNo')
    bus_time = models.CharField(max_length=255, blank=True, null=True, db_column='BusTime')
    admission_records_id = models.ForeignKey('PersonalDetails', on_delete=models.CASCADE, related_name='transport_details', db_column='AdmissionRecordsId', to_field='id')

    def __str__(self):
        return f"{self.bus_no} - {self.bus_route}"

    class Meta:
        db_table = 'transportdetails'
        managed = False
 

from django.db import models

class AcademicDetails(models.Model):
    CounsellingApplicationNo = models.CharField(max_length=255, null=True, blank=True)
    GQAdmissionNumber = models.CharField(max_length=255, null=True, blank=True)
    CounsellingGeneralRank = models.CharField(max_length=255, null=True, blank=True)
    ScholarShip = models.CharField(max_length=255, null=True, blank=True)
    FirstGraduateCertificateNo = models.CharField(max_length=255, null=True, blank=True)
    GovPer = models.CharField(max_length=255, null=True, blank=True)

    Occupation = models.CharField(max_length=255)
    JobDetails = models.CharField(max_length=255)
    AnnualIncome = models.CharField(max_length=255)

    NameOfTheBank = models.CharField(max_length=255)
    BranchNameOfTheBank = models.CharField(max_length=255)
    BranchCodeNo = models.CharField(max_length=255, null=True, blank=True)
    IFSC = models.CharField(max_length=255)
    MICR = models.CharField(max_length=255)
    AccountHolderName = models.CharField(max_length=255)
    AccountNo = models.CharField(max_length=255)

    How = models.CharField(max_length=255)
    DateAdmission = models.DateTimeField()
    AdmissionCategory = models.CharField(max_length=255, null=True, blank=True)
    AcademicYear = models.CharField(max_length=255, null=True, blank=True)

    AdmissionRecordsId = models.IntegerField(default=0)

    class Meta:
        db_table = "academicdetails"

    def __str__(self):
        return f"AcademicDetails {self.id} - {self.GQAdmissionNumber or 'N/A'}"


class AdmissionRecords(models.Model):
    admissionNo = models.CharField(
        max_length=20,
        primary_key=True,
        db_column='AdmissionNo'
    )
    admissionFor = models.CharField(max_length=100, db_column='AdmissionFor')
    Quota = models.CharField(max_length=100, db_column='Quota')
    Department = models.CharField(max_length=100, db_column='Department')
    Mode = models.CharField(max_length=100, db_column='Mode')

    # 👇 renamed related_name to avoid clash
    PersonalDetailsId = models.ForeignKey(
        PersonalDetails,
        on_delete=models.CASCADE,
        related_name='admission_records_set',  # changed from admission_records
        db_column='PersonalDetailsId'
    )   
    AcademicDetailsId = models.ForeignKey(
        AcademicDetails,
        on_delete=models.CASCADE,
        related_name='academic_records_set',  # safe unique name
        db_column='AcademicDetailsId'
    )
    SchoolDetailsId = models.IntegerField(db_column='SchoolDetailsId')

    TransportDetailsId = models.ForeignKey(
        TransportDetails,
        on_delete=models.CASCADE,
        related_name='transport_admission_records',  # safe unique name
        db_column='TransportDetailsId'
    )

    academic_Category = models.CharField(
        max_length=50, blank=True, null=True, db_column='AdmittedCategory'
    )
    certificate_status = models.CharField(
        max_length=50, blank=True, null=True, db_column='CertificateStatus'
    )
    certification_valiation_date = models.DateField(
        blank=True, null=True, db_column='CertificateVerificationDate'
    )
    group_code = models.CharField(
        max_length=50, blank=True, null=True, db_column='GroupCode'
    )
    round = models.CharField(
        max_length=50, blank=True, null=True, db_column='Round'
    )
    degree = models.CharField(max_length=255, blank=True, null=True, db_column='Degree')


    def __str__(self):
        return self.admissionNo

    class Meta:
        db_table = 'admissionrecords'
        managed = False
    
 

DEGREE_MAPPING = {
    "B.E": "Bachelor of Engineering",
    "B.TECH": "Bachelor of Technology",
    
    # add more codes as needed
}

class DegreeDepartment(models.Model):
    degree_code = models.CharField(max_length=255, null=True, blank=True)
    degree = models.CharField(max_length=255, null=True, blank=True)
    department_id = models.CharField(max_length=255, null=True, blank=True)
    degree_department = models.CharField(max_length=255, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Automatically set degree from degree_code
        if self.degree_code:
            self.degree = DEGREE_MAPPING.get(self.degree_code, self.degree_code)
        
        # Automatically set degree_department using department code
        if self.department_id and self.degree_code:
            try:
                dept = Department.objects.using("rit_approval_system").get(id=self.department_id)
                dept_code = dept.Department_code
            except Department.DoesNotExist:
                dept_code = "NA"
            self.degree_department = f"{self.degree_code} {dept_code}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.degree_department}"
  
class Scholarships(models.Model):
    Name  = models.CharField( max_length=50 , null = True , blank = True)
    Id  = models.IntegerField()
    class Meta:
        db_table ='scholarships'
        managed = False


from django.contrib.auth.models import AbstractUser, BaseUserManager, Group, Permission
from django.core.validators import FileExtensionValidator
from django.db import models
import os
import time



def sanitize_upload_path(instance, filename, folder_name):
    """
    Utility function to create safe upload paths for certificates
    Prevents path traversal attacks and ensures unique filenames
    """
    import os
    import time
    from datetime import datetime
    
    # Get faculty info to create directory structure
    faculty_id = instance.faculty_id or 'unknown'
    
    # Get department and academic year from session or use defaults
    # Note: This function is called during model save, so we need to get session data differently
    # We'll use a more robust approach by getting the current academic year
    current_year = datetime.now().year
    academic_year = f"{current_year - 1}-{current_year}"
    
    # Try to get department from the instance if it has a related general_information
    department = 'unknown'
    try:
        from .models import general_information
        gen_info = general_information.objects.filter(faculty_id=faculty_id).first()
        if gen_info and gen_info.department:
            department = gen_info.department
        else:
            # If no general_information record exists, try to get from User model
            from .models import User
            user = User.objects.filter(Employee_id=faculty_id).first()
            if user and user.Department and user.Department.Department:
                department = user.Department.Department
    except Exception as e:
        # print(f"Error getting department for faculty_id {faculty_id}: {e}")
        pass
    
    # Remove any leading slashes to prevent path traversal issues
    department = department.lstrip('/') if department else 'unknown'
    academic_year = academic_year.lstrip('/') if academic_year else 'unknown'
    faculty_id = str(faculty_id).lstrip('/') if faculty_id else 'unknown'
    
    # Create directory structure: department/academic_year/faculty_id/folder_name/
    upload_path = f'{department}/{academic_year}/{faculty_id}/{folder_name}/'
    
    # Ensure filename is unique and safe, but keep it short
    name, ext = os.path.splitext(filename)
    # Truncate name if too long (keep first 20 chars)
    short_name = name[:20] if len(name) > 20 else name
    # Use timestamp for uniqueness
    timestamp = int(time.time())
    safe_filename = f"{short_name}_{timestamp}{ext}"
    
    return upload_path + safe_filename


def PAN_certificate_upload_path(instance, filename):
    """Generate upload path for PAN certificates"""
    return sanitize_upload_path(instance, filename, 'Id_Card')

def Aadhar_certificate_upload_path(instance, filename):
    """Generate upload path for Aadhar certificates"""
    return sanitize_upload_path(instance, filename, 'Id_Card')
    
def Probation_confirmation_document_upload_path(instance, filename):
    """Generate upload path for Probation confirmation documents"""
    return sanitize_upload_path(instance, filename, 'service_records')

class general_information(models.Model):
    
    faculty_id=models.IntegerField(null=True,blank=True)
    name=models.CharField(max_length=225,null=True,blank=True)
    department=models.CharField(max_length=225,null=True,blank=True)
    designation=models.CharField(max_length=225,null=True,blank=True)
    dob=models.DateField(null=True,blank=True)
    address=models.CharField(max_length=225,null=True,blank=True)
    personal_email=models.CharField(max_length=225,null=True,blank=True)
    college_email=models.CharField(max_length=225,null=True,blank=True)
    phone=models.BigIntegerField(null=True,blank=True)
    blood_group=models.CharField(max_length=225,null=True,blank=True)
    community=models.CharField(max_length=225,null=True,blank=True)
    caste=models.CharField(max_length=225,null=True,blank=True)
    religion=models.CharField(max_length=225,null=True,blank=True)
    doj=models.DateField(null=True,blank=True)
    apaar_id = models.CharField(max_length=100,null=True,blank=True)
    anu_id = models.CharField(max_length=100,null=True,blank=True)
    aicte_id = models.CharField(max_length=100,null=True,blank=True)
    annauniversity_affiliation_id = models.CharField(max_length=100,null=True,blank=True)
    PAN_number = models.CharField(max_length=100,null=True,blank=True)
    Aadhar_number = models.CharField(max_length=100,null=True,blank=True)
    PAN_certificate = models.FileField(
        upload_to=PAN_certificate_upload_path, 
        null=True, 
        blank=True, 
        verbose_name="Certificate (PDF only, max 1000KB)",
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        help_text="Upload PDF certificate (max 1000KB)"
    )
    Aadhar_certificate = models.FileField(
        upload_to=Aadhar_certificate_upload_path, 
        null=True, 
        blank=True, 
        verbose_name="Certificate (PDF only, max 1000KB)",
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        help_text="Upload PDF certificate (max 1000KB)"
    )

    APPOINTMENT_TYPE_CHOICES = [
        ("Regular", "Regular"),
        ("Contract", "Contract"),
        ("Adhoc", "Adhoc"),
    ]
    appointment_type = models.CharField(
        max_length=20,
        choices=APPOINTMENT_TYPE_CHOICES,
        null=True,
        blank=True,
        verbose_name="Type of Appointment"
    )

    # Pay details
    basic_pay = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Basic Pay"
    )
    agp = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="AGP"
    )
    allowances = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Allowances"
    )
    pay_scale_notes = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Scale of Pay (As per AICTE / 7th CPC)"
    )

    RECRUITMENT_MODE_CHOICES = [
        ("Selection Committee", "Through Selection Committee"),
        ("Direct", "Direct"),
        ("Deputation", "Deputation"),
    ]
    recruitment_mode = models.CharField(
        max_length=30,
        choices=RECRUITMENT_MODE_CHOICES,
        null=True,
        blank=True,
        verbose_name="Mode of Recruitment"
    )

    DUTIES_CHOICES = [
        ("Teaching", "Teaching"),
        ("Research", "Research"),
        ("Administration", "Administration"),
    ]
    nature_of_duties = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        choices=DUTIES_CHOICES,
        verbose_name="Nature of Duties"
    )

    confirmation_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Confirmation of Service Date"
    )

    probation_period_months = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Probation Period (in months)"
    )
    probation_confirmation_reference = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Probation Confirmation Order Reference"
    )
    probation_confirmation_document = models.FileField(
        upload_to="service_records/probation_docs/",
        null=True,
        blank=True,
        verbose_name="Probation/Confirmation Document"
    )



    approval = models.CharField(max_length=10,choices=[('Pending', 'Pending'),('Approved', 'Approved'),],default='Pending',verbose_name="Approval Status" )
    
    
    class Meta:
        managed = False
        db_table = 'app_general_information'


from django.conf import settings
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class CURD_Approval(models.Model):
    """
    Defines workflow:
      requester_role can REQUEST action on a model,
      approver_role must APPROVE it.
    Example:
      Model=Degree, action=EDIT, requester=Admin, approver=Principal
    """
    ACTION_CHOICES = (
        ("ALL", "All Actions"),
        ("CREATE", "Create"),
        ("EDIT", "Edit"),
        ("DELETE", "Delete"),
        ("ACTIVATE", "Activate"),
        ("DEACTIVATE", "Deactivate"),
    )

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True,
        blank=True,)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, null=True,
        blank=True,)

    requester_role_id = models.PositiveIntegerField(null=True,
        blank=True,)
    approver_role_id = models.PositiveIntegerField(null=True,
        blank=True,)

    is_active = models.BooleanField(default=True, null=True,
        blank=True,)



    def __str__(self):
        return f"{self.content_type} {self.action}: {self.requester_role_id} -> {self.approver_role_id}"


from django.conf import settings
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class ApprovalRequest(models.Model):
    ACTION_CHOICES = (
        ("ALL", "All Actions"),
        ("CREATE", "Create"),
        ("EDIT", "Edit"),
        ("DELETE", "Delete"),
        ("ACTIVATE", "Activate"),
        ("DEACTIVATE", "Deactivate"),
    )
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    )

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True,
        blank=True,)
    object_id = models.PositiveIntegerField(null=True, blank=True)   # null for CREATE
    content_object = GenericForeignKey("content_type", "object_id")

    action = models.CharField(max_length=20, choices=ACTION_CHOICES, null=True,
        blank=True,)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING", null=True,
        blank=True,)

    # Who requested and who must approve
    requested_by = models.ForeignKey("faculty_management.general_information", on_delete=models.SET_NULL, null=True, blank=True)
    requester_role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name="requests_made_as", db_constraint=False)

    required_approver_role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True, related_name="requests_to_approve", db_constraint=False)

    payload = models.JSONField(default=dict, blank=True)

    approved_by = models.ForeignKey("faculty_management.general_information", on_delete=models.SET_NULL, null=True, blank=True, related_name="requests_approved_by")
    approved_at = models.DateTimeField(null=True, blank=True)

    rejected_reason = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "control_room_approval_request"
        indexes = [
            models.Index(fields=["status", "action"]),
            models.Index(fields=["content_type", "object_id"]),
        ]


class GlobalUsers(models.Model):
        role_id = models.CharField(max_length=255, null=True, blank=True)
        employee_id = models.CharField(max_length=255, null=True, blank=True)
        global_user = models.BooleanField(default=False, null=True, blank=True)


        def __str__(self):
            return f"{self.employee_id} ({self.role_id}) - {self.global_user}"



class AttendancePercentageMaster(models.Model):
    percentage_from = models.DecimalField(max_digits=5, decimal_places=2)
    percentage_to = models.DecimalField(max_digits=5, decimal_places=2)
    attendance_mark = models.DecimalField(max_digits=4, decimal_places=2)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey("faculty_management.general_information", on_delete=models.SET_NULL, null=True, blank=True, related_name="attendance_percentage_masters_created")
    updated_by = models.ForeignKey("faculty_management.general_information", on_delete=models.SET_NULL, null=True, blank=True, related_name="attendance_percentage_masters_updated")

    class Meta:
        ordering = ["percentage_from"]

    def __str__(self):
        return f"{self.percentage_from}% - {self.percentage_to}% => {self.attendance_mark}"
