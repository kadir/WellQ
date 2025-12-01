# Quick Fix for PostgreSQL "Not Ready" Issue

## 🔧 Immediate Fix

### Option 1: Use the Fix Script

**Windows:**
```powershell
.\fix-postgres.ps1
```

**Linux/Mac:**
```bash
chmod +x fix-postgres.sh
./fix-postgres.sh
```

### Option 2: Manual Fix

```bash
# 1. Stop everything
docker-compose -f docker-compose.simple.yml down

# 2. Remove PostgreSQL volume (fixes corruption)
docker volume rm wellq_postgres_data

# 3. Start database first and wait
docker-compose -f docker-compose.simple.yml up -d db

# 4. Wait 30 seconds for PostgreSQL to initialize
sleep 30

# 5. Check if PostgreSQL is ready
docker-compose -f docker-compose.simple.yml exec db pg_isready -U wellq

# 6. Start everything
docker-compose -f docker-compose.simple.yml up -d

# 7. Check logs
docker-compose -f docker-compose.simple.yml logs -f web
```

## 🔍 Diagnose the Issue

### Check PostgreSQL Logs
```bash
docker-compose -f docker-compose.simple.yml logs db
```

Look for:
- `database system is ready to accept connections` ✅ Good
- `FATAL` or `ERROR` ❌ Problem

### Check if PostgreSQL Container is Running
```bash
docker-compose -f docker-compose.simple.yml ps db
```

Should show: `Up (healthy)`

### Test Connection Manually
```bash
# Enter web container
docker-compose -f docker-compose.simple.yml exec web bash

# Test connection
pg_isready -h db -p 5432 -U wellq

# Try Python connection
python -c "import psycopg; conn = psycopg.connect('host=db port=5432 user=wellq password=wellq_dev_password dbname=wellq'); print('Connected!')"
```

## 🐛 Common Causes

1. **PostgreSQL volume corrupted** → Remove volume and restart
2. **Port 5432 already in use** → Change port in docker-compose.simple.yml
3. **Not enough time to initialize** → Wait longer (30-60 seconds)
4. **Network issues** → Check if services are on same network
5. **Wrong credentials** → Verify DB_USER and DB_PASSWORD match

## ✅ Verify It's Fixed

After running the fix:

```bash
# Check all services are running
docker-compose -f docker-compose.simple.yml ps

# Should show all services as "Up"
# Web should show "Up (healthy)" after a minute

# Check web logs for success
docker-compose -f docker-compose.simple.yml logs web | grep "PostgreSQL is ready"
```

## 🆘 Still Not Working?

1. **Check Docker resources:**
   ```bash
   docker system df
   ```
   Ensure you have enough disk space

2. **Increase wait time:**
   Edit `docker-entrypoint-simple.sh`:
   ```bash
   max_attempts=120  # Wait up to 4 minutes
   ```

3. **Use the full setup:**
   Switch to `docker-compose.yml` with a `.env` file for more control

4. **Check Docker Desktop:**
   - Is it running?
   - Has enough memory allocated (2GB+)?
   - WSL2 enabled (Windows)?


