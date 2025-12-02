from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Case, When, Value, Q, Count
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import Product, Release, Finding, Component, StatusApprovalRequest
from core.forms import ReleaseForm
from core.services.sbom import digest_sbom

@login_required
def release_create(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ReleaseForm(request.POST, request.FILES)
        if form.is_valid():
            release = form.save(commit=False)
            release.product = product
            release.save()
            if release.sbom_file:
                digest_sbom(release)
            return redirect('release_detail', release_id=release.id)
    else:
        form = ReleaseForm()
    return render(request, 'findings/release_form.html', {'form': form, 'product': product})

@login_required
def release_detail(request, release_id):
    release = get_object_or_404(Release.objects.select_related('product', 'product__workspace'), id=release_id)
    scans = release.scans.all().order_by('-started_at')

    # Findings Logic - Get all findings for this release with optimized queries
    # Use select_related to avoid N+1 queries when accessing scan.release.product
    all_findings = Finding.objects.filter(
        scan__release=release
    ).select_related(
        'scan',
        'scan__release',
        'scan__release__product',
        'scan__release__product__workspace',
        'triage_by'
    )
    
    # Apply filters from query parameters
    status_filter = request.GET.get('status')
    severity_filter = request.GET.get('severity')
    cve_filter = request.GET.get('cve_id')
    
    findings = all_findings
    
    # Apply status filter
    if status_filter:
        status_upper = status_filter.upper()
        # Map old status names to new ones for backward compatibility
        status_mapping = {
            'ACTIVE': 'OPEN',
            'RISK_ACCEPTED': 'WONT_FIX',
        }
        mapped_status = status_mapping.get(status_upper, status_upper)
        findings = findings.filter(status=mapped_status)
    # If no status filter (All selected), show all findings including FIXED
    
    # Apply severity filter
    if severity_filter:
        findings = findings.filter(severity=severity_filter.upper())
    
    # Apply CVE/Vulnerability ID filter
    if cve_filter:
        findings = findings.filter(vulnerability_id__icontains=cve_filter)
    
    # Apply EPSS score filter (minimum threshold) - from metadata JSON
    epss_filter = request.GET.get('epss', '').strip()
    if epss_filter:
        try:
            min_epss = float(epss_filter)
            findings = findings.filter(metadata__epss_score__gte=min_epss)
        except (ValueError, TypeError):
            # Invalid value, ignore filter
            pass
    
    # Apply KEV filter - from metadata JSON
    kev_filter = request.GET.get('kev')
    if kev_filter:
        if kev_filter.lower() == 'true' or kev_filter == '1':
            findings = findings.filter(metadata__kev_status=True)
        elif kev_filter.lower() == 'false' or kev_filter == '0':
            findings = findings.filter(metadata__kev_status=False)
    
    # Calculate statistics using aggregation (single query instead of 6 separate queries)
    stats_queryset = all_findings
    
    # Single aggregation query for all statistics
    stats_agg = stats_queryset.aggregate(
        total_active=Count('id', filter=~Q(status='FIXED')),
        critical=Count('id', filter=Q(severity='CRITICAL', status='OPEN')),
        high=Count('id', filter=Q(severity='HIGH', status='OPEN')),
        medium=Count('id', filter=Q(severity='MEDIUM', status='OPEN')),
        low=Count('id', filter=Q(severity='LOW', status='OPEN')),
        info=Count('id', filter=Q(severity='INFO', status='OPEN')),
    )
    
    vuln_stats = {
        'total': stats_agg['total_active'],
        'critical': stats_agg['critical'],
        'high': stats_agg['high'],
        'medium': stats_agg['medium'],
        'low': stats_agg['low'],
        'info': stats_agg['info'],
    }
    
    # Optimized ordering: Use database-level ordering instead of Case/When when possible
    # For better performance, we'll use a combination of status and severity ordering
    # This is faster than Case/When on large datasets
    findings = findings.order_by(
        Case(
            When(status='FIXED', then=Value(0)), # Fixed bottom
            When(severity='CRITICAL', then=Value(1)),
            When(severity='HIGH', then=Value(2)),
            When(severity='MEDIUM', then=Value(3)),
            When(severity='LOW', then=Value(4)),
            When(severity='INFO', then=Value(5)),
            default=Value(6)
        ),
        '-created_at'
    )

    # Paginate vulnerabilities - CRITICAL: Always paginate, never load all at once
    vuln_per_page = request.GET.get('vuln_per_page', '50')
    if vuln_per_page not in ['20', '50', '100']:
        vuln_per_page = '50'
    vuln_paginator = Paginator(findings, int(vuln_per_page))
    vuln_page_number = request.GET.get('vuln_page', 1)
    vuln_page_obj = vuln_paginator.get_page(vuln_page_number)

    # SBOM Logic
    all_components = release.components.all().order_by('name')
    total_components = all_components.count()
    
    lic_stats = {'foss': 0, 'coss': 0, 'unidentified': 0}
    foss_keywords = ['MIT', 'Apache', 'GPL', 'BSD', 'MPL', 'CC0', 'LGPL', 'ISC', 'Public Domain']
    for comp in all_components:
        lic = comp.license.upper() if comp.license else ""
        if not lic or lic == "UNKNOWN" or lic == "NONE":
            lic_stats['unidentified'] += 1
        elif any(k in lic for k in ['COMMERCIAL', 'PROPRIETARY']):
            lic_stats['coss'] += 1
        elif any(k.upper() in lic for k in foss_keywords):
            lic_stats['foss'] += 1
        else:
            lic_stats['unidentified'] += 1

    per_page = request.GET.get('per_page', '20')
    if per_page not in ['20', '50', '100']: per_page = '20'
    paginator = Paginator(all_components, int(per_page))
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'findings/release_detail.html', {
        'release': release,
        'scans': scans,
        'findings': vuln_page_obj,
        'vuln_per_page': vuln_per_page,
        'vuln_stats': vuln_stats,
        'lic_stats': lic_stats,
        'page_obj': page_obj,
        'per_page': per_page,
        'total_components': total_components,
        'filters': {
            'status': status_filter,
            'severity': severity_filter,
            'cve_id': cve_filter,
            'epss': epss_filter,
            'kev': kev_filter,
        }
    })

