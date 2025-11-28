from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Case, When, Value
from .models import Workspace, Product, Release, Scan, Finding, Component
from .forms import WorkspaceForm, ScanIngestForm, ProductForm, ReleaseForm
from django.core.paginator import Paginator # Import Paginator
from django.http import JsonResponse
# 1. SBOM Parser (Use sbom_utils, NOT utils)
from .sbom_utils import digest_sbom

# 2. Scanner Registry (The new modular system)
from core.scanners import get_scanner

@login_required
def workspace_create(request):
    """Create a new workspace."""
    if request.method == 'POST':
        form = WorkspaceForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('workspace_list')
    else:
        form = WorkspaceForm()
    
    return render(request, 'findings/workspace_form.html', {'form': form, 'title': 'Create Workspace'})

@login_required
def workspace_edit(request, workspace_id):
    """Edit an existing workspace."""
    workspace = get_object_or_404(Workspace, id=workspace_id)
    
    if request.method == 'POST':
        form = WorkspaceForm(request.POST, instance=workspace)
        if form.is_valid():
            form.save()
            return redirect('workspace_list')
    else:
        form = WorkspaceForm(instance=workspace)
    
    return render(request, 'findings/workspace_form.html', {'form': form, 'title': 'Edit Workspace'})

@login_required
def workspace_list(request):
    """List all workspaces with consolidated vulnerability counts."""
    
    # We use 'annotate' to count findings across the relationship chain:
    # Workspace -> Product -> Release -> Scan -> Finding
    workspaces = Workspace.objects.annotate(
        crit_count=Count('products__releases__scans__findings', 
            filter=Q(products__releases__scans__findings__severity='CRITICAL')),
        
        high_count=Count('products__releases__scans__findings', 
            filter=Q(products__releases__scans__findings__severity='HIGH')),
        
        med_count=Count('products__releases__scans__findings', 
            filter=Q(products__releases__scans__findings__severity='MEDIUM')),
            
        low_count=Count('products__releases__scans__findings', 
            filter=Q(products__releases__scans__findings__severity='LOW')),
    ).order_by('-created_at')

    return render(request, 'findings/workspace_list.html', {'workspaces': workspaces})

@login_required
def workspace_detail(request, workspace_id):
    """Show details of a specific workspace (The Products inside it)."""
    workspace = get_object_or_404(Workspace, id=workspace_id)
    
    # Get all products in this workspace
    products = workspace.products.all().order_by('-created_at')
    
    return render(request, 'findings/workspace_detail.html', {
        'workspace': workspace, 
        'products': products
    })

@login_required
def product_list(request):
    # Fetches ALL products from ALL workspaces
    products = Product.objects.all().select_related('workspace').order_by('-created_at')
    return render(request, 'findings/product_list.html', {'products': products})

@login_required
def product_detail(request, product_id):
    """
    Shows a single Product and lists its Releases (Versions).
    """
    product = get_object_or_404(Product, id=product_id)
    
    # Get releases with a count of findings per release
    releases = product.releases.annotate(
        vuln_count=Count('scans__findings')
    ).order_by('-created_at')

    return render(request, 'findings/product_detail.html', {
        'product': product, 
        'releases': releases
    })

@login_required
def product_create(request):
    """Explicitly create a new product."""
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            # Redirect to the detail page of the new product
            return redirect('product_detail', product_id=product.id)
    else:
        form = ProductForm()
    
    return render(request, 'findings/product_form.html', {'form': form})

@login_required
def product_edit(request, product_id):
    """Edit an existing product."""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            # Redirect back to the details page
            return redirect('product_detail', product_id=product.id)
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'findings/product_form.html', {
        'form': form, 
        'title': f'Edit {product.name}'
    })

