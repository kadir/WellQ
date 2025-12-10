from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from core.models import UserProfile
from core.forms import UserCreateForm, UserEditForm
from core.services.audit import log_user_action
from core.models import UserProfile

User = get_user_model()


@login_required
def user_list(request):
    """List all users with pagination and search"""
    users = User.objects.all().order_by('-date_joined')
    
    # Ensure all users have profiles
    for user in users:
        if not hasattr(user, 'profile'):
            UserProfile.objects.create(user=user)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    # Pagination
    per_page = request.GET.get('per_page', '50')
    if per_page not in ['20', '50', '100']:
        per_page = '50'
    paginator = Paginator(users, int(per_page))
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'users/user_list.html', {
        'users': page_obj,
        'per_page': per_page,
        'search_query': search_query,
        'total_count': users.count()
    })


@login_required
def user_create(request):
    """Create a new user"""
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Ensure UserProfile exists
            if not hasattr(user, 'profile'):
                UserProfile.objects.create(user=user)
            # Assign roles
            roles = form.cleaned_data['roles']
            user.profile.roles.set(roles)
            
            # Log audit event
            changes = {
                'roles': [role.name for role in roles],
                'email': user.email,
                'is_staff': user.is_staff,
                'is_active': user.is_active
            }
            log_user_action(request, 'USER_INVITE', user, changes)
            
            messages.success(request, f'User "{user.username}" created successfully.')
            return redirect('user_list')
    else:
        form = UserCreateForm()
    
    return render(request, 'users/user_form.html', {
        'form': form,
        'title': 'Create User',
        'action': 'Create'
    })


@login_required
def user_edit(request, user_id):
    """Edit an existing user"""
    user = get_object_or_404(User, id=user_id)
    
    # Ensure UserProfile exists
    if not hasattr(user, 'profile'):
        UserProfile.objects.create(user=user)
    
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            # Store old values for audit log
            old_roles = set(user.profile.roles.all())
            old_is_staff = user.is_staff
            old_is_active = user.is_active
            
            form.save()
            
            # Get new values
            new_roles = set(user.profile.roles.all())
            
            # Log audit event
            changes = {
                'old': {
                    'roles': [role.name for role in old_roles],
                    'is_staff': old_is_staff,
                    'is_active': old_is_active
                },
                'new': {
                    'roles': [role.name for role in new_roles],
                    'is_staff': user.is_staff,
                    'is_active': user.is_active
                }
            }
            log_user_action(request, 'ROLE_UPDATE', user, changes)
            
            messages.success(request, f'User "{user.username}" updated successfully.')
            return redirect('user_list')
    else:
        form = UserEditForm(instance=user)
    
    return render(request, 'users/user_form.html', {
        'form': form,
        'user': user,
        'title': f'Edit User: {user.username}',
        'action': 'Update'
    })


@login_required
def user_delete(request, user_id):
    """Delete a user"""
    user = get_object_or_404(User, id=user_id)
    
    # Prevent deleting yourself
    if user == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('user_list')
    
    if request.method == 'POST':
        username = user.username
        user_email = user.email
        
        # Log audit event before deletion
        changes = {
            'username': username,
            'email': user_email,
            'roles': [role.name for role in user.profile.roles.all()] if hasattr(user, 'profile') else []
        }
        log_user_action(request, 'USER_DELETE', user, changes)
        
        user.delete()
        messages.success(request, f'User "{username}" deleted successfully.')
        return redirect('user_list')
    
    return render(request, 'users/user_confirm_delete.html', {
        'user': user
    })

