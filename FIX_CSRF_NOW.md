# Fix CSRF Right Now

## The Issue

Your `.env` file has `CSRF_TRUSTED_ORIGINS=https://demo.wellq.io`, but Django shows `CSRF_TRUSTED_ORIGINS: []`.

## Why It's Not Working

The environment variable might not be reaching the container, OR the auto-configuration logic isn't triggering.

## Solution: Force It in docker-compose.simple.yml

Since you have `USE_PROXY=true` and `ALLOWED_HOSTS=demo.wellq.io`, the auto-config should work. But let's make sure:

### Step 1: Check Current Values

```bash
docker exec wellq-web python manage.py shell -c "
from django.conf import settings
import os
print('DEBUG:', settings.DEBUG)
print('ALLOWED_HOSTS:', settings.ALLOWED_HOSTS)
print('USE_PROXY env:', os.getenv('USE_PROXY'))
print('CSRF_TRUSTED_ORIGINS env:', os.getenv('CSRF_TRUSTED_ORIGINS'))
print('CSRF_TRUSTED_ORIGINS setting:', settings.CSRF_TRUSTED_ORIGINS)
"
```

### Step 2: Force the Value in docker-compose.simple.yml

Edit `docker-compose.simple.yml` and change line 65 from:
```yaml
CSRF_TRUSTED_ORIGINS: ${CSRF_TRUSTED_ORIGINS:-https://demo.wellq.io}
```

To (hardcode it):
```yaml
CSRF_TRUSTED_ORIGINS: "https://demo.wellq.io"
```

### Step 3: Restart

```bash
docker-compose -f docker-compose.simple.yml down
docker-compose -f docker-compose.simple.yml up -d
```

### Step 4: Verify

```bash
docker exec wellq-web python manage.py shell -c "from django.conf import settings; print('CSRF_TRUSTED_ORIGINS:', settings.CSRF_TRUSTED_ORIGINS)"
```

Should show: `CSRF_TRUSTED_ORIGINS: ['https://demo.wellq.io']`

## Alternative: The Auto-Config Should Work

With your current `.env`:
- `USE_PROXY=true` ✅
- `ALLOWED_HOSTS=demo.wellq.io,localhost,127.0.0.1` ✅
- `DEBUG=False` ✅

The auto-config should detect `demo.wellq.io` as a domain and add it. But it's not working. Let me check the logic...

Actually, the updated code should work now. Try restarting:

```bash
docker-compose -f docker-compose.simple.yml restart web
docker exec wellq-web python manage.py shell -c "from django.conf import settings; print('CSRF_TRUSTED_ORIGINS:', settings.CSRF_TRUSTED_ORIGINS)"
```

