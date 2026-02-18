"""
departments/models.py
Department model — core organisational unit in the attendance system.
"""
from django.db import models


class Department(models.Model):
    """Represents an academic department (e.g. Computer Science, Mechanical)."""

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"