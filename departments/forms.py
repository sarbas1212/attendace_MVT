"""
departments/forms.py
Forms for department management.
"""
from django import forms
from .models import Department


class DepartmentForm(forms.ModelForm):
    """Form for creating / editing a department."""

    class Meta:
        model = Department
        fields = ['name', 'code', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Computer Science',
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. CS',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Brief description (optional)',
            }),
        }