@login_required
def release_detail(request, release_id):
    """
    The 'War Room'. Shows:
    1. SBOM (Components) with Pagination
    2. Vulnerabilities (Findings)
    3. Stats & Audit Log
    """
    release = get_object_or_404(Release, id=release_id)
    
    # ---------------------------------------------------------
    # 1. SCANS (Audit Trail)
    # ---------------------------------------------------------
    scans = release.scans.all().order_by('-started_at')

    # ---------------------------------------------------------
    # 2. FINDINGS (Vulnerabilities)
    # ---------------------------------------------------------
    # Custom ordering: Critical -> High -> Med -> Low -> Info
    findings = Finding.objects.filter(scan__release=release).order_by(
        Case(
            When(severity='CRITICAL', then=Value(1)),
            When(severity='HIGH', then=Value(2)),
            When(severity='MEDIUM', then=Value(3)),
            When(severity='LOW', then=Value(4)),
            When(severity='INFO', then=Value(5)),
            default=Value(6)
        )
    )

    # Calculate Security Stats
    vuln_stats = {
        'total': findings.count(),
        'critical': findings.filter(severity='CRITICAL').count(),
        'high': findings.filter(severity='HIGH').count(),
        'medium': findings.filter(severity='MEDIUM').count(),
        'low': findings.filter(severity='LOW').count(),
        'info': findings.filter(severity='INFO').count(),
    }

    # ---------------------------------------------------------
    # 3. COMPONENTS (SBOM) & PAGINATION
    # ---------------------------------------------------------
    all_components = release.components.all().order_by('name')
    
    # IMPORTANT: Get total count BEFORE pagination to show in the Tab Header
    total_components = all_components.count()

    # --- License Analytics (Heuristic) ---
    # We calculate this on the FULL list, not just the current page
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

    # --- Pagination Logic ---
    per_page = request.GET.get('per_page', '20')
    if per_page not in ['20', '50', '100']:
        per_page = '20'
        
    paginator = Paginator(all_components, int(per_page))
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'findings/release_detail.html', {
        'release': release,
        'scans': scans,
        'findings': findings,
        'vuln_stats': vuln_stats,
        'lic_stats': lic_stats,
        
        # Pagination Context
        'page_obj': page_obj,   # The sliced list (e.g. 20 items)
        'per_page': per_page,   # The limit (e.g. "20")
        'total_components': total_components # The total count (e.g. 134)
    })
    release = get_object_or_404(Release, id=release_id)
    
    # 1. FETCH SCANS & FINDINGS (Keep existing logic)
    scans = release.scans.all().order_by('-started_at')
    
    # Findings Logic (Severity Sorting)
    findings = Finding.objects.filter(scan__release=release).order_by(
        Case(
            When(severity='CRITICAL', then=Value(1)),
            When(severity='HIGH', then=Value(2)),
            When(severity='MEDIUM', then=Value(3)),
            When(severity='LOW', then=Value(4)),
            When(severity='INFO', then=Value(5)),
            default=Value(6)
        )
    )

    # 2. FETCH COMPONENTS (With Pagination)
    all_components = release.components.all().order_by('name')
    
    # Get 'per_page' from URL, default to 20. Limit to valid options to prevent abuse.
    per_page = request.GET.get('per_page', '20')
    if per_page not in ['20', '50', '100']:
        per_page = '20'
        
    paginator = Paginator(all_components, int(per_page))
    
    # Get 'page' from URL, default to 1
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # 3. STATS (Keep existing logic)
    lic_stats = {'foss': 0, 'coss': 0, 'unidentified': 0}
    # ... (Keep your existing license loop logic here) ...
    # Note: You might want to calculate stats on 'all_components' BEFORE pagination
    # so the stats reflect the whole SBOM, not just the current page.
    for comp in all_components:
        # ... (Your existing license classification logic) ...
        # (Simplified for brevity here, paste your previous logic back)
        pass 

    vuln_stats = {
        'total': findings.count(),
        'critical': findings.filter(severity='CRITICAL').count(),
        'high': findings.filter(severity='HIGH').count(),
        'medium': findings.filter(severity='MEDIUM').count(),
        'low': findings.filter(severity='LOW').count(),
        'info': findings.filter(severity='INFO').count(),
    }

    return render(request, 'findings/release_detail.html', {
        'release': release,
        'scans': scans,
        'findings': findings,
        'vuln_stats': vuln_stats,
        'lic_stats': lic_stats,
        'page_obj': page_obj,   # Pass the Page Object instead of raw list
        'per_page': per_page,   # Pass current limit for the dropdown
    })

