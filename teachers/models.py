from django.db import models

from accounts.models import User
from departments.models import Department

# Create your models here.

class Teachers(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'TEACHER'})
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    subject=models.CharField(max_length=100, default="guest")
    is_class_teacher = models.BooleanField(default=False)  # New field

    class Meta:
        unique_together = ('department', 'teacher')

    def __str__(self):
        return f"{self.teacher.username} → {self.department.name} ({'Class Teacher' if self.is_class_teacher else 'Teacher'})"
