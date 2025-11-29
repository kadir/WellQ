#!/bin/bash
set -e

# Function to wait for PostgreSQL
wait_for_postgres() {
    echo "Waiting for PostgreSQL to be ready..."
    max_attempts=30
    attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if python -c "import psycopg; psycopg.connect('host=${DB_HOST:-db} port=${DB_PORT:-5432} user=${DB_USER:-wellq} password=${DB_PASSWORD:-wellq_password} dbname=${DB_NAME:-wellq} connect_timeout=1')" 2>/dev/null; then
            echo "PostgreSQL is ready!"
            return 0
        fi
        attempt=$((attempt + 1))
        echo "Attempt $attempt/$max_attempts: PostgreSQL not ready, waiting..."
        sleep 2
    done
    
    echo "ERROR: PostgreSQL did not become ready in time"
    exit 1
}

# Wait for PostgreSQL if using PostgreSQL
if [ "${DB_ENGINE:-sqlite3}" = "postgresql" ]; then
    wait_for_postgres
fi

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput || echo "Warning: collectstatic failed (this is OK if no static files)"

# Run production checks if in production mode
if [ "${ENVIRONMENT:-development}" = "production" ]; then
    echo "Running production checks..."
    python manage.py check_production || {
        echo "WARNING: Production checks failed. Please review the errors above."
        # Don't exit - allow the app to start but warn the user
    }
fi

echo "Starting application..."
exec "$@"

