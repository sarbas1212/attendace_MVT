from django import forms
from accounts.models import User


class UploadFileForm(forms.Form):
    file = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

# class TeacherCreationForm(forms.ModelForm):
#     password = forms.CharField(widget=forms.PasswordInput, required=True)
#     department = forms.ModelChoiceField(queryset=Department.objects.all(), required=True)

#     class Meta:
#         model = User
#         fields = ['username', 'first_name', 'last_name', 'email', 'password']

#     def save(self, commit=True):
#         # Create User
#         user = super().save(commit=False)
#         user.set_password(self.cleaned_data['password'])
#         user.role = 'TEACHER'
#         if commit:
#             user.save()
#             # Assign Department
#             TeacherDepartment.objects.create(
#                 teacher=user,
#                 department=self.cleaned_data['department']
#             )
#         return user

# class DepartmentForm(forms.ModelForm):
#     class Meta:
#         model = Department
#         fields = ['name', 'code']

# class AssignTeacherForm(forms.ModelForm):
#     is_class_teacher = forms.BooleanField(required=False, label="Assign as Class Teacher")

#     class Meta:
#         model = TeacherDepartment
#         fields = ['teacher', 'department', 'is_class_teacher']

#     def clean(self):
#         cleaned_data = super().clean()
#         teacher = cleaned_data.get('teacher')
#         department = cleaned_data.get('department')
#         is_class_teacher = cleaned_data.get('is_class_teacher')

#         if is_class_teacher:
#             # Check if department already has a class teacher
#             if TeacherDepartment.objects.filter(department=department, is_class_teacher=True).exists():
#                 raise forms.ValidationError(f"{department.name} already has a class teacher assigned.")

#         return cleaned_data
