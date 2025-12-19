from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.contrib import messages
from django.http import JsonResponse
import uuid
from core.models import Workspace, Product, Release, Finding, Scan, Component, Repository, Artifact
from core.forms import WorkspaceForm, ProductForm, RepositoryForm, ReleaseComposerForm

@login_required
def dashboard(request):
    """Enhanced dashboard with comprehensive metrics"""
    from django.db.models import Count, Q, Avg, Max, Min
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models.functions import TruncDate
    from core.models import Team, Product
    
    # Time ranges
    now = timezone.now()
    last_7_days = now - timedelta(days=7)
    last_30_days = now - timedelta(days=30)
    last_90_days = now - timedelta(days=90)
    
    # === SCOPE FILTERING ===
    scope = request.GET.get('scope', 'all')
    scope_products = None
    
    if scope == 'my_teams':
        # Get all teams where user is a member
        user_teams = Team.objects.filter(members=request.user)
        # Get all products assigned to those teams
        scope_products = Product.objects.filter(teams__in=user_teams).distinct()
    
    # === COMMAND CENTER METRICS ===
    active_findings = Finding.objects.filter(status='OPEN').exclude(status='FIXED')
    
    # Apply scope filtering to findings
    if scope_products is not None:
        active_findings = active_findings.filter(scan__release__product__in=scope_products)
    critical_high = active_findings.filter(severity__in=['CRITICAL', 'HIGH']).count()
    kev_count = active_findings.filter(metadata__kev_status=True).count()
    high_epss = active_findings.filter(metadata__epss_score__gte=0.7).count()
    
    # Secrets count
    secrets_count = active_findings.filter(finding_type=Finding.Type.SECRET).count()
    
    # Fix rate (last 30 days)
    fixed_last_30_qs = Finding.objects.filter(
        status='FIXED',
        last_seen__gte=last_30_days
    )
    total_last_30_qs = Finding.objects.filter(
        first_seen__gte=last_30_days
    )
    if scope_products is not None:
        fixed_last_30_qs = fixed_last_30_qs.filter(scan__release__product__in=scope_products)
        total_last_30_qs = total_last_30_qs.filter(scan__release__product__in=scope_products)
    fixed_last_30 = fixed_last_30_qs.count()
    total_last_30 = total_last_30_qs.count()
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
    if scope_products is not None:
        fixed_findings = fixed_findings.filter(scan__release__product__in=scope_products)
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
    
    risk_accepted_qs = Finding.objects.filter(status='WONT_FIX')
    if scope_products is not None:
        risk_accepted_qs = risk_accepted_qs.filter(scan__release__product__in=scope_products)
    risk_accepted = risk_accepted_qs.count()
    
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
    product_vulns_qs = Product.objects.annotate(
        vuln_count=Count('releases__scans__findings', filter=Q(
            releases__scans__findings__status='OPEN'
        ))
    )
    if scope_products is not None:
        product_vulns_qs = product_vulns_qs.filter(id__in=scope_products.values_list('id', flat=True))
    product_vulns = list(
        product_vulns_qs.filter(vuln_count__gt=0)
        .order_by('-vuln_count')[:10]
        .values('name', 'criticality', 'vuln_count')
    )
    
    # === REMEDIATION HEATMAP (Last 90 days) ===
    # Generate heatmap data showing "green days" when bugs were fixed
    # Split into 3 rows of 30 days each
    heatmap_data = []
    start_date = now - timedelta(days=89)  # Start from 90 days ago
    
    # Generate data for all 90 days
    all_days = []
    for i in range(90):
        date = start_date + timedelta(days=i)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)
        
        fixed_qs = Finding.objects.filter(
            status='FIXED',
            last_seen__gte=date_start,
            last_seen__lt=date_end
        )
        if scope_products is not None:
            fixed_qs = fixed_qs.filter(scan__release__product__in=scope_products)
        fixed_count = fixed_qs.count()
        
        # Green day = at least 1 finding was fixed
        is_green_day = fixed_count > 0
        
        all_days.append({
            'date': date_start.strftime('%Y-%m-%d'),
            'fixed_count': fixed_count,
            'is_green': is_green_day,
            'day_of_week': date_start.strftime('%a'),
            'day_of_month': date_start.day
        })
    
    # Split into 3 rows of 30 days each
    heatmap_data = [
        all_days[0:30],   # First 30 days (oldest)
        all_days[30:60],  # Middle 30 days
        all_days[60:90]   # Last 30 days (most recent)
    ]
    
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
        # Scope information
        'scope': scope,
        'scope_filter_active': scope == 'my_teams',
        
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
    
    try:
        if request.method == 'POST':
            # Get workspace ID first
            workspace_id = request.POST.get('workspace')
            
            # Create form with POST data
            form = ProductForm(request.POST, initial=initial)
            
            # IMPORTANT: Filter teams by workspace BEFORE validation
            # This ensures the teams field can validate against the correct queryset
            if workspace_id:
                from core.models import Team
                try:
                    # Update queryset before validation
                    form.fields['teams'].queryset = Team.objects.filter(workspace_id=workspace_id)
                except (ValueError, TypeError):
                    # Invalid workspace ID, set empty queryset
                    form.fields['teams'].queryset = Team.objects.none()
            else:
                # No workspace selected, set empty queryset
                form.fields['teams'].queryset = Team.objects.none()
            
            if form.is_valid():
                try:
                    product = form.save()
                    # Log audit event
                    try:
                        from core.services.audit import log_audit_event
                        log_audit_event(request, 'PRODUCT_CREATE', product, {
                            'teams': [team.name for team in product.teams.all()]
                        })
                    except Exception:
                        pass  # Don't fail if audit logging fails
                    messages.success(request, f'Product "{product.name}" created successfully.')
                    return redirect('product_detail', product_id=product.id)
                except Exception as e:
                    # Log the error for debugging
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error saving product: {str(e)}", exc_info=True)
                    # Add error to form
                    messages.error(request, f"Error creating product: {str(e)}")
                    # Re-raise to show form with errors
                    raise
            else:
                # If form is invalid, still filter teams by workspace if provided
                workspace_id = request.POST.get('workspace')
                if workspace_id:
                    from core.models import Team
                    try:
                        form.fields['teams'].queryset = Team.objects.filter(workspace_id=workspace_id)
                    except (ValueError, TypeError):
                        form.fields['teams'].queryset = Team.objects.none()
                # Log form errors for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Product form validation errors: {form.errors}")
                # Show specific field errors
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
        else:
            form = ProductForm(initial=initial)
            # Filter teams by workspace if provided
            if initial.get('workspace'):
                from core.models import Team
                try:
                    form.fields['teams'].queryset = Team.objects.filter(workspace_id=initial['workspace'])
                except (ValueError, TypeError):
                    form.fields['teams'].queryset = Team.objects.none()
            else:
                # If no workspace in initial, try to get user's current workspace
                if hasattr(request.user, 'profile') and request.user.profile.current_workspace:
                    from core.models import Team
                    try:
                        form.fields['workspace'].initial = request.user.profile.current_workspace
                        form.fields['teams'].queryset = Team.objects.filter(workspace=request.user.profile.current_workspace)
                    except Exception:
                        form.fields['teams'].queryset = Team.objects.none()
                else:
                    form.fields['teams'].queryset = Team.objects.none()
    except Exception as e:
        # Catch any unexpected errors during form initialization
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in product_create view: {str(e)}", exc_info=True)
        from django.contrib import messages
        messages.error(request, f"An error occurred: {str(e)}")
        # Create a basic form to prevent template errors
        from core.forms import ProductForm
        form = ProductForm(initial=initial)
    
    return render(request, 'findings/product_form.html', {'form': form})

