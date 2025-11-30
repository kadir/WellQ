# Final CSRF Fix - Step by Step

## The Problem
Even though `CSRF_TRUSTED_ORIGINS` is set in docker-compose.simple.yml, Django shows it as empty.

## Solution: Verify and Fix

### Step 1: Check if environment variable reaches container

```bash
docker exec wellq-web env | grep CSRF_TRUSTED_ORIGINS
```

**Expected output:**
```
CSRF_TRUSTED_ORIGINS=https://demo.wellq.io
```

If you see nothing, the environment variable isn't reaching the container.

### Step 2: If env var is NOT in container

**Option A: Recreate the container (not just restart)**

```bash
docker-compose -f docker-compose.simple.yml down
docker-compose -f docker-compose.simple.yml up -d
```

**Option B: Hardcode it directly in docker-compose.simple.yml**

Change line 65 from:
```yaml
CSRF_TRUSTED_ORIGINS: ${CSRF_TRUSTED_ORIGINS:-https://demo.wellq.io}
```

To:
```yaml
CSRF_TRUSTED_ORIGINS: "https://demo.wellq.io"
```

Then recreate:
```bash
docker-compose -f docker-compose.simple.yml down
docker-compose -f docker-compose.simple.yml up -d
```

### Step 3: Rebuild to get updated code

```bash
docker-compose -f docker-compose.simple.yml build web
docker-compose -f docker-compose.simple.yml restart web
```

### Step 4: Verify it works

```bash
docker exec wellq-web python manage.py shell -c "
from django.conf import settings
import os
print('CSRF_TRUSTED_ORIGINS env:', os.getenv('CSRF_TRUSTED_ORIGINS'))
print('CSRF_TRUSTED_ORIGINS setting:', settings.CSRF_TRUSTED_ORIGINS)
"
```

**Expected output:**
```
CSRF_TRUSTED_ORIGINS env: https://demo.wellq.io
CSRF_TRUSTED_ORIGINS setting: ['https://demo.wellq.io']
```

## Quick Fix (Guaranteed to Work)

If nothing else works, hardcode it directly in `core/settings.py`:

Find this section (around line 67):
```python
# CSRF Trusted Origins - Required for HTTPS behind proxy
```

Replace the entire CSRF_TRUSTED_ORIGINS section with:
```python
# CSRF Trusted Origins - Required for HTTPS behind proxy
CSRF_TRUSTED_ORIGINS = ['https://demo.wellq.io']
```

Then rebuild:
```bash
docker-compose -f docker-compose.simple.yml build web
docker-compose -f docker-compose.simple.yml restart web
```

This will definitely work, but it's less flexible.

