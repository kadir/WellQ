# Fix Static Files 404 Error

## The Problem
CSS files are returning 404 errors. You have `SERVE_STATIC=false` which means nginx should serve them, but nginx might not be configured or the files aren't accessible.

## Quick Fix: Enable Django to Serve Static Files

Since nginx might not be set up yet, let's enable Django to serve static files:

### Step 1: Update .env file

Add or change this line:
```env
SERVE_STATIC=true
```

### Step 2: Restart the container

```bash
docker-compose -f docker-compose.simple.yml restart web
```

### Step 3: Verify static files exist

```bash
docker exec wellq-web ls -la /app/staticfiles/css/
```

You should see:
- `dashboard.css`
- `forms.css`
- `auth.css`

### Step 4: Test in browser

Visit: `https://demo.wellq.io/static/css/dashboard.css`

Should return CSS content, not 404.

## If Files Don't Exist: Run collectstatic

```bash
docker exec wellq-web python manage.py collectstatic --noinput
```

## For Production with Nginx (Later)

Once nginx is properly configured:

1. **Mount staticfiles volume to host:**
   - The nginx config expects files at `/opt/WellQ/staticfiles/`
   - But Docker has them at `/app/staticfiles/` inside container
   - You need to mount the volume or copy files to host

2. **Or use WhiteNoise** (easier for Docker):
   - See `STATIC_FILES_SETUP.md` for WhiteNoise setup

## Verify It's Working

After setting `SERVE_STATIC=true` and restarting:

1. Check browser console - CSS 404 errors should be gone
2. Visit `https://demo.wellq.io` - page should have styling
3. Check Django logs: `docker-compose -f docker-compose.simple.yml logs web | tail -20`


