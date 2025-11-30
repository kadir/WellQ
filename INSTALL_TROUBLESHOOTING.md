# Installation Troubleshooting - PostgreSQL "Not Ready"

## 🔧 Quick Fix

### Run the Fix Script

**Windows:**
```powershell
.\fix-postgres.ps1
```

**Linux/Mac:**
```bash
chmod +x fix-postgres.sh
./fix-postgres.sh
```

## 🔍 Step-by-Step Diagnosis

### 1. Check PostgreSQL Container Status
```bash
docker-compose -f docker-compose.simple.yml ps db
```

**Should show:** `Up (healthy)`

If it shows `Up (unhealthy)` or `Restarting`:
- Check logs: `docker-compose -f docker-compose.simple.yml logs db`
- Look for errors in the logs

### 2. Check PostgreSQL Logs
```bash
docker-compose -f docker-compose.simple.yml logs db | tail -50
```

**Look for:**
- ✅ `database system is ready to accept connections` - Good!
- ❌ `FATAL` or `ERROR` - Problem found

### 3. Test PostgreSQL Connection Manually
```bash
# Enter the web container
docker-compose -f docker-compose.simple.yml exec web bash

# Test connection
pg_isready -h db -p 5432 -U wellq

# Should return: db:5432 - accepting connections
```

### 4. Check if Database Exists
```bash
# From web container
docker-compose -f docker-compose.simple.yml exec web bash

# Try to connect
python manage.py dbshell

# If it works, type: \q to exit
```

## 🛠️ Common Fixes

### Fix 1: Reset PostgreSQL Volume
```bash
# Stop everything
docker-compose -f docker-compose.simple.yml down

# Remove PostgreSQL volume
docker volume rm wellq_postgres_data

# Start again
docker-compose -f docker-compose.simple.yml up -d
```

### Fix 2: Start Database First, Then Wait
```bash
# Start only database
docker-compose -f docker-compose.simple.yml up -d db

# Wait 30-60 seconds
sleep 30

# Check if ready
docker-compose -f docker-compose.simple.yml exec db pg_isready -U wellq

# If ready, start everything
docker-compose -f docker-compose.simple.yml up -d
```

### Fix 3: Check Port Conflicts
```bash
# Windows
netstat -ano | findstr :5432

# Linux/Mac
lsof -i :5432
```

If port is in use, change it in `docker-compose.simple.yml`:
```yaml
ports:
  - "5433:5432"  # Use different external port
```

### Fix 4: Increase Wait Time
Edit `docker-entrypoint-simple.sh`:
```bash
max_attempts=120  # Wait up to 4 minutes instead of 3
```

### Fix 5: Rebuild Everything
```bash
# Complete reset
docker-compose -f docker-compose.simple.yml down -v
docker-compose -f docker-compose.simple.yml build --no-cache
docker-compose -f docker-compose.simple.yml up -d
```

## 📋 What the Script Does

The entrypoint script now:
1. ✅ Waits for PostgreSQL server to accept connections (using `pg_isready`)
2. ✅ Waits for the specific database to be accessible (using Python `psycopg`)
3. ✅ Provides better error messages
4. ✅ Waits longer (up to 3 minutes for server, 1 minute for database)

## ✅ Verify It's Working

After fixing:

```bash
# 1. Check all services
docker-compose -f docker-compose.simple.yml ps

# 2. Check web logs for success message
docker-compose -f docker-compose.simple.yml logs web | grep "PostgreSQL database is ready"

# 3. Test the application
curl http://localhost:8000/health/
# Should return: OK
```

## 🆘 Still Not Working?

1. **Check Docker resources:**
   - Docker Desktop has enough memory (2GB+)
   - Enough disk space
   - WSL2 enabled (Windows)

2. **Try the full setup:**
   ```bash
   # Use the full docker-compose.yml with .env file
   cp .env.example .env
   # Edit .env with your settings
   docker-compose up -d --build
   ```

3. **Check system requirements:**
   - Docker Desktop is running
   - No antivirus blocking Docker
   - Firewall allows Docker

4. **Get more help:**
   - Check logs: `docker-compose -f docker-compose.simple.yml logs`
   - Check Docker Desktop logs
   - Try restarting Docker Desktop

