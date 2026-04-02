"""
app/services.py
Business logic helpers — keeps views thin and logic reusable/testable.
"""
import pandas as pd
from django.utils import timezone

from django.contrib.auth import get_user_model
from .models import Absence, Student
from departments.models import Department
from django.db import IntegrityError

User = get_user_model()


def get_attendance_stats(students_qs, target_date=None):
    """
    Calculate attendance statistics for a given queryset of students
    on a specific date.

    Returns a dict with keys:
        total, absent, present, percentage
    """
    if target_date is None:
        target_date = timezone.now().date()

    total = students_qs.count()
    absent = Absence.objects.filter(
        date=target_date,
        student__in=students_qs,
    ).count()
    present = total - absent
    percentage = round((present / total) * 100, 1) if total else 0

    return {
        'total': total,
        'absent': absent,
        'present': present,
        'percentage': percentage,
    }


def sync_student_user(student, organization, password_raw=None):
    """
    Ensure a student has a linked User account.
    If password_raw is provided, it sets the password.
    Otherwise, if creating and DOB is present, it sets password to firstname@Year.
    """
    # Use email as username if available, fallback to roll number
    desired_username = student.email if student.email else student.roll_number
    email = student.email or f"{student.roll_number}@example.com"
    
    first_name = student.student_name.split()[0] if student.student_name else ""
    last_name = " ".join(student.student_name.split()[1:]) if len(student.student_name.split()) > 1 else ""

    user = student.user
    
    if not user:
        # Check if a user with this username already exists in SAME organization
        user = User.objects.filter(username=desired_username, organization=organization).first()
        if user and not hasattr(user, 'student_profile'):
            # Only link if user exists in same org AND not already linked to another student
            student.user = user
            student.save(update_fields=['user'])
        else:
            user = None  # Force creation of new user

    if user:
        # Sync existing user details
        user.username = desired_username
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.role = User.Role.STUDENT
        user.organization = organization  # Add this
        user.save()
        created = False
    else:
        # Create new user
        user = User.objects.create_user(
            username=desired_username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=User.Role.STUDENT,
            organization=organization  # Add this
        )
        student.user = user
        student.save(update_fields=['user'])
        created = True

    # Handle Password
    if password_raw:
        user.set_password(password_raw)
        user.save()
    elif created and student.date_of_birth:
        # Default password: firstname@YearofBirth (e.g. john@2005)
        default_pwd = f"{first_name.lower()}@{student.date_of_birth.year}"
        user.set_password(default_pwd)
        user.save()
    
    return user

def import_students_from_file(file, department, organization):
    """
    Parse an Excel/CSV file and create/update students
    in the given department.

    Expected columns: 'Student Name', 'Roll Number'
    Optional columns: 'Email', 'Parent Phone', 'Date of Birth'

    Returns a dict:
        created (int), updated (int), errors (list of str)
    """
    # Read file
    if file.name.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    # Strip whitespace from column headers
    df.columns = df.columns.str.strip()

    # Validate required columns
    required = ['Student Name', 'Roll Number', 'Email', 'Date of Birth']
    missing = [col for col in required if col not in df.columns]
    if missing:
        return {
            'created': 0,
            'updated': 0,
            'errors': [f"Missing required columns: {', '.join(missing)}"],
        }

    created = 0
    updated = 0
    errors = []

    for idx, row in df.iterrows():
        row_num = idx + 2  # Excel row (1-indexed header + data)

        name = str(row.get('Student Name', '')).strip()
        roll = str(row.get('Roll Number', '')).strip()
        email = str(row.get('Email', '')).strip()
        dob_val = row.get('Date of Birth')

        if not name or name == 'nan' or not roll or roll == 'nan' or not email or email == 'nan' or pd.isnull(dob_val) or str(dob_val).strip() == 'nan' or not str(dob_val).strip():
            errors.append(f"Row {row_num}: Missing required data (Name, Roll, Email, or DOB) — skipped.")
            continue

        defaults = {
            'student_name': name,
            'department': department,
            'email': email,
            'organization': organization,  # Added
        }

        # Optional fields
        phone = str(row.get('Parent Phone', '')).strip()
        if phone and phone != 'nan':
            defaults['parent_phone'] = phone
        
        # Handle DOB validation
        try:
            defaults['date_of_birth'] = pd.to_datetime(dob_val).date()
        except:
            errors.append(f"Row {row_num}: Invalid date format for DOB — skipped.")
            continue

        try:
            student, was_created = Student.objects.update_or_create(
                roll_number=roll,
                organization=organization,
                defaults=defaults,
            )

            # Create/Sync User account
            sync_student_user(student, organization)
            
            if was_created:
                created += 1
            else:
                updated += 1
                
        except IntegrityError as e:
            errors.append(f"Row {row_num}: Duplicate data - {str(e)}")
            continue
        except Exception as e:
            errors.append(f"Row {row_num}: Error - {str(e)}")
            continue

        # Create/Sync User account
        sync_student_user(student, organization)

        if was_created:
            created += 1
        else:
            updated += 1

    return {'created': created, 'updated': updated, 'errors': errors}


