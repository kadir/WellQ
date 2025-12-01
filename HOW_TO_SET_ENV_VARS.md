# How to Set Environment Variables for WellQ

This guide shows you how to set environment variables like `SERVE_STATIC=false`.

## Option 1: Create/Edit `.env` File (Easiest - Recommended)

Create a file named `.env` in your project root directory (same folder as `docker-compose.simple.yml`):

```bash
# Create .env file
nano .env
# or
vim .env
# or use any text editor
```

Add this line to the `.env` file:

```env
SERVE_STATIC=false
```

**Full example `.env` file:**

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=False
ENVIRONMENT=production
ALLOWED_HOSTS=demo.wellq.io,localhost,127.0.0.1

# Static Files (nginx will serve static files)
SERVE_STATIC=false

# SSL/HTTPS Settings (when behind nginx)
SECURE_SSL_REDIRECT=true
USE_PROXY=true

# Database (auto-configured in docker-compose)
DB_ENGINE=postgresql
DB_NAME=wellq
DB_USER=wellq
DB_PASSWORD=your-database-password

# Redis (auto-configured in docker-compose)
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

Docker Compose will automatically read this `.env` file!

**Restart your containers:**
```bash
docker-compose -f docker-compose.simple.yml down
docker-compose -f docker-compose.simple.yml up -d
```

---

## Option 2: Edit `docker-compose.simple.yml` Directly

Open `docker-compose.simple.yml` and find this line (around line 65):

```yaml
SERVE_STATIC: ${SERVE_STATIC:-true}
```

Change it to:

```yaml
SERVE_STATIC: ${SERVE_STATIC:-false}
```

Or set it directly (not recommended, but works):

```yaml
SERVE_STATIC: "false"
```

**Restart your containers:**
```bash
docker-compose -f docker-compose.simple.yml restart web
```

---

## Option 3: Set Environment Variable When Running Docker Compose

You can set it when running the command:

```bash
# Linux/Mac
SERVE_STATIC=false docker-compose -f docker-compose.simple.yml up -d

# Or export it first
export SERVE_STATIC=false
docker-compose -f docker-compose.simple.yml up -d
```

**Windows PowerShell:**
```powershell
$env:SERVE_STATIC="false"
docker-compose -f docker-compose.simple.yml up -d
```

---

## Which Option Should You Use?

- **Option 1 (.env file)** - ✅ **Best for production** - Keeps all settings in one place, easy to manage
- **Option 2 (edit docker-compose.yml)** - ✅ Good for quick testing, but less flexible
- **Option 3 (command line)** - ⚠️ Only for temporary testing, not persistent

## Verify It's Working

After setting `SERVE_STATIC=false`, check the logs:

```bash
docker-compose -f docker-compose.simple.yml logs web | grep -i static
```

You should see that Django is NOT serving static files (nginx will handle them).

Test that static files work:
```bash
curl http://your-domain/static/css/dashboard.css
```

If nginx is configured, this should return CSS content.

---

## Complete Example: Setting Up for Production with Nginx

1. **Create `.env` file:**
```env
SERVE_STATIC=false
DEBUG=False
ALLOWED_HOSTS=demo.wellq.io
SECURE_SSL_REDIRECT=true
USE_PROXY=true
```

2. **Restart containers:**
```bash
docker-compose -f docker-compose.simple.yml down
docker-compose -f docker-compose.simple.yml up -d
```

3. **Verify:**
```bash
docker-compose -f docker-compose.simple.yml logs web
```

Done! 🎉


