#!/bin/bash
echo "=== Testing Static File Serving ==="
echo ""

echo "1. Test if file exists in container:"
docker exec wellq-web test -f /app/staticfiles/css/dashboard.css && echo "   ✅ File exists" || echo "   ❌ File NOT found"
echo ""

echo "2. Test Django URL resolution:"
docker exec wellq-web python manage.py shell << 'PYEOF'
from django.urls import get_resolver
from django.conf import settings
import os

resolver = get_resolver()

# Try to resolve the static URL
try:
    match = resolver.resolve('/static/css/dashboard.css')
    print(f"   ✅ URL resolves: {match}")
except Exception as e:
    print(f"   ❌ URL does NOT resolve: {e}")

# Check if static pattern is registered
patterns = [str(p) for p in resolver.url_patterns]
static_patterns = [p for p in patterns if 'static' in p.lower()]
print(f"   Static patterns found: {len(static_patterns)}")
if static_patterns:
    for p in static_patterns[:3]:
        print(f"      - {p}")

# Check settings
print(f"\n   SERVE_STATIC env: {os.getenv('SERVE_STATIC', 'NOT SET')}")
print(f"   DEBUG: {settings.DEBUG}")
print(f"   STATIC_URL: {settings.STATIC_URL}")
print(f"   STATIC_ROOT: {settings.STATIC_ROOT}")
PYEOF

echo ""
echo "3. Test direct file access:"
docker exec wellq-web head -5 /app/staticfiles/css/dashboard.css
echo ""

echo "4. Test HTTP request from inside container:"
docker exec wellq-web curl -I http://localhost:8000/static/css/dashboard.css 2>/dev/null | head -5
echo ""