@login_required
def release_create(request, product_id):
    """
    1. Creates the Release
    2. Uploads the SBOM
    3. Triggers Digestion
    """
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = ReleaseForm(request.POST, request.FILES)
        if form.is_valid():
            # Save Release but attach Product first
            release = form.save(commit=False)
            release.product = product
            release.save()
            
            # TRIGGER: Digest the SBOM immediately
            if release.sbom_file:
                digest_sbom(release)
            
            # Go to the new detail page
            return redirect('release_detail', release_id=release.id)
    else:
        form = ReleaseForm()
    
    return render(request, 'findings/release_form.html', {
        'form': form, 
        'product': product
    })

@login_required
def upload_scan(request):
    # FIX 1: Initialize 'initial_data' to empty dict by default
    # This prevents "Undefined name 'initial_data'" error
    initial_data = {}
    
    # Check if we are pre-filling from a URL parameter
    prefill_release_id = request.GET.get('release_id')
    
    if prefill_release_id:
        # Use a different variable name (release_obj) to avoid confusion
        release_obj = get_object_or_404(Release, id=prefill_release_id)
        initial_data = {
            'workspace': release_obj.product.workspace,
            'product_name': release_obj.product.name,
            'release_name': release_obj.name
        }

    if request.method == 'POST':
        form = ScanIngestForm(request.POST, request.FILES)
        if form.is_valid():
            # Extract data
            workspace = form.cleaned_data['workspace']
            product_name = form.cleaned_data['product_name']
            release_name = form.cleaned_data['release_name']
            scanner_name = form.cleaned_data['scanner_name']
            json_file = request.FILES['file_upload']

            # A. Get or Create PRODUCT
            product, _ = Product.objects.get_or_create(
                name=product_name,
                workspace=workspace,
                defaults={'product_type': 'WEB'}
            )

            # B. Get or Create RELEASE
            # FIX 2: We define 'release' here, so it is available for the redirect below
            release, _ = Release.objects.get_or_create(
                name=release_name,
                product=product
            )

            # C. Create SCAN Record
            scan = Scan.objects.create(
                release=release,
                scanner_name=scanner_name
            )

            # D. RUN PARSER
            parser = get_scanner(scanner_name)
            if parser:
                parser.parse(scan, json_file)

            # E. Redirect using the 'release' object we defined in Step B
            return redirect('release_detail', release_id=release.id)
    else:
        # Now 'initial_data' always exists (either empty or populated)
        form = ScanIngestForm(initial=initial_data)

    return render(request, 'upload.html', {'form': form})

@login_required
def release_sbom_export(request, release_id):
    """
    Re-hydrates the SBOM JSON from the database for download.
    """
    release = get_object_or_404(Release, id=release_id)
    components = release.components.all()

    # 1. Build JSON Structure
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "metadata": {
            "component": {
                "name": release.product.name,
                "version": release.name,
                "type": "application"
            }
        },
        "components": []
    }

    # 2. Populate Components
    for comp in components:
        entry = {
            "type": comp.type.lower(),
            "name": comp.name,
            "version": comp.version,
            "purl": comp.purl,
            "licenses": [{"license": {"id": comp.license}}] if comp.license else []
        }
        sbom["components"].append(entry)

    # 3. Return File
    response = JsonResponse(sbom, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="{release.product.name}_{release.name}_sbom.json"'
    return response