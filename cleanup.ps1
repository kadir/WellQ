# WellQ Pre-Commit Cleanup Script for Windows PowerShell
# Run this before committing to GitHub

Write-Host "🧹 Cleaning up files before commit..." -ForegroundColor Cyan

# Delete __pycache__ folders
Write-Host "Deleting __pycache__ folders..." -ForegroundColor Yellow
$pycache = Get-ChildItem -Path . -Recurse -Directory -Filter __pycache__ -ErrorAction SilentlyContinue
if ($pycache) {
    $pycache | Remove-Item -Recurse -Force
    Write-Host "✓ Deleted $($pycache.Count) __pycache__ folder(s)" -ForegroundColor Green
} else {
    Write-Host "✓ No __pycache__ folders found" -ForegroundColor Green
}

# Delete database
Write-Host "Checking for database file..." -ForegroundColor Yellow
if (Test-Path db.sqlite3) {
    Remove-Item db.sqlite3 -Force
    Write-Host "✓ Deleted db.sqlite3" -ForegroundColor Green
} else {
    Write-Host "✓ No db.sqlite3 found" -ForegroundColor Green
}

# Delete .env files
Write-Host "Checking for .env files..." -ForegroundColor Yellow
$envFiles = Get-ChildItem -Path . -Filter .env* -File -ErrorAction SilentlyContinue
if ($envFiles) {
    $envFiles | Remove-Item -Force
    Write-Host "✓ Deleted $($envFiles.Count) .env file(s)" -ForegroundColor Green
} else {
    Write-Host "✓ No .env files found" -ForegroundColor Green
}

# Delete staticfiles
Write-Host "Checking for staticfiles folder..." -ForegroundColor Yellow
if (Test-Path staticfiles) {
    Remove-Item -Recurse -Force staticfiles
    Write-Host "✓ Deleted staticfiles folder" -ForegroundColor Green
} else {
    Write-Host "✓ No staticfiles folder found" -ForegroundColor Green
}

# Delete media
Write-Host "Checking for media folder..." -ForegroundColor Yellow
if (Test-Path media) {
    Remove-Item -Recurse -Force media
    Write-Host "✓ Deleted media folder" -ForegroundColor Green
} else {
    Write-Host "✓ No media folder found" -ForegroundColor Green
}

# Delete venv
Write-Host "Checking for virtual environment..." -ForegroundColor Yellow
if (Test-Path venv) {
    Remove-Item -Recurse -Force venv
    Write-Host "✓ Deleted venv folder" -ForegroundColor Green
}
if (Test-Path .venv) {
    Remove-Item -Recurse -Force .venv
    Write-Host "✓ Deleted .venv folder" -ForegroundColor Green
}
if (-not (Test-Path venv) -and -not (Test-Path .venv)) {
    Write-Host "✓ No virtual environment found" -ForegroundColor Green
}

# Delete IDE folders
Write-Host "Checking for IDE folders..." -ForegroundColor Yellow
$deleted = $false
if (Test-Path .vscode) {
    Remove-Item -Recurse -Force .vscode
    Write-Host "✓ Deleted .vscode folder" -ForegroundColor Green
    $deleted = $true
}
if (Test-Path .idea) {
    Remove-Item -Recurse -Force .idea
    Write-Host "✓ Deleted .idea folder" -ForegroundColor Green
    $deleted = $true
}
if (-not $deleted) {
    Write-Host "✓ No IDE folders found" -ForegroundColor Green
}

# Delete log files
Write-Host "Checking for log files..." -ForegroundColor Yellow
$logFiles = Get-ChildItem -Path . -Recurse -Filter *.log -File -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notlike "*\.git\*" }
if ($logFiles) {
    $logFiles | Remove-Item -Force
    Write-Host "✓ Deleted $($logFiles.Count) log file(s)" -ForegroundColor Green
} else {
    Write-Host "✓ No log files found" -ForegroundColor Green
}

# Delete Celery files
Write-Host "Checking for Celery files..." -ForegroundColor Yellow
$deleted = $false
if (Test-Path celerybeat-schedule) {
    Remove-Item celerybeat-schedule -Force
    Write-Host "✓ Deleted celerybeat-schedule" -ForegroundColor Green
    $deleted = $true
}
if (Test-Path celerybeat.pid) {
    Remove-Item celerybeat.pid -Force
    Write-Host "✓ Deleted celerybeat.pid" -ForegroundColor Green
    $deleted = $true
}
if (-not $deleted) {
    Write-Host "✓ No Celery files found" -ForegroundColor Green
}

# Delete OS files
Write-Host "Checking for OS files..." -ForegroundColor Yellow
$osFiles = Get-ChildItem -Path . -Recurse -Filter .DS_Store -File -ErrorAction SilentlyContinue
if ($osFiles) {
    $osFiles | Remove-Item -Force
    Write-Host "✓ Deleted $($osFiles.Count) .DS_Store file(s)" -ForegroundColor Green
}
$thumbFiles = Get-ChildItem -Path . -Recurse -Filter Thumbs.db -File -ErrorAction SilentlyContinue
if ($thumbFiles) {
    $thumbFiles | Remove-Item -Force
    Write-Host "✓ Deleted $($thumbFiles.Count) Thumbs.db file(s)" -ForegroundColor Green
}

Write-Host "`n✅ Cleanup complete! Ready to commit." -ForegroundColor Green
Write-Host "`nRun 'git status' to see what will be committed." -ForegroundColor Cyan


