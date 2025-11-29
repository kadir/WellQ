from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO
import sys

from core.models import PlatformSettings, UserProfile
from core.forms import PlatformSettingsForm


def is_admin(user):
    """Check if user is an administrator"""
    if not user.is_authenticated:
        return False
    # Allow superusers and staff
    if user.is_superuser or user.is_staff:
        return True
    # Check for ADMINISTRATOR role
    try:
        # Ensure profile exists
        if not hasattr(user, 'profile'):
            from core.models import UserProfile
            UserProfile.objects.get_or_create(user=user)
        # Check role
        return user.profile.has_role('ADMINISTRATOR')
    except Exception as e:
        # If anything fails, allow superuser/staff as fallback
        return user.is_superuser or user.is_staff


@login_required
def platform_settings(request):
    """Platform settings page - admin only"""
    if not is_admin(request.user):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    settings_obj = PlatformSettings.get_settings()
    
    if request.method == 'POST':
        form = PlatformSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            try:
                settings_obj = form.save(commit=False)
                settings_obj.updated_by = request.user
                settings_obj.full_clean()  # Run model validation (includes clean() method)
                settings_obj.save()
                messages.success(request, 'Platform settings updated successfully.')
            except Exception as e:
                messages.error(request, f'Error saving settings: {str(e)}')
            return redirect('platform_settings')
    else:
        form = PlatformSettingsForm(instance=settings_obj)
    
    return render(request, 'settings/platform_settings.html', {
        'form': form,
        'settings': settings_obj,
    })


@login_required
@require_POST
def trigger_enrich_db(request):
    """Trigger enrich_db command - admin only"""
    if not is_admin(request.user):
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('dashboard')
    
    try:
        # Capture command output
        out = StringIO()
        err = StringIO()
        
        # Call the enrich_db command
        call_command('enrich_db', stdout=out, stderr=err)
        
        output = out.getvalue()
        error_output = err.getvalue()
        
        if error_output:
            messages.error(request, f'Error during enrichment: {error_output}')
        else:
            messages.success(request, 'Threat intelligence enrichment completed successfully.')
            if output:
                messages.info(request, output[:500])  # Show first 500 chars of output
        
    except CommandError as e:
        messages.error(request, f'Command error: {str(e)}')
    except Exception as e:
        messages.error(request, f'Unexpected error: {str(e)}')
    
    return redirect('platform_settings')

