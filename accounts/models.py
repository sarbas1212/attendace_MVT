"""
accounts/models.py
Custom User model with role-based access control.
Roles: ADMIN, TEACHER, STUDENT
"""
from django.contrib.auth.models import AbstractUser,BaseUserManager
from django.db import models

class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError('The Username field must be set')
        if not email:
            raise ValueError('The Email field must be set')
        
        email = self.normalize_email(email)
        
        # Check if email already exists
        if self.model.objects.filter(email=email).exists():
            raise ValueError('A user with this email already exists.')

        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, email, password, **extra_fields)

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        TEACHER = 'TEACHER', 'Teacher'
        STUDENT = 'STUDENT', 'Student'

    # MANDATORY CHANGE: Set unique=True and make it required
    email = models.EmailField(
        unique=True, 
        error_messages={
            'unique': "A user with that email already exists.",
        }
    )
    
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        db_index=True
    )
    phone = models.CharField(max_length=20, blank=True, null=True)
    must_change_password = models.BooleanField(default=False)

    objects = CustomUserManager()

    # This makes the email field required in forms and createsuperuser
    REQUIRED_FIELDS = ['email'] 

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    class Meta:
        ordering = ['username']

    def __str__(self):
        return f"{self.username} ({self.email})"