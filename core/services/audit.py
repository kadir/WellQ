"""
Audit Logging Service
Centralized service for recording audit events.
"""
import logging
from django.conf import settings
from core.models import AuditLog, Workspace

logger = logging.getLogger(__name__)


def log_audit_event(request, action, target, changes=None, workspace=None):
    """
    Centralized audit logging function.
    
    Args:
        request: Django HttpRequest object (for IP, user, etc.)
        action: String describing the action (e.g., "FINDING_IGNORE", "USER_INVITE")
        target: The object being modified (e.g., a Finding instance)
        changes: Dict showing {old_val, new_val} or any change details
        workspace: Optional workspace override (defaults to user's workspace)
    
    Returns:
        AuditLog instance or None if logging fails
    
    Note:
        Audit logging failures should NOT crash the main application.
        Errors are logged but exceptions are caught and suppressed.
    """
    try:
        # Get IP address (check for proxy headers first)
        ip_address = None
        if request:
            ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
            if not ip_address:
                ip_address = request.META.get('REMOTE_ADDR')
        
        # Get user agent
        user_agent = ''
        if request:
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]  # Limit length
        
        # Get actor (user)
        actor = None
        actor_email = 'system'
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            actor = request.user
            actor_email = request.user.email or request.user.username
        
        # Determine workspace
        target_workspace = workspace
        if not target_workspace:
            # Try to get workspace from target object
            if hasattr(target, 'workspace'):
                target_workspace = target.workspace
            elif hasattr(target, 'product') and hasattr(target.product, 'workspace'):
                target_workspace = target.product.workspace
            elif hasattr(target, 'release') and hasattr(target.release, 'product') and hasattr(target.release.product, 'workspace'):
                target_workspace = target.release.product.workspace
            elif hasattr(target, 'scan') and hasattr(target.scan, 'release') and hasattr(target.scan.release, 'product') and hasattr(target.scan.release.product, 'workspace'):
                target_workspace = target.scan.release.product.workspace
            # If still no workspace, try to get from user's profile (if exists)
            elif actor and hasattr(actor, 'profile'):
                # Note: This assumes user has a workspace association
                # You may need to adjust based on your user model
                pass
        
        # If still no workspace, try to get default workspace
        if not target_workspace:
            # Try to get first workspace (fallback - not ideal but prevents errors)
            target_workspace = Workspace.objects.first()
            if not target_workspace:
                logger.warning("No workspace available for audit log - skipping")
                return None
        
        # Get resource type and ID
        resource_type = target.__class__.__name__
        resource_id = str(getattr(target, 'id', ''))
        
        # If target has a more descriptive identifier, use it
        if hasattr(target, 'vulnerability_id') and target.vulnerability_id:
            resource_id = target.vulnerability_id
        elif hasattr(target, 'name'):
            resource_id = f"{resource_id} ({target.name})"
        
        # Create audit log entry
        audit_log = AuditLog.objects.create(
            workspace=target_workspace,
            actor=actor,
            actor_email=actor_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return audit_log
    
    except Exception as e:
        # Failsafe: Audit logging failures should NOT crash the main app
        # Log the error for monitoring (Sentry, etc.)
        logger.error(f"AUDIT LOG FAILURE: {e}", exc_info=True)
        return None


def log_finding_status_change(request, finding, old_status, new_status, triage_note=None):
    """
    Convenience function for logging finding status changes.
    """
    changes = {
        'old': old_status,
        'new': new_status
    }
    if triage_note:
        changes['triage_note'] = triage_note
    
    action = 'FINDING_STATUS_CHANGE'
    if new_status == 'FALSE_POSITIVE':
        action = 'FINDING_IGNORE'
    elif new_status == 'OPEN' and old_status != 'OPEN':
        action = 'FINDING_REOPEN'
    elif new_status == 'WONT_FIX':
        action = 'FINDING_RISK_ACCEPTED'
    
    return log_audit_event(request, action, finding, changes)


def log_user_action(request, action, target_user, changes=None):
    """
    Convenience function for logging user management actions.
    """
    return log_audit_event(request, action, target_user, changes)


def log_scan_upload(request, scan):
    """
    Convenience function for logging scan uploads.
    """
    changes = {
        'scanner': scan.scanner_name,
        'findings_count': scan.findings.count() if hasattr(scan, 'findings') else 0
    }
    return log_audit_event(request, 'SCAN_UPLOAD', scan, changes)

