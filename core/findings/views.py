from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Case, When, Value
from .models import Workspace, Product, Release, Scan, Finding
from .forms import WorkspaceForm

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
def release_detail(request, release_id):
    release = get_object_or_404(Release, id=release_id)
    
    findings = Finding.objects.filter(scan__release=release).order_by(
        # FIX: Use Case/When directly (without "models.")
        Case(
            When(severity='CRITICAL', then=Value(1)),
            When(severity='HIGH', then=Value(2)),
            When(severity='MEDIUM', then=Value(3)),
            When(severity='LOW', then=Value(4)),
            default=Value(5)
        )
    )

    stats = {
        'total': findings.count(),
        'critical': findings.filter(severity='CRITICAL').count(),
        'high': findings.filter(severity='HIGH').count(),
        'medium': findings.filter(severity='MEDIUM').count(),
    }

    return render(request, 'findings/release_detail.html', {
        'release': release, 
        'findings': findings, 
        'stats': stats
    })