from rest_framework import serializers
from core.models import Workspace, Product, Release, Scan, Finding, Artifact
from core.scanners import SCANNER_REGISTRY


class WorkspaceSerializer(serializers.ModelSerializer):
    """Serializer for Workspace model"""
    class Meta:
        model = Workspace
        fields = ['id', 'name', 'description', 'slug', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for Product model"""
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'workspace', 'workspace_name', 'name', 'description',
            'product_type', 'criticality', 'tags', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ReleaseSerializer(serializers.ModelSerializer):
    """Serializer for Release model"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = Release
        fields = [
            'id', 'product', 'product_name', 'name', 'commit_hash',
            'sbom_file', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ScanSerializer(serializers.ModelSerializer):
    """Serializer for Scan model"""
    release_name = serializers.CharField(source='release.name', read_only=True)
    product_name = serializers.CharField(source='release.product.name', read_only=True)
    findings_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Scan
        fields = [
            'id', 'release', 'release_name', 'product_name',
            'scanner_name', 'started_at', 'findings_count'
        ]
        read_only_fields = ['id', 'started_at']
    
    def get_findings_count(self, obj):
        """Calculate the number of findings for this scan"""
        return obj.findings.count()


class FindingSerializer(serializers.ModelSerializer):
    """Serializer for Finding model"""
    scan_scanner = serializers.CharField(source='scan.scanner_name', read_only=True)
    release_name = serializers.CharField(source='scan.release.name', read_only=True)
    product_name = serializers.CharField(source='scan.release.product.name', read_only=True)
    
    class Meta:
        model = Finding
        fields = [
            'id', 'scan', 'scan_scanner', 'release_name', 'product_name',
            'title', 'description', 'severity', 'finding_type',
            'vulnerability_id', 'package_name', 'package_version', 'fix_version',
            'file_path', 'line_number', 'metadata',
            'status', 'triage_note', 'triage_by', 'triage_at',
            'hash_id', 'first_seen', 'last_seen'
        ]
        read_only_fields = [
            'id', 'hash_id', 'first_seen', 'last_seen'
        ]


class ScanUploadSerializer(serializers.Serializer):
    """
    Serializer for uploading scan results.
    Accepts scan JSON file and metadata to create/update scans and findings.
    
    NEW BOM Architecture: Supports artifact-based scanning.
    - artifact_name + artifact_version: Scan an artifact directly (recommended)
    - product_name + release_name: Legacy mode (backward compatibility)
    """
    workspace_id = serializers.UUIDField(
        help_text="UUID of the workspace"
    )
    
    # NEW: Artifact-based fields (recommended for BOM architecture)
    artifact_name = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        help_text="Name of the artifact (e.g., 'payment-service-image'). Required if using artifact-based scanning."
    )
    artifact_version = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        help_text="Version of the artifact (e.g., 'sha256:a1b2...' or 'v1.0.5'). Required if using artifact-based scanning."
    )
    artifact_type = serializers.ChoiceField(
        choices=[
            ('CONTAINER', 'Container Image'),
            ('LIBRARY', 'Library'),
            ('PACKAGE', 'Package'),
            ('BINARY', 'Binary Executable'),
        ],
        default='CONTAINER',
        required=False,
        help_text="Type of artifact (defaults to CONTAINER)"
    )
    repository_name = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        help_text="Optional repository name (e.g., 'payment-service')"
    )
    repository_url = serializers.URLField(
        required=False,
        allow_blank=True,
        help_text="Optional repository URL (e.g., 'https://github.com/acme/payment')"
    )
    
    # LEGACY: Product/Release fields (for backward compatibility)
    product_name = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        help_text="Name of the product (legacy mode, will be created if doesn't exist)"
    )
    release_name = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        help_text="Version/release name (legacy mode, e.g., 'v1.2.0')"
    )
    
    scanner_name = serializers.ChoiceField(
        choices=list(SCANNER_REGISTRY.keys()),
        help_text="Name of the scanner that generated the results"
    )
    scan_file = serializers.FileField(
        help_text="JSON file containing scan results (format depends on scanner)",
        allow_empty_file=False
    )
    
    def validate_scan_file(self, value):
        """Validate scan file with comprehensive security checks"""
        from core.utils.security import validate_json_file
        
        is_valid, error_msg = validate_json_file(value, max_size_mb=100)
        if not is_valid:
            raise serializers.ValidationError(error_msg)
        
        return value
    
    def validate(self, data):
        """Validate that either artifact fields OR product/release fields are provided"""
        artifact_name = data.get('artifact_name', '').strip()
        artifact_version = data.get('artifact_version', '').strip()
        product_name = data.get('product_name', '').strip()
        release_name = data.get('release_name', '').strip()
        
        # Check if using artifact-based mode
        has_artifact = artifact_name and artifact_version
        # Check if using legacy mode
        has_legacy = product_name and release_name
        
        if not has_artifact and not has_legacy:
            raise serializers.ValidationError(
                "Either (artifact_name + artifact_version) OR (product_name + release_name) must be provided."
            )
        
        return data
    
    commit_hash = serializers.CharField(
        max_length=64,
        required=False,
        allow_blank=True,
        help_text="Optional Git commit hash for the release"
    )
    product_type = serializers.ChoiceField(
        choices=Product.PRODUCT_TYPES,
        default='WEB',
        required=False,
        help_text="Type of product (defaults to WEB, legacy mode only)"
    )
    product_criticality = serializers.ChoiceField(
        choices=Product.IMPACT_CHOICES,
        default='MEDIUM',
        required=False,
        help_text="Criticality level of the product (defaults to MEDIUM, legacy mode only)"
    )

    def validate_workspace_id(self, value):
        """Validate that workspace exists"""
        try:
            Workspace.objects.get(id=value)
        except Workspace.DoesNotExist:
            raise serializers.ValidationError("Workspace with this ID does not exist.")
        return value

    def validate_scanner_name(self, value):
        """Validate that scanner is supported"""
        if value not in SCANNER_REGISTRY:
            raise serializers.ValidationError(
                f"Scanner '{value}' is not supported. Available scanners: {', '.join(SCANNER_REGISTRY.keys())}"
            )
        return value