@login_required
def release_sbom_upload(request, release_id):
    """Handle SBOM file upload for a specific release"""
    release = get_object_or_404(Release, id=release_id)
    
    if request.method == 'POST':
        if 'sbom_file' not in request.FILES:
            messages.error(request, 'No file provided.')
            return redirect('release_detail', release_id=release.id)
        
        sbom_file = request.FILES['sbom_file']
        
        # Security: Comprehensive file validation
        from core.utils.security import validate_json_file
        is_valid, error_msg = validate_json_file(sbom_file, max_size_mb=50)
        if not is_valid:
            messages.error(request, f'SBOM file validation failed: {error_msg}')
            return redirect('release_detail', release_id=release.id)
        
        try:
            # Save the SBOM file
            release.sbom_file = sbom_file
            release.save()
            
            # Process the SBOM (this will track changes)
            digest_sbom(release)
            
            messages.success(request, 'SBOM uploaded and processed successfully.')
            return redirect('release_detail', release_id=release.id)
        except Exception as e:
            messages.error(request, f'Error processing SBOM: {str(e)}')
            return redirect('release_detail', release_id=release.id)
    
    return redirect('release_detail', release_id=release.id)

@login_required
def sboms_list(request):
    """List all releases with SBOMs"""
    # Get all releases that have SBOM files
    releases = Release.objects.filter(sbom_file__isnull=False).exclude(sbom_file='').select_related('product', 'product__workspace').order_by('-created_at')
    
    # Get component counts for each release
    releases = releases.annotate(component_count=Count('components'))
    
    # Pagination
    per_page = request.GET.get('per_page', '50')
    if per_page not in ['20', '50', '100']:
        per_page = '50'
    paginator = Paginator(releases, int(per_page))
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'findings/sboms_list.html', {
        'releases': page_obj,
        'per_page': per_page,
        'total_count': releases.count()
    })

