"""
teachers/forms.py
Forms for creating / editing teachers and assigning them to departments.
"""
from django import forms
from accounts.models import User
from departments.models import Department
from .models import TeacherAssignment


class TeacherCreationForm(forms.ModelForm):
    """
    Creates a new User with role=TEACHER and optionally assigns
    them to a department via TeacherAssignment.
    """
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True,
    )
    subject = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. Mathematics',
        }),
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        required=False,
        empty_label="— No Department Assigned —",
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = 'TEACHER'

        if commit:
            user.save()
            department = self.cleaned_data.get('department')
            subject = self.cleaned_data.get('subject') or 'General'

            if department:
                TeacherAssignment.objects.update_or_create(
                    teacher=user,
                    department=department,
                    defaults={'subject': subject},
                )
        return user


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

    def clean(self):
        cleaned_data = super().clean()
        department = cleaned_data.get('department')
        is_class_teacher = cleaned_data.get('is_class_teacher')

        if is_class_teacher and department:
            existing = TeacherAssignment.objects.filter(
                department=department,
                is_class_teacher=True,
            )
            # Exclude current instance when editing
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)

            if existing.exists():
                raise forms.ValidationError(
                    f"{department.name} already has a class teacher assigned."
                )
        return cleaned_data