class SBOMUploadSerializer(serializers.Serializer):
    """
    Serializer for uploading SBOM files.
    Accepts SBOM JSON file and metadata to create/update releases and components.
    """
    workspace_id = serializers.UUIDField(
        help_text="UUID of the workspace"
    )
    product_name = serializers.CharField(
        max_length=200,
        help_text="Name of the product (will be created if doesn't exist)"
    )
    release_name = serializers.CharField(
        max_length=100,
        help_text="Version/release name (e.g., 'v1.2.0')"
    )
    sbom_file = serializers.FileField(
        help_text="SBOM JSON file (CycloneDX format)",
        allow_empty_file=False
    )
    
    def validate_sbom_file(self, value):
        """Validate SBOM file with comprehensive security checks"""
        from core.utils.security import validate_json_file
        
        is_valid, error_msg = validate_json_file(value, max_size_mb=50)
        if not is_valid:
            raise serializers.ValidationError(error_msg)
        
        return value
    commit_hash = serializers.CharField(
        max_length=64,
        required=False,
        allow_blank=True,
        help_text="Optional Git commit hash for the release"
    )
    product_type = serializers.ChoiceField(
        choices=Product.PRODUCT_TYPES,
        default='WEB',
        required=False,
        help_text="Type of product (defaults to WEB)"
    )
    product_criticality = serializers.ChoiceField(
        choices=Product.IMPACT_CHOICES,
        default='MEDIUM',
        required=False,
        help_text="Criticality level of the product (defaults to MEDIUM)"
    )

    def validate_workspace_id(self, value):
        """Validate that workspace exists"""
        try:
            Workspace.objects.get(id=value)
        except Workspace.DoesNotExist:
            raise serializers.ValidationError("Workspace with this ID does not exist.")
        return value

