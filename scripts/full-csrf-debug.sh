#!/bin/bash
echo "=== Full CSRF Debug ==="
echo ""
echo "1. Environment Variables in Container:"
docker exec wellq-web env | grep -E "(ALLOWED_HOSTS|USE_PROXY|CSRF|DEBUG)" | sort
echo ""
echo "2. Django Settings - Detailed:"
docker exec wellq-web python manage.py shell << 'PYEOF'
from django.conf import settings
import os

print("=" * 50)
print("Environment Variables:")
print(f"  ALLOWED_HOSTS env: '{os.getenv('ALLOWED_HOSTS', 'NOT SET')}'")
print(f"  CSRF_TRUSTED_ORIGINS env: '{os.getenv('CSRF_TRUSTED_ORIGINS', 'NOT SET')}'")
print(f"  USE_PROXY env: '{os.getenv('USE_PROXY', 'NOT SET')}'")
print(f"  DEBUG env: '{os.getenv('DEBUG', 'NOT SET')}'")
print("")
print("Django Settings:")
print(f"  DEBUG: {settings.DEBUG} (type: {type(settings.DEBUG)})")
print(f"  ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
print(f"  ALLOWED_HOSTS type: {type(settings.ALLOWED_HOSTS)}")
print(f"  ALLOWED_HOSTS length: {len(settings.ALLOWED_HOSTS) if settings.ALLOWED_HOSTS else 0}")
print(f"  ALLOWED_HOSTS is truthy: {bool(settings.ALLOWED_HOSTS)}")
print("")
print("CSRF Configuration:")
print(f"  CSRF_TRUSTED_ORIGINS: {settings.CSRF_TRUSTED_ORIGINS}")
print(f"  CSRF_TRUSTED_ORIGINS type: {type(settings.CSRF_TRUSTED_ORIGINS)}")
print(f"  CSRF_TRUSTED_ORIGINS length: {len(settings.CSRF_TRUSTED_ORIGINS) if settings.CSRF_TRUSTED_ORIGINS else 0}")
print("")
print("Logic Check:")
print(f"  not CSRF_TRUSTED_ORIGINS: {not settings.CSRF_TRUSTED_ORIGINS}")
print(f"  ALLOWED_HOSTS exists: {bool(settings.ALLOWED_HOSTS)}")
print(f"  Condition should be: {not settings.CSRF_TRUSTED_ORIGINS and settings.ALLOWED_HOSTS}")
PYEOF

