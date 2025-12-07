"""
Release Risk Aggregation Service
Implements Requirement 3: The "Risk Aggregation" logic for the BOM architecture.

Since Release no longer owns Findings directly, we need helper functions to calculate
stats for releases based on their linked artifacts.
"""
from django.db.models import Q, Count
from core.models import Finding, Release


def get_release_findings_queryset(release):
    """
    Get all findings for a release.
    
    In the new BOM architecture:
    - Findings are linked to artifacts (via scans)
    - A release is composed of multiple artifacts (M2M)
    - Release Risk = Sum(Findings of all Linked Artifacts)
    
    This function supports both:
    1. New BOM mode: Finds findings via release.artifacts -> scans -> findings
    2. Legacy mode: Finds findings via scan.release (backward compatibility)
    
    Args:
        release: Release instance
    
    Returns:
        QuerySet: Findings queryset for this release
    """
    # Get artifacts linked to this release
    artifacts = release.artifacts.all()
    
    # Build query: findings from artifacts OR from legacy release scans
    if artifacts.exists():
        # New BOM architecture: Get findings from all artifacts
        artifact_ids = list(artifacts.values_list('id', flat=True))
        findings = Finding.objects.filter(
            scan__artifact__id__in=artifact_ids
        )
    else:
        # Legacy mode: Get findings from scans directly linked to release
        findings = Finding.objects.filter(
            scan__release=release
        )
    
    return findings


def get_release_risk_stats(release):
    """
    Calculate risk statistics for a release.
    
    Returns a dictionary with:
    - total: Total active findings
    - critical: Critical severity findings
    - high: High severity findings
    - medium: Medium severity findings
    - low: Low severity findings
    - info: Info severity findings
    - secrets: Secret findings count
    - kev: KEV findings count
    - high_epss: High EPSS score findings count
    
    Args:
        release: Release instance
    
    Returns:
        dict: Risk statistics
    """
    findings = get_release_findings_queryset(release)
    active_findings = findings.filter(status='OPEN')
    
    stats = active_findings.aggregate(
        total=Count('id'),
        critical=Count('id', filter=Q(severity='CRITICAL')),
        high=Count('id', filter=Q(severity='HIGH')),
        medium=Count('id', filter=Q(severity='MEDIUM')),
        low=Count('id', filter=Q(severity='LOW')),
        info=Count('id', filter=Q(severity='INFO')),
        secrets=Count('id', filter=Q(finding_type=Finding.Type.SECRET)),
        kev=Count('id', filter=Q(metadata__kev_status=True)),
        high_epss=Count('id', filter=Q(metadata__epss_score__gte=0.7)),
    )
    
    return stats


