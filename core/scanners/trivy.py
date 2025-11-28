import json
from core.findings.models import Finding
from .base import BaseScanner

class TrivyScanner(BaseScanner):
    
    def parse(self, scan_instance, json_file):
        try:
            # Reset file pointer
            json_file.seek(0)
            data = json.load(json_file)
            
            # Trivy Logic
            results = data.get('Results', [])
            findings_to_create = []

            for result in results:
                vulnerabilities = result.get('Vulnerabilities', [])

                for vuln in vulnerabilities:
                    severity = vuln.get('Severity', 'INFO').upper()
                    
                    finding = Finding(
                        scan=scan_instance,
                        title=vuln.get('Title', 'Unknown Vulnerability'),
                        cve_id=vuln.get('VulnerabilityID', 'Unknown'),
                        severity=severity,
                        description=vuln.get('Description', ''),
                        package_name=vuln.get('PkgName', 'Unknown'),
                        package_version=vuln.get('InstalledVersion', 'Unknown'),
                        fixed_version=vuln.get('FixedVersion', ''),
                    )
                    findings_to_create.append(finding)

            # Bulk Save
            if findings_to_create:
                Finding.objects.bulk_create(findings_to_create)
            
            return len(findings_to_create)

        except Exception as e:
            print(f"Trivy Parsing Error: {e}")
            return 0