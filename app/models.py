"""
app/models.py
Core attendance models: Student and Absence.
"""
from django.db import models
from django.conf import settings


class Student(models.Model):
    """
    Represents a student enrolled in a department.
    Optionally linked to a User account for self-service login.
    """
    student_name = models.CharField(max_length=100)
    roll_number = models.CharField(max_length=50, unique=True, db_index=True)
    department = models.ForeignKey(
        'departments.Department',
        on_delete=models.CASCADE,
        related_name='students',
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_profile',
        help_text="Link to a User account so the student can log in.",
    )
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField()
    parent_phone = models.CharField(max_length=20, blank=True, default='')
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['roll_number']

    def __str__(self):
        return f"{self.student_name} ({self.roll_number})"


class Absence(models.Model):
    """
    Records a single day of absence for a student.
    The unique_together constraint prevents duplicate absence entries
    for the same student on the same date.
    """
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
        help_text="Teacher/Admin who marked this absence.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'date')
        ordering = ['-date', 'student__roll_number']

    def __str__(self):
        return f"{self.student.student_name} — {self.date}"
