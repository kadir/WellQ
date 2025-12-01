#!/bin/bash
echo "=== Verifying WhiteNoise ==="
echo ""

echo "1. Check if WhiteNoise is installed:"
docker exec wellq-web python -c "import whitenoise; print('✅ WhiteNoise is installed')" 2>/dev/null && echo "   ✅ Installed" || echo "   ❌ NOT installed"
echo ""

echo "2. Check Django settings:"
docker exec wellq-web python manage.py shell << 'PYEOF'
from django.conf import settings

print("MIDDLEWARE contains WhiteNoise:")
middleware_list = list(settings.MIDDLEWARE)
has_whitenoise = any('whitenoise' in str(m).lower() for m in middleware_list)
print(f"   {'✅' if has_whitenoise else '❌'} WhiteNoise middleware: {has_whitenoise}")

if has_whitenoise:
    # Find WhiteNoise position
    for i, m in enumerate(middleware_list):
        if 'whitenoise' in str(m).lower():
            print(f"   Position: {i} (after {middleware_list[i-1] if i > 0 else 'start'})")

print(f"\nSTATIC_URL: {settings.STATIC_URL}")
print(f"STATIC_ROOT: {settings.STATIC_ROOT}")
print(f"STATICFILES_STORAGE: {getattr(settings, 'STATICFILES_STORAGE', 'NOT SET')}")
PYEOF

echo ""
echo "3. Check static files:"
docker exec wellq-web ls -la /app/staticfiles/css/ 2>/dev/null | head -3 || echo "   ❌ No CSS files found"
echo ""

echo "4. Run collectstatic:"
docker exec wellq-web python manage.py collectstatic --noinput 2>&1 | tail -3
echo ""

echo "✅ If everything above looks good, test: https://demo.wellq.io/static/css/dashboard.css"


