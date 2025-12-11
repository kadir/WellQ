from django import forms
from core.models import Workspace, Product, Release, Role, PlatformSettings, Repository, Artifact, Team
from core.scanners import SCANNER_REGISTRY
from django.contrib.auth.forms import UserChangeForm, PasswordChangeForm as DjangoPasswordChangeForm
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


# Workspace Form
class WorkspaceForm(forms.ModelForm):
    class Meta:
        model = Workspace
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'cra-input'}),
            'description': forms.Textarea(attrs={'class': 'cra-input', 'rows': 4}),
        }


# Product Form
class ProductForm(forms.ModelForm):
    teams = forms.ModelMultipleChoiceField(
        queryset=Team.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'cra-input', 'size': '5'}),
        help_text="Assign teams responsible for this product"
    )
    
    class Meta:
        model = Product
        fields = ['name', 'product_type', 'workspace', 'description', 'criticality']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'cra-input'}),
            'product_type': forms.Select(attrs={'class': 'cra-input'}),
            'workspace': forms.Select(attrs={'class': 'cra-input'}),
            'description': forms.Textarea(attrs={'class': 'cra-input', 'rows': 4}),
            'criticality': forms.Select(attrs={'class': 'cra-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', {})
        super().__init__(*args, **kwargs)
        # Filter teams by workspace
        if self.instance and self.instance.pk and self.instance.workspace:
            # Existing product - filter by its workspace
            self.fields['teams'].queryset = Team.objects.filter(workspace=self.instance.workspace)
            self.fields['teams'].initial = self.instance.teams.all()
        elif initial.get('workspace'):
            # New product with workspace in initial data
            workspace_id = initial['workspace']
            self.fields['teams'].queryset = Team.objects.filter(workspace_id=workspace_id)
        else:
            # No workspace yet - show all teams (will be filtered when workspace is selected)
            self.fields['teams'].queryset = Team.objects.all()
    
    def clean(self):
        cleaned_data = super().clean()
        # Filter teams by the selected workspace to ensure security
        workspace = cleaned_data.get('workspace')
        teams = cleaned_data.get('teams', [])
        
        if workspace and teams:
            # teams is a queryset from ModelMultipleChoiceField
            # Ensure all selected teams belong to the selected workspace
            team_ids = [t.id for t in teams]
            valid_teams = Team.objects.filter(workspace=workspace, id__in=team_ids)
            if valid_teams.count() != len(team_ids):
                raise forms.ValidationError("All selected teams must belong to the selected workspace.")
            cleaned_data['teams'] = list(valid_teams)
        elif teams and not workspace:
            # If teams are selected but no workspace, clear teams
            cleaned_data['teams'] = []
        
        return cleaned_data
    
    def save(self, commit=True):
        # Get teams before saving (if any)
        teams_data = self.cleaned_data.get('teams', []) if hasattr(self, 'cleaned_data') and self.cleaned_data else []
        
        product = super().save(commit=commit)
        
        if commit:
            # Handle teams assignment
            if teams_data:
                product.teams.set(teams_data)
            # Don't clear teams if not provided - let it be empty by default
        
        return product


# Release Form
class ReleaseForm(forms.ModelForm):
    class Meta:
        model = Release
        fields = ['name', 'commit_hash', 'sbom_file']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'cra-input'}),
            'commit_hash': forms.TextInput(attrs={'class': 'cra-input', 'placeholder': 'Git commit SHA (optional)'}),
            'sbom_file': forms.FileInput(attrs={'class': 'cra-input', 'accept': '.json'}),
        }


# Scan Ingest Form
class ScanIngestForm(forms.Form):
    workspace = forms.ModelChoiceField(
        queryset=Workspace.objects.all(),
        widget=forms.Select(attrs={'class': 'cra-input'}),
        required=True
    )
    product_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'cra-input'}),
        required=True
    )
    release_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'cra-input'}),
        required=True
    )
    scanner_name = forms.ChoiceField(
        choices=[(name, name) for name in SCANNER_REGISTRY.keys()],
        widget=forms.Select(attrs={'class': 'cra-input'}),
        required=True
    )
    file_upload = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'cra-input', 'accept': '.json'}),
        required=True
    )
    
    def clean_file_upload(self):
        """Validate uploaded file with comprehensive security checks"""
        from core.utils.security import validate_json_file
        
        file = self.cleaned_data.get('file_upload')
        if file:
            is_valid, error_msg = validate_json_file(file, max_size_mb=100)
            if not is_valid:
                raise forms.ValidationError(error_msg)
        
        return file


# Profile Update Form
class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'cra-input'}),
            'last_name': forms.TextInput(attrs={'class': 'cra-input'}),
            'email': forms.EmailInput(attrs={'class': 'cra-input'}),
        }


# Password Change Form
class PasswordChangeForm(DjangoPasswordChangeForm):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'cra-input'}),
        label='Current Password'
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'cra-input'}),
        label='New Password'
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'cra-input'}),
        label='Confirm New Password'
    )


# API Token Form
class APITokenForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'cra-input'}),
        required=True,
        help_text="A descriptive name for this token"
    )
    expires_at = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'class': 'cra-input', 'type': 'datetime-local'}),
        required=False,
        help_text="Optional expiration date (leave blank for no expiration)"
    )
    
    def clean_expires_at(self):
        expires_at = self.cleaned_data.get('expires_at')
        if expires_at and expires_at <= timezone.now():
            raise forms.ValidationError("Expiration date must be in the future.")
        return expires_at


# User Management Forms
class UserCreateForm(forms.ModelForm):
    """Form for creating new users"""
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'cra-input'}),
        help_text="Password must be at least 8 characters."
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'cra-input'}),
        help_text="Enter the same password as above, for verification."
    )
    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'space-y-2'}),
        help_text="Select roles for this user"
    )
    teams = forms.ModelMultipleChoiceField(
        queryset=Team.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'cra-input', 'size': '5'}),
        help_text="Assign user to teams (optional)"
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'cra-input'}),
            'email': forms.EmailInput(attrs={'class': 'cra-input'}),
            'first_name': forms.TextInput(attrs={'class': 'cra-input'}),
            'last_name': forms.TextInput(attrs={'class': 'cra-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-emerald-600 bg-zinc-900 border-zinc-700 rounded focus:ring-emerald-500'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-emerald-600 bg-zinc-900 border-zinc-700 rounded focus:ring-emerald-500'}),
        }
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match.")
        return password2
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
            # Assign roles
            if hasattr(user, 'profile'):
                user.profile.roles.set(self.cleaned_data['roles'])
            # Assign teams
            if 'teams' in self.cleaned_data:
                user.teams.set(self.cleaned_data['teams'])
        return user


class UserEditForm(forms.ModelForm):
    """Form for editing existing users"""
    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'space-y-2'}),
        help_text="Select roles for this user"
    )
    teams = forms.ModelMultipleChoiceField(
        queryset=Team.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'cra-input', 'size': '5'}),
        help_text="Assign user to teams (optional)"
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'cra-input'}),
            'email': forms.EmailInput(attrs={'class': 'cra-input'}),
            'first_name': forms.TextInput(attrs={'class': 'cra-input'}),
            'last_name': forms.TextInput(attrs={'class': 'cra-input'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-emerald-600 bg-zinc-900 border-zinc-700 rounded focus:ring-emerald-500'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-emerald-600 bg-zinc-900 border-zinc-700 rounded focus:ring-emerald-500'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove password field from UserChangeForm
        if 'password' in self.fields:
            del self.fields['password']
        
        # Set initial roles if user has a profile
        if self.instance and hasattr(self.instance, 'profile'):
            self.fields['roles'].initial = self.instance.profile.roles.all()
        
        # Set initial teams
        if self.instance:
            self.fields['teams'].initial = self.instance.teams.all()
    
    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            if hasattr(user, 'profile'):
                user.profile.roles.set(self.cleaned_data['roles'])
            # Assign teams
            if 'teams' in self.cleaned_data:
                user.teams.set(self.cleaned_data['teams'])
        return user


# Role Form
class RoleForm(forms.ModelForm):
    """Form for editing role permissions"""
    class Meta:
        model = Role
        fields = ['description', 'can_manage_users', 'can_manage_workspaces', 'can_manage_products',
                  'can_upload_scans', 'can_upload_sbom', 'can_triage_findings', 'can_view_all',
                  'can_export_data', 'can_manage_roles']
        widgets = {
            'description': forms.Textarea(attrs={'class': 'cra-input', 'rows': 3}),
            'can_manage_users': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-emerald-600 bg-zinc-900 border-zinc-700 rounded focus:ring-emerald-500'}),
            'can_manage_workspaces': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-emerald-600 bg-zinc-900 border-zinc-700 rounded focus:ring-emerald-500'}),
            'can_manage_products': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-emerald-600 bg-zinc-900 border-zinc-700 rounded focus:ring-emerald-500'}),
            'can_upload_scans': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-emerald-600 bg-zinc-900 border-zinc-700 rounded focus:ring-emerald-500'}),
            'can_upload_sbom': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-emerald-600 bg-zinc-900 border-zinc-700 rounded focus:ring-emerald-500'}),
            'can_triage_findings': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-emerald-600 bg-zinc-900 border-zinc-700 rounded focus:ring-emerald-500'}),
            'can_view_all': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-emerald-600 bg-zinc-900 border-zinc-700 rounded focus:ring-emerald-500'}),
            'can_export_data': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-emerald-600 bg-zinc-900 border-zinc-700 rounded focus:ring-emerald-500'}),
            'can_manage_roles': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-emerald-600 bg-zinc-900 border-zinc-700 rounded focus:ring-emerald-500'}),
        }


# Platform Settings Form
class PlatformSettingsForm(forms.ModelForm):
    """Form for platform settings (EPSS and KEV URLs)"""
    class Meta:
        model = PlatformSettings
        fields = ['epss_url', 'kev_url']
        widgets = {
            'epss_url': forms.URLInput(attrs={
                'class': 'cra-input',
                'placeholder': 'https://epss.empiricalsecurity.com/epss_scores-current.csv.gz'
            }),
            'kev_url': forms.URLInput(attrs={
                'class': 'cra-input',
                'placeholder': 'https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json'
            }),
        }
        help_texts = {
            'epss_url': 'URL for EPSS scores CSV (gzipped). Only http/https URLs are allowed.',
            'kev_url': 'URL for CISA KEV JSON feed. Only http/https URLs are allowed.',
        }
    
    def clean(self):
        """Validate URLs to prevent SSRF"""
        cleaned_data = super().clean()
        # Model's clean() method will handle URL validation
        return cleaned_data


# Team Form
class TeamForm(forms.ModelForm):
    """Form for creating/editing teams"""
    class Meta:
        model = Team
        fields = ['workspace', 'name', 'description']
        widgets = {
            'workspace': forms.Select(attrs={'class': 'cra-input'}),
            'name': forms.TextInput(attrs={'class': 'cra-input'}),
            'description': forms.Textarea(attrs={'class': 'cra-input', 'rows': 4}),
        }


# Repository Form
class RepositoryForm(forms.ModelForm):
    """Form for creating/editing repositories"""
    class Meta:
        model = Repository
        fields = ['name', 'url', 'workspace']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full bg-black border border-zinc-700 rounded p-2 text-white',
                'placeholder': 'e.g. backend-api'
            }),
            'url': forms.URLInput(attrs={
                'class': 'w-full bg-black border border-zinc-700 rounded p-2 text-white',
                'placeholder': 'https://github.com/org/repo'
            }),
            'workspace': forms.Select(attrs={
                'class': 'w-full bg-black border border-zinc-700 rounded p-2 text-white'
            }),
        }


