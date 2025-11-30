# Quick fix script for PostgreSQL connection issues (Windows PowerShell)

Write-Host "🔧 Fixing PostgreSQL Connection Issues..." -ForegroundColor Cyan
Write-Host ""

# Stop services
Write-Host "1. Stopping services..." -ForegroundColor Yellow
docker-compose -f docker-compose.simple.yml down

# Remove PostgreSQL volume
$response = Read-Host "2. Remove PostgreSQL volume? (y/n)"
if ($response -eq 'y' -or $response -eq 'Y') {
    Write-Host "   Removing PostgreSQL volume..." -ForegroundColor Yellow
    docker volume rm wellq_postgres_data 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "   Volume doesn't exist or already removed" -ForegroundColor Yellow
    }
}

# Rebuild images
Write-Host ""
Write-Host "3. Rebuilding images..." -ForegroundColor Yellow
docker-compose -f docker-compose.simple.yml build --no-cache

# Start database first
Write-Host ""
Write-Host "4. Starting PostgreSQL..." -ForegroundColor Yellow
docker-compose -f docker-compose.simple.yml up -d db

# Wait for PostgreSQL
Write-Host ""
Write-Host "5. Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
$maxWait = 60
$waited = 0
$ready = $false

while ($waited -lt $maxWait) {
    $result = docker-compose -f docker-compose.simple.yml exec -T db pg_isready -U wellq 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ PostgreSQL is ready!" -ForegroundColor Green
        $ready = $true
        break
    }
    Write-Host "   Waiting... ($waited/$maxWait seconds)" -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    $waited += 2
}

if (-not $ready) {
    Write-Host "   ❌ PostgreSQL did not start in time" -ForegroundColor Red
    Write-Host "   Check logs: docker-compose -f docker-compose.simple.yml logs db" -ForegroundColor Yellow
    exit 1
}

# Start Redis
Write-Host ""
Write-Host "6. Starting Redis..." -ForegroundColor Yellow
docker-compose -f docker-compose.simple.yml up -d redis

# Wait a bit
Start-Sleep -Seconds 5

# Start web services
Write-Host ""
Write-Host "7. Starting web services..." -ForegroundColor Yellow
docker-compose -f docker-compose.simple.yml up -d

Write-Host ""
Write-Host "✅ Done! Check status with: docker-compose -f docker-compose.simple.yml ps" -ForegroundColor Green
Write-Host "   View logs: docker-compose -f docker-compose.simple.yml logs -f" -ForegroundColor Cyan

