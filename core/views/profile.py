from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.utils import timezone
from django.utils.crypto import get_random_string
import hashlib

from core.models import APIToken
from core.forms import ProfileUpdateForm, PasswordChangeForm, APITokenForm


@login_required
def profile_settings(request):
    """Profile settings page with personal information and API token management"""
    # Handle dismiss token notification
    if request.method == 'POST' and 'dismiss_token' in request.POST:
        if 'new_token' in request.session:
            del request.session['new_token']
            del request.session['new_token_id']
        return redirect('profile_settings')
    
    # Get user's API tokens
    api_tokens = APIToken.objects.filter(user=request.user).order_by('-created_at')
    
    # Handle profile update
    if request.method == 'POST' and 'update_profile' in request.POST:
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile_settings')
    else:
        form = ProfileUpdateForm(instance=request.user)
    
    # Handle password change
    password_form = None
    if request.method == 'POST' and 'change_password' in request.POST:
        password_form = PasswordChangeForm(user=request.user, data=request.POST)
        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(request, password_form.user)
            messages.success(request, 'Password changed successfully.')
            return redirect('profile_settings')
    else:
        password_form = PasswordChangeForm(user=request.user)
    
    return render(request, 'profile/settings.html', {
        'form': form,
        'password_form': password_form,
        'api_tokens': api_tokens,
    })


@login_required
def create_api_token(request):
    """Create a new API token"""
    if request.method == 'POST':
        form = APITokenForm(request.POST)
        if form.is_valid():
            # Generate a secure token
            raw_token = f"wq_{get_random_string(32)}"
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
            token_preview = raw_token[:8]
            
            # Create token record
            api_token = APIToken.objects.create(
                user=request.user,
                name=form.cleaned_data['name'],
                token=token_hash,
                token_preview=token_preview,
                expires_at=form.cleaned_data.get('expires_at'),
            )
            
            # Store raw token in session temporarily to show to user
            request.session['new_token'] = raw_token
            request.session['new_token_id'] = str(api_token.id)
            
            messages.success(request, 'API token created successfully. Make sure to copy it now - you won\'t be able to see it again!')
            return redirect('profile_settings')
    else:
        form = APITokenForm()
    
    return render(request, 'profile/create_token.html', {'form': form})


@login_required
def revoke_api_token(request, token_id):
    """Revoke an API token"""
    try:
        token = APIToken.objects.get(id=token_id, user=request.user)
        token.revoke()
        messages.success(request, f'Token "{token.name}" has been revoked.')
    except APIToken.DoesNotExist:
        messages.error(request, 'Token not found.')
    
    return redirect('profile_settings')

