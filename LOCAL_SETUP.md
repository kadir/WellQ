# Local Development Setup Guide

This guide will help you set up and run WellQ on your local machine.

## Prerequisites

### Option 1: Docker (Recommended - Easiest)

**What to Install:**
1. **Docker Desktop** (includes Docker and Docker Compose)
   - Windows: Download from https://www.docker.com/products/docker-desktop/
   - Mac: Download from https://www.docker.com/products/docker-desktop/
   - Linux: Install Docker Engine and Docker Compose
     ```bash
     # Ubuntu/Debian
     sudo apt-get update
     sudo apt-get install docker.io docker-compose
     sudo systemctl start docker
     sudo systemctl enable docker
     ```

### Option 2: Manual Installation (Without Docker)

**What to Install:**
1. **Python 3.10 or higher**
   - Windows: Download from https://www.python.org/downloads/
   - Mac: `brew install python3` or download from python.org
   - Linux: `sudo apt-get install python3 python3-pip python3-venv`

2. **PostgreSQL 12+** (optional, SQLite works for development)
   - Windows: Download from https://www.postgresql.org/download/windows/
   - Mac: `brew install postgresql`
   - Linux: `sudo apt-get install postgresql postgresql-contrib`

3. **Redis** (for Celery)
   - Windows: Use WSL2 or Docker: `docker run -d -p 6379:6379 redis:alpine`
   - Mac: `brew install redis`
   - Linux: `sudo apt-get install redis-server`

4. **Git** (if not already installed)
   - Windows: Download from https://git-scm.com/download/win
   - Mac: `brew install git` or comes with Xcode
   - Linux: `sudo apt-get install git`

---

## Quick Start with Docker (Recommended)

### Step 1: Clone the Repository

```bash
git clone <your-repo-url>
cd WellQ
```

### Step 2: Create Environment File

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# Linux/Mac
cp .env.example .env
```

### Step 3: Edit .env File

Open `.env` in a text editor and set:

```env
# Django Settings
SECRET_KEY=dev-secret-key-change-in-production-12345
DEBUG=True
ENVIRONMENT=development
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database Configuration (Docker will use these)
DB_ENGINE=postgresql
DB_NAME=wellq
DB_USER=wellq
DB_PASSWORD=wellq_password
DB_HOST=db
DB_PORT=5432

# Redis Configuration
REDIS_PORT=6379
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Web Server
WEB_PORT=8000
```

### Step 4: Build and Start Services

```bash
# Build and start all services
docker-compose up -d --build

# View logs (optional)
docker-compose logs -f
```

### Step 5: Run Migrations

```bash
docker-compose exec web python manage.py migrate
```

### Step 6: Create Superuser

```bash
docker-compose exec web python manage.py createsuperuser
```

Follow the prompts to create an admin user.

### Step 7: Access the Application

- **Web UI**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin
- **API Docs**: http://localhost:8000/api/swagger/

### Useful Docker Commands

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (deletes database)
docker-compose down -v

# View logs
docker-compose logs -f web
docker-compose logs -f celery

# Access Django shell
docker-compose exec web python manage.py shell

# Run management commands
docker-compose exec web python manage.py <command>

# Rebuild after code changes
docker-compose up -d --build
```

---

## Manual Installation (Without Docker)

### Step 1: Clone the Repository

```bash
git clone <your-repo-url>
cd WellQ
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Create Environment File

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# Linux/Mac
cp .env.example .env
```

### Step 5: Edit .env File

Open `.env` and configure:

```env
# Django Settings
SECRET_KEY=dev-secret-key-change-in-production-12345
DEBUG=True
ENVIRONMENT=development
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Configuration (SQLite for local dev)
DB_ENGINE=sqlite3
# Or use PostgreSQL:
# DB_ENGINE=postgresql
# DB_NAME=wellq
# DB_USER=wellq
# DB_PASSWORD=wellq_password
# DB_HOST=localhost
# DB_PORT=5432

# Redis Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Step 6: Start Redis

**Windows:**
```bash
# Option 1: Use Docker
docker run -d -p 6379:6379 --name redis redis:alpine

# Option 2: Use WSL2
# Install Redis in WSL2

