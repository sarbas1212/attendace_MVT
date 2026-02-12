from django import forms

from accounts.models import User
from departments.models import Department
from .models import Teachers



class TeacherCreationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    subject = forms.CharField(max_length=100, required=True)
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,  # Make department optional
        empty_label="No Department Assigned"
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']

    def save(self, commit=True):
        # Create User
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = 'TEACHER'
        if commit:
            user.save()

            # Assign Department only if selected
            department = self.cleaned_data.get('department')
            if department:
                Teachers.objects.create(
                    teacher=user,
                    department=department
                )
        return user


class AssignTeacherForm(forms.ModelForm):
    is_class_teacher = forms.BooleanField(required=False, label="Assign as Class Teacher")

    class Meta:
        model = Teachers
        fields = ['teacher', 'department', 'is_class_teacher']

    def clean(self):
        cleaned_data = super().clean()
        teacher = cleaned_data.get('teacher')
        department = cleaned_data.get('department')
        is_class_teacher = cleaned_data.get('is_class_teacher')

        if is_class_teacher:
            # Check if department already has a class teacher
            if Teachers.objects.filter(department=department, is_class_teacher=True).exists():
                raise forms.ValidationError(f"{department.name} already has a class teacher assigned.")

        return cleaned_data
