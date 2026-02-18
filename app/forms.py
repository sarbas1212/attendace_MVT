"""
app/forms.py
Forms for the core attendance module.
"""
from django import forms
from departments.models import Department
from .models import Student


class UploadFileForm(forms.Form):
    """File upload form for Excel/CSV student import."""
    file = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.xlsx,.xls,.csv'}),
        help_text="Accepted formats: .xlsx, .xls, .csv",
    )


class StudentEditForm(forms.ModelForm):
    """Form for editing student details."""
    class Meta:
        model = Student
        fields = ['student_name', 'roll_number', 'department', 'email', 'date_of_birth', 'parent_phone']
        widgets = {
            'student_name': forms.TextInput(attrs={'class': 'form-control'}),
            'roll_number': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'parent_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional'}),
        }


class StudentPasswordChangeForm(forms.Form):
    """Form for teachers/admins to manually set a student's password."""
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter new password'}),
        label="New Password",
        min_length=6,
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'}),
        label="Confirm New Password",
        min_length=6,
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("new_password")
        confirm = cleaned_data.get("confirm_password")
        if password and confirm and password != confirm:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data
