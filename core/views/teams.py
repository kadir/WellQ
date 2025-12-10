from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Count
from core.models import Team, Workspace
from core.forms import TeamForm
from core.services.audit import log_audit_event

User = get_user_model()


@login_required
def team_list(request):
    """List all teams with member counts"""
    teams = Team.objects.select_related('workspace').prefetch_related('members').annotate(
        member_count=Count('members')
    ).order_by('workspace__name', 'name')
    
    # Filter by workspace if provided
    workspace_id = request.GET.get('workspace')
    if workspace_id:
        try:
            workspace = Workspace.objects.get(id=workspace_id)
            teams = teams.filter(workspace=workspace)
        except Workspace.DoesNotExist:
            pass
    
    workspaces = Workspace.objects.all().order_by('name')
    
    return render(request, 'teams/team_list.html', {
        'teams': teams,
        'workspaces': workspaces,
        'selected_workspace': workspace_id
    })


@login_required
def team_create(request):
    """Create a new team"""
    if request.method == 'POST':
        form = TeamForm(request.POST)
        if form.is_valid():
            team = form.save()
            log_audit_event(request, 'TEAM_CREATE', team, {'name': team.name})
            messages.success(request, f'Team "{team.name}" created successfully.')
            return redirect('team_list')
    else:
        form = TeamForm()
        # Pre-select workspace if provided
        workspace_id = request.GET.get('workspace')
        if workspace_id:
            try:
                workspace = Workspace.objects.get(id=workspace_id)
                form.fields['workspace'].initial = workspace
            except Workspace.DoesNotExist:
                pass
    
    return render(request, 'teams/team_form.html', {
        'form': form,
        'title': 'Create Team'
    })


@login_required
def team_edit(request, team_id):
    """Edit a team"""
    team = get_object_or_404(Team, id=team_id)
    
    if request.method == 'POST':
        form = TeamForm(request.POST, instance=team)
        if form.is_valid():
            old_name = team.name
            team = form.save()
            log_audit_event(request, 'TEAM_UPDATE', team, {
                'name': {'old': old_name, 'new': team.name}
            })
            messages.success(request, f'Team "{team.name}" updated successfully.')
            return redirect('team_list')
    else:
        form = TeamForm(instance=team)
    
    return render(request, 'teams/team_form.html', {
        'form': form,
        'team': team,
        'title': 'Edit Team'
    })


@login_required
def team_delete(request, team_id):
    """Delete a team"""
    team = get_object_or_404(Team, id=team_id)
    
    if request.method == 'POST':
        team_name = team.name
        log_audit_event(request, 'TEAM_DELETE', team, {'name': team_name})
        team.delete()
        messages.success(request, f'Team "{team_name}" deleted successfully.')
        return redirect('team_list')
    
    return render(request, 'teams/team_confirm_delete.html', {
        'team': team
    })


@login_required
def team_detail(request, team_id):
    """View team details with members"""
    team = get_object_or_404(Team.objects.prefetch_related('members', 'products'), id=team_id)
    
    return render(request, 'teams/team_detail.html', {
        'team': team
    })

