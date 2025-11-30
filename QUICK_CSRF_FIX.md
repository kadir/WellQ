# Quick CSRF Fix for demo.wellq.io

## The Problem

You're getting CSRF errors because `CSRF_TRUSTED_ORIGINS` is not configured.

## The Solution (Choose One)

### Option 1: Set USE_PROXY=true (Recommended)

Create/update `.env` file:
```env
USE_PROXY=true
ALLOWED_HOSTS=demo.wellq.io,localhost,127.0.0.1
```

Then restart:
```bash
docker-compose -f docker-compose.simple.yml restart web
```

### Option 2: Explicitly Set CSRF_TRUSTED_ORIGINS

Create/update `.env` file:
```env
CSRF_TRUSTED_ORIGINS=https://demo.wellq.io
ALLOWED_HOSTS=demo.wellq.io,localhost,127.0.0.1
```

Then restart:
```bash
docker-compose -f docker-compose.simple.yml restart web
```

### Option 3: Set DEBUG=False (Production Mode)

The code now auto-configures CSRF when it detects a domain (not localhost).

Create/update `.env` file:
```env
DEBUG=False
ALLOWED_HOSTS=demo.wellq.io,localhost,127.0.0.1
```

Then restart:
```bash
docker-compose -f docker-compose.simple.yml restart web
```

## Verify It Works

Run this command:
```bash
docker exec wellq-web python manage.py shell -c "from django.conf import settings; print('CSRF_TRUSTED_ORIGINS:', settings.CSRF_TRUSTED_ORIGINS)"
```

You should see:
```
CSRF_TRUSTED_ORIGINS: ['https://demo.wellq.io']
```

## Complete Production .env File

For production with nginx and SSL:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=False
ENVIRONMENT=production
ALLOWED_HOSTS=demo.wellq.io,localhost,127.0.0.1

# CSRF (auto-configured, but you can set explicitly)
CSRF_TRUSTED_ORIGINS=https://demo.wellq.io

# SSL/HTTPS (when behind nginx)
USE_PROXY=true
SECURE_SSL_REDIRECT=true

# Static Files (nginx will serve them)
SERVE_STATIC=false
```

## What Changed?

The code now automatically detects when you're using a domain (like `demo.wellq.io`) and adds it to `CSRF_TRUSTED_ORIGINS` with `https://` prefix, even if `USE_PROXY` is not set.

But it's still recommended to set `USE_PROXY=true` for proper proxy header handling.

