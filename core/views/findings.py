from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Case, When, Value, Q, Count
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import Product, Release, Finding, Component
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
    release = get_object_or_404(Release, id=release_id)
    scans = release.scans.all().order_by('-started_at')

    # Findings Logic - Get all findings for this release
    all_findings = Finding.objects.filter(scan__release=release)
    
    # Apply filters from query parameters
    status_filter = request.GET.get('status')
    severity_filter = request.GET.get('severity')
    cve_filter = request.GET.get('cve_id')
    
    findings = all_findings
    
    # Apply status filter
    if status_filter:
        status_upper = status_filter.upper()
        if status_upper == 'ACTIVE':
            # Show both ACTIVE and OPEN for backward compatibility
            findings = findings.filter(status__in=['ACTIVE', 'OPEN'])
        else:
            findings = findings.filter(status=status_upper)
    # If no status filter (All selected), show all findings including FIXED
    
    # Apply severity filter
    if severity_filter:
        findings = findings.filter(severity=severity_filter.upper())
    
    # Apply CVE filter
    if cve_filter:
        findings = findings.filter(cve_id__icontains=cve_filter)
    
    # Apply EPSS score filter (minimum threshold)
    epss_filter = request.GET.get('epss', '').strip()
    if epss_filter:
        try:
            min_epss = float(epss_filter)
            findings = findings.filter(epss_score__gte=min_epss)
        except (ValueError, TypeError):
            # Invalid value, ignore filter
            pass
    
    # Apply KEV filter
    kev_filter = request.GET.get('kev')
    if kev_filter:
        if kev_filter.lower() == 'true' or kev_filter == '1':
            findings = findings.filter(kev_status=True)
        elif kev_filter.lower() == 'false' or kev_filter == '0':
            findings = findings.filter(kev_status=False)
    
    # Calculate statistics from all findings (before filtering)
    vuln_stats = {
        'total': all_findings.exclude(status='FIXED').count(), # Only count active for header
        'critical': all_findings.filter(severity='CRITICAL', status__in=['ACTIVE', 'OPEN']).count(),
        'high': all_findings.filter(severity='HIGH', status__in=['ACTIVE', 'OPEN']).count(),
        'medium': all_findings.filter(severity='MEDIUM', status__in=['ACTIVE', 'OPEN']).count(),
        'low': all_findings.filter(severity='LOW', status__in=['ACTIVE', 'OPEN']).count(),
        'info': all_findings.filter(severity='INFO', status__in=['ACTIVE', 'OPEN']).count(),
    }
    
    # Order findings for display
    findings = findings.order_by(
        Case(
            When(status='FIXED', then=Value(0)), # Fixed bottom
            When(severity='CRITICAL', then=Value(1)),
            When(severity='HIGH', then=Value(2)),
            When(severity='MEDIUM', then=Value(3)),
            When(severity='LOW', then=Value(4)),
            When(severity='INFO', then=Value(5)),
            default=Value(6)
        )
    )

    # Paginate vulnerabilities
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
        if status_upper == 'ACTIVE':
            # Show both ACTIVE and OPEN for backward compatibility
            findings = findings.filter(status__in=['ACTIVE', 'OPEN'])
        else:
            findings = findings.filter(status=status_upper)
    # If no status filter (All selected), show all findings including FIXED
    
    severity_filter = request.GET.get('severity')
    if severity_filter:
        findings = findings.filter(severity=severity_filter.upper())
    
    cve_filter = request.GET.get('cve_id')
    if cve_filter:
        findings = findings.filter(cve_id__icontains=cve_filter)
    
    product_filter = request.GET.get('product')
    if product_filter:
        findings = findings.filter(scan__release__product__name__icontains=product_filter)
    
    workspace_filter = request.GET.get('workspace')
    if workspace_filter:
        findings = findings.filter(scan__release__product__workspace__name__icontains=workspace_filter)
    
    # Apply EPSS score filter (minimum threshold)
    epss_filter = request.GET.get('epss', '').strip()
    if epss_filter:
        try:
            min_epss = float(epss_filter)
            findings = findings.filter(epss_score__gte=min_epss)
        except (ValueError, TypeError):
            # Invalid value, ignore filter
            pass
    
    # Apply KEV filter
    kev_filter = request.GET.get('kev')
    if kev_filter:
        if kev_filter.lower() == 'true' or kev_filter == '1':
            findings = findings.filter(kev_status=True)
        elif kev_filter.lower() == 'false' or kev_filter == '0':
            findings = findings.filter(kev_status=False)
    
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
    
    # Calculate statistics from all findings (before filtering)
    all_findings = Finding.objects.all()
    vuln_stats = {
        'total': all_findings.exclude(status='FIXED').count(),
        'critical': all_findings.filter(severity='CRITICAL', status__in=['ACTIVE', 'OPEN']).count(),
        'high': all_findings.filter(severity='HIGH', status__in=['ACTIVE', 'OPEN']).count(),
        'medium': all_findings.filter(severity='MEDIUM', status__in=['ACTIVE', 'OPEN']).count(),
        'low': all_findings.filter(severity='LOW', status__in=['ACTIVE', 'OPEN']).count(),
        'info': all_findings.filter(severity='INFO', status__in=['ACTIVE', 'OPEN']).count(),
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
    
    data = {
        'id': str(finding.id),
        'cve_id': finding.cve_id,
        'title': finding.title,
        'description': finding.description,
        'severity': finding.severity,
        'status': finding.status,
        'package_name': finding.package_name,
        'package_version': finding.package_version,
        'fixed_version': finding.fixed_version or 'Not available',
        'epss_score': finding.epss_score,
        'epss_percentile': finding.epss_percentile,
        'kev_status': finding.kev_status,
        'kev_date': finding.kev_date.strftime('%Y-%m-%d') if finding.kev_date else None,
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


@login_required
def update_vulnerability_status(request, finding_id):
    """Update vulnerability status"""
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
    
    # Update status
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