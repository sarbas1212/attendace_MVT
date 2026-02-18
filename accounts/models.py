"""
accounts/models.py
Custom User model with role-based access control.
Roles: ADMIN, TEACHER, STUDENT
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Extended user model supporting three distinct roles.
    - ADMIN: Full system access (manage departments, teachers, students, attendance)
    - TEACHER: Department-scoped access (import students, mark attendance)
    - STUDENT: Read-only access to own attendance data
    """

    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        TEACHER = 'TEACHER', 'Teacher'
        STUDENT = 'STUDENT', 'Student'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        db_index=True,
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Optional contact number",
    )

    class Meta:
        ordering = ['username']

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    # ── Convenience properties ──────────────────────────────────
    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT
