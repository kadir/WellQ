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
    try:
        teams = Team.objects.select_related('workspace').prefetch_related('members').annotate(
            member_count=Count('members')
        ).order_by('workspace__name', 'name')
        
        # Filter by workspace if provided
        workspace_id = request.GET.get('workspace')
        if workspace_id:
            try:
                workspace = Workspace.objects.get(id=workspace_id)
                teams = teams.filter(workspace=workspace)
            except (Workspace.DoesNotExist, ValueError, TypeError):
                # Invalid workspace ID, just ignore the filter
                workspace_id = None
        
        workspaces = Workspace.objects.all().order_by('name')
        
        # Convert workspace_id to string for template comparison
        selected_workspace_str = str(workspace_id) if workspace_id else None
        
        return render(request, 'teams/team_list.html', {
            'teams': teams,
            'workspaces': workspaces,
            'selected_workspace': selected_workspace_str
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in team_list view: {str(e)}", exc_info=True)
        messages.error(request, f"An error occurred while loading teams: {str(e)}")
        # Return empty context to prevent template errors
        try:
            workspaces = Workspace.objects.all().order_by('name')
        except Exception:
            workspaces = Workspace.objects.none()
        
        return render(request, 'teams/team_list.html', {
            'teams': Team.objects.none(),
            'workspaces': workspaces,
            'selected_workspace': None
        })


@login_required
def team_create(request):
    """Create a new team"""
    initial = {}
    workspace_id = request.GET.get('workspace')
    if workspace_id:
        initial['workspace'] = workspace_id
    
    if request.method == 'POST':
        form = TeamForm(request.POST, initial=initial)
        
        # Filter members by workspace from POST data if provided (before validation)
        workspace_id = request.POST.get('workspace')
        if workspace_id:
            from core.models import UserProfile
            try:
                # Update queryset before validation
                workspace_users = get_user_model().objects.filter(
                    profile__current_workspace_id=workspace_id
                ).distinct()
                form.fields['members'].queryset = workspace_users
            except (ValueError, TypeError):
                # Invalid workspace ID, set empty queryset
                form.fields['members'].queryset = get_user_model().objects.none()
        else:
            # No workspace selected, set empty queryset
            form.fields['members'].queryset = get_user_model().objects.none()
        
        if form.is_valid():
            team = form.save()
            log_audit_event(request, 'TEAM_CREATE', team, {
                'name': team.name,
                'members': [member.username for member in team.members.all()]
            })
            messages.success(request, f'Team "{team.name}" created successfully.')
            return redirect('team_list')
        else:
            # If form is invalid, still filter members by workspace if provided
            if workspace_id:
                from core.models import UserProfile
                try:
                    workspace_users = get_user_model().objects.filter(
                        profile__current_workspace_id=workspace_id
                    ).distinct()
                    form.fields['members'].queryset = workspace_users
                except (ValueError, TypeError):
                    form.fields['members'].queryset = get_user_model().objects.none()
    else:
        form = TeamForm(initial=initial)
        # Filter members by workspace if provided
        if initial.get('workspace'):
            from core.models import UserProfile
            try:
                workspace_users = get_user_model().objects.filter(
                    profile__current_workspace_id=initial['workspace']
                ).distinct()
                form.fields['members'].queryset = workspace_users
            except (ValueError, TypeError):
                form.fields['members'].queryset = get_user_model().objects.none()
    
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
        
        # Filter members by team's workspace
        if team.workspace:
            from core.models import UserProfile
            workspace_users = get_user_model().objects.filter(
                profile__current_workspace=team.workspace
            ).distinct()
            form.fields['members'].queryset = workspace_users
        
        if form.is_valid():
            old_name = team.name
            old_members = set(team.members.all())
            team = form.save()
            new_members = set(team.members.all())
            log_audit_event(request, 'TEAM_UPDATE', team, {
                'name': {'old': old_name, 'new': team.name},
                'members': {
                    'old': [m.username for m in old_members],
                    'new': [m.username for m in new_members]
                }
            })
            messages.success(request, f'Team "{team.name}" updated successfully.')
            return redirect('team_list')
    else:
        form = TeamForm(instance=team)
        # Filter members by team's workspace
        if team.workspace:
            from core.models import UserProfile
            workspace_users = get_user_model().objects.filter(
                profile__current_workspace=team.workspace
            ).distinct()
            form.fields['members'].queryset = workspace_users
    
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