@login_required
def release_sbom_export(request, release_id):
    release = get_object_or_404(Release, id=release_id)
    components = release.components.all()
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "metadata": {"component": {"name": release.product.name, "version": release.name, "type": "application"}},
        "components": []
    }
    for comp in components:
        sbom["components"].append({
            "type": comp.type.lower(),
            "name": comp.name,
            "version": comp.version,
            "purl": comp.purl,
            "licenses": [{"license": {"id": comp.license}}] if comp.license else []
        })
    response = JsonResponse(sbom, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="{release.product.name}_{release.name}_sbom.json"'
    return response

@login_required
def vulnerabilities_list(request):
    """List all vulnerabilities from all products"""
    # Get all findings from all products
    findings = Finding.objects.select_related('scan__release__product__workspace').all()
    
    # Apply filters from query parameters
    status_filter = request.GET.get('status')
    if status_filter:
        status_upper = status_filter.upper()
        # Map old status names to new ones for backward compatibility
        status_mapping = {
            'ACTIVE': 'OPEN',
            'RISK_ACCEPTED': 'WONT_FIX',
        }
        mapped_status = status_mapping.get(status_upper, status_upper)
        findings = findings.filter(status=mapped_status)
    # If no status filter (All selected), show all findings including FIXED
    
    severity_filter = request.GET.get('severity')
    if severity_filter:
        findings = findings.filter(severity=severity_filter.upper())
    
    cve_filter = request.GET.get('cve_id')
    if cve_filter:
        findings = findings.filter(vulnerability_id__icontains=cve_filter)
    
    product_filter = request.GET.get('product')
    if product_filter:
        findings = findings.filter(scan__release__product__name__icontains=product_filter)
    
    workspace_filter = request.GET.get('workspace')
    if workspace_filter:
        findings = findings.filter(scan__release__product__workspace__name__icontains=workspace_filter)
    
    # Apply EPSS score filter (minimum threshold) - from metadata JSON
    epss_filter = request.GET.get('epss', '').strip()
    if epss_filter:
        try:
            min_epss = float(epss_filter)
            findings = findings.filter(metadata__epss_score__gte=min_epss)
        except (ValueError, TypeError):
            # Invalid value, ignore filter
            pass
    
    # Apply KEV filter - from metadata JSON
    kev_filter = request.GET.get('kev')
    if kev_filter:
        if kev_filter.lower() == 'true' or kev_filter == '1':
            findings = findings.filter(metadata__kev_status=True)
        elif kev_filter.lower() == 'false' or kev_filter == '0':
            findings = findings.filter(metadata__kev_status=False)
    
    # Order by severity and date
    findings = findings.order_by(
        Case(
            When(status='FIXED', then=Value(0)),  # Fixed bottom
            When(severity='CRITICAL', then=Value(1)),
            When(severity='HIGH', then=Value(2)),
            When(severity='MEDIUM', then=Value(3)),
            When(severity='LOW', then=Value(4)),
            When(severity='INFO', then=Value(5)),
            default=Value(6)
        ),
        '-created_at'
    )
    
    # Calculate statistics using aggregation (single query instead of 6 separate queries)
    from django.db.models import Count, Q
    all_findings = Finding.objects.all()
    # Single aggregation query for all statistics - much faster than multiple count() calls
    stats_agg = all_findings.aggregate(
        total_active=Count('id', filter=Q(status='OPEN')),
        critical=Count('id', filter=Q(severity='CRITICAL', status='OPEN')),
        high=Count('id', filter=Q(severity='HIGH', status='OPEN')),
        medium=Count('id', filter=Q(severity='MEDIUM', status='OPEN')),
        low=Count('id', filter=Q(severity='LOW', status='OPEN')),
        info=Count('id', filter=Q(severity='INFO', status='OPEN')),
    )
    
    vuln_stats = {
        'total': stats_agg['total_active'],
        'critical': stats_agg['critical'],
        'high': stats_agg['high'],
        'medium': stats_agg['medium'],
        'low': stats_agg['low'],
        'info': stats_agg['info'],
    }
    
    # Pagination
    per_page = request.GET.get('per_page', '50')
    if per_page not in ['20', '50', '100']:
        per_page = '50'
    paginator = Paginator(findings, int(per_page))
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'findings/vulnerabilities_list.html', {
        'findings': page_obj,
        'vuln_stats': vuln_stats,
        'per_page': per_page,
        'filters': {
            'status': status_filter,
            'severity': severity_filter,
            'cve_id': cve_filter,
            'product': product_filter,
            'workspace': workspace_filter,
            'epss': epss_filter,
            'kev': kev_filter,
        }
    })


