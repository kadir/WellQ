from django import forms
from .models import Workspace

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