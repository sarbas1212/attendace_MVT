from django.shortcuts import render
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
from app.models import Student, Absence, AttendanceSession # Added AttendanceSession
from departments.models import Department
from accounts.models import User
from accounts.decorators import role_required


@role_required(['ADMIN', 'TEACHER'])
def reports_hub(request):
    # 1. Get Filters
    target_date_str = request.GET.get('date') 
    start_str = request.GET.get('start')      
    end_str = request.GET.get('end')          
    view = request.GET.get('view', 'all')
    dept_id = request.GET.get('dept')

    today = timezone.now().date()
    is_single_day = True

    # 2. Determine Date Context
    if target_date_str:
        date_obj = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        start_date = end_date = date_obj
    elif start_str or end_str:
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date() if start_str else today
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date() if end_str else today
        if start_date != end_date:
            is_single_day = False
    else:
        start_date = end_date = today

    # 3. Base Query
    students = Student.objects.filter(is_active=True).select_related('department')
    if dept_id:
        students = students.filter(department_id=dept_id)

    # 4. Process Data using AttendanceSessions
    report_data = []
    for s in students:
        # ERP LOGIC: Get count of official sessions held for this student's department
        sessions_query = AttendanceSession.objects.filter(
            department=s.department,
            date__range=[start_date, end_date]
        )
        total_sessions = sessions_query.count()

        # Fetch actual Absence objects
        absence_records = Absence.objects.filter(
            student=s, 
            date__range=[start_date, end_date]
        ).order_by('-date').select_related('marked_by')

        absent_count = absence_records.count()
        
        # Calculate Percentage based on SESSIONS held, not calendar days
        if total_sessions > 0:
            present_count = total_sessions - absent_count
            rate = round((present_count / total_sessions * 100), 1)
        else:
            present_count = 0
            rate = 100.0 if absent_count == 0 else 0.0

        # ERP Filtering Logic
        show = False
        if view == 'all': show = True
        elif view == 'perfect' and absent_count == 0 and total_sessions > 0: show = True
        elif view == 'zero' and present_count == 0 and total_sessions > 0: show = True
        elif view == 'risk' and rate < 75: show = True

        if show:
            report_data.append({
                'id': s.id,
                'name': s.student_name,
                'roll': s.roll_number,
                'dept': s.department.code,
                'present': present_count,
                'absent': absent_count,
                'sessions': total_sessions, # Added for UI
                'rate': rate,
                'absence_list': absence_records,
                'is_absent_today': absent_count > 0 if is_single_day else None
            })

    return render(request, 'attendance/reports/hub.html', {
        'report_data': report_data,
        'departments': Department.objects.filter(is_active=True),
        'start': start_date, 
        'end': end_date,
        'is_single_day': is_single_day,
        'current_view': view
    })