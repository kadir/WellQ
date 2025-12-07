"""
Release Risk Aggregation Service
Implements Requirement 3: The "Risk Aggregation" logic for the BOM architecture.

Since Release no longer owns Findings directly, we need helper functions to calculate
stats for releases based on their linked artifacts.
"""
from django.db.models import Q, Count, F, Max
from core.models import Finding, Release, Component


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


def get_license_stats(release):
    """
    Calculate license compliance statistics for a release.
    
    Categorizes components by license type:
    - compliant: Permissive licenses (MIT, Apache-2.0, BSD, etc.)
    - violations: Forbidden/Copyleft licenses (AGPL-3.0, GPL-3.0, GPL-2.0)
    - unknown: Unknown or empty licenses
    
    Args:
        release: Release instance
    
    Returns:
        dict: License statistics with counts and violation details
    """
    try:
        # Get all components in this release
        components = Component.objects.filter(release=release)
    
    # Define license policy
    # Forbidden licenses (Copyleft/Forbidden)
    FORBIDDEN = ['AGPL-3.0', 'AGPL-3', 'AGPL', 'GPL-3.0', 'GPL-3', 'GPL-2.0', 'GPL-2', 'GPL']
    
    # Permissive licenses (safe to use)
    PERMISSIVE = [
        'MIT', 'Apache-2.0', 'Apache-2', 'BSD-2-Clause', 'BSD-3-Clause', 'BSD',
        'ISC', 'Unlicense', 'CC0-1.0', 'CC-BY-4.0', 'MPL-2.0', 'LGPL-2.1', 'LGPL-3.0'
    ]
    
    stats = {
        'compliant': 0,
        'violations': [],
        'unknown': 0,
        'total': 0
    }
    
    for comp in components:
        stats['total'] += 1
        
        # Get license from license_expression or fallback to license field
        lic = (comp.license_expression or comp.license or '').strip()
        
        if not lic or lic.lower() in ['unknown', 'none', 'n/a', '']:
            stats['unknown'] += 1
            continue
        
        # Check if license contains any forbidden licenses
        # Handle license expressions like "MIT OR GPL-3.0" or "GPL-3.0 AND LGPL-2.1"
        lic_upper = lic.upper()
        has_forbidden = False
        forbidden_licenses_found = []
        
        for forbidden in FORBIDDEN:
            if forbidden.upper() in lic_upper:
                has_forbidden = True
                forbidden_licenses_found.append(forbidden)
        
        if has_forbidden:
            # This is a violation
            stats['violations'].append({
                'component': comp.name,
                'version': comp.version,
                'license': lic,
                'forbidden_licenses': forbidden_licenses_found,
                'risk': 'CRITICAL' if 'AGPL' in lic_upper else 'HIGH'
            })
        else:
            # Check if it's a known permissive license
            is_permissive = any(perm.upper() in lic_upper for perm in PERMISSIVE)
            
            if is_permissive:
                stats['compliant'] += 1
            else:
                # Unknown license (not in our lists)
                stats['unknown'] += 1
    
        return stats
    except Exception as e:
        # Log the error but return empty stats to prevent 500 errors
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting license stats for release {release.id}: {str(e)}")
        return {
            'compliant': 0,
            'violations': [],
            'unknown': 0,
            'total': 0
        }


def get_toxic_components(release):
    """
    Get high-risk components (packages with KEV findings) using efficient database aggregation.
    
    This function groups findings by package_name and package_version, counting
    how many KEV (Known Exploited Vulnerability) findings each package has.
    Uses SQL GROUP BY for optimal performance.
    
    Args:
        release: Release instance
    
    Returns:
        list: List of dicts with package_name, package_version, kev_count, and fix_version
    """
    try:
        # Get all findings for this release
        findings = get_release_findings_queryset(release)
        
        # Filter for OPEN findings with KEV status
        # Handle cases where metadata might be None or not have kev_status
        kev_findings = findings.filter(
            status='OPEN',
            metadata__kev_status=True
        ).exclude(
            package_name__isnull=True
        ).exclude(
            package_name=''
        )
        
        # Check if we have any KEV findings
        if not kev_findings.exists():
            return []
        
        # Use database aggregation to group by package_name and package_version
        # This generates a single optimized SQL query with GROUP BY
        toxic_comps = (
            kev_findings
            .values('package_name', 'package_version')
            .annotate(
                kev_count=Count('id'),
                # Get the latest fix_version (most recent one)
                # Use Coalesce to handle NULL values
                latest_fix=Max('fix_version')
            )
            .order_by('-kev_count', 'package_name')
        )
        
        # Convert to list of dicts for easier consumption
        result = []
        for comp in toxic_comps:
            result.append({
                'package_name': comp['package_name'] or 'Unknown',
                'package_version': comp['package_version'] or 'Unknown',
                'kev_count': comp['kev_count'],
                'fix_version': comp['latest_fix'] or 'Not available'
            })
        
        return result
    except Exception as e:
        # Log the error but return empty list to prevent 500 errors
        # In production, you might want to log this properly
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting toxic components for release {release.id}: {str(e)}")
        return []


