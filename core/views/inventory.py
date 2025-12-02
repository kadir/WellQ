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
    
    # === OVERVIEW CARDS ===
    active_findings = Finding.objects.filter(status='OPEN').exclude(status='FIXED')
    critical_high = active_findings.filter(severity__in=['CRITICAL', 'HIGH']).count()
    kev_count = active_findings.filter(metadata__kev_status=True).count()
    high_epss = active_findings.filter(metadata__epss_score__gte=0.7).count()
    
    # Fix rate (last 30 days)
    fixed_last_30 = Finding.objects.filter(
        status='FIXED',
        last_seen__gte=last_30_days
    ).count()
    total_last_30 = Finding.objects.filter(
        first_seen__gte=last_30_days
    ).count()
    fix_rate = (fixed_last_30 / total_last_30 * 100) if total_last_30 > 0 else 0
    
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
        # Overview Cards
        'total_active': active_findings.count(),
        'critical_high': critical_high,
        'kev_count': kev_count,
        'high_epss': high_epss,
        'fix_rate': round(fix_rate, 1),
        'risk_accepted': risk_accepted,
        
        # Charts Data (as Python objects - json_script filter will handle JSON conversion)
        'severity_data': severity_data,
        'status_data': status_data,
        'top_cves': top_cves,
        'epss_data': epss_data,
        'kev_data': kev_data,
        'product_vulns': product_vulns,
        'trend_data': trend_data,
        'scanner_data': scanner_data,
        
        # Component Stats
        'total_components': total_components,
        'new_components': new_components,
        'removed_components': removed_components,
        'components_with_vulns': components_with_vulns,
        
        # Activity
        'recent_scans': list(recent_scans),
        
        # General Stats
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
    # Findings are accessed through scans: Finding -> Scan -> Release
    for release in releases:
        release.vuln_count = Finding.objects.filter(
            scan__release=release,
            status='OPEN'
        ).count()

    return render(request, 'findings/product_detail.html', {
        'product': product,
        'releases': releases
    })