from django import forms
from django.conf import settings
from .models import User

class AdminRegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    registration_code = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        registration_code = cleaned_data.get("registration_code")

        # 1. Check if passwords match
        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        # 2. Validate Secret Code
        if registration_code != settings.ADMIN_REGISTRATION_CODE:
            raise forms.ValidationError("Invalid Registration Code. Access Denied.")

        # 3. Prevent duplicate admin creation at form level
        if User.objects.filter(role=User.Role.ADMIN).exists():
            raise forms.ValidationError("An administrator already exists. Registration is disabled.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        
        # Force Secure Role Assignments
        user.role = User.Role.ADMIN
        user.is_staff = True
        user.is_superuser = False # Per your requirement
        
        if commit:
            user.save()
        return user