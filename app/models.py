"""
app/models.py
Core attendance models: Student and Absence.
"""
from django.db import models
from django.conf import settings
from organizations.models import Organization


class Student(models.Model):
    """
    Represents a student enrolled in a department.
    """
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    student_name = models.CharField(max_length=100)
    
    # Roll Number must be unique per Organization
    roll_number = models.CharField(max_length=50, db_index=True)
    
    department = models.ForeignKey(
        'departments.Department',
        on_delete=models.CASCADE,
        related_name='students',
    )

    profile_photo = models.ImageField(
        upload_to='student_photos/',
        blank=True,
        null=True,
        help_text='Student profile photo'
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_profile',
        help_text="Link to a User account so the student can log in.",
    )
    
    # Email must be unique per Organization
    email = models.EmailField()
    
    date_of_birth = models.DateField()
    parent_phone = models.CharField(max_length=20, blank=True, default='')
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['roll_number']
        # STRICT CONSTRAINTS:
        # 1. Roll Number must be unique within an Organization.
        # 2. Email must be unique within an Organization.
        unique_together = [
            ['organization', 'roll_number'],
            ['organization', 'email']
        ]

    def __str__(self):
        return f"{self.student_name} ({self.roll_number})"


class Absence(models.Model):
    """
    Records a single day of absence for a student.
    """
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='absences',
    )
    date = models.DateField(db_index=True)
    reason = models.TextField(blank=True, default='')
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='absences_marked',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'date')
        ordering = ['-date', 'student__roll_number']

    def __str__(self):
        return f"{self.student.student_name} — {self.date}"


class AttendanceSession(models.Model):
    """Officially records that attendance was taken for a department on a specific date."""
    date = models.DateField(db_index=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    department = models.ForeignKey('departments.Department', on_delete=models.CASCADE)
    marked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('date', 'department')