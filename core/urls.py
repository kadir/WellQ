from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.http import HttpResponse
from django.conf import settings as django_settings
from django.conf.urls.static import static
import os

# Import from the new views package
from core.views import inventory, findings, ingestion, profile, users, roles, settings, teams

urlpatterns = [
    # Health check endpoint (for Docker/Kubernetes)
    path('health/', lambda r: HttpResponse('OK'), name='health'),
    
    path('admin/', admin.site.urls),
    
    # API routes
    path('api/', include('core.api.urls')),
    
    # Auth
    path('', auth_views.LoginView.as_view(template_name='login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # Dashboard
    path('dashboard/', inventory.dashboard, name='dashboard'),
    
    # Workspaces
    path('workspaces/', inventory.workspace_list, name='workspace_list'),
    path('workspaces/create/', inventory.workspace_create, name='workspace_create'),
    path('workspaces/<uuid:workspace_id>/', inventory.workspace_detail, name='workspace_detail'),
    path('workspaces/<uuid:workspace_id>/edit/', inventory.workspace_edit, name='workspace_edit'),

    # Products
    path('products/', inventory.product_list, name='product_list'),
    path('products/create/', inventory.product_create, name='product_create'),
    path('products/<uuid:product_id>/', inventory.product_detail, name='product_detail'),
    path('products/<uuid:product_id>/edit/', inventory.product_edit, name='product_edit'),

    # Releases & Findings
    path('products/<uuid:product_id>/releases/create/', findings.release_create, name='release_create'),
    path('products/<uuid:product_id>/releases/compose/', inventory.release_composer, name='release_composer'),
    path('releases/<uuid:release_id>/', findings.release_detail, name='release_detail'),
    path('releases/<uuid:release_id>/upload-sbom/', findings.release_sbom_upload, name='release_sbom_upload'),
    path('releases/<uuid:release_id>/export-sbom/', findings.release_sbom_export, name='release_sbom_export'),
    
    # Asset Inventory (BOM Architecture)
    path('inventory/', inventory.asset_inventory, name='asset_inventory'),
    path('inventory/repositories/create/', inventory.repository_create, name='repository_create'),
    path('api/artifacts/search/', inventory.artifact_search_api, name='artifact_search_api'),
    path('api/releases/risk-preview/', inventory.release_composer_risk_preview, name='release_composer_risk_preview'),

    # Ingestion
    path('upload/', ingestion.upload_scan, name='upload_scan'),
    
    # Vulnerabilities
    path('vulnerabilities/', findings.vulnerabilities_list, name='vulnerabilities_list'),
    path('vulnerabilities/<uuid:finding_id>/detail/', findings.vulnerability_detail, name='vulnerability_detail'),
    path('vulnerabilities/<uuid:finding_id>/update-status/', findings.update_vulnerability_status, name='update_vulnerability_status'),
    
    # Approvals
    path('approvals/', findings.approvals_list, name='approvals_list'),
    path('approvals/<uuid:request_id>/approve/', findings.approve_status_request, name='approve_status_request'),
    path('approvals/<uuid:request_id>/reject/', findings.reject_status_request, name='reject_status_request'),
    
    # SBOMs
    path('sboms/', findings.sboms_list, name='sboms_list'),
    
    # Profile Settings
    path('profile/', profile.profile_settings, name='profile_settings'),
    path('profile/tokens/create/', profile.create_api_token, name='create_api_token'),
    path('profile/tokens/<uuid:token_id>/revoke/', profile.revoke_api_token, name='revoke_api_token'),
    
    # User Management
    path('users/', users.user_list, name='user_list'),
    path('users/create/', users.user_create, name='user_create'),
    path('users/<int:user_id>/edit/', users.user_edit, name='user_edit'),
    path('users/<int:user_id>/delete/', users.user_delete, name='user_delete'),
    
    # Role Management
    path('roles/', roles.role_list, name='role_list'),
    path('roles/<uuid:role_id>/', roles.role_detail, name='role_detail'),
    path('roles/<uuid:role_id>/edit/', roles.role_edit, name='role_edit'),
    
    # Platform Settings (Admin Only)
    path('settings/platform/', settings.platform_settings, name='platform_settings'),
    path('settings/platform/trigger-enrich/', settings.trigger_enrich_db, name='trigger_enrich_db'),
    
    # Audit Logs (Admin and Auditor Only)
    path('settings/audit-logs/', settings.audit_logs, name='audit_logs'),
    
    # Team Management
    path('settings/teams/', teams.team_list, name='team_list'),
    path('settings/teams/create/', teams.team_create, name='team_create'),
    path('settings/teams/<uuid:team_id>/', teams.team_detail, name='team_detail'),
    path('settings/teams/<uuid:team_id>/edit/', teams.team_edit, name='team_edit'),
    path('settings/teams/<uuid:team_id>/delete/', teams.team_delete, name='team_delete'),
]

# WhiteNoise handles static files automatically - no need for static() function
# Media files still need to be served (user uploads)
# Only add media serving if not using nginx
serve_media = django_settings.DEBUG or os.getenv('SERVE_MEDIA', 'False').lower() == 'true'
if serve_media:
    urlpatterns += static(django_settings.MEDIA_URL, document_root=str(django_settings.MEDIA_ROOT))