@login_required
def product_edit(request, product_id):
    product = get_object_or_404(Product.objects.prefetch_related('teams'), id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save()
            # Log audit event for team assignment changes
            from core.services.audit import log_audit_event
            log_audit_event(request, 'PRODUCT_UPDATE', product, {
                'teams': [team.name for team in product.teams.all()]
            })
            return redirect('product_detail', product_id=product.id)
    else:
        form = ProductForm(instance=product)
        # Filter teams by product's workspace
        form.fields['teams'].queryset = Team.objects.filter(workspace=product.workspace)
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


# ===== ASSET INVENTORY (BOM Architecture) =====

@login_required
def asset_inventory(request):
    """
    Asset Inventory page - Manage Repositories and view Artifacts
    Lists all repositories with expandable rows showing their artifacts
    """
    repositories = Repository.objects.select_related('workspace').prefetch_related(
        'artifacts'
    ).order_by('workspace__name', 'name')
    
    # Group repositories by workspace
    repos_by_workspace = {}
    for repo in repositories:
        workspace_name = repo.workspace.name
        if workspace_name not in repos_by_workspace:
            repos_by_workspace[workspace_name] = []
        repos_by_workspace[workspace_name].append(repo)
    
    # Get artifact scan status for each repository
    for repo in repositories:
        artifacts = repo.artifacts.all()[:5]  # Latest 5 artifacts
        for artifact in artifacts:
            # Get latest scan status for this artifact
            latest_scan = Scan.objects.filter(artifact=artifact).order_by('-started_at').first()
            artifact.latest_scan_status = latest_scan.status if latest_scan else 'NO_SCAN'
            artifact.latest_scan_date = latest_scan.started_at if latest_scan else None
            artifact.findings_count = Finding.objects.filter(
                scan__artifact=artifact,
                status='OPEN'
            ).count() if latest_scan else 0
    
    workspaces = Workspace.objects.all().order_by('name')
    
    return render(request, 'inventory/asset_inventory.html', {
        'repositories': repositories,
        'repos_by_workspace': repos_by_workspace,
        'workspaces': workspaces,
    })


@login_required
def repository_create(request):
    """Create a new repository (modal form handler)"""
    if request.method == 'POST':
        form = RepositoryForm(request.POST)
        if form.is_valid():
            repository = form.save()
            messages.success(request, f'Repository "{repository.name}" created successfully.')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Repository "{repository.name}" created successfully.',
                    'repository_id': str(repository.id)
                })
            return redirect('asset_inventory')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)
            messages.error(request, 'Error creating repository. Please check the form.')
    else:
        form = RepositoryForm()
    
    return render(request, 'inventory/repository_form_modal.html', {
        'form': form
    })