# Release Composer Form (BOM Builder)
class ReleaseComposerForm(forms.ModelForm):
    """Form for composing a release with artifacts (BOM Builder)"""
    artifact_ids = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text="Comma-separated list of artifact IDs"
    )
    
    class Meta:
        model = Release
        fields = ['name', 'commit_hash']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full bg-black border border-zinc-700 text-white p-3 rounded',
                'placeholder': 'v1.5.0-production'
            }),
            'commit_hash': forms.TextInput(attrs={
                'class': 'w-full bg-black border border-zinc-700 text-white p-3 rounded',
                'placeholder': 'Git commit SHA (optional)'
            }),
        }
    
    def clean_artifact_ids(self):
        """Validate and parse artifact IDs"""
        artifact_ids_str = self.cleaned_data.get('artifact_ids', '')
        if not artifact_ids_str:
            return []
        
        # Parse comma-separated IDs
        try:
            artifact_ids = [uuid.UUID(id.strip()) for id in artifact_ids_str.split(',') if id.strip()]
            # Verify artifacts exist
            existing_count = Artifact.objects.filter(id__in=artifact_ids).count()
            if existing_count != len(artifact_ids):
                raise forms.ValidationError("One or more artifacts not found.")
            return artifact_ids
        except (ValueError, TypeError) as e:
            raise forms.ValidationError(f"Invalid artifact ID format: {str(e)}")
