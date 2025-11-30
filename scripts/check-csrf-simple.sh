#!/bin/bash
# Simple script to check CSRF configuration

echo "=== CSRF Configuration Check ==="
echo ""

echo "1. Environment Variables:"
echo "   ALLOWED_HOSTS:"
docker exec wellq-web env | grep ALLOWED_HOSTS || echo "   ❌ Not set"
echo ""
echo "   USE_PROXY:"
docker exec wellq-web env | grep USE_PROXY || echo "   ❌ Not set (needs to be 'true')"
echo ""
echo "   CSRF_TRUSTED_ORIGINS:"
docker exec wellq-web env | grep CSRF_TRUSTED_ORIGINS || echo "   ⚠️  Not set (will auto-configure)"
echo ""

echo "2. Django Settings:"
docker exec wellq-web python manage.py shell -c "
from django.conf import settings
import os
print('DEBUG:', settings.DEBUG)
print('ALLOWED_HOSTS:', settings.ALLOWED_HOSTS)
print('CSRF_TRUSTED_ORIGINS:', settings.CSRF_TRUSTED_ORIGINS)
print('USE_PROXY env:', os.getenv('USE_PROXY', 'NOT SET'))
print('SECURE_PROXY_SSL_HEADER:', settings.SECURE_PROXY_SSL_HEADER)
"

echo ""
echo "✅ If CSRF_TRUSTED_ORIGINS includes 'https://demo.wellq.io', you're good!"
echo "❌ If it's empty, set USE_PROXY=true and restart the container"

