from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, action, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle, ScopedRateThrottle
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from core.models import Workspace, Product, Release, Scan, Finding, Component


# Custom throttle class for upload endpoints
class UploadRateThrottle(ScopedRateThrottle):
    """Throttle class for upload endpoints with 'upload' scope."""
    scope_attr = 'throttle_scope'
    
    def get_scope(self):
        return 'upload'
from core.api.serializers import (
    WorkspaceSerializer, ProductSerializer, ReleaseSerializer,
    ScanSerializer, FindingSerializer, ScanUploadSerializer, SBOMUploadSerializer
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
        release.save()
    
    # Create scan with PENDING status
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
    
    return Response(
        {
            'success': True,
            'message': 'Scan uploaded and queued for processing',
            'scan_id': str(scan.id),
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
        findings = Finding.objects.filter(scan__release=release)
        
        # Apply filters
        status_filter = request.query_params.get('status')
        if status_filter:
            findings = findings.filter(status=status_filter.upper())
        
        severity_filter = request.query_params.get('severity')
        if severity_filter:
            findings = findings.filter(severity=severity_filter.upper())
        
        findings = findings.order_by('-severity', '-created_at')
        serializer = FindingSerializer(findings, many=True)
        return Response(serializer.data)


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
            queryset = queryset.filter(cve_id__icontains=cve_filter)
        
        kev_filter = request.query_params.get('kev_status')
        if kev_filter is not None:
            queryset = queryset.filter(kev_status=kev_filter.lower() == 'true')
        
        queryset = queryset.order_by('-severity', '-created_at')
        
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

