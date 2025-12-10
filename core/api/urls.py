from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework import permissions
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView
)

from core.api import views

# Create router and register viewsets
router = DefaultRouter()
router.register(r'workspaces', views.WorkspaceViewSet, basename='workspace')
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'releases', views.ReleaseViewSet, basename='release')
router.register(r'scans', views.ScanViewSet, basename='scan')
router.register(r'findings', views.FindingViewSet, basename='finding')
router.register(r'repositories', views.RepositoryViewSet, basename='repository')
router.register(r'artifacts', views.ArtifactViewSet, basename='artifact')

urlpatterns = [
    # API v1 routes
    path('v1/', include(router.urls)),
    
    # Scan upload endpoint (not using ViewSet)
    path('v1/scans/upload/', views.upload_scan, name='api-upload-scan'),
    
    # SBOM endpoints
    path('v1/sbom/upload/', views.upload_sbom, name='api-upload-sbom'),
    path('v1/releases/<uuid:release_id>/sbom/export/', views.export_sbom, name='api-export-sbom'),
    
    # Audit Log endpoints
    path('v1/audit-logs/', views.audit_logs_list, name='api-audit-logs-list'),
    path('v1/audit-logs/export/', views.audit_logs_export, name='api-audit-logs-export'),
    
    # Swagger/OpenAPI documentation
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