@login_required
def artifact_search_api(request):
    """
    API endpoint for artifact search (used by Release Composer)
    Returns JSON list of artifacts matching the search query
    """
    query = request.GET.get('q', '').strip()
    workspace_id = request.GET.get('workspace_id')
    
    artifacts = Artifact.objects.select_related('repository', 'workspace').all()
    
    # Filter by workspace if provided
    if workspace_id:
        try:
            artifacts = artifacts.filter(workspace_id=workspace_id)
        except ValueError:
            pass
    
    # Search by name or version
    if query:
        artifacts = artifacts.filter(
            Q(name__icontains=query) | Q(version__icontains=query)
        )
    
    # Limit results
    artifacts = artifacts[:20]
    
    # Get scan status for each artifact
    results = []
    for artifact in artifacts:
        latest_scan = Scan.objects.filter(artifact=artifact).order_by('-started_at').first()
        results.append({
            'id': str(artifact.id),
            'name': artifact.name,
            'version': artifact.version,
            'type': artifact.type,
            'repository': artifact.repository.name if artifact.repository else None,
            'workspace': artifact.workspace.name,
            'latest_scan_status': latest_scan.status if latest_scan else 'NO_SCAN',
            'findings_count': Finding.objects.filter(
                scan__artifact=artifact,
                status='OPEN'
            ).count() if latest_scan else 0,
        })
    
    return JsonResponse({'artifacts': results})


# ===== RELEASE COMPOSER (BOM Builder) =====

@login_required
def release_composer(request, product_id):
    """
    Release Composer - BOM Builder
    Allows users to compose a release by selecting artifacts
    """
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = ReleaseComposerForm(request.POST)
        if form.is_valid():
            release = form.save(commit=False)
            release.product = product
            release.save()
            
            # Link artifacts to release
            artifact_ids = form.cleaned_data.get('artifact_ids', [])
            if artifact_ids:
                try:
                    artifacts = Artifact.objects.filter(id__in=artifact_ids)
                    release.artifacts.set(artifacts)
                except Exception as e:
                    messages.error(request, f'Error linking artifacts: {str(e)}')
            
            messages.success(request, f'Release "{release.name}" created successfully with {len(artifact_ids)} artifacts.')
            return redirect('release_detail', release_id=release.id)
        else:
            messages.error(request, 'Error creating release. Please check the form.')
    else:
        form = ReleaseComposerForm()
    
    # Get all workspaces for filtering
    workspaces = Workspace.objects.all().order_by('name')
    
    return render(request, 'inventory/release_composer.html', {
        'product': product,
        'form': form,
        'workspaces': workspaces,
    })


@login_required
def release_composer_risk_preview(request):
    """
    API endpoint to calculate estimated risk for selected artifacts
    Used by Release Composer to show risk preview
    """
    artifact_ids = request.GET.get('artifact_ids', '').strip()
    
    if not artifact_ids:
        return JsonResponse({
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'total': 0
        })
    
    try:
        artifact_id_list = [uuid.UUID(id.strip()) for id in artifact_ids.split(',') if id.strip()]
        artifacts = Artifact.objects.filter(id__in=artifact_id_list)
        
        # Get all findings from scans of these artifacts
        findings = Finding.objects.filter(
            scan__artifact__in=artifacts,
            status='OPEN'
        )
        
        stats = findings.aggregate(
            critical=Count('id', filter=Q(severity='CRITICAL')),
            high=Count('id', filter=Q(severity='HIGH')),
            medium=Count('id', filter=Q(severity='MEDIUM')),
            low=Count('id', filter=Q(severity='LOW')),
            total=Count('id')
        )
        
        return JsonResponse(stats)
    except (ValueError, Exception) as e:
        return JsonResponse({
            'error': str(e),
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'total': 0
        }, status=400)