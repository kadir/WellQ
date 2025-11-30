# One-command Docker setup script for WellQ (Windows PowerShell)
# Usage: .\setup-docker.ps1

Write-Host "🚀 WellQ Docker Setup" -ForegroundColor Cyan
Write-Host "====================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is installed
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker is not installed. Please install Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Check if Docker Compose is available
if (-not (docker compose version 2>$null) -and -not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker Compose is not available. Please install Docker Desktop." -ForegroundColor Red
    exit 1
}

# Generate secret key
Write-Host "🔑 Generating secret key..." -ForegroundColor Yellow
try {
    $SECRET_KEY = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 50 | ForEach-Object {[char]$_})
} catch {
    $SECRET_KEY = "dev-secret-key-change-in-production-$(Get-Random)"
}

# Create .env file if it doesn't exist
if (-not (Test-Path .env)) {
    Write-Host "📝 Creating .env file..." -ForegroundColor Yellow
    @"
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
"@ | Out-File -FilePath .env -Encoding utf8
    Write-Host "✅ Created .env file" -ForegroundColor Green
} else {
    Write-Host "ℹ️  .env file already exists, skipping..." -ForegroundColor Yellow
}

# Build and start services
Write-Host ""
Write-Host "🏗️  Building Docker images..." -ForegroundColor Yellow
docker-compose -f docker-compose.simple.yml build

Write-Host ""
Write-Host "🚀 Starting services..." -ForegroundColor Yellow
docker-compose -f docker-compose.simple.yml up -d

# Wait for services to be ready
Write-Host ""
Write-Host "⏳ Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check if services are running
$services = docker-compose -f docker-compose.simple.yml ps 2>$null
if ($services -match "Up") {
    Write-Host "✅ Services are running!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Some services may not be running. Check with: docker-compose -f docker-compose.simple.yml ps" -ForegroundColor Yellow
}

# Show access information
Write-Host ""
Write-Host "✅ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Access Information:" -ForegroundColor Cyan
Write-Host "   Web UI:      http://localhost:8000"
Write-Host "   Admin:       http://localhost:8000/admin"
Write-Host "   API Docs:    http://localhost:8000/api/swagger/"
Write-Host ""
Write-Host "📊 Useful Commands:" -ForegroundColor Cyan
Write-Host "   View logs:   docker-compose -f docker-compose.simple.yml logs -f"
Write-Host "   Stop:        docker-compose -f docker-compose.simple.yml down"
Write-Host "   Restart:     docker-compose -f docker-compose.simple.yml restart"
Write-Host "   Create user: docker-compose -f docker-compose.simple.yml exec web python manage.py createsuperuser"
Write-Host ""

