"""
departments/models.py
Department model — core organisational unit in the attendance system.
"""
from django.db import models

from organizations.models import Organization

class Department(models.Model):
    """Represents an academic department (e.g. Computer Science, Mechanical)."""
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE
    )

    # REMOVED unique=True from here so different orgs can use same names
    name = models.CharField(max_length=100) 
    code = models.CharField(max_length=10)
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        # THIS IS THE KEY: Unique name/code per organization
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'name'],
                name='unique_department_name_per_org'
            ),
            models.UniqueConstraint(
                fields=['organization', 'code'],
                name='unique_department_code_per_org'
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"