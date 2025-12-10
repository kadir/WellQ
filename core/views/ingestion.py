from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from core.models import Workspace, Product, Release, Scan
from core.forms import ScanIngestForm
from core.services.scan_engine import process_scan_upload # Using Service
from core.services.audit import log_scan_upload

@login_required
def upload_scan(request):
    initial_data = {}
    prefill_release_id = request.GET.get('release_id')
    
    if prefill_release_id:
        release_obj = get_object_or_404(Release, id=prefill_release_id)
        initial_data = {
            'workspace': release_obj.product.workspace,
            'product_name': release_obj.product.name,
            'release_name': release_obj.name
        }

    if request.method == 'POST':
        form = ScanIngestForm(request.POST, request.FILES)
        if form.is_valid():
            workspace = form.cleaned_data['workspace']
            product_name = form.cleaned_data['product_name']
            release_name = form.cleaned_data['release_name']
            scanner_name = form.cleaned_data['scanner_name']
            json_file = request.FILES['file_upload']

            product, _ = Product.objects.get_or_create(
                name=product_name,
                workspace=workspace,
                defaults={'product_type': 'WEB'}
            )
            release, _ = Release.objects.get_or_create(name=release_name, product=product)
            scan = Scan.objects.create(release=release, scanner_name=scanner_name)

            # DELEGATE TO SERVICE
            process_scan_upload(scan, json_file)
            
            # Log audit event
            log_scan_upload(request, scan)

            return redirect('release_detail', release_id=release.id)
    else:
        form = ScanIngestForm(initial=initial_data)

    return render(request, 'upload.html', {'form': form})