# Install WhiteNoise - Quick Fix

## The Problem
WhiteNoise is not installed in the container because it wasn't rebuilt after adding it to requirements.txt.

## Solution: Rebuild Container

### Step 1: Rebuild with No Cache

```bash
docker-compose -f docker-compose.simple.yml build --no-cache web
```

**This will:**
- Install WhiteNoise from requirements.txt
- Install all other dependencies fresh
- Take a few minutes

### Step 2: Recreate Container

```bash
docker-compose -f docker-compose.simple.yml down
docker-compose -f docker-compose.simple.yml up -d
```

### Step 3: Verify WhiteNoise is Installed

```bash
docker exec wellq-web python -c "import whitenoise; print('WhiteNoise version:', whitenoise.__version__)"
```

Should show: `WhiteNoise version: 6.6.0`

### Step 4: Run collectstatic

```bash
docker exec wellq-web python manage.py collectstatic --noinput --clear
```

### Step 5: Restart (if needed)

```bash
docker-compose -f docker-compose.simple.yml restart web
```

### Step 6: Test

Visit: `https://demo.wellq.io/static/css/dashboard.css`

Should work now!

## Why This Happened

When you add a package to `requirements.txt`, Docker doesn't automatically install it. You must rebuild the image for the new package to be installed.

The `--no-cache` flag ensures a clean rebuild and that WhiteNoise is definitely installed.


