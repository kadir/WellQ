#!/bin/bash
# Quick fix script for PostgreSQL connection issues

echo "🔧 Fixing PostgreSQL Connection Issues..."
echo ""

# Stop services
echo "1. Stopping services..."
docker-compose -f docker-compose.simple.yml down

# Remove PostgreSQL volume if corrupted
read -p "2. Remove PostgreSQL volume? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "   Removing PostgreSQL volume..."
    docker volume rm wellq_postgres_data 2>/dev/null || echo "   Volume doesn't exist or already removed"
fi

# Rebuild images
echo ""
echo "3. Rebuilding images..."
docker-compose -f docker-compose.simple.yml build --no-cache

# Start database first
echo ""
echo "4. Starting PostgreSQL..."
docker-compose -f docker-compose.simple.yml up -d db

# Wait for PostgreSQL
echo ""
echo "5. Waiting for PostgreSQL to be ready..."
max_wait=60
waited=0
while [ $waited -lt $max_wait ]; do
    if docker-compose -f docker-compose.simple.yml exec -T db pg_isready -U wellq >/dev/null 2>&1; then
        echo "   ✅ PostgreSQL is ready!"
        break
    fi
    echo "   Waiting... ($waited/$max_wait seconds)"
    sleep 2
    waited=$((waited + 2))
done

if [ $waited -ge $max_wait ]; then
    echo "   ❌ PostgreSQL did not start in time"
    echo "   Check logs: docker-compose -f docker-compose.simple.yml logs db"
    exit 1
fi

# Start Redis
echo ""
echo "6. Starting Redis..."
docker-compose -f docker-compose.simple.yml up -d redis

# Wait a bit
sleep 5

# Start web services
echo ""
echo "7. Starting web services..."
docker-compose -f docker-compose.simple.yml up -d

echo ""
echo "✅ Done! Check status with: docker-compose -f docker-compose.simple.yml ps"
echo "   View logs: docker-compose -f docker-compose.simple.yml logs -f"


