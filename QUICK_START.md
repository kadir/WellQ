# Quick Start Guide - WellQ Local Setup

## 🚀 Fastest Way: Docker (Recommended)

### What to Install First:

1. **Docker Desktop**
   - Download: https://www.docker.com/products/docker-desktop/
   - Install and start Docker Desktop
   - Verify: Open terminal and run `docker --version`

### Exact Commands (Copy & Paste):

```bash
# 1. Navigate to project directory
cd WellQ

# 2. Create .env file
# Windows PowerShell:
Copy-Item .env.example .env

# Windows CMD:
copy .env.example .env

# Linux/Mac:
cp .env.example .env

# 3. Edit .env file (use any text editor)
# Set these values:
# SECRET_KEY=dev-secret-key-12345
# DEBUG=True
# ENVIRONMENT=development
# ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# 4. Build and start all services
docker-compose up -d --build

# 5. Wait for services to start (30-60 seconds), then run migrations
docker-compose exec web python manage.py migrate

# 6. Create admin user
docker-compose exec web python manage.py createsuperuser
# Follow prompts: username, email, password

# 7. Access the application
# Open browser: http://localhost:8000
```

### Verify It's Working:

```bash
# Check all services are running
docker-compose ps

# View logs
docker-compose logs -f web

# Test database
docker-compose exec web python manage.py dbshell
# Type: \q to exit
```

---

## 📝 Manual Setup (Without Docker)

### What to Install First:

1. **Python 3.10+**
   - Windows: https://www.python.org/downloads/
   - Mac: `brew install python3`
   - Linux: `sudo apt-get install python3 python3-pip python3-venv`

2. **Redis**
   - Windows: Use Docker: `docker run -d -p 6379:6379 redis:alpine`
   - Mac: `brew install redis && brew services start redis`
   - Linux: `sudo apt-get install redis-server && sudo systemctl start redis`

3. **PostgreSQL (Optional - SQLite works for dev)**
   - Windows: https://www.postgresql.org/download/windows/
   - Mac: `brew install postgresql && brew services start postgresql`
   - Linux: `sudo apt-get install postgresql postgresql-contrib`

### Exact Commands (Copy & Paste):

```bash
# 1. Navigate to project directory
cd WellQ

# 2. Create virtual environment
# Windows:
python -m venv venv
venv\Scripts\activate

# Linux/Mac:
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Create .env file
# Windows PowerShell:
Copy-Item .env.example .env

# Windows CMD:
copy .env.example .env

# Linux/Mac:
cp .env.example .env

# 5. Edit .env file - set these:
# SECRET_KEY=dev-secret-key-12345
# DEBUG=True
# ENVIRONMENT=development
# ALLOWED_HOSTS=localhost,127.0.0.1
# DB_ENGINE=sqlite3
# CELERY_BROKER_URL=redis://localhost:6379/0
# CELERY_RESULT_BACKEND=redis://localhost:6379/0

# 6. Start Redis (if not using Docker)
# Mac:
brew services start redis

# Linux:
sudo systemctl start redis

# Windows: Use Docker command above or install Redis for Windows

# 7. Run migrations
python manage.py migrate

# 8. Create superuser
python manage.py createsuperuser
# Follow prompts: username, email, password

# 9. Start Django server (Terminal 1)
python manage.py runserver

# 10. Start Celery worker (Terminal 2 - NEW TERMINAL)
# Activate venv first, then:
celery -A core worker -l info

# 11. Start Celery beat (Terminal 3 - NEW TERMINAL)
# Activate venv first, then:
celery -A core beat -l info

# 12. Access the application
# Open browser: http://localhost:8000
```

---

## ✅ Testing Checklist

After setup, test these:

1. **Access Web UI**
   - Go to: http://localhost:8000
   - Should see login page

2. **Login**
   - Use superuser credentials you created
   - Should see dashboard

3. **Check Admin Panel**
   - Go to: http://localhost:8000/admin/
   - Login with superuser
   - Should see Django admin

4. **Check API Docs**
   - Go to: http://localhost:8000/api/swagger/
   - Should see Swagger UI

5. **Test File Upload**
   - Go to: http://localhost:8000/upload/
   - Try uploading a JSON scan file

6. **Check Celery**
   - Look at Celery worker terminal
   - Should see "ready" message
   - Tasks should process when uploaded

---

## 🔧 Troubleshooting

### Docker Issues:

```bash
# If port 8000 is in use, change it in .env:
# WEB_PORT=8001

# If services won't start:
docker-compose down
docker-compose up -d --build

# View detailed logs:
docker-compose logs -f

# Reset everything (deletes database):
docker-compose down -v
docker-compose up -d --build
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

### Manual Setup Issues:

```bash
# Redis not running?
# Mac: brew services start redis
# Linux: sudo systemctl start redis
# Windows: docker run -d -p 6379:6379 redis:alpine

# Database errors?
# Delete db.sqlite3 and run migrations again:
rm db.sqlite3  # Linux/Mac
del db.sqlite3  # Windows
python manage.py migrate

# Import errors?
# Make sure virtual environment is activated
# Reinstall dependencies:
pip install -r requirements.txt

# Port already in use?
# Change port: python manage.py runserver 8001
```

---

## 📚 Next Steps

1. Create a workspace
2. Create a product
3. Create a release
4. Upload a scan file
5. View findings in dashboard
6. Explore API at /api/swagger/

---

## 🆘 Need Help?

- Check logs: `docker-compose logs -f` (Docker) or terminal output (Manual)
- Verify all services are running
- Check .env file configuration
- Ensure ports are not in use
- See LOCAL_SETUP.md for detailed guide

