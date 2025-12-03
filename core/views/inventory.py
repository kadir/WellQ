from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from core.models import Workspace, Product, Release, Finding, Scan, Component
from core.forms import WorkspaceForm, ProductForm

@login_required
def dashboard(request):
    """Enhanced dashboard with comprehensive metrics"""
    from django.db.models import Count, Q, Avg, Max, Min
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models.functions import TruncDate
    
    # Time ranges
    now = timezone.now()
    last_7_days = now - timedelta(days=7)
    last_30_days = now - timedelta(days=30)
    last_90_days = now - timedelta(days=90)
    
    # === COMMAND CENTER METRICS ===
    active_findings = Finding.objects.filter(status='OPEN').exclude(status='FIXED')
    critical_high = active_findings.filter(severity__in=['CRITICAL', 'HIGH']).count()
    kev_count = active_findings.filter(metadata__kev_status=True).count()
    high_epss = active_findings.filter(metadata__epss_score__gte=0.7).count()
    
    # Secrets count
    secrets_count = active_findings.filter(finding_type=Finding.Type.SECRET).count()
    
    # Fix rate (last 30 days)
    fixed_last_30 = Finding.objects.filter(
        status='FIXED',
        last_seen__gte=last_30_days
    ).count()
    total_last_30 = Finding.objects.filter(
        first_seen__gte=last_30_days
    ).count()
    fix_rate = (fixed_last_30 / total_last_30 * 100) if total_last_30 > 0 else 0
    
    # Calculate Security Grade (A, B, C, F)
    # Grade calculation: Based on critical/high findings, secrets, and fix rate
    total_active = active_findings.count()
    grade_score = 100
    
    # Deduct points for critical/high findings
    if critical_high > 0:
        grade_score -= min(critical_high * 2, 40)  # Max 40 points deduction
    
    # Deduct points for secrets (secrets are always critical)
    if secrets_count > 0:
        grade_score -= min(secrets_count * 5, 30)  # Max 30 points deduction
    
    # Deduct points for low fix rate
    if fix_rate < 50:
        grade_score -= (50 - fix_rate) * 0.5  # Max 25 points deduction
    
    # Deduct points for KEV findings
    if kev_count > 0:
        grade_score -= min(kev_count * 3, 20)  # Max 20 points deduction
    
    # Calculate grade letter
    if grade_score >= 90:
        security_grade = 'A'
    elif grade_score >= 75:
        security_grade = 'B'
    elif grade_score >= 60:
        security_grade = 'C'
    else:
        security_grade = 'F'
    
    # Calculate MTTR (Mean Time to Remediation) in days
    # Average time from first_seen to last_seen for FIXED findings
    fixed_findings = Finding.objects.filter(status='FIXED')
    mttr_days = 0
    if fixed_findings.exists():
        from django.db.models import F, ExpressionWrapper, DurationField
        mttr_avg = fixed_findings.annotate(
            remediation_time=ExpressionWrapper(
                F('last_seen') - F('first_seen'),
                output_field=DurationField()
            )
        ).aggregate(avg_time=Avg('remediation_time'))
        
        if mttr_avg['avg_time']:
            mttr_days = round(mttr_avg['avg_time'].total_seconds() / 86400, 1)
    
    risk_accepted = Finding.objects.filter(status='WONT_FIX').count()
    
    # === SEVERITY DISTRIBUTION ===
    severity_data = list(
        active_findings.values('severity')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    # Ensure we have data for all severities even if count is 0
    if not severity_data:
        severity_data = [
            {'severity': 'CRITICAL', 'count': 0},
            {'severity': 'HIGH', 'count': 0},
            {'severity': 'MEDIUM', 'count': 0},
            {'severity': 'LOW', 'count': 0},
            {'severity': 'INFO', 'count': 0},
        ]
    
    # === STATUS DISTRIBUTION ===
    status_data = list(
        Finding.objects.values('status')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    # Ensure we have data for all statuses even if count is 0
    if not status_data:
        status_data = [
            {'status': 'OPEN', 'count': 0},
            {'status': 'FIXED', 'count': 0},
            {'status': 'FALSE_POSITIVE', 'count': 0},
            {'status': 'WONT_FIX', 'count': 0},
            {'status': 'DUPLICATE', 'count': 0},
        ]
    
    # === TOP 10 CVEs ===
    top_cves = list(
        active_findings.values('vulnerability_id', 'severity')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )
    if not top_cves:
        top_cves = []
    
    # === EPSS DISTRIBUTION ===
    epss_ranges = [
        {'range': '0.0-0.2', 'min': 0.0, 'max': 0.2},
        {'range': '0.2-0.4', 'min': 0.2, 'max': 0.4},
        {'range': '0.4-0.6', 'min': 0.4, 'max': 0.6},
        {'range': '0.6-0.8', 'min': 0.6, 'max': 0.8},
        {'range': '0.8-1.0', 'min': 0.8, 'max': 1.0},
    ]
    epss_data = []
    for r in epss_ranges:
        count = active_findings.filter(
            metadata__epss_score__gte=r['min'],
            metadata__epss_score__lt=r['max'] if r['max'] < 1.0 else 1.01
        ).count()
        epss_data.append({'range': r['range'], 'count': count})
    
    # === KEV STATUS ===
    kev_count_active = active_findings.filter(metadata__kev_status=True).count()
    kev_not_exploited = active_findings.filter(metadata__kev_status=False).count()
    kev_data = [
        {'label': 'Exploited (KEV)', 'count': kev_count_active},
        {'label': 'Not Exploited', 'count': kev_not_exploited}
    ]
    
    # === VULNERABILITIES BY PRODUCT ===
    product_vulns = list(
        Product.objects.annotate(
            vuln_count=Count('releases__scans__findings', filter=Q(
                releases__scans__findings__status='OPEN'
            ))
        )
        .filter(vuln_count__gt=0)
        .order_by('-vuln_count')[:10]
        .values('name', 'criticality', 'vuln_count')
    )
    
    # === REMEDIATION HEATMAP (Last 90 days) ===
    # Generate heatmap data showing "green days" when bugs were fixed
    heatmap_data = []
    start_date = now - timedelta(days=89)  # Start from 90 days ago
    for i in range(90):
        date = start_date + timedelta(days=i)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)
        
        fixed_count = Finding.objects.filter(
            status='FIXED',
            last_seen__gte=date_start,
            last_seen__lt=date_end
        ).count()
        
        # Green day = at least 1 finding was fixed
        is_green_day = fixed_count > 0
        
        heatmap_data.append({
            'date': date_start.strftime('%Y-%m-%d'),
            'fixed_count': fixed_count,
            'is_green': is_green_day,
            'day_of_week': date_start.strftime('%a'),
            'day_of_month': date_start.day
        })
    
    # === VULNERABILITY TRENDS (Last 30 days) ===
    trend_data = []
    for i in range(30):
        date = last_30_days + timedelta(days=i)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)
        
        new_count = Finding.objects.filter(
            first_seen__gte=date_start,
            first_seen__lt=date_end
        ).count()
        
        fixed_count = Finding.objects.filter(
            status='FIXED',
            last_seen__gte=date_start,
            last_seen__lt=date_end
        ).count()
        
        active_count = Finding.objects.filter(
            status='OPEN',
            first_seen__lte=date_end
        ).exclude(status='FIXED').count()
        
        trend_data.append({
            'date': date_start.strftime('%Y-%m-%d'),
            'new': new_count,
            'fixed': fixed_count,
            'active': active_count
        })
    
    # === ACTION LIST: TOP VULNERABILITIES (with upgrade versions) ===
    top_vulnerabilities = list(
        active_findings.filter(finding_type=Finding.Type.SCA)
        .exclude(vulnerability_id__isnull=True)
        .exclude(vulnerability_id='')
        .values('vulnerability_id', 'title', 'severity', 'package_name', 'package_version', 'fix_version')
        .annotate(count=Count('id'))
        .order_by('-severity', '-count')[:10]
    )
    
    # === ACTION LIST: TOP SECRETS (with file paths) ===
    # Get full Finding objects for secrets to access metadata properly
    secret_findings = active_findings.filter(
        finding_type=Finding.Type.SECRET
    ).exclude(
        file_path__isnull=True
    ).exclude(
        file_path=''
    ).order_by('-severity', '-first_seen')[:10]
    
    top_secrets = []
    for finding in secret_findings:
        top_secrets.append({
            'id': str(finding.id),
            'title': finding.title,
            'file_path': finding.file_path,
            'line_number': finding.line_number,
            'severity': finding.severity,
            'metadata': finding.metadata or {},
        })
    
    # === SCANNER COVERAGE ===
    scanner_data = list(
        Scan.objects.values('scanner_name')
        .annotate(
            total=Count('findings'),
            critical=Count('findings', filter=Q(findings__severity='CRITICAL')),
            high=Count('findings', filter=Q(findings__severity='HIGH')),
            medium=Count('findings', filter=Q(findings__severity='MEDIUM')),
        )
        .order_by('-total')
    )
    
    # === COMPONENT STATS ===
    total_components = Component.objects.count()
    new_components = Component.objects.filter(
        status='NEW',
        created_at__gte=last_30_days
    ).count()
    removed_components = Component.objects.filter(
        status='REMOVED',
        created_at__gte=last_30_days
    ).count()
    
    # Components with vulnerabilities
    components_with_vulns = Component.objects.filter(
        release__scans__findings__status='OPEN'
    ).distinct().count()
    
    # === RECENT ACTIVITY (Last 10 events) ===
    recent_scans = Scan.objects.order_by('-started_at')[:5].values(
        'id', 'scanner_name', 'started_at', 'release__product__name', 'release__name'
    )
    
    # === WORKSPACE STATS ===
    workspace_count = Workspace.objects.count()
    product_count = Product.objects.count()
    release_count = Release.objects.count()
    
    context = {
        # Command Center Metrics
        'security_grade': security_grade,
        'grade_score': round(grade_score, 1),
        'critical_high': critical_high,
        'secrets_count': secrets_count,
        'mttr_days': mttr_days,
        'fix_rate': round(fix_rate, 1),
        'total_active': active_findings.count(),
        
        # Heatmap Data
        'heatmap_data': heatmap_data,
        
        # Action Lists
        'top_vulnerabilities': top_vulnerabilities,
        'top_secrets': top_secrets,
        
        # Legacy data (for backward compatibility if needed)
        'kev_count': kev_count,
        'high_epss': high_epss,
        'risk_accepted': risk_accepted,
        'severity_data': severity_data,
        'status_data': status_data,
        'top_cves': top_cves,
        'epss_data': epss_data,
        'kev_data': kev_data,
        'product_vulns': product_vulns,
        'trend_data': trend_data,
        'scanner_data': scanner_data,
        'total_components': total_components,
        'new_components': new_components,
        'removed_components': removed_components,
        'components_with_vulns': components_with_vulns,
        'recent_scans': list(recent_scans),
        'workspace_count': workspace_count,
        'product_count': product_count,
        'release_count': release_count,
    }
    
    return render(request, 'dashboard.html', context)

