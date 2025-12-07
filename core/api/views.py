from rest_framework import status, viewsets, filters
from rest_framework.decorators import api_view, permission_classes, action, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle, ScopedRateThrottle
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from core.models import Workspace, Product, Release, Scan, Finding, Component, Repository, Artifact


# Custom throttle class for upload endpoints
class UploadRateThrottle(ScopedRateThrottle):
    """Throttle class for upload endpoints with 'upload' scope."""
    scope_attr = 'throttle_scope'
    
    def get_scope(self):
        return 'upload'
from core.api.serializers import (
    WorkspaceSerializer, ProductSerializer, ReleaseSerializer,
    ScanSerializer, FindingSerializer, ScanUploadSerializer, SBOMUploadSerializer,
    RepositorySerializer, ArtifactSerializer
)
from core.services.scan_engine import process_scan_upload
from core.services.sbom import digest_sbom
from core.tasks import process_scan_async, process_sbom_async
from django.http import JsonResponse
import base64


@extend_schema(
    tags=['Scan Upload'],
    summary='Upload scan results',
    description='Upload scan results from a security scanner. This endpoint automatically creates product and release if they don\'t exist, then processes the scan file to create/update findings.',
    request=ScanUploadSerializer,
    responses={
        201: {
            'description': 'Scan uploaded and processed successfully',
            'content': {
                'application/json': {
                    'example': {
                        'success': True,
                        'message': 'Scan uploaded and processed successfully',
                        'scan_id': '550e8400-e29b-41d4-a716-446655440000',
                        'release_id': '550e8400-e29b-41d4-a716-446655440001',
                        'product_id': '550e8400-e29b-41d4-a716-446655440002',
                        'findings_count': 42,
                        'new_findings': 15,
                        'updated_findings': 27
                    }
                }
            }
        },
        400: {'description': 'Invalid request data'},
        404: {'description': 'Workspace not found'},
    },
    examples=[
        OpenApiExample(
            'Trivy Scan Upload',
            value={
                'workspace_id': '550e8400-e29b-41d4-a716-446655440000',
                'product_name': 'payment-gateway',
                'release_name': 'v1.2.0',
                'scanner_name': 'Trivy',
                'scan_file': '<file>',
                'commit_hash': '7b3f1a2c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2',
                'product_type': 'WEB',
                'product_criticality': 'HIGH'
            },
            request_only=True
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([UploadRateThrottle])
def upload_scan(request):
    """
    Upload and process scan results.
    
    This endpoint automatically creates product and release if they don't exist:
    1. Creates or retrieves the workspace
    2. Creates or retrieves the product (creates if doesn't exist)
    3. Creates or retrieves the release (creates if doesn't exist)
    4. Creates a new scan record
    5. Processes the scan file to extract findings
    6. Deduplicates findings using hash-based fingerprinting
    7. Updates existing findings or creates new ones
    
    Supported scanners: Trivy, Trufflehog, JFrog Xray (more can be added)
    """
    serializer = ScanUploadSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'success': False, 'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    validated_data = serializer.validated_data
    
    # Get or create workspace
    workspace = get_object_or_404(Workspace, id=validated_data['workspace_id'])
    
    # NEW BOM Architecture: Check if using artifact-based or legacy mode
    artifact_name = validated_data.get('artifact_name', '').strip()
    artifact_version = validated_data.get('artifact_version', '').strip()
    
    scan = None
    artifact = None
    release = None
    product = None
    product_created = False
    release_created = False
    artifact_created = False
    
    if artifact_name and artifact_version:
        # NEW: Artifact-based scanning (BOM architecture)
        from core.services.artifact import upsert_artifact, get_or_create_scan_for_artifact
        
        # Upsert artifact
        artifact, artifact_created, _ = upsert_artifact(
            workspace=workspace,
            artifact_name=artifact_name,
            artifact_version=artifact_version,
            artifact_type=validated_data.get('artifact_type', 'CONTAINER'),
            repository_name=validated_data.get('repository_name', '').strip() or None,
            repository_url=validated_data.get('repository_url', '').strip() or None
        )
        
        # Get or create scan for artifact (with deduplication)
        scan, is_new_scan = get_or_create_scan_for_artifact(
            artifact=artifact,
            scanner_name=validated_data['scanner_name']
        )
        
    else:
        # LEGACY: Product/Release-based scanning (backward compatibility)
        product_name = validated_data.get('product_name', '').strip()
        release_name = validated_data.get('release_name', '').strip()
        
        # Get or create product
        product, product_created = Product.objects.get_or_create(
            name=product_name,
            workspace=workspace,
            defaults={
                'product_type': validated_data.get('product_type', 'WEB'),
                'criticality': validated_data.get('product_criticality', 'MEDIUM')
            }
        )
        
        # Get or create release
        release, release_created = Release.objects.get_or_create(
            name=release_name,
            product=product,
            defaults={
                'commit_hash': validated_data.get('commit_hash', '')
            }
        )
        
        # Update commit hash if provided and release already existed
        if not release_created and validated_data.get('commit_hash'):
            release.commit_hash = validated_data['commit_hash']
            release.save()
        
        # Create scan with PENDING status (legacy mode)
        scan = Scan.objects.create(
            release=release,
            scanner_name=validated_data['scanner_name'],
            status='PENDING'
        )
    
    # Read file content for async processing
    scan_file = validated_data['scan_file']
    scan_file.seek(0)
    file_content = scan_file.read()
    file_name = scan_file.name
    
    # Queue async task for processing
    task = process_scan_async.delay(
        str(scan.id),
        base64.b64encode(file_content).decode('utf-8'),
        file_name
    )
    
    response_data = {
        'success': True,
        'message': 'Scan uploaded and queued for processing',
        'scan_id': str(scan.id),
        'task_id': task.id,
        'status': 'PENDING',
    }
    
    # Add artifact info if using BOM architecture
    if artifact:
        response_data.update({
            'artifact_id': str(artifact.id),
            'artifact_name': artifact.name,
            'artifact_version': artifact.version,
            'artifact_created': artifact_created,
        })
    
    # Add legacy info if using product/release mode
    if release and product:
        response_data.update({
            'release_id': str(release.id),
            'product_id': str(product.id),
            'product_created': product_created,
            'release_created': release_created,
        })
    
    return Response(response_data, status=status.HTTP_202_ACCEPTED)


@extend_schema(
    tags=['SBOM'],
    summary='Upload SBOM file',
    description='Upload a Software Bill of Materials (SBOM) file. This endpoint automatically creates product and release if they don\'t exist, then processes the SBOM to extract components.',
    request=SBOMUploadSerializer,
    responses={
        201: {
            'description': 'SBOM uploaded and processed successfully',
            'content': {
                'application/json': {
                    'example': {
                        'success': True,
                        'message': 'SBOM uploaded and processed successfully',
                        'release_id': '550e8400-e29b-41d4-a716-446655440001',
                        'product_id': '550e8400-e29b-41d4-a716-446655440002',
                        'components_count': 150,
                        'product_created': True,
                        'release_created': True
                    }
                }
            }
        },
        400: {'description': 'Invalid request data'},
        404: {'description': 'Workspace not found'},
    },
    examples=[
        OpenApiExample(
            'CycloneDX SBOM Upload',
            value={
                'workspace_id': '550e8400-e29b-41d4-a716-446655440000',
                'product_name': 'payment-gateway',
                'release_name': 'v1.2.0',
                'sbom_file': '<file>',
                'commit_hash': '7b3f1a2c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2',
                'product_type': 'WEB',
                'product_criticality': 'HIGH'
            },
            request_only=True
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([UploadRateThrottle])
def upload_sbom(request):
    """
    Upload and process SBOM file.
    
    This endpoint automatically creates product and release if they don't exist:
    1. Creates or retrieves the workspace
    2. Creates or retrieves the product (creates if doesn't exist)
    3. Creates or retrieves the release (creates if doesn't exist)
    4. Uploads and stores the SBOM file
    5. Processes the SBOM to extract components
    6. Creates Component records for inventory tracking
    
    Supported format: CycloneDX JSON
    """
    serializer = SBOMUploadSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'success': False, 'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    validated_data = serializer.validated_data
    
    # Get or create workspace
    workspace = get_object_or_404(Workspace, id=validated_data['workspace_id'])
    
    # Get or create product
    product, product_created = Product.objects.get_or_create(
        name=validated_data['product_name'],
        workspace=workspace,
        defaults={
            'product_type': validated_data.get('product_type', 'WEB'),
            'criticality': validated_data.get('product_criticality', 'MEDIUM')
        }
    )
    
    # Get or create release
    release, release_created = Release.objects.get_or_create(
        name=validated_data['release_name'],
        product=product,
        defaults={
            'commit_hash': validated_data.get('commit_hash', '')
        }
    )
    
    # Update commit hash if provided and release already existed
    if not release_created and validated_data.get('commit_hash'):
        release.commit_hash = validated_data['commit_hash']
    
    # Upload SBOM file (replace if exists)
    sbom_file = validated_data['sbom_file']
    release.sbom_file = sbom_file
    release.save()
    
    # Clear existing components for this release (if re-uploading)
    Component.objects.filter(release=release).delete()
    
    # Queue async task for SBOM processing
    task = process_sbom_async.delay(str(release.id))
    
    return Response(
        {
            'success': True,
            'message': 'SBOM uploaded and queued for processing',
            'release_id': str(release.id),
            'product_id': str(product.id),
            'task_id': task.id,
            'status': 'PENDING',
            'product_created': product_created,
            'release_created': release_created
        },
        status=status.HTTP_202_ACCEPTED
    )


@extend_schema(
    tags=['SBOM'],
    summary='Export SBOM file',
    description='Export a Software Bill of Materials (SBOM) for a specific release in CycloneDX format.',
    responses={
        200: {
            'description': 'SBOM file exported successfully',
            'content': {
                'application/json': {
                    'example': {
                        'bomFormat': 'CycloneDX',
                        'specVersion': '1.4',
                        'metadata': {
                            'component': {
                                'name': 'payment-gateway',
                                'version': 'v1.2.0',
                                'type': 'application'
                            }
                        },
                        'components': [
                            {
                                'type': 'library',
                                'name': 'requests',
                                'version': '2.28.1',
                                'purl': 'pkg:pypi/requests@2.28.1',
                                'licenses': [{'license': {'id': 'Apache-2.0'}}]
                            }
                        ]
                    }
                }
            }
        },
        404: {'description': 'Release not found'},
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_sbom(request, release_id):
    """
    Export SBOM file for a release.
    
    Returns the SBOM in CycloneDX format as a downloadable JSON file.
    The SBOM is generated from the components stored in the database.
    """
    release = get_object_or_404(Release, id=release_id)
    components = release.components.all()
    
    # Build CycloneDX format SBOM
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.4",
        "metadata": {
            "component": {
                "name": release.product.name,
                "version": release.name,
                "type": "application"
            }
        },
        "components": []
    }
    
    for comp in components:
        component_data = {
            "type": comp.type.lower(),
            "name": comp.name,
            "version": comp.version,
        }
        
        if comp.purl:
            component_data["purl"] = comp.purl
        
        if comp.license and comp.license != "Unknown":
            component_data["licenses"] = [{"license": {"id": comp.license}}]
        
        sbom["components"].append(component_data)
    
    # Return as downloadable JSON file
    response = JsonResponse(sbom, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="{release.product.name}_{release.name}_sbom.json"'
    return response


class WorkspaceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing workspaces.
    
    list: List all workspaces
    retrieve: Get a specific workspace with its products
    """
    queryset = Workspace.objects.all()
    serializer_class = WorkspaceSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary='List workspaces',
        description='Get a list of all workspaces'
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @extend_schema(
        summary='Get workspace details',
        description='Get detailed information about a specific workspace'
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @extend_schema(
        summary='Get workspace products',
        description='Get all products in a workspace',
        responses={200: ProductSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def products(self, request, pk=None):
        """Get all products in this workspace"""
        workspace = self.get_object()
        products = workspace.products.all()
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing products.
    
    list: List all products
    retrieve: Get a specific product with its releases
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary='List products',
        description='Get a list of all products'
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @extend_schema(
        summary='Get product details',
        description='Get detailed information about a specific product'
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @extend_schema(
        summary='Get product releases',
        description='Get all releases for a product',
        responses={200: ReleaseSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def releases(self, request, pk=None):
        """Get all releases for this product"""
        product = self.get_object()
        releases = product.releases.all().order_by('-created_at')
        serializer = ReleaseSerializer(releases, many=True)
        return Response(serializer.data)


class ReleaseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing releases.
    
    list: List all releases
    retrieve: Get a specific release with its scans and findings
    """
    queryset = Release.objects.all()
    serializer_class = ReleaseSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary='List releases',
        description='Get a list of all releases'
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @extend_schema(
        summary='Get release details',
        description='Get detailed information about a specific release'
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @extend_schema(
        summary='Get release scans',
        description='Get all scans for a release',
        responses={200: ScanSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def scans(self, request, pk=None):
        """Get all scans for this release"""
        release = self.get_object()
        scans = release.scans.all().order_by('-started_at')
        serializer = ScanSerializer(scans, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary='Get release findings',
        description='Get all findings for a release',
        responses={200: FindingSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by status (OPEN, FIXED, FALSE_POSITIVE, etc.)',
                required=False
            ),
            OpenApiParameter(
                name='severity',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by severity (CRITICAL, HIGH, MEDIUM, LOW, INFO)',
                required=False
            )
        ]
    )
    @action(detail=True, methods=['get'])
    def findings(self, request, pk=None):
        """Get all findings for this release"""
        release = self.get_object()
        
        # Support both artifact-based (BOM) and legacy modes
        artifacts = release.artifacts.all()
        if artifacts.exists():
            # BOM mode: get findings from all scans of linked artifacts
            artifact_ids = artifacts.values_list('id', flat=True)
            findings = Finding.objects.filter(scan__artifact_id__in=artifact_ids)
        else:
            # Legacy mode: get findings from direct release scans
            findings = Finding.objects.filter(scan__release=release)
        
        # Apply filters
        status_filter = request.query_params.get('status')
        if status_filter:
            findings = findings.filter(status=status_filter.upper())
        
        severity_filter = request.query_params.get('severity')
        if severity_filter:
            findings = findings.filter(severity=severity_filter.upper())
        
        findings = findings.order_by('-severity', '-first_seen')
        serializer = FindingSerializer(findings, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary='Link artifacts to release',
        description='Link existing artifacts to a release (Release Composer functionality). This allows building a release BOM by selecting artifacts.',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'artifact_ids': {
                        'type': 'array',
                        'items': {'type': 'string', 'format': 'uuid'},
                        'description': 'List of artifact UUIDs to link to this release'
                    },
                    'replace': {
                        'type': 'boolean',
                        'default': False,
                        'description': 'If true, replace existing links. If false, append to existing links.'
                    }
                },
                'required': ['artifact_ids']
            }
        },
        responses={
            200: {'description': 'Artifacts linked successfully'},
            400: {'description': 'Invalid request data'},
            404: {'description': 'Release or artifact not found'}
        }
    )
    @action(detail=True, methods=['post'])
    def link_artifacts(self, request, pk=None):
        """
        Link artifacts to a release.
        
        This implements Requirement 3: The "Release Composer" Endpoint.
        Allows Product Managers to manually link existing artifacts to a release.
        """
        release = self.get_object()
        artifact_ids = request.data.get('artifact_ids', [])
        replace = request.data.get('replace', False)
        
        if not artifact_ids:
            return Response(
                {'error': 'artifact_ids is required and cannot be empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not isinstance(artifact_ids, list):
            return Response(
                {'error': 'artifact_ids must be a list'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get artifacts
        try:
            artifacts = Artifact.objects.filter(id__in=artifact_ids)
            found_ids = set(str(a.id) for a in artifacts)
            requested_ids = set(artifact_ids)
            
            if found_ids != requested_ids:
                missing = requested_ids - found_ids
                return Response(
                    {'error': f'Artifacts not found: {list(missing)}'},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            return Response(
                {'error': f'Invalid artifact IDs: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Perform M2M link
        if replace:
            # Clear existing links and add new ones
            release.artifacts.clear()
            release.artifacts.add(*artifacts)
        else:
            # Append to existing links (default behavior)
            release.artifacts.add(*artifacts)
        
        # Return updated release with artifact count
        serializer = ReleaseSerializer(release)
        return Response({
            'success': True,
            'message': f'Linked {len(artifacts)} artifact(s) to release',
            'release': serializer.data
        }, status=status.HTTP_200_OK)
    
    @extend_schema(
        summary='Get release summary',
        description='Get comprehensive release summary with risk score, compliance status, SLA breaches, kill list, and risk treemap data. This is the primary endpoint for the Release Summary Dashboard.',
        responses={
            200: {
                'description': 'Release summary data',
                'content': {
                    'application/json': {
                        'example': {
                            'risk_score': 85,
                            'health_grade': 'B',
                            'compliance_status': False,
                            'compliance_blocking_issues': 3,
                            'sla_breaches': 2,
                            'kill_list': [],
                            'risk_treemap': []
                        }
                    }
                }
            }
        }
    )
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """
        Get comprehensive release summary for the Release Summary Dashboard.
        
        This implements the Release Summary & Risk Engine feature specification.
        Calculates:
        - Enterprise Risk Score (0-100)
        - EU CRA Compliance Status
        - SLA Breaches
        - Kill List (blocking issues)
        - Risk Treemap (artifact risk breakdown)
        """
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Q, Count, Max
        from core.services.release_risk import get_release_findings_queryset, get_license_stats, get_toxic_components
        
        release = self.get_object()
        
        # Get all findings for this release (supports both BOM and legacy modes)
        all_findings = get_release_findings_queryset(release)
        active_findings = all_findings.filter(status='OPEN')
        
        # Get artifact count
        artifact_count = release.artifacts.count()
        if artifact_count == 0:
            # Legacy mode: check if release has direct scans
            artifact_count = release.scans.count() or 1
        
        # Weighting constants
        W_KEV = 50
        W_SECRET = 50
        W_CRITICAL = 10
        W_HIGH = 2
        W_MEDIUM = 0.5
        
        # Calculate finding counts
        kev_count = active_findings.filter(metadata__kev_status=True).count()
        secret_count = active_findings.filter(finding_type='SECRET').count()
        critical_count = active_findings.filter(severity='CRITICAL').count()
        high_count = active_findings.filter(severity='HIGH').count()
        medium_count = active_findings.filter(severity='MEDIUM').count()
        
        # Calculate Total Risk Points (TRP)
        trp = (
            (kev_count * W_KEV) +
            (secret_count * W_SECRET) +
            (critical_count * W_CRITICAL) +
            (high_count * W_HIGH) +
            (medium_count * W_MEDIUM)
        )
        
        # Calculate Risk Density
        risk_density = trp / artifact_count if artifact_count > 0 else trp
        
        # Calculate Final Score (Inverse Decay)
        # Formula: Score = 100 / (1 + Risk Density / 25)
        sensitivity_factor = 25
        risk_score = 100 / (1 + (risk_density / sensitivity_factor))
        risk_score = round(risk_score)
        
        # Calculate Health Grade
        if risk_score >= 90:
            health_grade = 'A'
        elif risk_score >= 80:
            health_grade = 'B'
        elif risk_score >= 70:
            health_grade = 'C'
        else:
            health_grade = 'F'
        
        # Calculate Compliance Status (EU CRA)
        # Compliant if: KEV count = 0 AND Secret count = 0
        compliance_status = (kev_count == 0) and (secret_count == 0)
        compliance_blocking_issues = kev_count + secret_count
        
        # Calculate SLA Breaches (CRITICAL findings >7 days old)
        seven_days_ago = timezone.now() - timedelta(days=7)
        sla_breaches = active_findings.filter(
            severity='CRITICAL',
            first_seen__lt=seven_days_ago
        ).count()
        
        # Build Kill List (blocking issues: KEVs + Secrets)
        kill_list_findings = active_findings.filter(
            Q(metadata__kev_status=True) | Q(finding_type='SECRET')
        ).select_related(
            'scan__artifact',
            'scan__release'
        ).order_by('-severity', '-first_seen')
        
        kill_list = []
        for finding in kill_list_findings:
            # Determine type icon
            if finding.metadata and finding.metadata.get('kev_status'):
                issue_type = 'KEV'
                type_icon = 'skull'
            elif finding.finding_type == 'SECRET':
                issue_type = 'SECRET'
                type_icon = 'key'
            else:
                continue  # Skip if somehow not KEV or SECRET
            
            # Get affected component (package name)
            affected_component = finding.package_name or finding.title or 'N/A'
            
            # Get location (artifact name)
            artifact = finding.scan.artifact if finding.scan and finding.scan.artifact else None
            location = f"{artifact.name}:{artifact.version}" if artifact else 'Unknown'
            
            # Get remediation
            if finding.finding_type == 'SECRET':
                remediation = 'Revoke'
            else:
                remediation = finding.fix_version or 'Not available'
            
            kill_list.append({
                'id': str(finding.id),
                'type': issue_type,
                'type_icon': type_icon,
                'issue': finding.vulnerability_id or finding.title,
                'affected_component': affected_component,
                'location': location,
                'remediation': remediation,
                'severity': finding.severity,
                'first_seen': finding.first_seen.isoformat() if finding.first_seen else None
            })
        
        # Build Risk Treemap (artifact risk breakdown)
        artifacts = release.artifacts.all()
        risk_treemap = []
        
        if artifacts.exists():
            # BOM mode: calculate risk per artifact
            for artifact in artifacts:
                artifact_findings = Finding.objects.filter(
                    scan__artifact=artifact,
                    status='OPEN'
                )
                
                artifact_critical = artifact_findings.filter(severity='CRITICAL').count()
                artifact_high = artifact_findings.filter(severity='HIGH').count()
                artifact_medium = artifact_findings.filter(severity='MEDIUM').count()
                artifact_low = artifact_findings.filter(severity='LOW').count()
                artifact_total = artifact_findings.count()
                
                # Determine max severity for color coding
                if artifact_critical > 0:
                    max_severity = 'CRITICAL'
                    color = 'red'
                elif artifact_high > 0:
                    max_severity = 'HIGH'
                    color = 'orange'
                elif artifact_medium > 0 or artifact_low > 0:
                    max_severity = 'MEDIUM'
                    color = 'yellow'
                else:
                    max_severity = 'CLEAN'
                    color = 'green'
                
                risk_treemap.append({
                    'artifact_id': str(artifact.id),
                    'artifact_name': artifact.name,
                    'artifact_version': artifact.version,
                    'max_severity': max_severity,
                    'color': color,
                    'critical': artifact_critical,
                    'high': artifact_high,
                    'medium': artifact_medium,
                    'low': artifact_low,
                    'total': artifact_total
                })
        else:
            # Legacy mode: treat release as single "artifact"
            risk_treemap.append({
                'artifact_id': None,
                'artifact_name': release.name,
                'artifact_version': release.commit_hash or 'N/A',
                'max_severity': 'CRITICAL' if critical_count > 0 else ('HIGH' if high_count > 0 else 'CLEAN'),
                'color': 'red' if critical_count > 0 else ('orange' if high_count > 0 else 'green'),
                'critical': critical_count,
                'high': high_count,
                'medium': medium_count,
                'low': active_findings.filter(severity='LOW').count(),
                'total': active_findings.count()
            })
        
        # Calculate license compliance stats
        license_stats = get_license_stats(release)
        
        # Format license violations for response
        license_violations = []
        for violation in license_stats['violations']:
            license_violations.append({
                'component': violation['component'],
                'version': violation['version'],
                'license': violation['license'],
                'forbidden_licenses': violation['forbidden_licenses'],
                'risk': violation['risk']
            })
        
        # Get toxic components (high-risk dependencies with KEV findings)
        toxic_components = get_toxic_components(release)
        
        return Response({
            'risk_score': risk_score,
            'health_grade': health_grade,
            'compliance_status': compliance_status,
            'compliance_blocking_issues': compliance_blocking_issues,
            'sla_breaches': sla_breaches,
            'artifact_count': artifact_count,
            'finding_counts': {
                'kev': kev_count,
                'secrets': secret_count,
                'critical': critical_count,
                'high': high_count,
                'medium': medium_count,
                'low': active_findings.filter(severity='LOW').count(),
                'info': active_findings.filter(severity='INFO').count(),
                'total': active_findings.count()
            },
            'kill_list': kill_list,
            'risk_treemap': risk_treemap,
            'license_compliance': {
                'compliant': license_stats['compliant'],
                'violations': license_stats['violations'],
                'unknown': license_stats['unknown'],
                'total': license_stats['total'],
                'violation_count': len(license_stats['violations'])
            },
            'toxic_components': toxic_components
        }, status=status.HTTP_200_OK)


class ScanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing scans.
    
    list: List all scans
    retrieve: Get a specific scan with its findings
    """
    queryset = Scan.objects.all()
    serializer_class = ScanSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary='List scans',
        description='Get a list of all scans'
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @extend_schema(
        summary='Get scan details',
        description='Get detailed information about a specific scan'
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @extend_schema(
        summary='Get scan findings',
        description='Get all findings from a scan',
        responses={200: FindingSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def findings(self, request, pk=None):
        """Get all findings from this scan"""
        scan = self.get_object()
        findings = scan.findings.all().order_by('-severity', '-created_at')
        serializer = FindingSerializer(findings, many=True)
        return Response(serializer.data)


class FindingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing findings.
    
    list: List all findings with filtering options
    retrieve: Get a specific finding
    """
    queryset = Finding.objects.all()
    serializer_class = FindingSerializer
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary='List findings',
        description='Get a list of all findings with optional filtering',
        parameters=[
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by status',
                required=False
            ),
            OpenApiParameter(
                name='severity',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by severity',
                required=False
            ),
            OpenApiParameter(
                name='cve_id',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by CVE ID',
                required=False
            ),
            OpenApiParameter(
                name='kev_status',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter by KEV status (true for exploited)',
                required=False
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Apply filters
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter.upper())
        
        severity_filter = request.query_params.get('severity')
        if severity_filter:
            queryset = queryset.filter(severity=severity_filter.upper())
        
        cve_filter = request.query_params.get('cve_id')
        if cve_filter:
            queryset = queryset.filter(vulnerability_id__icontains=cve_filter)
        
        kev_filter = request.query_params.get('kev_status')
        if kev_filter is not None:
            queryset = queryset.filter(metadata__kev_status=kev_filter.lower() == 'true')
        
        queryset = queryset.order_by('-severity', '-first_seen')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary='Get finding details',
        description='Get detailed information about a specific finding'
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class RepositoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing repositories.
    
    This implements Requirement 1: The Inventory ViewSets.
    Repositories are typically created via ingestion, not manually.
    """
    queryset = Repository.objects.all()
    serializer_class = RepositorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['workspace', 'name']
    search_fields = ['name', 'url']
    
    @extend_schema(
        summary='List repositories',
        description='Get a list of all repositories with optional filtering and search',
        parameters=[
            OpenApiParameter(
                name='workspace',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description='Filter by workspace ID',
                required=False
            ),
            OpenApiParameter(
                name='name',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by repository name',
                required=False
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search in name and URL fields',
                required=False
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @extend_schema(
        summary='Get repository details',
        description='Get detailed information about a specific repository'
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class ArtifactViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing artifacts.
    
    This implements Requirement 1: The Inventory ViewSets.
    Artifacts represent physical software assets (Docker images, libraries, etc.)
    """
    queryset = Artifact.objects.all()
    serializer_class = ArtifactSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['repository', 'workspace', 'name', 'version', 'type']
    search_fields = ['name', 'version', 'tag']
    
    @extend_schema(
        summary='List artifacts',
        description='Get a list of all artifacts with optional filtering and search. Supports partial hash search (e.g., sha256:8f2...)',
        parameters=[
            OpenApiParameter(
                name='repository',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description='Filter by repository ID',
                required=False
            ),
            OpenApiParameter(
                name='workspace',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description='Filter by workspace ID',
                required=False
            ),
            OpenApiParameter(
                name='name',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by artifact name',
                required=False
            ),
            OpenApiParameter(
                name='version',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by artifact version',
                required=False
            ),
            OpenApiParameter(
                name='type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by artifact type (CONTAINER, LIBRARY, PACKAGE, BINARY)',
                required=False
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search in name, version, and tag fields. Supports partial hash search.',
                required=False
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Handle partial hash search (e.g., sha256:8f2...)
        search_query = request.query_params.get('search', '')
        if search_query and ':' in search_query:
            # If search contains a colon, it might be a hash prefix
            # Search in version field for partial matches
            queryset = queryset.filter(version__icontains=search_query)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary='Get artifact details',
        description='Get detailed information about a specific artifact'
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @extend_schema(
        summary='Get artifact scans',
        description='Get all scans associated with this specific artifact',
        responses={200: ScanSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def scans(self, request, pk=None):
        """
        Get all scans for this artifact.
        
        This implements Requirement 1: Action to return scans for an artifact.
        """
        artifact = self.get_object()
        scans = Scan.objects.filter(artifact=artifact).order_by('-started_at')
        serializer = ScanSerializer(scans, many=True)
        return Response(serializer.data)

