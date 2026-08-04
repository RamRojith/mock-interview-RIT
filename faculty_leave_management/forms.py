from  faculty_management.models import DesignationMaster, general_information
from user_accounts.models import USER
from faculty_leave_management.models import LeaveType,LeaveAllotment,LeaveApplication,Alteration
from django import forms
import os
from django.db.models import Sum, Count,Max
from django.forms import modelformset_factory,inlineformset_factory
import datetime
from django.contrib import messages
from django.core.exceptions import ValidationError
import datetime

from django import forms

from django.forms import inlineformset_factory



def generate_academic_years():
    """
    Generate academic years as choices (current year + next 5 years).
    """
    current_year = datetime.datetime.now().year
    academic_years = [
        (f"{start_year}-{start_year + 1}", f"{start_year}-{start_year + 1}")
        for start_year in range(current_year, current_year + 6)
    ]
    return academic_years
 

class LeaveTypeForm(forms.ModelForm):
    class Meta:
        model=LeaveType
        fields=['name','code']
        widgets={
            'name': forms.TextInput(attrs={'class':'form-control','placeholder':"Enter the Leave type name..."}),
            'code': forms.TextInput(attrs={'class':'form-control','placeholder':"Enter the Leave type code..."})
        }

class LeaveAllotmentForm(forms.ModelForm):
    academic_year = forms.ChoiceField(
        choices=generate_academic_years(),
        widget=forms.Select(attrs={"class": "form-select"}),
        required=True
    )
    class Meta:
        model = LeaveAllotment
        fields = ['academic_year', 'role','start_date','end_date']
        widgets={
            
            'role': forms.Select(attrs={'class':'form-control'}),
            'start_date':forms.DateInput(attrs={'class':'form-control',"type": "date"}),
            'end_date':forms.DateInput(attrs={'class':'form-control',"type": "date"})
                
            
        }
class LeaveAllotmentUpdateForm(forms.ModelForm):
    academic_year = forms.ChoiceField(
        choices=generate_academic_years(),
        widget=forms.Select(attrs={"class": "form-select"}),
        required=True
    )
    class Meta:
        model = LeaveAllotment
        fields = ['academic_year', 'role','start_date','end_date','leave_type', 'default_allotment']
        widgets={
            
            'role': forms.Select(attrs={'class':'form-control'}),
            'start_date':forms.DateInput(attrs={'class':'form-control',"type": "date"}),
            'end_date':forms.DateInput(attrs={'class':'form-control',"type": "date"}),
            'leave_type': forms.Select(attrs={'class':'form-control'}),
            'default_allotment': forms.NumberInput(attrs={'class':'form-control'})
                
            
        }
class LeaveAllotmentEntryForm(forms.ModelForm):
    class Meta:
        model = LeaveAllotment
        fields = ['leave_type', 'default_allotment']
        widgets={
            'leave_type': forms.Select(attrs={'class':'form-control'}),
            'default_allotment': forms.NumberInput(attrs={'class':'form-control'})
        }
LeaveAllotmentFormSet = inlineformset_factory(
    parent_model=DesignationMaster,
    model=LeaveAllotment,
    form=LeaveAllotmentEntryForm,
    extra=1,  # Only one empty form initially
    can_delete=False
)

class LeaveApplicationForm(forms.ModelForm):
    display_user = forms.CharField(
        label='User',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        })
    )
    class Meta:
        model=LeaveApplication
        fields=['from_date','to_date','leave_type','reason','user','designation']

        widgets={
            'user':forms.TextInput(attrs={'class':'form-control'}),
            'designation':forms.TextInput(attrs={'class':'form-control'}),
            'from_date':forms.DateInput(attrs={'class':'form-control','type':'date'}),
            'to_date':forms.DateInput(attrs={'class':'form-control','type':'date'}),
            'leave_type':forms.Select(attrs={'class':'form-select'}),
            'reason':forms.Textarea(attrs={'class':'form-control'}),

        }
    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

    
        self.fields['role'].widget=forms.HiddenInput()
        # Hide the actual user field
        self.fields['user'].widget = forms.HiddenInput()
class LeaveApplicationAlterationForm(forms.ModelForm):
    class Meta:
        model=Alteration
        fields=['date','class_name','hour','faculty_altered_to']
        widgets={
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'class_name': forms.TextInput(attrs={'class': 'form-control'}),
            'hour': forms.NumberInput(attrs={'class': 'form-control'}),
            'faculty_altered_to': forms.Select(attrs={'class': 'form-control'})
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Exclude users who are students (i.e., where is_student=True)
        self.fields['faculty_altered_to'].queryset = general_information.objects.values_list('name', flat=True)
LeaveApplicationFormSet= inlineformset_factory(
    parent_model=LeaveApplication,
    model=Alteration,
    form=LeaveApplicationAlterationForm,
    extra=1,  # Only one empty form initially
    can_delete=False


)