@login_required
def workspace_list(request):
    workspaces = Workspace.objects.all()
    
    # Calculate vulnerability counts for each workspace
    for workspace in workspaces:
        # Get all findings for products in this workspace, excluding FIXED status
        findings = Finding.objects.filter(
            scan__release__product__workspace=workspace
        ).exclude(status='FIXED')
        
        # Count by severity, including both ACTIVE and OPEN for backward compatibility
        workspace.crit_count = findings.filter(severity='CRITICAL', status='OPEN').count()
        workspace.high_count = findings.filter(severity='HIGH', status='OPEN').count()
        workspace.med_count = findings.filter(severity='MEDIUM', status='OPEN').count()
        workspace.low_count = findings.filter(severity='LOW', status='OPEN').count()
    
    return render(request, 'findings/workspace_list.html', {'workspaces': workspaces})

@login_required
def workspace_create(request):
    if request.method == 'POST':
        form = WorkspaceForm(request.POST)
        if form.is_valid():
            ws = form.save()
            return redirect('workspace_detail', workspace_id=ws.id)
    else:
        form = WorkspaceForm()
    return render(request, 'findings/workspace_form.html', {'form': form})

@login_required
def workspace_detail(request, workspace_id):
    workspace = get_object_or_404(Workspace, id=workspace_id)
    products = workspace.products.all()
    return render(request, 'findings/workspace_detail.html', {'workspace': workspace, 'products': products})

