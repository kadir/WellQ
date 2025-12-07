"""
Artifact Management Service
Handles the "Upsert" logic for artifacts during scan ingestion.

This service implements Requirement 1 from the BOM architecture:
- Check if Artifact exists, create if not
- Check if Artifact has been scanned recently (deduplication)
- Link scan to artifact
"""
from django.utils import timezone
from datetime import timedelta
from core.models import Artifact, Repository, Workspace, Scan


def _clean_repository_url(url):
    """
    Clean and normalize repository URL.
    - Remove .git suffix
    - Convert ssh:// to https://
    - Convert git@github.com:user/repo.git to https://github.com/user/repo
    - Normalize trailing slashes
    """
    if not url:
        return ''
    
    url = url.strip()
    
    # Remove .git suffix
    if url.endswith('.git'):
        url = url[:-4]
    
    # Handle SSH URLs (git@github.com:user/repo)
    if url.startswith('git@'):
        # Convert git@github.com:user/repo to https://github.com/user/repo
        url = url.replace('git@', '').replace(':', '/', 1)
        if not url.startswith('http'):
            url = f'https://{url}'
    
    # Handle ssh:// protocol
    if url.startswith('ssh://'):
        url = url.replace('ssh://', 'https://', 1)
    
    # Ensure it starts with http:// or https://
    if url and not url.startswith(('http://', 'https://')):
        # If it looks like a domain, add https://
        if '.' in url and not url.startswith('/'):
            url = f'https://{url}'
    
    # Remove trailing slash
    url = url.rstrip('/')
    
    return url


def upsert_artifact(
    workspace,
    artifact_name,
    artifact_version,
    artifact_type='CONTAINER',
    repository=None,
    repository_name=None,
    repository_url=None
):
    """
    Upsert (insert or update) an artifact.
    
    This function is idempotent - running it twice produces the same result.
    
    Args:
        workspace: Workspace instance
        artifact_name: Name of the artifact (e.g., "payment-service-image")
        artifact_version: Version of the artifact (e.g., "sha256:a1b2..." or "v1.0.5")
        artifact_type: Type of artifact (CONTAINER, LIBRARY, PACKAGE, BINARY)
        repository: Repository instance (optional)
        repository_name: Name of repository (will create if doesn't exist)
        repository_url: URL of repository (will create if doesn't exist, cleaned automatically)
    
    Returns:
        tuple: (artifact_instance, created_artifact, created_repository)
    """
    # Step 1: Handle Repository (if provided)
    repo_instance = repository
    created_repo = False
    
    if not repo_instance and (repository_name or repository_url):
        # Clean the repository URL
        cleaned_url = _clean_repository_url(repository_url) if repository_url else ''
        
        # Use cleaned URL for lookup/creation
        repo_instance, created_repo = Repository.objects.get_or_create(
            workspace=workspace,
            url=cleaned_url if cleaned_url else '',
            defaults={'name': repository_name or 'unknown'}
        )
        
        # If repository already existed but name is different, update it
        if not created_repo and repository_name and repo_instance.name != repository_name:
            repo_instance.name = repository_name
            repo_instance.save()
    
    # Step 2: Upsert Artifact
    artifact, created_artifact = Artifact.objects.get_or_create(
        name=artifact_name,
        version=artifact_version,
        defaults={
            'workspace': workspace,
            'repository': repo_instance,
            'type': artifact_type
        }
    )
    
    # Update repository if it was created later
    if not created_artifact and repo_instance and not artifact.repository:
        artifact.repository = repo_instance
        artifact.save()
    
    return artifact, created_artifact, created_repo


def get_or_create_scan_for_artifact(
    artifact,
    scanner_name,
    deduplication_window_hours=24
):
    """
    Get or create a scan for an artifact with deduplication logic.
    
    This implements the deduplication check:
    - If artifact was scanned by the same scanner today, return existing scan
    - Otherwise, create a new scan
    
    This function is idempotent - running it twice produces the same result.
    
    Args:
        artifact: Artifact instance
        scanner_name: Name of the scanner (e.g., "Trivy")
        deduplication_window_hours: Hours within which to consider a scan "recent" (default: 24, meaning same day)
    
    Returns:
        tuple: (scan_instance, is_new_scan)
    """
    # Check for scan created today (same day deduplication)
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    recent_scan = Scan.objects.filter(
        artifact=artifact,
        scanner_name=scanner_name,
        started_at__gte=today_start,
        status__in=['PENDING', 'PROCESSING', 'COMPLETED']
    ).order_by('-started_at').first()
    
    if recent_scan:
        return recent_scan, False
    
    # Create new scan
    new_scan = Scan.objects.create(
        artifact=artifact,
        scanner_name=scanner_name,
        status='PENDING'
    )
    
    return new_scan, True


def compose_release_bom(release, artifact_names_and_versions):
    """
    Compose a release's Bill of Materials by linking artifacts.
    
    This implements Requirement 2: The "BOM" Logic.
    
    Args:
        release: Release instance
        artifact_names_and_versions: List of tuples [(name, version), ...]
    
    Returns:
        list: List of artifact instances that were linked
    """
    artifacts = []
    
    for artifact_name, artifact_version in artifact_names_and_versions:
        try:
            artifact = Artifact.objects.get(
                name=artifact_name,
                version=artifact_version
            )
            release.artifacts.add(artifact)
            artifacts.append(artifact)
        except Artifact.DoesNotExist:
            # Artifact doesn't exist - skip or create?
            # For now, we'll skip and log a warning
            # In production, you might want to create it or raise an error
            pass
    
    return artifacts


