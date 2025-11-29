from .trivy import TrivyScanner

# Scanner Type Classifications
# Maps scanner names to their type (SCA, SAST, DAST, etc.)
SCANNER_TYPES = {
    'Trivy': 'SCA Scan',
    'Grype': 'SCA Scan',
    'Snyk': 'SCA Scan',
    'Dependabot': 'SCA Scan',
    'SonarQube': 'SAST Scan',
    'Bandit': 'SAST Scan',
    'Semgrep': 'SAST Scan',
    'CodeQL': 'SAST Scan',
    'OWASP ZAP': 'DAST Scan',
    'Burp Suite': 'DAST Scan',
    'Nessus': 'DAST Scan',
}

# 1. The Registry Dictionary
# Key = The name shown in the UI
# Value = The Class that handles it
SCANNER_REGISTRY = {
    'Trivy': TrivyScanner,
    # 'Grype': GrypeScanner,       <-- Easy to add later
    # 'SonarQube': SonarScanner,   <-- Easy to add later
}

def get_scanner(name):
    """Factory function to return the correct scanner instance"""
    scanner_class = SCANNER_REGISTRY.get(name)
    if scanner_class:
        return scanner_class()
    return None

def get_scanner_type(scanner_name):
    """Get the type/category of a scanner"""
    return SCANNER_TYPES.get(scanner_name, 'Unknown Scan')