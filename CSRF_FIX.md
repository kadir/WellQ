# CSRF Error Fix for HTTPS

## Problem

When accessing your site via HTTPS (e.g., `https://demo.wellq.io`), you get this error:

```
Forbidden (403)
CSRF verification failed. Request aborted.
Origin checking failed - https://demo.wellq.io does not match any trusted origins.
```

## Solution

Django needs to know which origins to trust for CSRF protection. This is already fixed in the code, but you need to configure it.

## Quick Fix

### Option 1: Set in `.env` file (Recommended)

Create or edit your `.env` file:

```env
# CSRF Trusted Origins
CSRF_TRUSTED_ORIGINS=https://demo.wellq.io

# Also set these for HTTPS behind nginx
USE_PROXY=true
SECURE_SSL_REDIRECT=true
ALLOWED_HOSTS=demo.wellq.io,localhost,127.0.0.1
```

Then restart:
```bash
docker-compose -f docker-compose.simple.yml restart web
```

### Option 2: Auto-Configuration (Already Done!)

The code now **automatically** adds HTTPS origins from `ALLOWED_HOSTS` when:
- `USE_PROXY=true` is set, OR
- `DEBUG=False` (production mode)

So if you have:
```env
ALLOWED_HOSTS=demo.wellq.io
USE_PROXY=true
```

Django will automatically trust `https://demo.wellq.io` for CSRF!

## Complete Production `.env` File

For production with HTTPS and nginx:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=False
ENVIRONMENT=production
ALLOWED_HOSTS=demo.wellq.io,localhost,127.0.0.1

# CSRF Trusted Origins (auto-configured from ALLOWED_HOSTS if USE_PROXY=true)
CSRF_TRUSTED_ORIGINS=https://demo.wellq.io

# SSL/HTTPS Settings (when behind nginx)
SECURE_SSL_REDIRECT=true
USE_PROXY=true

# Static Files (nginx will serve them)
SERVE_STATIC=false

# Database (auto-configured in docker-compose)
DB_ENGINE=postgresql
DB_NAME=wellq
DB_USER=wellq
DB_PASSWORD=your-database-password

# Redis (auto-configured in docker-compose)
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

## Verify It's Working

1. **Restart your containers:**
```bash
docker-compose -f docker-compose.simple.yml restart web
```

2. **Check the logs:**
```bash
docker-compose -f docker-compose.simple.yml logs web | tail -20
```

3. **Test in browser:**
- Visit: `https://demo.wellq.io`
- Try to log in or submit a form
- Should work without CSRF errors!

## What Changed?

The code now:
1. ✅ Automatically adds HTTPS origins to `CSRF_TRUSTED_ORIGINS` from `ALLOWED_HOSTS`
2. ✅ Respects `CSRF_TRUSTED_ORIGINS` environment variable if set
3. ✅ Works correctly in both development and production
4. ✅ Handles HTTPS behind nginx proxy correctly

## Troubleshooting

### Still getting CSRF errors?

1. **Check your `.env` file:**
```bash
cat .env | grep -i csrf
cat .env | grep -i allowed
cat .env | grep -i proxy
```

2. **Verify environment variables are loaded:**
```bash
docker exec wellq-web env | grep -i csrf
docker exec wellq-web env | grep ALLOWED_HOSTS
```

3. **Check Django settings:**
```bash
docker exec wellq-web python manage.py shell
>>> from django.conf import settings
>>> print(settings.CSRF_TRUSTED_ORIGINS)
>>> print(settings.ALLOWED_HOSTS)
```

4. **Clear browser cookies** - Sometimes old cookies cause issues

### Multiple Domains?

If you have multiple domains, add them all:

```env
CSRF_TRUSTED_ORIGINS=https://demo.wellq.io,https://www.wellq.io,https://wellq.io
ALLOWED_HOSTS=demo.wellq.io,www.wellq.io,wellq.io
```

## Summary

✅ **Fixed!** The code now automatically handles CSRF trusted origins for HTTPS.

Just make sure you have:
- `ALLOWED_HOSTS` set correctly
- `USE_PROXY=true` when behind nginx
- Restart your containers

That's it! 🎉


