# Troubleshooting Guide - WellQ Docker Setup

## PostgreSQL Not Ready Issues

### Problem: "PostgreSQL is not ready" or connection timeouts

### Solution 1: Check PostgreSQL Logs
```bash
docker-compose -f docker-compose.simple.yml logs db
```

Look for errors like:
- Permission denied
- Database initialization failed
- Port conflicts

### Solution 2: Increase Wait Time
The entrypoint script waits up to 60 attempts (2 minutes). If PostgreSQL is slow to start:

Edit `docker-entrypoint-simple.sh` and increase `max_attempts`:
```bash
max_attempts=120  # Wait up to 4 minutes
```

### Solution 3: Reset PostgreSQL Volume
If the database volume is corrupted:

```bash
# Stop services
docker-compose -f docker-compose.simple.yml down

# Remove PostgreSQL volume
docker volume rm wellq_postgres_data

# Start again
docker-compose -f docker-compose.simple.yml up -d
```

### Solution 4: Check Port Conflicts
```bash
# Windows
netstat -ano | findstr :5432

# Linux/Mac
lsof -i :5432
```

If port 5432 is in use, change it in `docker-compose.simple.yml`:
```yaml
ports:
  - "5433:5432"  # Use 5433 externally
```

### Solution 5: Manual PostgreSQL Check
```bash
# Check if PostgreSQL container is running
docker-compose -f docker-compose.simple.yml ps db

# Check PostgreSQL health
docker-compose -f docker-compose.simple.yml exec db pg_isready -U wellq

# Try connecting manually
docker-compose -f docker-compose.simple.yml exec db psql -U wellq -d wellq
```

### Solution 6: Use Health Check Wait
Wait for health check to pass before starting web:

```bash
# Check health status
docker inspect wellq-postgres | grep -A 10 Health
```

## Common Issues

### Issue: "psycopg module not found"
**Solution:** The Docker image should have psycopg installed. Rebuild:
```bash
docker-compose -f docker-compose.simple.yml build --no-cache
```

### Issue: "Database does not exist"
**Solution:** PostgreSQL might not have created the database. Check logs:
```bash
docker-compose -f docker-compose.simple.yml logs db | grep -i "database\|error"
```

### Issue: "Connection refused"
**Solution:** 
1. Check if services are on the same network:
```bash
docker network inspect wellq_wellq-network
```

2. Verify service names match:
   - Database service name: `db`
   - Redis service name: `redis`
   - Web connects to: `db:5432` and `redis:6379`

### Issue: "Permission denied" on database
**Solution:** Reset PostgreSQL with correct permissions:
```bash
docker-compose -f docker-compose.simple.yml down -v
docker-compose -f docker-compose.simple.yml up -d db
# Wait 30 seconds
docker-compose -f docker-compose.simple.yml up -d
```

## Debug Mode

### Enable Verbose Logging
Edit `docker-entrypoint-simple.sh` and remove `2>/dev/null` to see errors:
```bash
if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; then
```

### Test Connection Manually
```bash
# Enter web container
docker-compose -f docker-compose.simple.yml exec web bash

# Test PostgreSQL connection
pg_isready -h db -p 5432 -U wellq

# Test with Python
python -c "import psycopg; conn = psycopg.connect('host=db port=5432 user=wellq password=wellq_dev_password dbname=wellq'); print('Connected!')"
```

## Quick Fixes

### Complete Reset
```bash
# Stop everything
docker-compose -f docker-compose.simple.yml down -v

# Remove all volumes
docker volume prune -f

# Rebuild and start
docker-compose -f docker-compose.simple.yml up -d --build
```

### Check All Services
```bash
# View all service status
docker-compose -f docker-compose.simple.yml ps

# View all logs
docker-compose -f docker-compose.simple.yml logs

# View specific service logs
docker-compose -f docker-compose.simple.yml logs db
docker-compose -f docker-compose.simple.yml logs web
```

## Still Having Issues?

1. **Check Docker resources:**
   - Ensure Docker has enough memory (at least 2GB)
   - Check disk space: `docker system df`

2. **Update Docker:**
   - Ensure Docker Desktop is up to date

3. **Try the full setup:**
   - Use `docker-compose.yml` with a `.env` file for more control

4. **Check system requirements:**
   - Docker Desktop running?
   - WSL2 enabled (Windows)?
   - Enough disk space?


