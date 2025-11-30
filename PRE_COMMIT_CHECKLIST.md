# Pre-Commit Checklist - Files to Delete Before Pushing to GitHub

## 🗑️ Files/Folders to DELETE

### 1. Python Cache Files (__pycache__)
**Location:** Throughout the project
**Command:**
```bash
# Windows PowerShell
Get-ChildItem -Path . -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force

# Windows CMD
for /d /r . %d in (__pycache__) do @if exist "%d" rd /s /q "%d"

# Linux/Mac
find . -type d -name __pycache__ -exec rm -r {} +
```

### 2. Database File
**File:** `db.sqlite3`
**Why:** Contains local development data, should not be in version control
**Command:**
```bash
# Windows
del db.sqlite3

# Linux/Mac
rm db.sqlite3
```

### 3. Environment Files
**Files:** `.env`, `.env.local`, `.env.*`
**Why:** Contains sensitive secrets and local configuration
**Command:**
```bash
# Check if they exist first
ls .env*

# Delete if found
rm .env .env.local .env.*
```

### 4. Static Files (Collected)
**Folder:** `staticfiles/` (if exists)
**Why:** Generated files, should be collected in production
**Command:**
```bash
rm -rf staticfiles/
```

### 5. Media Files (User Uploads)
**Folder:** `media/` (if exists)
**Why:** User-uploaded content, should not be in version control
**Command:**
```bash
rm -rf media/
```

### 6. Virtual Environment
**Folders:** `venv/`, `.venv/`, `env/`, `ENV/`
**Why:** Can be recreated, too large for git
**Command:**
```bash
rm -rf venv/ .venv/ env/ ENV/
```

### 7. IDE/Editor Files
**Folders:** `.vscode/`, `.idea/`, `.pycharm/`
**Why:** IDE-specific settings (optional, but recommended)
**Command:**
```bash
rm -rf .vscode/ .idea/ .pycharm/
```

### 8. OS Files
**Files:** `.DS_Store`, `Thumbs.db`, `desktop.ini`
**Why:** OS-specific files
**Command:**
```bash
# Mac
find . -name .DS_Store -delete

# Windows
del Thumbs.db /s /q
del desktop.ini /s /q
```

### 9. Log Files
**Files:** `*.log`, `*.log.*`
**Why:** Generated logs
**Command:**
```bash
find . -name "*.log" -type f -delete
```

### 10. Test SBOM Files (Optional)
**File:** `sboms/test_Product_v1.13.0_sbom.json`
**Why:** Test data, might want to keep for examples or remove
**Decision:** Your choice - keep if useful for examples, delete if not needed

### 11. Celery Beat Schedule
**Files:** `celerybeat-schedule`, `celerybeat.pid`
**Why:** Local Celery state files
**Command:**
```bash
rm -f celerybeat-schedule celerybeat.pid
```

### 12. Helm Chart Dependencies (Optional)
**Folder:** `helm/wellq/charts/` (if exists after `helm dependency update`)
**Why:** Downloaded chart dependencies, will be regenerated
**Note:** Only delete if you've run `helm dependency update` locally

## ✅ Quick Cleanup Script

### Windows PowerShell
```powershell
# Delete __pycache__ folders
Get-ChildItem -Path . -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force

# Delete database
if (Test-Path db.sqlite3) { Remove-Item db.sqlite3 }

# Delete staticfiles
if (Test-Path staticfiles) { Remove-Item -Recurse -Force staticfiles }

# Delete media
if (Test-Path media) { Remove-Item -Recurse -Force media }

# Delete venv
if (Test-Path venv) { Remove-Item -Recurse -Force venv }
if (Test-Path .venv) { Remove-Item -Recurse -Force .venv }

# Delete IDE folders
if (Test-Path .vscode) { Remove-Item -Recurse -Force .vscode }
if (Test-Path .idea) { Remove-Item -Recurse -Force .idea }

# Delete log files
Get-ChildItem -Path . -Recurse -File -Filter *.log | Remove-Item -Force

# Delete Celery files
if (Test-Path celerybeat-schedule) { Remove-Item celerybeat-schedule }
if (Test-Path celerybeat.pid) { Remove-Item celerybeat.pid }
```

### Linux/Mac Bash
```bash
#!/bin/bash
# Delete __pycache__ folders
find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null

# Delete database
rm -f db.sqlite3

# Delete staticfiles
rm -rf staticfiles/

# Delete media
rm -rf media/

# Delete venv
rm -rf venv/ .venv/ env/ ENV/

# Delete IDE folders
rm -rf .vscode/ .idea/ .pycharm/

# Delete OS files
find . -name .DS_Store -delete 2>/dev/null
find . -name Thumbs.db -delete 2>/dev/null

# Delete log files
find . -name "*.log" -type f -delete

# Delete Celery files
rm -f celerybeat-schedule celerybeat.pid
```

## 🔍 Verify Before Committing

### Check what will be committed:
```bash
git status
```

### Check for large files:
```bash
# Find files larger than 1MB
find . -type f -size +1M -not -path "./.git/*" -not -path "./venv/*" -not -path "./.venv/*"
```

### Check for sensitive files:
```bash
# Look for potential secrets
grep -r "SECRET_KEY" --include="*.py" --include="*.env" .
grep -r "password" --include="*.py" --include="*.env" . | grep -i "="
```

## 📋 Final Checklist

Before pushing to GitHub, ensure:

- [ ] All `__pycache__/` folders deleted
- [ ] `db.sqlite3` deleted
- [ ] `.env` files deleted (if any)
- [ ] `staticfiles/` folder deleted (if exists)
- [ ] `media/` folder deleted (if exists)
- [ ] `venv/` or `.venv/` deleted
- [ ] `.vscode/` or `.idea/` deleted (optional)
- [ ] Log files deleted
- [ ] Celery beat files deleted
- [ ] No sensitive data in code
- [ ] `.gitignore` is up to date
- [ ] `git status` shows only intended files

## 🚀 Ready to Commit

After cleanup:

```bash
# Stage all changes
git add .

# Review what will be committed
git status

# Commit
git commit -m "Your commit message"

# Push
git push origin main
```

## ⚠️ Important Notes

1. **Never commit:**
   - `.env` files with secrets
   - `db.sqlite3` with real data
   - API keys or passwords
   - Personal credentials

2. **Always check:**
   - `git status` before committing
   - `git diff` to see what changed
   - Large files (>100MB) - GitHub has limits

3. **Use `.gitignore`:**
   - Already configured for most common files
   - Add custom patterns if needed



