# WhiteNoise Setup - Step by Step

## The Problem
Static files are returning 404 even after WhiteNoise setup.

## Solution: Complete Setup Steps

### Step 1: Rebuild Container (CRITICAL)

WhiteNoise must be installed. Rebuild the container:

```bash
docker-compose -f docker-compose.simple.yml build --no-cache web
```

**Important:** Use `--no-cache` to ensure WhiteNoise is installed.

### Step 2: Recreate Container

```bash
docker-compose -f docker-compose.simple.yml down
docker-compose -f docker-compose.simple.yml up -d
```

### Step 3: Run collectstatic with WhiteNoise

WhiteNoise needs to generate a manifest file:

```bash
docker exec wellq-web python manage.py collectstatic --noinput --clear
```

The `--clear` flag ensures old files are removed and WhiteNoise manifest is regenerated.

### Step 4: Verify WhiteNoise is Installed

```bash
docker exec wellq-web python -c "import whitenoise; print('WhiteNoise version:', whitenoise.__version__)"
```

Should show: `WhiteNoise version: 6.6.0`

### Step 5: Check Middleware

```bash
docker exec wellq-web python manage.py shell -c "
from django.conf import settings
middleware = str(settings.MIDDLEWARE)
print('WhiteNoise in middleware:', 'whitenoise' in middleware.lower())
"
```

Should show: `WhiteNoise in middleware: True`

### Step 6: Test Static File

Visit: `https://demo.wellq.io/static/css/dashboard.css`

Should return CSS content, not 404.

## Troubleshooting

### If WhiteNoise is not installed:

```bash
# Check if it's in requirements.txt
grep whitenoise requirements.txt

# Rebuild with no cache
docker-compose -f docker-compose.simple.yml build --no-cache web
docker-compose -f docker-compose.simple.yml restart web
```

### If collectstatic fails:

```bash
# Check logs
docker-compose -f docker-compose.simple.yml logs web | grep -i collectstatic

# Run manually
docker exec wellq-web python manage.py collectstatic --noinput --clear -v 2
```

### If still 404:

1. **Check nginx is not intercepting:**
   - Make sure nginx `/static/` location is commented out
   - Reload nginx: `sudo systemctl reload nginx`

2. **Check WhiteNoise middleware order:**
   - Must be right after `SecurityMiddleware`
   - Check: `docker exec wellq-web python manage.py shell -c "from django.conf import settings; print(settings.MIDDLEWARE[:2])"`

3. **Check static files exist:**
   ```bash
   docker exec wellq-web ls -la /app/staticfiles/css/
   ```

## Quick Fix Script

Run this to check everything:

```bash
chmod +x scripts/check-whitenoise.sh
./scripts/check-whitenoise.sh
```

This will show you exactly what's wrong.


