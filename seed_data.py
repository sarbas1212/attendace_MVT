import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'attendance_pro.settings')
django.setup()

from accounts.models import User
from departments.models import Department
from teachers.models import TeacherAssignment
from app.models import Student

def seed():
    print("Seeding initial data...")
    
    # 1. Create Admin
    admin, created = User.objects.get_or_create(username='admin')
    if created:
        admin.set_password('admin123')
        admin.email = 'admin@example.com'
    admin.role = User.Role.ADMIN
    admin.is_staff = True
    admin.is_superuser = True
    admin.save()
    print(f"Admin 'admin' {'created' if created else 'updated'}.")

    # 2. Create Department
    cs, created = Department.objects.get_or_create(name='Computer Science', code='CS')
    print(f"Department 'Computer Science' {'created' if created else 'already exists'}.")

    # 3. Create Teacher
    teacher, created = User.objects.get_or_create(username='teacher1')
    if created:
        teacher.set_password('teacher123')
        teacher.email = 'teacher1@example.com'
    teacher.role = User.Role.TEACHER
    teacher.save()
    print(f"Teacher 'teacher1' {'created' if created else 'updated'}.")

    # 4. Create Teacher Assignment
    assignment, created = TeacherAssignment.objects.get_or_create(
        teacher=teacher,
        department=cs,
        defaults={'subject': 'Python Programming', 'is_class_teacher': True}
    )
    print(f"Teacher assignment {'created' if created else 'already exists'}.")

    # 5. Create Student
    student_user, created = User.objects.get_or_create(username='student1')
    if created:
        student_user.set_password('student123')
        student_user.email = 'student1@example.com'
    student_user.role = User.Role.STUDENT
    student_user.save()
    
    student, created = Student.objects.get_or_create(
        roll_number='CS101',
        defaults={
            'student_name': 'John Doe',
            'department': cs,
            'user': student_user,
            'email': 'john@example.com'
        }
    )
    print(f"Student 'John Doe' {'created' if created else 'already exists'}.")
    
    print("\nSeeding complete!")
    print("--- Credentials ---")
    print("Admin: admin / admin123")
    print("Teacher: teacher1 / teacher123")
    print("Student: student1 / student123")

if __name__ == '__main__':
    seed()