def mark_attendance_for_date(students_qs, absent_student_ids, target_date, marked_by=None):
    """
    Mark attendance for a set of students on a given date.

    - Students whose IDs are in *absent_student_ids* get an Absence record.
    - Students NOT in that set get any existing Absence record removed.

    Uses get_or_create to prevent duplicates.
    """
    for student in students_qs:
        if student.id in absent_student_ids:
            Absence.objects.get_or_create(
                student=student,
                date=target_date,
                defaults={'marked_by': marked_by},
            )
        else:
            Absence.objects.filter(student=student, date=target_date).delete()
"""
app/services.py
Business logic helpers — keeps views thin and logic reusable/testable.
"""
import pandas as pd
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from .models import Absence, Student
from departments.models import Department

User = get_user_model()


def get_attendance_stats(students_qs, target_date=None):
    """
    Calculate attendance statistics for a given queryset of students
    on a specific date.
    """
    if target_date is None:
        target_date = timezone.now().date()

    total = students_qs.count()
    absent = Absence.objects.filter(
        date=target_date,
        student__in=students_qs,
    ).count()
    present = total - absent
    percentage = round((present / total) * 100, 1) if total else 0

    return {
        'total': total,
        'absent': absent,
        'present': present,
        'percentage': percentage,
    }


def sync_student_user(student, organization, password_raw=None):
    """
    Ensure a student has a linked User account.
    Handles email conflicts gracefully.
    """
    # Determine desired username/email
    desired_username = student.email if student.email else student.roll_number
    # Ensure email is valid format, fallback if needed (rare)
    email = student.email if student.email else f"{student.roll_number}@example.com"
    
    first_name = student.student_name.split()[0] if student.student_name else ""
    last_name = " ".join(student.student_name.split()[1:]) if len(student.student_name.split()) > 1 else ""

    user = student.user
    
    # 1. Handle Existing User Link
    if not user:
        # Check if a user with this username/email already exists in SAME organization
        # We prioritize checking by email, then username
        user = User.objects.filter(email=email, organization=organization).first()
        if not user:
            user = User.objects.filter(username=desired_username, organization=organization).first()
            
        if user and not hasattr(user, 'student_profile'):
            # Only link if user exists in same org AND not already linked to another student
            student.user = user
            student.save(update_fields=['user'])
        else:
            user = None  # Force creation of new user

    # 2. Create or Update User
    if user:
        # Sync existing user details
        # We use .save() inside try-catch to handle if email was changed to a taken one
        try:
            user.username = desired_username
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.role = User.Role.STUDENT
            user.organization = organization
            user.save()
            created = False
        except IntegrityError:
            # Email/Username conflict in User table. Keep old user/email.
            # This prevents crashing if Student email changed to a User email taken by someone else.
            created = False
    else:
        # Create new user
        try:
            user = User.objects.create_user(
                username=desired_username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=User.Role.STUDENT,
                organization=organization
            )
            student.user = user
            student.save(update_fields=['user'])
            created = True
        except IntegrityError:
            # User creation failed (Email conflict).
            # We proceed without linking a user account for this import.
            user = None
            created = False

    # 3. Handle Password
    if user:
        if password_raw:
            user.set_password(password_raw)
            user.save()
        elif created and student.date_of_birth:
            default_pwd = f"{first_name.lower()}@{student.date_of_birth.year}"
            user.set_password(default_pwd)
            user.save()
    
    return user


