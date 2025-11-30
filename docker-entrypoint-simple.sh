#!/bin/bash
set -e

echo "🚀 Starting WellQ..."

# Set default values
DB_HOST=${DB_HOST:-db}
DB_PORT=${DB_PORT:-5432}
DB_USER=${DB_USER:-wellq}
DB_NAME=${DB_NAME:-wellq}
DB_PASSWORD=${DB_PASSWORD:-wellq_dev_password}

# Wait for PostgreSQL - More reliable method
echo "⏳ Waiting for PostgreSQL..."

# Step 1: Wait for PostgreSQL server to accept connections (using pg_isready)
echo "   Step 1: Waiting for PostgreSQL server to start..."
max_attempts=90
attempt=0

while [ $attempt -lt $max_attempts ]; do
  # Check if PostgreSQL is accepting connections (pg_isready is installed in container)
  if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" >/dev/null 2>&1; then
    echo "   ✅ PostgreSQL server is accepting connections"
    break
  fi
  attempt=$((attempt + 1))
  if [ $((attempt % 10)) -eq 0 ]; then
    echo "   Attempt $attempt/$max_attempts: PostgreSQL server not ready..."
  fi
  sleep 2
done

if [ $attempt -ge $max_attempts ]; then
  echo "❌ ERROR: PostgreSQL server did not become ready in time"
  echo "   Check PostgreSQL logs: docker-compose -f docker-compose.simple.yml logs db"
  echo "   Try: docker-compose -f docker-compose.simple.yml restart db"
  exit 1
fi

# Step 2: Wait for the database to be accessible (using Python psycopg)
echo "   Step 2: Waiting for database '$DB_NAME' to be accessible..."
attempt=0
max_attempts=30

while [ $attempt -lt $max_attempts ]; do
  # Use Python psycopg to test connection (more reliable)
  if python3 -c "
import sys
try:
    import psycopg
    conn = psycopg.connect(
        host='$DB_HOST',
        port=$DB_PORT,
        user='$DB_USER',
        password='$DB_PASSWORD',
        dbname='$DB_NAME',
        connect_timeout=3
    )
    conn.close()
    sys.exit(0)
except Exception as e:
    sys.exit(1)
" 2>/dev/null; then
    echo "✅ PostgreSQL database is ready!"
    break
  fi
  attempt=$((attempt + 1))
  if [ $((attempt % 5)) -eq 0 ]; then
    echo "   Attempt $attempt/$max_attempts: Database not accessible, waiting..."
  fi
  sleep 2
done

if [ $attempt -ge $max_attempts ]; then
  echo "⚠️  WARNING: Could not verify database connection"
  echo "   Continuing anyway - this might work if database is still initializing"
  echo "   If migrations fail, wait 30 seconds and restart: docker-compose -f docker-compose.simple.yml restart web"
fi

# Wait for Redis
echo "⏳ Waiting for Redis..."
max_attempts=60
attempt=0
REDIS_HOST=${REDIS_HOST:-redis}
REDIS_PORT=${REDIS_PORT:-6379}

while [ $attempt -lt $max_attempts ]; do
  if python3 -c "
import sys
try:
    import redis
    r = redis.Redis(host='$REDIS_HOST', port=$REDIS_PORT, socket_connect_timeout=2, decode_responses=False)
    r.ping()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; then
    echo "✅ Redis is ready!"
    break
  fi
  attempt=$((attempt + 1))
  if [ $((attempt % 10)) -eq 0 ]; then
    echo "   Attempt $attempt/$max_attempts: Redis not ready, waiting..."
  fi
  sleep 2
done

if [ $attempt -eq $max_attempts ]; then
  echo "❌ ERROR: Redis did not become ready in time"
  echo "   Check Redis logs: docker-compose -f docker-compose.simple.yml logs redis"
  exit 1
fi

# Run migrations
echo "📦 Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "📁 Collecting static files..."
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput --clear || {
    echo "⚠️  Warning: collectstatic failed"
    echo "   This might be OK if static files are served by nginx"
    echo "   If you see 404 errors for CSS/JS files, check that collectstatic ran successfully"
}

# Create superuser if it doesn't exist (optional - for first run)
if [ "${CREATE_SUPERUSER:-false}" = "true" ]; then
  echo "👤 Creating superuser..."
  python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print('Superuser created: admin/admin')
else:
    print('Superuser already exists')
EOF
fi

echo "✅ Setup complete! Starting application..."
exec "$@"
