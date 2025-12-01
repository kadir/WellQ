# Static Files Setup Guide

## Problem
Static files (CSS, JS) are returning HTML (404 pages) instead of the actual files. This happens because Django doesn't serve static files in production by default.

## Solutions

### Option 1: Django Serves Static Files (Quick Fix - For Testing)

This is already configured in `core/urls.py`. Just set the environment variable:

```bash
# In docker-compose.simple.yml or .env file
SERVE_STATIC=true
```

**Pros:**
- Quick to set up
- Works immediately

**Cons:**
- Not recommended for production
- Slower than nginx
- Uses Django worker processes

### Option 2: Nginx Serves Static Files (Recommended for Production)

1. **Install nginx** on your server:
```bash
sudo apt-get update
sudo apt-get install nginx
```

2. **Create nginx configuration** (`/etc/nginx/sites-available/wellq`):
```nginx
server {
    listen 80;
    server_name 157.180.86.151;  # Your server IP or domain

    # Static files
    location /static/ {
        alias /opt/WellQ/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /opt/WellQ/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # Proxy to Django
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

3. **Enable the site**:
```bash
sudo ln -s /etc/nginx/sites-available/wellq /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl reload nginx
```

4. **Set SERVE_STATIC=false** in your environment:
```bash
SERVE_STATIC=false
```

5. **Restart Django**:
```bash
docker-compose -f docker-compose.simple.yml restart web
```

### Option 3: Use WhiteNoise (Recommended for Docker)

WhiteNoise is a Django package that efficiently serves static files.

1. **Add to requirements.txt**:
```
whitenoise==6.6.0
```

2. **Update settings.py**:
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add this
    # ... rest of middleware
]

# WhiteNoise configuration
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

3. **Rebuild and restart**:
```bash
docker-compose -f docker-compose.simple.yml build
docker-compose -f docker-compose.simple.yml up -d
```

## Current Configuration

The current setup:
- ✅ `collectstatic` runs automatically in `docker-entrypoint-simple.sh`
- ✅ Static files are collected to `/app/staticfiles/`
- ✅ `SERVE_STATIC=true` enables Django to serve static files
- ✅ `STATIC_URL = '/static/'` is correctly configured

## Troubleshooting

### Check if static files exist:
```bash
docker exec wellq-web ls -la /app/staticfiles/css/
```

### Check collectstatic logs:
```bash
docker-compose -f docker-compose.simple.yml logs web | grep collectstatic
```

### Manually run collectstatic:
```bash
docker exec wellq-web python manage.py collectstatic --noinput
```

### Verify static files URL:
Visit: `http://157.180.86.151:8000/static/css/dashboard.css`
- Should return CSS content, not HTML

## Tailwind CSS CDN Warning

The browser warning about Tailwind CDN is expected. For production, you should:

1. **Build Tailwind properly** using PostCSS or Tailwind CLI
2. **Include compiled CSS** in your static files
3. **Remove CDN script** from templates

For now, the CDN works but is not optimal for production.


