#!/bin/bash
# Script to check CSRF configuration in Django

echo "🔍 Checking CSRF Configuration..."
echo ""

echo "1. Environment Variables:"
echo "   ALLOWED_HOSTS:"
docker exec wellq-web env | grep ALLOWED_HOSTS || echo "   ❌ Not set"
echo ""
echo "   USE_PROXY:"
docker exec wellq-web env | grep USE_PROXY || echo "   ❌ Not set (should be 'true' for HTTPS)"
echo ""
echo "   CSRF_TRUSTED_ORIGINS:"
docker exec wellq-web env | grep CSRF_TRUSTED_ORIGINS || echo "   ⚠️  Not set (will be auto-configured)"
echo ""

echo "2. Django Settings (actual values):"
echo ""
docker exec wellq-web python manage.py shell << 'EOF'
from django.conf import settings
print(f"   DEBUG: {settings.DEBUG}")
print(f"   ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
print(f"   CSRF_TRUSTED_ORIGINS: {settings.CSRF_TRUSTED_ORIGINS}")
print(f"   USE_PROXY (from env): {getattr(settings, 'USE_PROXY', 'Not set')}")
print(f"   SECURE_PROXY_SSL_HEADER: {settings.SECURE_PROXY_SSL_HEADER}")
print(f"   CSRF_COOKIE_SECURE: {getattr(settings, 'CSRF_COOKIE_SECURE', 'Not set')}")
EOF

echo ""
echo "✅ If CSRF_TRUSTED_ORIGINS includes 'https://demo.wellq.io', you're good!"
echo ""


