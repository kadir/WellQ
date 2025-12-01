#!/bin/bash
echo "=== WhiteNoise Diagnostic ==="
echo ""

echo "1. Check if WhiteNoise is installed:"
docker exec wellq-web python -c "import whitenoise; print('✅ WhiteNoise version:', whitenoise.__version__)" 2>/dev/null || echo "❌ WhiteNoise NOT installed"
echo ""

echo "2. Check Django settings:"
docker exec wellq-web python manage.py shell << 'PYEOF'
from django.conf import settings
import os

print("MIDDLEWARE contains WhiteNoise:")
middleware_str = str(settings.MIDDLEWARE)
if 'whitenoise' in middleware_str.lower():
    print("   ✅ WhiteNoise middleware is configured")
else:
    print("   ❌ WhiteNoise middleware NOT found")
    print(f"   Middleware: {settings.MIDDLEWARE[:3]}...")

print(f"\nSTATIC_URL: {settings.STATIC_URL}")
print(f"STATIC_ROOT: {settings.STATIC_ROOT}")
print(f"STATICFILES_STORAGE: {getattr(settings, 'STATICFILES_STORAGE', 'NOT SET')}")
PYEOF

echo ""
echo "3. Check if static files exist:"
docker exec wellq-web ls -la /app/staticfiles/css/ 2>/dev/null | head -5 || echo "   ❌ staticfiles/css/ does not exist"
echo ""

echo "4. Check WhiteNoise manifest:"
docker exec wellq-web ls -la /app/staticfiles/staticfiles.json 2>/dev/null && echo "   ✅ Manifest exists" || echo "   ⚠️  Manifest not found (run collectstatic)"
echo ""

echo "5. Test URL resolution:"
docker exec wellq-web python manage.py shell << 'PYEOF'
from django.urls import get_resolver
try:
    resolver = get_resolver()
    match = resolver.resolve('/static/css/dashboard.css')
    print(f"   ✅ URL resolves: {match}")
except Exception as e:
    print(f"   ❌ URL does NOT resolve: {e}")
PYEOF

echo ""
echo "6. Check if collectstatic ran:"
docker-compose -f docker-compose.simple.yml logs web | grep -i "collectstatic\|static files" | tail -3
echo ""

echo "✅ If WhiteNoise is not installed, rebuild: docker-compose -f docker-compose.simple.yml build web"
echo "✅ If manifest is missing, run: docker exec wellq-web python manage.py collectstatic --noinput"


