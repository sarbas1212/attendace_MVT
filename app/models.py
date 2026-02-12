# app/models.py
from django.db import models
from accounts.models import User

# class Department(models.Model):
#     name = models.CharField(max_length=100, unique=True)
#     code = models.CharField(max_length=10, unique=True)

#     def __str__(self):
#         return self.name

class Student(models.Model):
    student_name = models.CharField(max_length=100)
    roll_number = models.CharField(max_length=50, unique=True)
    course_name = models.CharField(max_length=100)
    department = models.ForeignKey(
        'departments.Department',  # note quotes if Department defined below
        on_delete=models.CASCADE,
        related_name='students'
    )


# class TeacherDepartment(models.Model):
#     teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'TEACHER'})
#     department = models.ForeignKey(Department, on_delete=models.CASCADE)
#     is_class_teacher = models.BooleanField(default=False)  # New field

#     class Meta:
#         unique_together = ('department', 'teacher')

#     def __str__(self):
#         return f"{self.teacher.username} → {self.department.name} ({'Class Teacher' if self.is_class_teacher else 'Teacher'})"


class Absence(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField()
    date_time = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('student', 'date')

    def __str__(self):
        return f"{self.student.student_name} - {self.date}"
