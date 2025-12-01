#!/usr/bin/env python
"""Test if static URL pattern is registered"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
from django.urls import get_resolver
from django.conf.urls.static import static

print("=" * 50)
print("Static Files Configuration")
print("=" * 50)
print(f"STATIC_URL: {settings.STATIC_URL}")
print(f"STATIC_ROOT: {settings.STATIC_ROOT}")
print(f"SERVE_STATIC env: {os.getenv('SERVE_STATIC', 'NOT SET')}")
print(f"DEBUG: {settings.DEBUG}")
print(f"Should serve static: {settings.DEBUG or os.getenv('SERVE_STATIC', 'False').lower() == 'true'}")
print()

print("=" * 50)
print("URL Patterns")
print("=" * 50)
resolver = get_resolver()
url_patterns = resolver.url_patterns

# Check if static pattern exists
static_pattern_found = False
for pattern in url_patterns:
    pattern_str = str(pattern)
    if 'static' in pattern_str.lower() or '/static/' in pattern_str:
        print(f"Found pattern: {pattern}")
        static_pattern_found = True

if not static_pattern_found:
    print("❌ No static URL pattern found!")
    print("   This means Django is NOT serving static files")
else:
    print("✅ Static URL pattern is registered")

print()
print("=" * 50)
print("Testing URL Resolution")
print("=" * 50)
try:
    match = resolver.resolve('/static/css/dashboard.css')
    print(f"✅ URL resolves to: {match}")
except Exception as e:
    print(f"❌ URL does not resolve: {e}")


