from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from core.findings.models import Workspace  # Import the Workspace model

@login_required
def dashboard(request):
    # 1. Get real stats
    workspace_count = Workspace.objects.count()
    
    # 2. Pass them to the template
    context = {
        'workspace_count': workspace_count,
        # We will add 'product_count' and 'finding_count' here later
    }
    
    return render(request, 'dashboard.html', context)