@login_required
def workspace_edit(request, workspace_id):
    workspace = get_object_or_404(Workspace, id=workspace_id)
    if request.method == 'POST':
        form = WorkspaceForm(request.POST, instance=workspace)
        if form.is_valid():
            form.save()
            return redirect('workspace_detail', workspace_id=workspace.id)
    else:
        form = WorkspaceForm(instance=workspace)
    return render(request, 'findings/workspace_form.html', {'form': form, 'title': 'Edit Configuration'})

@login_required
def product_list(request):
    products = Product.objects.all()
    return render(request, 'findings/product_list.html', {'products': products})

@login_required
def product_create(request):
    initial = {}
    if request.GET.get('workspace'):
        initial['workspace'] = request.GET.get('workspace')
        
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            return redirect('product_detail', product_id=product.id)
    else:
        form = ProductForm(initial=initial)
    return render(request, 'findings/product_form.html', {'form': form})

@login_required
def product_edit(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect('product_detail', product_id=product.id)
    else:
        form = ProductForm(instance=product)
    return render(request, 'findings/product_form.html', {'form': form, 'title': f'Edit {product.name}'})

@login_required
def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    releases = product.releases.all().order_by('-created_at')
    
    # Calculate findings count for each release for the UI
    # Support both artifact-based (new BOM) and release-based (legacy) modes
    from core.services.release_risk import get_release_findings_queryset
    
    for release in releases:
        findings = get_release_findings_queryset(release)
        release.vuln_count = findings.filter(status='OPEN').count()

    return render(request, 'findings/product_detail.html', {
        'product': product,
        'releases': releases
    })