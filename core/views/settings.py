from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO
import sys

from core.models import PlatformSettings, UserProfile, AuditLog
from core.forms import PlatformSettingsForm
from core.services.audit import log_audit_event
from django.core.paginator import Paginator
from django.db.models import Q


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
                old_epss_url = settings_obj.epss_url
                old_kev_url = settings_obj.kev_url
                settings_obj = form.save(commit=False)
                settings_obj.updated_by = request.user
                settings_obj.full_clean()  # Run model validation (includes clean() method)
                settings_obj.save()
                
                # Log audit event
                changes = {}
                if old_epss_url != settings_obj.epss_url:
                    changes['epss_url'] = {'old': old_epss_url, 'new': settings_obj.epss_url}
                if old_kev_url != settings_obj.kev_url:
                    changes['kev_url'] = {'old': old_kev_url, 'new': settings_obj.kev_url}
                if changes:
                    log_audit_event(request, 'POLICY_UPDATE', settings_obj, changes)
                
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


def has_audit_permission(user):
    """Check if user has permission to view audit logs (ADMIN or AUDITOR only)"""
    if not user.is_authenticated:
        return False
    
    # Check if user has ADMINISTRATOR or AUDITOR role
    if hasattr(user, 'profile'):
        return user.profile.has_role('ADMINISTRATOR') or user.profile.has_role('AUDITOR')
    
    # Fallback: superuser/staff can also access
    return user.is_superuser or user.is_staff


@login_required
def audit_logs(request):
    """Audit logs page - ADMIN and AUDITOR only"""
    if not has_audit_permission(request.user):
        messages.error(request, 'You do not have permission to view audit logs. Only ADMIN and AUDITOR roles are allowed.')
        return redirect('dashboard')
    
    # Get filters from query parameters
    actor_email = request.GET.get('actor_email', '')
    action_filter = request.GET.get('action', '')
    resource_type = request.GET.get('resource_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Build queryset
    queryset = AuditLog.objects.all().select_related('actor', 'workspace').order_by('-timestamp')
    
    # Apply filters
    if actor_email:
        queryset = queryset.filter(actor_email__icontains=actor_email)
    if action_filter:
        queryset = queryset.filter(action__icontains=action_filter)
    if resource_type:
        queryset = queryset.filter(resource_type__icontains=resource_type)
    if date_from:
        from django.utils.dateparse import parse_date
        from datetime import datetime
        from django.utils import timezone
        parsed_date = parse_date(date_from)
        if parsed_date:
            queryset = queryset.filter(timestamp__gte=timezone.make_aware(
                datetime.combine(parsed_date, datetime.min.time())
            ))
    if date_to:
        from django.utils.dateparse import parse_date
        from datetime import datetime
        from django.utils import timezone
        parsed_date = parse_date(date_to)
        if parsed_date:
            queryset = queryset.filter(timestamp__lte=timezone.make_aware(
                datetime.combine(parsed_date, datetime.max.time())
            ))
    
    # Pagination
    per_page = int(request.GET.get('per_page', 20))
    if per_page not in [20, 50, 100]:
        per_page = 20
    
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get unique values for filter dropdowns
    unique_actions = AuditLog.objects.values_list('action', flat=True).distinct().order_by('action')
    unique_resource_types = AuditLog.objects.values_list('resource_type', flat=True).distinct().order_by('resource_type')
    unique_actors = AuditLog.objects.values_list('actor_email', flat=True).distinct().order_by('actor_email')[:50]  # Limit to 50
    
    return render(request, 'settings/audit_logs.html', {
        'logs': page_obj,
        'actor_email': actor_email,
        'action_filter': action_filter,
        'resource_type': resource_type,
        'date_from': date_from,
        'date_to': date_to,
        'per_page': per_page,
        'unique_actions': unique_actions,
        'unique_resource_types': unique_resource_types,
        'unique_actors': unique_actors,
    })

