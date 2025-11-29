#!/bin/bash
# WellQ Pre-Commit Cleanup Script for Linux/Mac
# Run this before committing to GitHub

echo "🧹 Cleaning up files before commit..."

# Delete __pycache__ folders
echo "Deleting __pycache__ folders..."
find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✓ Deleted __pycache__ folders"
else
    echo "✓ No __pycache__ folders found"
fi

# Delete database
echo "Checking for database file..."
if [ -f db.sqlite3 ]; then
    rm -f db.sqlite3
    echo "✓ Deleted db.sqlite3"
else
    echo "✓ No db.sqlite3 found"
fi

# Delete .env files
echo "Checking for .env files..."
env_count=$(find . -maxdepth 1 -name ".env*" -type f 2>/dev/null | wc -l)
if [ $env_count -gt 0 ]; then
    find . -maxdepth 1 -name ".env*" -type f -delete
    echo "✓ Deleted $env_count .env file(s)"
else
    echo "✓ No .env files found"
fi

# Delete staticfiles
echo "Checking for staticfiles folder..."
if [ -d staticfiles ]; then
    rm -rf staticfiles/
    echo "✓ Deleted staticfiles folder"
else
    echo "✓ No staticfiles folder found"
fi

# Delete media
echo "Checking for media folder..."
if [ -d media ]; then
    rm -rf media/
    echo "✓ Deleted media folder"
else
    echo "✓ No media folder found"
fi

# Delete venv
echo "Checking for virtual environment..."
deleted=false
if [ -d venv ]; then
    rm -rf venv/
    echo "✓ Deleted venv folder"
    deleted=true
fi
if [ -d .venv ]; then
    rm -rf .venv/
    echo "✓ Deleted .venv folder"
    deleted=true
fi
if [ "$deleted" = false ]; then
    echo "✓ No virtual environment found"
fi

# Delete IDE folders
echo "Checking for IDE folders..."
deleted=false
if [ -d .vscode ]; then
    rm -rf .vscode/
    echo "✓ Deleted .vscode folder"
    deleted=true
fi
if [ -d .idea ]; then
    rm -rf .idea/
    echo "✓ Deleted .idea folder"
    deleted=true
fi
if [ "$deleted" = false ]; then
    echo "✓ No IDE folders found"
fi

# Delete log files
echo "Checking for log files..."
log_count=$(find . -name "*.log" -type f ! -path "./.git/*" 2>/dev/null | wc -l)
if [ $log_count -gt 0 ]; then
    find . -name "*.log" -type f ! -path "./.git/*" -delete
    echo "✓ Deleted $log_count log file(s)"
else
    echo "✓ No log files found"
fi

# Delete Celery files
echo "Checking for Celery files..."
deleted=false
if [ -f celerybeat-schedule ]; then
    rm -f celerybeat-schedule
    echo "✓ Deleted celerybeat-schedule"
    deleted=true
fi
if [ -f celerybeat.pid ]; then
    rm -f celerybeat.pid
    echo "✓ Deleted celerybeat.pid"
    deleted=true
fi
if [ "$deleted" = false ]; then
    echo "✓ No Celery files found"
fi

# Delete OS files
echo "Checking for OS files..."
ds_count=$(find . -name .DS_Store -type f 2>/dev/null | wc -l)
if [ $ds_count -gt 0 ]; then
    find . -name .DS_Store -delete
    echo "✓ Deleted $ds_count .DS_Store file(s)"
fi
thumb_count=$(find . -name Thumbs.db -type f 2>/dev/null | wc -l)
if [ $thumb_count -gt 0 ]; then
    find . -name Thumbs.db -delete
    echo "✓ Deleted $thumb_count Thumbs.db file(s)"
fi

echo ""
echo "✅ Cleanup complete! Ready to commit."
echo ""
echo "Run 'git status' to see what will be committed."

