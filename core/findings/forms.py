from django import forms
from .models import Workspace, Product, Release
from core.scanners import SCANNER_REGISTRY

# --- WORKSPACE FORM ---
class WorkspaceForm(forms.ModelForm):
    class Meta:
        model = Workspace
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'cra-input', 'placeholder': 'e.g. Engineering Team'}),
            'description': forms.Textarea(attrs={'class': 'cra-input', 'rows': 3, 'placeholder': 'Brief description...'}),
        }

# --- PRODUCT FORM ---
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['workspace', 'name', 'description', 'product_type', 'criticality']
        widgets = {
            'workspace': forms.Select(attrs={'class': 'cra-input'}),
            'name': forms.TextInput(attrs={'class': 'cra-input', 'placeholder': 'e.g. Payment-Gateway'}),
            'description': forms.Textarea(attrs={'class': 'cra-input', 'rows': 4}),
            'product_type': forms.Select(attrs={'class': 'cra-input'}),
            'criticality': forms.Select(attrs={'class': 'cra-input'}),
        }

# --- RELEASE FORM ---
class ReleaseForm(forms.ModelForm):
    class Meta:
        model = Release
        fields = ['name', 'commit_hash', 'sbom_file']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'cra-input', 'placeholder': 'e.g. v1.2.0'}),
            'commit_hash': forms.TextInput(attrs={'class': 'cra-input', 'placeholder': 'e.g. 7b3f1a2 (Git SHA)'}),
            'sbom_file': forms.FileInput(attrs={'class': 'block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-zinc-100 file:text-zinc-900 hover:file:bg-white cursor-pointer'}),
        }

# --- SCAN INGEST FORM (Merged & Fixed) ---
class ScanIngestForm(forms.Form):
    # 1. Workspace
    workspace = forms.ModelChoiceField(
        queryset=Workspace.objects.all(),
        empty_label="Select Workspace",
        widget=forms.Select(attrs={'class': 'cra-input'})
    )

    # 2. Product Name
    product_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'cra-input', 'placeholder': 'e.g. Payment-Gateway'})
    )

    # 3. Release Name
    release_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'cra-input', 'placeholder': 'e.g. v1.2.0'})
    )

    # 4. Scanner Name (Dynamic Dropdown from Registry)
    scanner_name = forms.ChoiceField(
        choices=[(k, k) for k in SCANNER_REGISTRY.keys()],
        widget=forms.Select(attrs={'class': 'cra-input'})
    )

    # 5. File Upload
    file_upload = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-zinc-100 file:text-zinc-900 hover:file:bg-white cursor-pointer'
        })
    )