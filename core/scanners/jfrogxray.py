import json
import hashlib
import re
from django.utils import timezone
from core.models import Finding
from core.utils.security import safe_json_load
from .base import BaseScanner

class JFrogXrayScanner(BaseScanner):
    """
    Parser for JFrog Xray scan results.
    
    JFrog Xray outputs JSON with the following structure:
    {
        "total_count": <number>,
        "data": [
            {
                "id": "",
                "severity": "High|Medium|Low|Critical",
                "summary": "Vulnerability summary",
                "issue_type": "security",
                "provider": "JFrog|Snyk|...",
                "component": "component-name",
                "source_id": "package-manager://component",
                "source_comp_id": "package-manager://component:version",
                "component_versions": {
                    "id": "component-name",
                    "vulnerable_versions": [...],
                    "fixed_versions": [...],
                    "more_details": {
                        "cves": [
                            {
                                "cve": "CVE-YYYY-NNNNN",
                                "cwe": [...],
                                "cvss_v2": "...",
                                "cvss_v3": "..."
                            }
                        ],
                        "description": "...",
                        "provider": "..."
                    }
                },
                "edited": "ISO timestamp"
            }
        ]
    }
    """
    
    def _extract_component_info(self, source_comp_id, component):
        """
        Extract component name and version from source_comp_id or component field.
        
        Examples:
        - "gav://org.apache.sshd:sshd-core:1.0.0" -> name: "org.apache.sshd:sshd-core", version: "1.0.0"
        - "deb://debian:stretch:libx11:2:1.6.4-3" -> name: "debian:stretch:libx11", version: "2:1.6.4-3"
        """
        if not source_comp_id:
            return component, ""
        
        # Remove protocol prefix (gav://, deb://, etc.)
        parts = source_comp_id.split("://")
        if len(parts) < 2:
            return component, ""
        
        path = parts[1]
        
        # For Maven (gav://), format is groupId:artifactId:version
        if source_comp_id.startswith("gav://"):
            path_parts = path.split(":")
            if len(path_parts) >= 3:
                name = ":".join(path_parts[:-1])  # groupId:artifactId
                version = path_parts[-1]  # version
                return name, version
            elif len(path_parts) == 2:
                return path_parts[0], path_parts[1]
            else:
                return path, ""
        
        # For Debian (deb://), format is debian:suite:package:epoch:version
        elif source_comp_id.startswith("deb://"):
            path_parts = path.split(":")
            if len(path_parts) >= 3:
                name = ":".join(path_parts[:3])  # debian:suite:package
                version = ":".join(path_parts[3:]) if len(path_parts) > 3 else ""
                return name, version
            else:
                return path, ""
        
        # For npm (npm://), format is package@version
        elif source_comp_id.startswith("npm://"):
            if "@" in path:
                name, version = path.rsplit("@", 1)
                return name, version
            return path, ""
        
        # Default: try to extract version from end
        # Look for common version patterns
        version_pattern = r'[:@](\d+\.\d+[\.\d]*[-\w]*)$'
        match = re.search(version_pattern, path)
        if match:
            version = match.group(1)
            name = path[:match.start()]
            return name, version
        
        return component or path, ""
    
    def _get_fixed_version(self, fixed_versions):
        """
        Extract the first fixed version from the array.
        Fixed versions can be like: ["≥ 2:1.6.4-3+deb9u1"] or ["1.3.0"]
        """
        if not fixed_versions or len(fixed_versions) == 0:
            return ""
        
        # Get first fixed version and clean it up
        fixed = fixed_versions[0]
        # Remove comparison operators if present
        fixed = re.sub(r'^[≥≤<>]+\s*', '', fixed.strip())
        return fixed
    
    def _get_cve_info(self, cves_array):
        """
        Extract CVE information from the cves array.
        Returns tuple: (cve_id, description, cvss_v3)
        """
        if not cves_array or len(cves_array) == 0:
            return None, None, None
        
        # Use the first CVE if available
        first_cve = cves_array[0]
        cve_id = first_cve.get('cve', '')
        description = first_cve.get('description', '')
        cvss_v3 = first_cve.get('cvss_v3', '')
        
        return cve_id, description, cvss_v3
    
    def parse(self, scan_instance, json_file):
        try:
            # Security: Use safe JSON loading with size limits (max 100MB for scan files)
            data = safe_json_load(json_file, max_size_mb=100)
            vulnerabilities = data.get('data', [])
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

            for vuln_data in vulnerabilities:
                # Extract basic information
                severity = vuln_data.get('severity', 'INFO').upper()
                summary = vuln_data.get('summary', 'Unknown vulnerability')
                component = vuln_data.get('component', 'Unknown')
                source_comp_id = vuln_data.get('source_comp_id', '')
                component_versions = vuln_data.get('component_versions', {})
                more_details = component_versions.get('more_details', {})
                cves = more_details.get('cves', [])
                
                # Extract component name and version
                pkg_name, pkg_version = self._extract_component_info(source_comp_id, component)
                
                # Get fixed version
                fixed_versions = component_versions.get('fixed_versions', [])
                fixed_version = self._get_fixed_version(fixed_versions)
                
                # Get CVE information
                cve_id, cve_description, cvss_v3 = self._get_cve_info(cves)
                
                # If no CVE, use a placeholder based on component and summary
                if not cve_id:
                    # Generate a unique identifier
                    cve_id = f"JFROG-XRAY-{hashlib.md5(f'{component}-{summary}'.encode()).hexdigest()[:8].upper()}"
                
                # Use CVE description if available, otherwise use summary
                description = cve_description or more_details.get('description', summary)
                
                # Add additional context to description
                description_parts = [description]
                if more_details.get('provider'):
                    description_parts.append(f"\nProvider: {more_details.get('provider')}")
                if cvss_v3:
                    description_parts.append(f"\nCVSS v3: {cvss_v3}")
                if component_versions.get('vulnerable_versions'):
                    vuln_versions = ", ".join(component_versions.get('vulnerable_versions', []))
                    description_parts.append(f"\nVulnerable versions: {vuln_versions}")
                
                full_description = "\n".join(description_parts)
                
                # Generate Hash (will be regenerated in save(), but we need it for deduplication)
                unique_str = f"{cve_id}-{pkg_name}-{pkg_version}-{release.id}"
                finding_hash = hashlib.sha256(unique_str.encode('utf-8')).hexdigest()
                seen_hashes.add(finding_hash)

                if finding_hash in existing_map:
                    # EXISTS: Prepare for Update
                    obj = existing_map[finding_hash]
                    
                    # Only update if something changed (Performance tweak)
                    needs_save = False
                    
                    if obj.status == Finding.Status.FIXED:
                        obj.status = Finding.Status.OPEN  # Regression
                        needs_save = True
                    
                    # Always update metadata
                    obj.scan = scan_instance
                    obj.last_seen = now
                    
                    # Add to update list
                    to_update.append(obj)
                else:
                    # NEW: Prepare for Create
                    # Build metadata with additional JFrog-specific data
                    metadata = {
                        'provider': more_details.get('provider', vuln_data.get('provider', '')),
                        'cvss_v3': cvss_v3,
                        'issue_type': vuln_data.get('issue_type', ''),
                        'source_id': vuln_data.get('source_id', ''),
                        'source_comp_id': vuln_data.get('source_comp_id', ''),
                        'vulnerable_versions': component_versions.get('vulnerable_versions', []),
                    }
                    
                    # Add CWE if available
                    if cves and len(cves) > 0:
                        first_cve = cves[0]
                        if 'cwe' in first_cve:
                            metadata['cwe'] = first_cve.get('cwe', [])
                        if 'cvss_v2' in first_cve:
                            metadata['cvss_v2'] = first_cve.get('cvss_v2', '')
                    
                    to_create.append(Finding(
                        scan=scan_instance,
                        title=summary,
                        description=full_description,
                        severity=severity,
                        finding_type=Finding.Type.SCA,
                        vulnerability_id=cve_id,
                        package_name=pkg_name,
                        package_version=pkg_version,
                        fix_version=fixed_version,
                        hash_id=finding_hash,
                        status=Finding.Status.OPEN,
                        metadata=metadata
                    ))

            # 2. BULK OPERATIONS (The Speed Boost)
            
            # A. Bulk Create (1 Query)
            if to_create:
                Finding.objects.bulk_create(to_create)
            
            # B. Bulk Update (1 Query)
            if to_update:
                Finding.objects.bulk_update(to_update, ['scan', 'last_seen', 'status'], batch_size=100)

            # 3. AUTO-CLOSE LOGIC (1 Query)
            all_known_hashes = set(existing_map.keys())
            missing_hashes = all_known_hashes - seen_hashes
            
            if missing_hashes:
                Finding.objects.filter(
                    scan__release=release, 
                    hash_id__in=missing_hashes
                ).exclude(status=Finding.Status.FIXED).update(  # Don't update if already fixed
                    status=Finding.Status.FIXED,
                    last_seen=now
                )

            # 4. Snapshot
            scan_instance.findings_count = len(seen_hashes)
            scan_instance.save()

            return len(seen_hashes)

        except Exception as e:
            print(f"JFrog Xray Parser Error: {e}")
            import traceback
            traceback.print_exc()
            return 0

