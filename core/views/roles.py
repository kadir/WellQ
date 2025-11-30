from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator

from core.models import Role, UserProfile
from core.forms import RoleForm


@login_required
def role_list(request):
    """List all roles"""
    roles = Role.objects.all().order_by('name')
    
    # Get user count for each role
    for role in roles:
        role.user_count = role.users.count()
    
    return render(request, 'roles/role_list.html', {
        'roles': roles
    })


@login_required
def role_detail(request, role_id):
    """View role details and permissions"""
    role = get_object_or_404(Role, id=role_id)
    users_with_role = role.users.all().order_by('user__username')
    
    return render(request, 'roles/role_detail.html', {
        'role': role,
        'users_with_role': users_with_role
    })


@login_required
def role_edit(request, role_id):
    """Edit role permissions"""
    role = get_object_or_404(Role, id=role_id)
    
    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            form.save()
            messages.success(request, f'Role "{role.get_name_display()}" updated successfully.')
            return redirect('role_detail', role_id=role.id)
    else:
        form = RoleForm(instance=role)
    
    return render(request, 'roles/role_form.html', {
        'form': form,
        'role': role,
        'title': f'Edit Role: {role.get_name_display()}',
        'action': 'Update'
    })



