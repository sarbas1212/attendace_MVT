from django import forms
from .models import User


class AdminRegisterForm(forms.ModelForm):
    organization_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['organization_name', 'first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        email = cleaned_data.get("email")
        organization_name = cleaned_data.get("organization_name")

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        
        if email and User.objects.filter(email=email).exists():
            self.add_error("email", "A user with this email already exists.")

        if organization_name and len(organization_name.strip()) < 2:
            self.add_error("organization_name", "Enter a valid organization name.")

        return cleaned_data

    def save(self, commit=False):
        user = super().save(commit=False)
        email = self.cleaned_data["email"].strip().lower()
        user.username = email
        user.email = email
        user.set_password(self.cleaned_data["password"])
        user.role = User.Role.ADMIN
        user.is_staff = True
        user.is_superuser = False
        return user