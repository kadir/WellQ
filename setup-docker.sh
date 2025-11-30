#!/bin/bash
# One-command Docker setup script for WellQ
# Usage: ./setup-docker.sh

set -e

echo "🚀 WellQ Docker Setup"
echo "===================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Generate secret key
echo "🔑 Generating secret key..."
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))" 2>/dev/null || openssl rand -base64 32)

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
# Django Settings
SECRET_KEY=$SECRET_KEY
DEBUG=True
ENVIRONMENT=development
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database (auto-configured in docker-compose)
DB_ENGINE=postgresql
DB_NAME=wellq
DB_USER=wellq
DB_PASSWORD=wellq_dev_password

# Redis (auto-configured in docker-compose)
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Optional: Create superuser on first run
CREATE_SUPERUSER=true
EOF
    echo "✅ Created .env file"
else
    echo "ℹ️  .env file already exists, skipping..."
fi

# Build and start services
echo ""
echo "🏗️  Building Docker images..."
docker-compose -f docker-compose.simple.yml build

echo ""
echo "🚀 Starting services..."
docker-compose -f docker-compose.simple.yml up -d

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are running
if docker-compose -f docker-compose.simple.yml ps | grep -q "Up"; then
    echo "✅ Services are running!"
else
    echo "⚠️  Some services may not be running. Check with: docker-compose -f docker-compose.simple.yml ps"
fi

# Create superuser
echo ""
echo "👤 Creating superuser..."
echo "   You can create a superuser manually with:"
echo "   docker-compose -f docker-compose.simple.yml exec web python manage.py createsuperuser"
echo ""

# Show access information
echo "✅ Setup complete!"
echo ""
echo "📋 Access Information:"
echo "   Web UI:      http://localhost:8000"
echo "   Admin:       http://localhost:8000/admin"
echo "   API Docs:    http://localhost:8000/api/swagger/"
echo ""
echo "📊 Useful Commands:"
echo "   View logs:   docker-compose -f docker-compose.simple.yml logs -f"
echo "   Stop:        docker-compose -f docker-compose.simple.yml down"
echo "   Restart:     docker-compose -f docker-compose.simple.yml restart"
echo ""


