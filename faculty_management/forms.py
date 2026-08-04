# from faculty_management.models import Faculty, EducationalDetail, ExperienceDetail,Designation , FacultyPublication
# from django import forms



# class FacultyForm(forms.ModelForm):
#     class Meta:
#         model = Faculty
#         fields = [
#             'name','sure_name', 'gender', 'father_or_husband_name', 'date_of_birth', 
#             'department', 'present_designation', 'date_of_joining', 
#             'aadhar_nrc_number', 'address_for_communication', 'present_address', 
#             'mobile_number', 'whatsapp_number', 'personal_mail_id', 
#             'official_mail_id', 'signature' 
#         ]
#         widgets = {
#             'name': forms.TextInput(attrs={'type': 'text', 'class': 'form-control'}),
#             'sure_name': forms.TextInput(attrs={'type': 'text', 'class': 'form-control'}),
#             'gender': forms.Select(attrs={'class': 'form-control'}),
#             'father_or_husband_name': forms.TextInput(attrs={'type': 'text', 'class': 'form-control'}),
#             'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
#             'department': forms.Select(attrs={ 'class': 'form-control'}),
#             'present_designation': forms.Select(attrs={'class': 'form-control'}),
#             'date_of_joining': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
#             'aadhar_nrc_number': forms.TextInput(attrs={'type': 'text', 'class': 'form-control'}),
#             'address_for_communication': forms.TextInput(attrs={'type': 'text', 'class': 'form-control'}),
#             'present_address': forms.TextInput(attrs={'type': 'text', 'class': 'form-control'}),
#             'mobile_number': forms.TextInput(attrs={'type': 'text', 'class': 'form-control'}),
#             'whatsapp_number': forms.TextInput(attrs={'type': 'text', 'class': 'form-control'}),
#             'personal_mail_id': forms.EmailInput(attrs={'type': 'email', 'class': 'form-control'}),
#             'official_mail_id': forms.EmailInput(attrs={'type': 'email', 'class': 'form-control'}),
#             'signature': forms.FileInput(attrs={'class': 'form-control'}),
#         }
#         def __init__(self, *args, **kwargs):
#             super(FacultyForm, self).__init__(*args, **kwargs)
#             if self.instance.pk and self.instance.attachment:
#                 self.fields['signature'].widget.attrs.update({
#                     'data-current-file': self.instance.signature.url,
#                 })
            
# class EducationalDetailForm(forms.ModelForm):
#     class Meta:
#         model = EducationalDetail
#         fields = ['degree', 'branch_specialization', 'institute_university', 'year_of_passing']
#         widgets = {
#             'degree':forms.TextInput(attrs={'type': 'text','class':'form-control'}),
#             'branch_specialization':forms.TextInput(attrs={'type': 'text','class':'form-control'}),
#             'institute_university':forms.TextInput(attrs={'type': 'text','class':'form-control'}),
#             'year_of_passing':forms.NumberInput(attrs={'type': 'text','class':'form-control'}),
#         }

# class ExperienceDetailForm(forms.ModelForm):
#     class Meta:
#         model = ExperienceDetail
#         fields = ['designation', 'department', 'institution_organization', 'period_from', 'period_to']
#         widgets = {
#             'designation':forms.TextInput(attrs={'type': 'text','class':'form-control'}),
#             'department':forms.TextInput(attrs={'type': 'text','class':'form-control'}),
#             'institution_organization':forms.TextInput(attrs={'type': 'text','class':'form-control'}),
#             'period_from': forms.DateInput(attrs={'type': 'date','class':'form-control'}),
#             'period_to': forms.DateInput(attrs={'type': 'date','class':'form-control'}),
#         }

# # Combined Form for multiple EducationalDetail and ExperienceDetail
# EducationalDetailFormSet = forms.inlineformset_factory(
#     Faculty, EducationalDetail, form=EducationalDetailForm, extra=1, can_delete=True
# )

# ExperienceDetailFormSet = forms.inlineformset_factory(
#     Faculty, ExperienceDetail, form=ExperienceDetailForm, extra=1, can_delete=True
# )

# class DesignationForm(forms.ModelForm):
#     class Meta:
#         model=Designation
#         fields=['name']
#         widgets={
#             'name':forms.TextInput(attrs={'class': 'form-control'})
#         }
# class FacultyPublicationForm(forms.ModelForm):
#     class Meta:
#         model = FacultyPublication
#         fields = ['publication']
#         widgets = {
#             'publication': forms.TextInput(attrs={'class': 'form-control'}),  # Changed to TextInput
#         }

# FacultyPublicationFormSet = forms.inlineformset_factory(
#     Faculty,
#     FacultyPublication,
#     form=FacultyPublicationForm,
#     extra=1,
#     can_delete=True,
#     max_num=5,  # Limit the number of publications to 5
# )



