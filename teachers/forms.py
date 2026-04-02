"""
teachers/forms.py
Forms for creating / editing teachers and assigning them to departments.
"""
import string
from django import forms
from accounts.models import User
from departments.models import Department
from .models import TeacherAssignment
from django.utils.crypto import get_random_string


class TeacherCreationForm(forms.ModelForm):
    """
    Creates a new User with role=TEACHER and optionally assigns
    them to a department via TeacherAssignment.
    """
    subject = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. Mathematics',
        }),
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.none(),  # Empty by default, set in __init__
        required=False,
        empty_label="— No Department Assigned —",
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        # Pop organization from kwargs
        self.organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        
        # Filter departments by organization
        if self.organization:
            self.fields['department'].queryset = Department.objects.filter(
                organization=self.organization,
                is_active=True
            )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        qs = User.objects.filter(email=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This email is already registered to another account.")
        return email

    def save(self, commit=True, organization=None):
        user = super().save(commit=False)
        
        # Use passed organization or the one from __init__
        org = organization or self.organization
        
        temp_password = get_random_string(10, allowed_chars=string.ascii_letters + string.digits)
        user.set_password(temp_password)
        
        user.role = User.Role.TEACHER
        user.organization = org
        user.must_change_password = True

        if commit:
            user.save()
            department = self.cleaned_data.get('department')
            subject = self.cleaned_data.get('subject') or 'General'

            if department:
                TeacherAssignment.objects.update_or_create(
                    teacher=user,
                    department=department,
                    defaults={
                        'subject': subject,
                        'organization': org,
                    },
                )
        return user, temp_password


class AssignTeacherForm(forms.ModelForm):
    """Assigns an existing teacher to a department."""

    is_class_teacher = forms.BooleanField(
        required=False,
        label="Assign as Class Teacher",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    class Meta:
        model = TeacherAssignment
        fields = ['teacher', 'department', 'subject', 'is_class_teacher']
        widgets = {
            'teacher': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Physics',
            }),
        }

    def __init__(self, *args, **kwargs):
        # Pop organization from kwargs
        self.organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)
        
        # Filter teachers and departments by organization
        if self.organization:
            self.fields['teacher'].queryset = User.objects.filter(
                organization=self.organization,
                role=User.Role.TEACHER
            )
            self.fields['department'].queryset = Department.objects.filter(
                organization=self.organization,
                is_active=True
            )

    def clean(self):
        cleaned_data = super().clean()
        department = cleaned_data.get('department')
        is_class_teacher = cleaned_data.get('is_class_teacher')

        if is_class_teacher and department:
            existing = TeacherAssignment.objects.filter(
                department=department,
                is_class_teacher=True,
            )
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise forms.ValidationError(
                    f"{department.name} already has a class teacher assigned."
                )
        return cleaned_data

    def save(self, commit=True, organization=None):
        """Save with organization support."""
        assignment = super().save(commit=False)
        org = organization or self.organization
        if org:
            assignment.organization = org
        if commit:
            assignment.save()
        return assignment