def import_students_from_file(file, department, organization):
    """
    Parse an Excel/CSV file and create/update students.
    
    Returns a dict:
        created (int), updated (int), errors (list of str)
    """
    # Read file
    if file.name.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    # Strip whitespace from column headers
    df.columns = df.columns.str.strip()

    # Validate required columns
    required = ['Student Name', 'Roll Number', 'Email', 'Date of Birth']
    missing = [col for col in required if col not in df.columns]
    if missing:
        return {
            'created': 0,
            'updated': 0,
            'errors': [f"Missing required columns: {', '.join(missing)}"],
        }

    created = 0
    updated = 0
    errors = []

    for idx, row in df.iterrows():
        row_num = idx + 2  # Excel row (1-indexed header + data)

        name = str(row.get('Student Name', '')).strip()
        roll = str(row.get('Roll Number', '')).strip()
        email = str(row.get('Email', '')).strip()
        dob_val = row.get('Date of Birth')

        # Validation: Check for empty strings and 'nan' values
        if not name or name == 'nan' or not roll or roll == 'nan' or not email or email == 'nan' or pd.isnull(dob_val) or str(dob_val).strip() == 'nan' or not str(dob_val).strip():
            errors.append(f"Row {row_num}: Missing required data (Name, Roll, Email, or DOB) — skipped.")
            continue

        defaults = {
            'student_name': name,
            'department': department,
            'email': email,
            'organization': organization,
        }

        # Optional fields
        phone = str(row.get('Parent Phone', '')).strip()
        if phone and phone != 'nan':
            defaults['parent_phone'] = phone
        
        # Handle DOB validation
        try:
            defaults['date_of_birth'] = pd.to_datetime(dob_val).date()
        except:
            errors.append(f"Row {row_num}: Invalid date format for DOB — skipped.")
            continue

        try:
            # Attempt to Update or Create
            # We rely on DB to enforce constraints. If it fails, we catch it.
            student, was_created = Student.objects.update_or_create(
                roll_number=roll,
                organization=organization,
                defaults=defaults,
            )

            # Sync User Account
            sync_student_user(student, organization)
            
            if was_created:
                created += 1
            else:
                updated += 1
                
        except IntegrityError as e:
            # STRICT ERROR HANDLING: Identify which field caused the error
            err_msg = str(e).lower()
            
            if 'email' in err_msg:
                errors.append(
                    f"Row {row_num}: <strong>Email Conflict</strong>. "
                    f"The email '{email}' is already assigned to another student in this organization. "
                    f"Student <strong>{name}</strong> skipped."
                )
            elif 'roll' in err_msg or 'roll_number' in err_msg:
                errors.append(
                    f"Row {row_num}: <strong>Roll Number Conflict</strong>. "
                    f"The roll number '{roll}' already exists. "
                    f"Student <strong>{name}</strong> skipped."
                )
            else:
                errors.append(f"Row {row_num}: Database integrity error - {str(e)}")
            continue
        
        except Exception as e:
            errors.append(f"Row {row_num}: Unexpected error - {str(e)}")
            continue

    return {'created': created, 'updated': updated, 'errors': errors}


def mark_attendance_for_date(students_qs, absent_student_ids, target_date, marked_by=None, organization=None):
    """
    Mark attendance for a set of students on a given date.

    - Students whose IDs are in *absent_student_ids* get an Absence record.
    - Students NOT in that set get any existing Absence record removed.
    """
    for student in students_qs:
        if student.id in absent_student_ids:
            Absence.objects.get_or_create(
                student=student,
                date=target_date,
                organization=organization,  # <-- ADD THIS
                defaults={'marked_by': marked_by},
            )
        else:
            Absence.objects.filter(student=student, date=target_date).delete()