from django.contrib import messages
from django.shortcuts import redirect, render

from accounts.decorators import role_required
from departments.models import Department
from departments.forms import DepartmentForm


@role_required(['ADMIN'])
def add_department(request):
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Department added successfully!")
            return redirect('list_departments')
        else:
            messages.error(request, "⚠ Please fix the errors below.")
    else:
        form = DepartmentForm()

    return render(request, 'attendance/add_department.html', {'form': form})

@role_required(['ADMIN'])
def list_departments(request):
    departments = Department.objects.all()
    return render(request, 'attendance/list_departments.html', {'departments': departments})
