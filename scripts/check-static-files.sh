#!/bin/bash
echo "=== Checking Static Files Configuration ==="
echo ""

echo "1. Environment Variables:"
docker exec wellq-web env | grep -E "(SERVE_STATIC|STATIC)" || echo "   (none found)"
echo ""

echo "2. Django Settings:"
docker exec wellq-web python manage.py shell << 'PYEOF'
from django.conf import settings
import os
print("STATIC_URL:", settings.STATIC_URL)
print("STATIC_ROOT:", settings.STATIC_ROOT)
print("SERVE_STATIC env:", os.getenv('SERVE_STATIC', 'NOT SET'))
print("DEBUG:", settings.DEBUG)
PYEOF

echo ""
echo "3. Static Files in Container:"
docker exec wellq-web ls -la /app/staticfiles/css/ 2>/dev/null || echo "   ❌ /app/staticfiles/css/ does not exist"
echo ""

echo "4. Test Static File Access:"
docker exec wellq-web test -f /app/staticfiles/css/dashboard.css && echo "   ✅ dashboard.css exists" || echo "   ❌ dashboard.css NOT found"
docker exec wellq-web test -f /app/staticfiles/css/forms.css && echo "   ✅ forms.css exists" || echo "   ❌ forms.css NOT found"
echo ""

echo "5. Check if collectstatic ran:"
docker-compose -f docker-compose.simple.yml logs web | grep -i collectstatic | tail -5
echo ""

echo "✅ If files don't exist, run: docker exec wellq-web python manage.py collectstatic --noinput"