# Option 3: Download Redis for Windows
# https://github.com/microsoftarchive/redis/releases
```

**Mac:**
```bash
brew services start redis
# Or: redis-server
```

**Linux:**
```bash
sudo systemctl start redis
# Or: redis-server
```

### Step 7: Setup Database

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Step 8: Start the Application

You need **3 terminal windows**:

**Terminal 1 - Django Server:**
```bash
# Activate virtual environment first
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

python manage.py runserver
```

**Terminal 2 - Celery Worker:**
```bash
# Activate virtual environment first
celery -A core worker -l info
```

**Terminal 3 - Celery Beat (Scheduler):**
```bash
# Activate virtual environment first
celery -A core beat -l info
```

### Step 9: Access the Application

- **Web UI**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin
- **API Docs**: http://localhost:8000/api/swagger/

---

## Testing the Setup

### 1. Check Database Connection

```bash
# Docker
docker-compose exec web python manage.py dbshell

# Manual
python manage.py dbshell
```

### 2. Check Redis Connection

```bash
# Test Redis
redis-cli ping
# Should return: PONG
```

### 3. Test Celery

```bash
# Docker
docker-compose exec web python manage.py shell
>>> from core.tasks import *
>>> # Test a task

# Manual
python manage.py shell
>>> from core.tasks import *
```

### 4. Run Production Checks

```bash
# Docker
docker-compose exec web python manage.py check_production

# Manual
python manage.py check_production
```

### 5. Test File Upload

1. Go to http://localhost:8000/upload/
2. Upload a scan file (JSON format)
3. Check if it processes correctly

---

## Common Issues and Solutions

### Issue: Port 8000 already in use

**Solution:**
```bash
# Change port in docker-compose.yml or .env
WEB_PORT=8001

# Or for manual: python manage.py runserver 8001
```

### Issue: Redis connection error

**Solution:**
```bash
# Check if Redis is running
redis-cli ping

# Docker: Check Redis container
docker-compose ps redis

# Start Redis if not running
# Docker: docker-compose up -d redis
# Manual: redis-server (or systemctl start redis)
```

### Issue: Database connection error (Docker)

**Solution:**
```bash
# Wait for database to be ready
docker-compose logs db

# Restart services
docker-compose restart
```

### Issue: Migration errors

**Solution:**
```bash
# Reset database (WARNING: deletes all data)
# Docker:
docker-compose down -v
docker-compose up -d
docker-compose exec web python manage.py migrate

# Manual:
# Delete db.sqlite3 (if using SQLite)
python manage.py migrate
```

### Issue: Static files not loading

**Solution:**
```bash
# Collect static files
# Docker:
docker-compose exec web python manage.py collectstatic --noinput

# Manual:
python manage.py collectstatic
```

### Issue: Permission errors (Linux/Mac)

**Solution:**
```bash
# Fix file permissions
chmod +x docker-entrypoint.sh

# Fix Docker permissions (if needed)
sudo usermod -aG docker $USER
# Log out and back in
```

---

## Development Tips

### 1. Auto-reload on Code Changes

Docker Compose already mounts your code, so changes are reflected immediately. For manual setup, Django's runserver auto-reloads.

### 2. View Logs

```bash
# Docker
docker-compose logs -f web
docker-compose logs -f celery

# Manual
# Logs appear in terminal windows
```

### 3. Access Django Admin

1. Go to http://localhost:8000/admin/
2. Login with superuser credentials
3. Create workspaces, products, etc.

### 4. Test API

```bash
# Get API token from /profile/tokens/create/
# Then test:
curl -H "Authorization: Token YOUR_TOKEN" \
     http://localhost:8000/api/v1/workspaces/
```

### 5. Reset Everything

```bash
# Docker
docker-compose down -v
docker-compose up -d --build
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser

# Manual
# Delete db.sqlite3
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

---

## Next Steps

1. ✅ Create a workspace
2. ✅ Create a product
3. ✅ Create a release
4. ✅ Upload a scan file
5. ✅ View findings in dashboard
6. ✅ Explore API documentation

---

## Need Help?

- Check logs: `docker-compose logs -f` or check terminal output
- Review error messages carefully
- Check that all services are running
- Verify environment variables in `.env`
- Ensure ports are not in use by other applications

