"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from core.findings import views as finding_views
from core import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Login Page (Home) 
    path('', auth_views.LoginView.as_view(
        template_name='login.html',
        redirect_authenticated_user=True  # If already logged in, go to dashboard (later)
    ), name='login'),

    # Dashboard URL
    path('dashboard/', views.dashboard, name='dashboard'),

    # WORKSPACES
    path('workspaces/', finding_views.workspace_list, name='workspace_list'),
    path('workspaces/create/', finding_views.workspace_create, name='workspace_create'),
    path('workspaces/<uuid:workspace_id>/', finding_views.workspace_detail, name='workspace_detail'),
    path('workspaces/<uuid:workspace_id>/edit/', finding_views.workspace_edit, name='workspace_edit'),
    path('products/', finding_views.product_list, name='product_list'),
    path('products/create/', finding_views.product_create, name='product_create'),
    path('products/<uuid:product_id>/', finding_views.product_detail, name='product_detail'),
    path('products/<uuid:product_id>/edit/', finding_views.product_edit, name='product_edit'),
    path('releases/<uuid:release_id>/', finding_views.release_detail, name='release_detail'),
    path('products/<uuid:product_id>/releases/create/', finding_views.release_create, name='release_create'),
    path('releases/<uuid:release_id>/export-sbom/', finding_views.release_sbom_export, name='release_sbom_export'),
    path('upload/', finding_views.upload_scan, name='upload_scan'),

    # Logout (Redirects back to login page)
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
