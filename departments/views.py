"""
departments/views.py
CRUD views for Department management (Admin-only).
"""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import role_required
from .models import Department
from .forms import DepartmentForm

@role_required(['ADMIN'])
def add_department(request):
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            department = form.save(commit=False)
            department.organization = request.user.organization # Set organization
            department.save()
            messages.success(request, 'Department added successfully!')
            return redirect('list_departments')
    else:
        form = DepartmentForm()

    return render(request, 'departments/add_department.html', {'form': form})

@role_required(['ADMIN'])
def edit_department(request, pk):
    """Edit an existing department."""
    # SECURITY: Only get departments for THIS organization
    department = get_object_or_404(Department, pk=pk, organization=request.user.organization)

    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, "Department updated successfully!")
            return redirect('list_departments')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = DepartmentForm(instance=department)

    return render(request, 'attendance/department/add_department.html', {
        'form': form,
        'title': 'Edit Department',
        'edit_mode': True,
    })

@role_required(['ADMIN'])
def delete_department(request, pk):
    """Delete a department (POST-only for safety)."""
    # SECURITY: Only get departments for THIS organization
    department = get_object_or_404(Department, pk=pk, organization=request.user.organization)

    if request.method == 'POST':
        department.delete()
        messages.success(request, "Department deleted successfully!")
        return redirect('list_departments')

    return render(request, 'attendance/app/delete_confirm.html', {
        'object': department,
        'object_type': 'Department',
        'cancel_url': 'list_departments',
    })

@role_required(['ADMIN'])
def list_departments(request):
    """List all departments for THIS organization."""
    # SECURITY: Filter by organization
    departments = Department.objects.filter(organization=request.user.organization)
    return render(request, 'attendance/department/list_departments.html', {
        'departments': departments,
    })