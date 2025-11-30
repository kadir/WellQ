#!/bin/bash
set -e

echo "🚀 Starting WellQ..."

# Wait for PostgreSQL (simplified - uses Python psycopg)
echo "⏳ Waiting for PostgreSQL..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
  if python -c "import psycopg; psycopg.connect('host=${DB_HOST:-db} port=${DB_PORT:-5432} user=${DB_USER:-wellq} password=${DB_PASSWORD:-wellq_dev_password} dbname=${DB_NAME:-wellq} connect_timeout=1')" 2>/dev/null; then
    echo "✅ PostgreSQL is ready!"
    break
  fi
  attempt=$((attempt + 1))
  echo "   Attempt $attempt/$max_attempts: PostgreSQL not ready, waiting..."
  sleep 2
done

if [ $attempt -eq $max_attempts ]; then
  echo "❌ ERROR: PostgreSQL did not become ready in time"
  exit 1
fi

# Wait for Redis
echo "⏳ Waiting for Redis..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
  if python -c "import redis; r = redis.Redis(host='${REDIS_HOST:-redis}', port=${REDIS_PORT:-6379}, socket_connect_timeout=1); r.ping()" 2>/dev/null; then
    echo "✅ Redis is ready!"
    break
  fi
  attempt=$((attempt + 1))
  echo "   Attempt $attempt/$max_attempts: Redis not ready, waiting..."
  sleep 2
done

if [ $attempt -eq $max_attempts ]; then
  echo "❌ ERROR: Redis did not become ready in time"
  exit 1
fi

# Run migrations
echo "📦 Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput || echo "⚠️  Warning: collectstatic failed (OK if no static files)"

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

