from rest_framework import serializers
from core.models import Workspace, Product, Release, Scan, Finding, Artifact, Repository, AuditLog, Team
from core.scanners import SCANNER_REGISTRY
from django.db.models import Count
from django.contrib.auth import get_user_model

User = get_user_model()


class WorkspaceSerializer(serializers.ModelSerializer):
    """Serializer for Workspace model"""
    class Meta:
        model = Workspace
        fields = ['id', 'name', 'description', 'slug', 'created_at']
        read_only_fields = ['id', 'slug', 'created_at']


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for Product model"""
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    team_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Team.objects.all(),
        source='teams',
        required=False,
        allow_empty=True
    )
    team_names = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'workspace', 'workspace_name', 'name', 'description',
            'product_type', 'criticality', 'tags', 'team_ids', 'team_names', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_team_names(self, obj):
        return [team.name for team in obj.teams.all()]


class RepositorySerializer(serializers.ModelSerializer):
    """Serializer for Repository model"""
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    artifacts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Repository
        fields = [
            'id', 'workspace', 'workspace_name', 'name', 'url', 'created_at', 'artifacts_count'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_artifacts_count(self, obj):
        """Get count of artifacts in this repository"""
        return obj.artifacts.count()


class ArtifactSerializer(serializers.ModelSerializer):
    """Serializer for Artifact model"""
    repository_name = serializers.CharField(source='repository.name', read_only=True)
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    scans_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Artifact
        fields = [
            'id', 'repository', 'repository_name', 'workspace', 'workspace_name',
            'name', 'version', 'type', 'created_at', 'scans_count'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_scans_count(self, obj):
        """Get count of scans for this artifact"""
        return obj.scan_set.count()


class ReleaseSerializer(serializers.ModelSerializer):
    """Serializer for Release model"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    stats = serializers.SerializerMethodField()
    artifacts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Release
        fields = [
            'id', 'product', 'product_name', 'name', 'commit_hash',
            'sbom_file', 'created_at', 'stats', 'artifacts_count'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_artifacts_count(self, obj):
        """Get count of artifacts linked to this release"""
        return obj.artifacts.count()
    
    def get_stats(self, obj):
        """
        Calculate risk statistics dynamically from all artifacts linked to this release.
        This implements Requirement 4: Risk Aggregation Service.
        """
        from core.models import Finding
        from django.db.models import Q, Count
        
        # Get all artifacts linked to this release
        artifacts = obj.artifacts.all()
        
        if not artifacts.exists():
            # Legacy mode: check if release has direct scans
            findings = Finding.objects.filter(scan__release=obj)
        else:
            # BOM mode: get findings from all scans of linked artifacts
            # Get latest scan for each artifact
            artifact_ids = artifacts.values_list('id', flat=True)
            findings = Finding.objects.filter(
                scan__artifact_id__in=artifact_ids
            )
        
        # Filter to only OPEN findings (exclude FIXED, WONT_FIX, etc.)
        active_findings = findings.filter(status='OPEN')
        
        # Aggregate by severity
        stats = active_findings.aggregate(
            critical=Count('id', filter=Q(severity='CRITICAL')),
            high=Count('id', filter=Q(severity='HIGH')),
            medium=Count('id', filter=Q(severity='MEDIUM')),
            low=Count('id', filter=Q(severity='LOW')),
            info=Count('id', filter=Q(severity='INFO')),
            total=Count('id')
        )
        
        return {
            'critical': stats['critical'] or 0,
            'high': stats['high'] or 0,
            'medium': stats['medium'] or 0,
            'low': stats['low'] or 0,
            'info': stats['info'] or 0,
            'total': stats['total'] or 0
        }


class ScanSerializer(serializers.ModelSerializer):
    """Serializer for Scan model"""
    release_name = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()
    artifact_name = serializers.SerializerMethodField()
    artifact_version = serializers.SerializerMethodField()
    findings_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Scan
        fields = [
            'id', 'release', 'release_name', 'product_name',
            'artifact', 'artifact_name', 'artifact_version',
            'scanner_name', 'started_at', 'status', 'findings_count'
        ]
        read_only_fields = ['id', 'started_at']
    
    def get_release_name(self, obj):
        """Get release name if scan is linked to a release (legacy mode)"""
        return obj.release.name if obj.release else None
    
    def get_product_name(self, obj):
        """Get product name if scan is linked to a release (legacy mode)"""
        return obj.release.product.name if obj.release and obj.release.product else None
    
    def get_artifact_name(self, obj):
        """Get artifact name if scan is linked to an artifact (BOM mode)"""
        return obj.artifact.name if obj.artifact else None
    
    def get_artifact_version(self, obj):
        """Get artifact version if scan is linked to an artifact (BOM mode)"""
        return obj.artifact.version if obj.artifact else None
    
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


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for AuditLog model (Read-only)"""
    actor_username = serializers.CharField(source='actor.username', read_only=True)
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'workspace', 'workspace_name', 'actor', 'actor_username',
            'actor_email', 'action', 'resource_type', 'resource_id',
            'changes', 'ip_address', 'user_agent', 'timestamp'
        ]
        read_only_fields = '__all__'  # All fields are read-only


class TeamMemberSerializer(serializers.ModelSerializer):
    """Serializer for team members (User model)"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class TeamSerializer(serializers.ModelSerializer):
    """Serializer for Team model"""
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    member_count = serializers.SerializerMethodField()
    members = TeamMemberSerializer(many=True, read_only=True)
    
    class Meta:
        model = Team
        fields = [
            'id', 'workspace', 'workspace_name', 'name', 'description',
            'members', 'member_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_member_count(self, obj):
        return obj.members.count()

