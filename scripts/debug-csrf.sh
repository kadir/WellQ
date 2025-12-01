#!/bin/bash
echo "=== Debugging CSRF Configuration ==="
echo ""
echo "1. Environment Variables:"
docker exec wellq-web env | grep -E "(ALLOWED_HOSTS|USE_PROXY|CSRF|DEBUG)" | sort
echo ""
echo "2. Django Settings:"
docker exec wellq-web python manage.py shell << 'PYEOF'
from django.conf import settings
import os
print("DEBUG:", settings.DEBUG)
print("ALLOWED_HOSTS:", settings.ALLOWED_HOSTS)
print("ALLOWED_HOSTS type:", type(settings.ALLOWED_HOSTS))
print("ALLOWED_HOSTS length:", len(settings.ALLOWED_HOSTS) if settings.ALLOWED_HOSTS else 0)
print("USE_PROXY env:", os.getenv('USE_PROXY', 'NOT SET'))
print("USE_PROXY bool:", os.getenv('USE_PROXY', 'False').lower() == 'true')
print("CSRF_TRUSTED_ORIGINS env:", os.getenv('CSRF_TRUSTED_ORIGINS', 'NOT SET'))
print("CSRF_TRUSTED_ORIGINS setting:", settings.CSRF_TRUSTED_ORIGINS)
print("CSRF_TRUSTED_ORIGINS type:", type(settings.CSRF_TRUSTED_ORIGINS))
PYEOF


