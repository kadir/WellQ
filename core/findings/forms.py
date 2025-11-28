from django import forms
from .models import Workspace, Product, Release
from core.scanners import SCANNER_REGISTRY

class WorkspaceForm(forms.ModelForm):
    class Meta:
        model = Workspace
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                # ONLY use the class name. No Tailwind clutter.
                'class': 'cra-input', 
                'placeholder': 'e.g. Engineering Team'
            }),
            'description': forms.Textarea(attrs={
                'class': 'cra-input', 
                'rows': 3,
                'placeholder': 'Brief description of this workspace...'
            }),
        }

class ScanIngestForm(forms.Form):
    workspace = forms.ModelChoiceField(
        queryset=Workspace.objects.all(),
        empty_label="Select Workspace",
        widget=forms.Select(attrs={'class': 'cra-input'})
    )

    product_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'cra-input',
            'placeholder': 'e.g. Payment-Service'
        })
    )

    release_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'cra-input',
            'placeholder': 'e.g. v1.2.0'
        })
    )

    scanner_name = forms.CharField(
        initial="Trivy",
        widget=forms.TextInput(attrs={'class': 'cra-input'})
    )

    file_upload = forms.FileField(
        widget=forms.FileInput(attrs={
            # File inputs are tricky, we keep some tailwind for the "Browse" button part
            'class': 'block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-zinc-100 file:text-zinc-900 hover:file:bg-white cursor-pointer'
        })
    )

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['workspace', 'name', 'description', 'product_type', 'criticality'] # Added product_type
        widgets = {
            'workspace': forms.Select(attrs={'class': 'cra-input'}),
            'name': forms.TextInput(attrs={'class': 'cra-input', 'placeholder': 'e.g. Payment-Gateway'}),
            'description': forms.Textarea(attrs={'class': 'cra-input', 'rows': 4}),
            
            # NEW: Dropdown for Icon Type
            'product_type': forms.Select(attrs={'class': 'cra-input'}),
            
            'criticality': forms.Select(attrs={'class': 'cra-input'}),
        }

class ReleaseForm(forms.ModelForm):
    class Meta:
        model = Release
        fields = ['name', 'commit_hash', 'sbom_file']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'cra-input', 
                'placeholder': 'e.g. v1.2.0'
            }),
            'commit_hash': forms.TextInput(attrs={
                'class': 'cra-input', 
                'placeholder': 'e.g. 7b3f1a2 (Git SHA)'
            }),
            # Styled File Input
            'sbom_file': forms.FileInput(attrs={
                 'class': 'block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-zinc-100 file:text-zinc-900 hover:file:bg-white cursor-pointer'
            }),
        }

class ScanIngestForm(forms.Form):
    # ... (keep workspace, product_name, release_name as they were) ...
    # Copy paste the top part from previous steps
    
    # CHANGED: Scanner Name is now a Dynamic Dropdown
    scanner_name = forms.ChoiceField(
        choices=[(k, k) for k in SCANNER_REGISTRY.keys()], # Auto-fill from registry
        widget=forms.Select(attrs={'class': 'cra-input'})
    )