@login_required
def vulnerability_detail(request, finding_id):
    """Get vulnerability detail for modal display"""
    from django.http import JsonResponse
    from core.models import Finding
    
    finding = get_object_or_404(Finding, id=finding_id)
    
    # Extract EPSS and KEV from metadata
    metadata = finding.metadata or {}
    epss_score = metadata.get('epss_score', 0.0)
    epss_percentile = metadata.get('epss_percentile', 0.0)
    kev_status = metadata.get('kev_status', False)
    kev_date = metadata.get('kev_date')
    
    data = {
        'id': str(finding.id),
        'vulnerability_id': finding.vulnerability_id or 'N/A',
        'title': finding.title,
        'description': finding.description,
        'severity': finding.severity,
        'finding_type': finding.finding_type,
        'status': finding.status,
        'package_name': finding.package_name or 'N/A',
        'package_version': finding.package_version or 'N/A',
        'fix_version': finding.fix_version or 'Not available',
        'file_path': finding.file_path or 'N/A',
        'line_number': finding.line_number,
        'epss_score': epss_score,
        'epss_percentile': epss_percentile,
        'kev_status': kev_status,
        'kev_date': kev_date.strftime('%Y-%m-%d') if kev_date and hasattr(kev_date, 'strftime') else (kev_date if kev_date else None),
        'metadata': metadata,
        'triage_note': finding.triage_note,
        'triage_by': finding.triage_by.username if finding.triage_by else None,
        'triage_at': finding.triage_at.strftime('%Y-%m-%d %H:%M') if finding.triage_at else None,
        'first_seen': finding.first_seen.strftime('%Y-%m-%d %H:%M'),
        'last_seen': finding.last_seen.strftime('%Y-%m-%d %H:%M'),
        'product_name': finding.scan.release.product.name,
        'release_name': finding.scan.release.name,
        'workspace_name': finding.scan.release.product.workspace.name,
        'scanner_name': finding.scan.scanner_name,
        'product_id': str(finding.scan.release.product.id),
        'release_id': str(finding.scan.release.id),
    }
    
    return JsonResponse(data)


def can_approve_status(user):
    """Check if user can approve status change requests (Security Expert or Administrator)"""
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    try:
        if not hasattr(user, 'profile'):
            from core.models import UserProfile
            UserProfile.objects.get_or_create(user=user)
        return user.profile.has_role('SECURITY_EXPERT') or user.profile.has_role('ADMINISTRATOR')
    except Exception:
        return user.is_superuser or user.is_staff


@login_required
def update_vulnerability_status(request, finding_id):
    """Update vulnerability status - now creates approval request for non-ACTIVE statuses"""
    from django.http import JsonResponse
    from django.utils import timezone
    from core.models import Finding
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    finding = get_object_or_404(Finding, id=finding_id)
    
    new_status = request.POST.get('status')
    triage_note = request.POST.get('triage_note', '')
    
    if new_status not in dict(Finding.STATUS_CHOICES):
        return JsonResponse({'error': 'Invalid status'}, status=400)
    
    # If status is ACTIVE, update directly (no approval needed)
    if new_status == 'ACTIVE':
        finding.status = new_status
        finding.triage_note = triage_note
        finding.triage_by = request.user
        finding.triage_at = timezone.now()
        finding.save()
        
        return JsonResponse({
            'success': True,
            'status': finding.status,
            'triage_note': finding.triage_note,
            'triage_by': finding.triage_by.username,
            'triage_at': finding.triage_at.strftime('%Y-%m-%d %H:%M'),
        })
    
    # For other statuses (FIXED, FALSE_POSITIVE, RISK_ACCEPTED, DUPLICATE), create approval request
    # Check if user has approval permission - if yes, update directly
    if can_approve_status(request.user):
        finding.status = new_status
        finding.triage_note = triage_note
        finding.triage_by = request.user
        finding.triage_at = timezone.now()
        finding.save()
        
        return JsonResponse({
            'success': True,
            'status': finding.status,
            'triage_note': finding.triage_note,
            'triage_by': finding.triage_by.username,
            'triage_at': finding.triage_at.strftime('%Y-%m-%d %H:%M'),
        })
    
    # Create approval request for users without approval permission
    approval_request = StatusApprovalRequest.objects.create(
        finding=finding,
        requested_status=new_status,
        triage_note=triage_note,
        requested_by=request.user,
    )
    
    return JsonResponse({
        'success': True,
        'requires_approval': True,
        'message': 'Status change request submitted and pending approval.',
        'request_id': str(approval_request.id),
    })


