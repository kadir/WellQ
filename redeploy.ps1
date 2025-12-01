# Redeploy script for WellQ - PowerShell version
# Ensures all changes are picked up

Write-Host "🔄 Redeploying WellQ..." -ForegroundColor Cyan
Write-Host ""

# Step 1: Rebuild the web container (no cache to ensure fresh build)
Write-Host "📦 Step 1: Rebuilding web container (no cache)..." -ForegroundColor Yellow
docker-compose build --no-cache web

# Step 2: Stop and remove the web container
Write-Host ""
Write-Host "🛑 Step 2: Stopping web container..." -ForegroundColor Yellow
docker-compose stop web
docker-compose rm -f web

# Step 3: Start the web container
Write-Host ""
Write-Host "🚀 Step 3: Starting web container..." -ForegroundColor Yellow
docker-compose up -d web

# Step 4: Wait a moment for container to start
Write-Host ""
Write-Host "⏳ Step 4: Waiting for container to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Step 5: Run collectstatic (in case static files changed)
Write-Host ""
Write-Host "📁 Step 5: Collecting static files..." -ForegroundColor Yellow
docker-compose exec web python manage.py collectstatic --noinput
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  collectstatic had issues (may be OK)" -ForegroundColor Yellow
}

# Step 6: Show container status
Write-Host ""
Write-Host "✅ Step 6: Container status:" -ForegroundColor Yellow
docker-compose ps web

Write-Host ""
Write-Host "🎉 Redeployment complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Clear your browser cache (Ctrl+Shift+Delete)"
Write-Host "   2. Hard refresh the page (Ctrl+F5)"
Write-Host "   3. Check logs: docker-compose logs -f web"
Write-Host ""


