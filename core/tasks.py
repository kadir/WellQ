"""
Celery tasks for WellQ
"""
from celery import shared_task
from django.core.files.base import ContentFile
from django.utils import timezone
from core.models import Scan, Release, Finding
from core.services.scan_engine import process_scan_upload
from core.services.sbom import digest_sbom
import gzip
import csv
import json
import requests
import io


@shared_task(bind=True, max_retries=3)
def process_scan_async(self, scan_id, file_content_b64, file_name):
    """
    Async task to process scan upload.
    
    Args:
        scan_id: UUID of the Scan instance
        file_content_b64: Base64 encoded file content
        file_name: Original file name
    """
    import base64
    
    try:
        scan = Scan.objects.get(id=scan_id)
        scan.status = 'PROCESSING'
        scan.save()
        
        # Decode base64 content
        file_content = base64.b64decode(file_content_b64)
        file_obj = ContentFile(file_content, name=file_name)
        
        # Process the scan
        findings_count = process_scan_upload(scan, file_obj)
        
        # Update scan status
        scan.status = 'COMPLETED'
        scan.completed_at = timezone.now()
        scan.findings_count = findings_count
        scan.save()
        
        return {
            'success': True,
            'scan_id': str(scan_id),
            'findings_count': findings_count
        }
    except Scan.DoesNotExist:
        return {
            'success': False,
            'error': f'Scan {scan_id} not found'
        }
    except Exception as exc:
        # Update scan status to failed
        try:
            scan = Scan.objects.get(id=scan_id)
            scan.status = 'FAILED'
            scan.save()
        except:
            pass
        
        # Retry the task
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def process_sbom_async(self, release_id):
    """
    Async task to process SBOM file.
    
    Args:
        release_id: UUID of the Release instance
    """
    try:
        release = Release.objects.get(id=release_id)
        
        # Ensure file is accessible
        if not release.sbom_file:
            return {
                'success': False,
                'error': 'No SBOM file found for this release'
            }
        
        # Process the SBOM
        digest_sbom(release)
        
        components_count = release.components.count()
        
        return {
            'success': True,
            'release_id': str(release_id),
            'components_count': components_count
        }
    except Release.DoesNotExist:
        return {
            'success': False,
            'error': f'Release {release_id} not found'
        }
    except Exception as exc:
        # Retry the task
        raise self.retry(exc=exc, countdown=60)


@shared_task
def enrich_findings_with_threat_intel():
    """
    Scheduled task to enrich all findings with EPSS and KEV data.
    Runs daily to update threat intelligence.
    """
    from core.models import Finding
    
    # Constants
    EPSS_URL = "https://epss.empiricalsecurity.com/epss_scores-current.csv.gz"
    KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
    
    try:
        # Fetch KEV data
        kev_response = requests.get(KEV_URL, timeout=30)
        kev_response.raise_for_status()
        kev_data = kev_response.json()
        kev_dict = {}
        
        for vuln in kev_data.get('vulnerabilities', []):
            cve_id = vuln.get('cveID', '').upper()
            if cve_id:
                kev_dict[cve_id] = {
                    'dateAdded': vuln.get('dateAdded'),
                    'vulnerabilityName': vuln.get('vulnerabilityName', '')
                }
        
        # Fetch EPSS data
        epss_response = requests.get(EPSS_URL, timeout=30)
        epss_response.raise_for_status()
        epss_dict = {}
        
        with gzip.open(io.BytesIO(epss_response.content), 'rt') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cve_id = row.get('cve', '').upper()
                if cve_id:
                    try:
                        epss_dict[cve_id] = {
                            'score': float(row.get('epss', 0)),
                            'percentile': float(row.get('percentile', 0))
                        }
                    except (ValueError, TypeError):
                        continue
        
        # Update findings in batches
        updated_count = 0
        batch_size = 1000
        
        findings = Finding.objects.all()
        total = findings.count()
        
        for i in range(0, total, batch_size):
            batch = findings[i:i + batch_size]
            to_update = []
            
            for finding in batch:
                needs_update = False
                
                # Update KEV status
                if finding.vulnerability_id in kev_dict:
                    # Store KEV in metadata
                    if not finding.metadata:
                        finding.metadata = {}
                    if not finding.metadata.get('kev_status'):
                        finding.metadata['kev_status'] = True
                        needs_update = True
                    kev_info = kev_dict[finding.vulnerability_id]
                    if kev_info.get('dateAdded'):
                        try:
                            from datetime import datetime
                            # Store KEV date in metadata
                            if not finding.metadata:
                                finding.metadata = {}
                            finding.metadata['kev_date'] = datetime.strptime(
                                kev_info['dateAdded'], 
                                '%Y-%m-%d'
                            ).date()
                            needs_update = True
                        except:
                            pass
                else:
                    # Update KEV status in metadata
                    if not finding.metadata:
                        finding.metadata = {}
                    if finding.metadata.get('kev_status'):
                        finding.metadata['kev_status'] = False
                        needs_update = True
                
                # Update EPSS data
                if finding.vulnerability_id in epss_dict:
                    epss_info = epss_dict[finding.vulnerability_id]
                    # Store EPSS in metadata
                    if not finding.metadata:
                        finding.metadata = {}
                    if finding.metadata.get('epss_score') != epss_info['score']:
                        finding.metadata['epss_score'] = epss_info['score']
                        finding.metadata['epss_percentile'] = epss_info.get('percentile', 0.0)
                        needs_update = True
                    # EPSS percentile is already handled above
                    pass
                
                if needs_update:
                    finding.last_enrichment = timezone.now()
                    to_update.append(finding)
            
            if to_update:
                Finding.objects.bulk_update(
                    to_update, 
                    ['kev_status', 'kev_date', 'epss_score', 'epss_percentile', 'last_enrichment'],
                    batch_size=500
                )
                updated_count += len(to_update)
        
        return {
            'success': True,
            'updated_count': updated_count,
            'total_findings': total
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

