from .trivy import TrivyScanner

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