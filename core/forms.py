from django import forms
from core.models import Workspace, Product, Release, Role, PlatformSettings
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
        return user


class UserEditForm(forms.ModelForm):
    """Form for editing existing users"""
    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'space-y-2'}),
        help_text="Select roles for this user"
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
    
    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit and hasattr(user, 'profile'):
            user.profile.roles.set(self.cleaned_data['roles'])
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
