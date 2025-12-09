from django import template
from core.scanners import get_scanner_type

register = template.Library()

@register.filter
def get_scanner_type(scanner_name):
    """Template filter to get scanner type"""
    from core.scanners import get_scanner_type as _get_scanner_type
    return _get_scanner_type(scanner_name)






