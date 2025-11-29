from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

# Import from the new views package
from core.views import inventory, findings, ingestion, profile, users, roles, settings

urlpatterns = [
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
    path('releases/<uuid:release_id>/', findings.release_detail, name='release_detail'),
    path('releases/<uuid:release_id>/upload-sbom/', findings.release_sbom_upload, name='release_sbom_upload'),
    path('releases/<uuid:release_id>/export-sbom/', findings.release_sbom_export, name='release_sbom_export'),

    # Ingestion
    path('upload/', ingestion.upload_scan, name='upload_scan'),
    
    # Vulnerabilities
    path('vulnerabilities/', findings.vulnerabilities_list, name='vulnerabilities_list'),
    path('vulnerabilities/<uuid:finding_id>/detail/', findings.vulnerability_detail, name='vulnerability_detail'),
    path('vulnerabilities/<uuid:finding_id>/update-status/', findings.update_vulnerability_status, name='update_vulnerability_status'),
    
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
]