"""
teachers/models.py
TeacherAssignment — links a User (role=TEACHER) to a Department.
"""
from django.db import models
from accounts.models import User
from departments.models import Department
from organizations.models import Organization


class TeacherAssignment(models.Model):
    """
    Join table that assigns a teacher (User) to a department.
    A teacher may teach in multiple departments; each row is one assignment.
    One department may have at most one class-teacher (enforced via constraint).
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE
    )

    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'TEACHER'},
        related_name='assignments',
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='teacher_assignments',
    )
    subject = models.CharField(max_length=100, default='General')
    is_class_teacher = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('department', 'teacher')
        constraints = [
            models.UniqueConstraint(
                fields=['department'],
                condition=models.Q(is_class_teacher=True),
                name='unique_class_teacher_per_department',
            ),
        ]
        ordering = ['teacher__username']

    def __str__(self):
        role_label = 'Class Teacher' if self.is_class_teacher else 'Teacher'
        return f"{self.teacher.get_full_name() or self.teacher.username} → {self.department.name} ({role_label})"
