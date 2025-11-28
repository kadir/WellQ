import json
import hashlib
from django.utils import timezone
from core.findings.models import Finding
from .base import BaseScanner

class TrivyScanner(BaseScanner):
    
    def parse(self, scan_instance, json_file):
        try:
            json_file.seek(0)
            data = json.load(json_file)
            results = data.get('Results', [])
            release = scan_instance.release
            now = timezone.now()

            # 1. FETCH ALL EXISTING (Map: Hash -> ID)
            # We only need ID and Status to make decisions
            existing_map = {
                f.hash_id: f 
                for f in Finding.objects.filter(scan__release=release)
            }
            
            seen_hashes = set()
            
            # Lists for Bulk Operations
            to_create = []
            to_update = [] 

            for result in results:
                vulnerabilities = result.get('Vulnerabilities', [])
                for vuln in vulnerabilities:
                    cve = vuln.get('VulnerabilityID', 'Unknown')
                    pkg = vuln.get('PkgName', 'Unknown')
                    ver = vuln.get('InstalledVersion', 'Unknown')
                    
                    # Generate Hash
                    unique_str = f"{cve}-{pkg}-{ver}-{release.id}"
                    finding_hash = hashlib.sha256(unique_str.encode('utf-8')).hexdigest()
                    seen_hashes.add(finding_hash)

                    if finding_hash in existing_map:
                        # EXISTS: Prepare for Update
                        obj = existing_map[finding_hash]
                        
                        # Only update if something changed (Performance tweak)
                        needs_save = False
                        
                        if obj.status == 'FIXED':
                            obj.status = 'OPEN' # Regression
                            needs_save = True
                        
                        # Always update metadata
                        obj.scan = scan_instance
                        obj.last_seen = now
                        
                        # Add to update list
                        to_update.append(obj)
                    else:
                        # NEW: Prepare for Create
                        to_create.append(Finding(
                            scan=scan_instance,
                            title=vuln.get('Title', 'Unknown'),
                            cve_id=cve,
                            severity=vuln.get('Severity', 'INFO').upper(),
                            description=vuln.get('Description', ''),
                            package_name=pkg,
                            package_version=ver,
                            fixed_version=vuln.get('FixedVersion', ''),
                            hash_id=finding_hash,
                            status='OPEN'
                        ))

            # 2. BULK OPERATIONS (The Speed Boost)
            
            # A. Bulk Create (1 Query)
            if to_create:
                Finding.objects.bulk_create(to_create)
            
            # B. Bulk Update (1 Query)
            if to_update:
                Finding.objects.bulk_update(to_update, ['scan', 'last_seen', 'status'])

            # 3. AUTO-CLOSE LOGIC (1 Query)
            all_known_hashes = set(existing_map.keys())
            missing_hashes = all_known_hashes - seen_hashes
            
            if missing_hashes:
                Finding.objects.filter(
                    scan__release=release, 
                    hash_id__in=missing_hashes
                ).exclude(status='FIXED').update( # Don't update if already fixed
                    status='FIXED',
                    last_seen=now
                )

            # 4. Snapshot
            scan_instance.findings_count = len(seen_hashes)
            scan_instance.save()

            return len(seen_hashes)

        except Exception as e:
            print(f"Trivy Performance Logic Error: {e}")
            return 0