@login_required
def approvals_list(request):
    """List all approval requests with tabs for pending and history"""
    # Only Security Expert and Administrator can view this page
    if not can_approve_status(request.user):
        messages.error(request, 'You do not have permission to view approval requests.')
        return redirect('dashboard')
    
    # Get active tab (default to 'pending')
    active_tab = request.GET.get('tab', 'pending')
    
    # Pagination settings
    per_page = request.GET.get('per_page', '50')
    if per_page not in ['20', '50', '100']:
        per_page = '50'
    
    # Pending requests (first tab)
    pending_requests = StatusApprovalRequest.objects.filter(
        status='PENDING'
    ).select_related(
        'finding',
        'finding__scan__release__product__workspace',
        'requested_by'
    ).order_by('-requested_at')
    
    pending_paginator = Paginator(pending_requests, int(per_page))
    pending_page = request.GET.get('pending_page', 1)
    pending_page_obj = pending_paginator.get_page(pending_page)
    
    # History requests (second tab) - approved and rejected
    history_requests = StatusApprovalRequest.objects.filter(
        status__in=['APPROVED', 'REJECTED']
    ).select_related(
        'finding',
        'finding__scan__release__product__workspace',
        'requested_by',
        'reviewed_by'
    ).order_by('-reviewed_at', '-requested_at')
    
    history_paginator = Paginator(history_requests, int(per_page))
    history_page = request.GET.get('history_page', 1)
    history_page_obj = history_paginator.get_page(history_page)
    
    return render(request, 'findings/approvals_list.html', {
        'pending_requests': pending_page_obj,
        'history_requests': history_page_obj,
        'per_page': per_page,
        'active_tab': active_tab,
    })


@login_required
@require_POST
def approve_status_request(request, request_id):
    """Approve a status change request"""
    if not can_approve_status(request.user):
        messages.error(request, 'You do not have permission to approve requests.')
        return redirect('dashboard')
    
    approval_request = get_object_or_404(StatusApprovalRequest, id=request_id, status='PENDING')
    review_note = request.POST.get('review_note', '')
    
    try:
        approval_request.approve(request.user, review_note)
        messages.success(request, f'Status change request approved. Vulnerability status updated to {approval_request.requested_status}.')
    except ValueError as e:
        messages.error(request, f'Error approving request: {str(e)}')
    
    # Redirect back to pending tab
    return redirect('approvals_list?tab=pending')


@login_required
@require_POST
def reject_status_request(request, request_id):
    """Reject a status change request"""
    if not can_approve_status(request.user):
        messages.error(request, 'You do not have permission to reject requests.')
        return redirect('dashboard')
    
    approval_request = get_object_or_404(StatusApprovalRequest, id=request_id, status='PENDING')
    review_note = request.POST.get('review_note', '')
    
    try:
        approval_request.reject(request.user, review_note)
        messages.success(request, 'Status change request rejected.')
    except ValueError as e:
        messages.error(request, f'Error rejecting request: {str(e)}')
    
    # Redirect back to pending tab
    return redirect('approvals_list?tab=pending')