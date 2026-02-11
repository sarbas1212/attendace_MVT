from django.db import models

# Create your models here.
# models.py

class Student(models.Model):
    student_name = models.CharField(max_length=100)
    roll_number = models.CharField(max_length=50, unique=True)
    course_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.student_name} ({self.roll_number})"

class Absence(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField()
    date_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'date')

    def __str__(self):
        return f"{self.student.student_name} - {self.date}"
