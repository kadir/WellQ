# Fix: Nginx Intercepting Static Files

## The Problem

Nginx is configured to serve static files from `/opt/WellQ/staticfiles/`, but the files are in the Docker container at `/app/staticfiles/`. Nginx intercepts the request first and returns 404.

## Solution: Comment Out Nginx Static Location

Since you have `SERVE_STATIC=true`, Django should serve the files. But nginx is intercepting first.

### Option 1: Comment Out Nginx Static Location (Quick Fix)

Edit `/etc/nginx/sites-available/wellq` and comment out the static files location:

```nginx
# Static files - served directly by nginx (faster)
# COMMENTED OUT: Let Django serve static files when SERVE_STATIC=true
# location /static/ {
#     alias /opt/WellQ/staticfiles/;
#     expires 30d;
#     add_header Cache-Control "public, immutable";
#     access_log off;
# }
```

Then reload nginx:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

### Option 2: Mount Static Files to Host (Better for Production)

If you want nginx to serve static files (faster), mount the Docker volume to the host:

1. **Update docker-compose.simple.yml** to mount staticfiles to host:
```yaml
volumes:
  - /opt/WellQ/staticfiles:/app/staticfiles  # Mount to host
  - media_volume:/app/media
```

2. **Ensure nginx can read the files:**
```bash
sudo chown -R www-data:www-data /opt/WellQ/staticfiles
sudo chmod -R 755 /opt/WellQ/staticfiles
```

3. **Set SERVE_STATIC=false** in .env

4. **Restart containers:**
```bash
docker-compose -f docker-compose.simple.yml down
docker-compose -f docker-compose.simple.yml up -d
```

### Option 3: Verify Django URL Pattern (Debug)

Test if Django URL pattern is registered:

```bash
docker exec wellq-web python manage.py shell -c "
from django.urls import get_resolver
resolver = get_resolver()
patterns = [str(p) for p in resolver.url_patterns]
static_patterns = [p for p in patterns if 'static' in p.lower()]
print('Static patterns:', static_patterns)
"
```

If empty, the URL pattern isn't being added. Check that `SERVE_STATIC=true` is being read.

## Quick Fix Right Now

**Comment out the nginx static location block**, then:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Then test: `https://demo.wellq.io/static/css/dashboard.css`

This should work immediately!


