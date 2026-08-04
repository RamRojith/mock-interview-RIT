from django import forms

class EmployeeLoginForm(forms.Form):
    Employee_id = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)
