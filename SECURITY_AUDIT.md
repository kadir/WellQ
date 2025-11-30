# Security Audit Report - WellQ ASPM Platform

## Executive Summary
This security audit identifies several critical and medium-severity issues that need to be addressed before production deployment.

## Critical Issues (Must Fix)

### 1. **ALLOWED_HOSTS Configuration** ⚠️ CRITICAL
**Location:** `core/settings.py:32`
**Issue:** `ALLOWED_HOSTS = []` is empty, which is insecure in production.
**Risk:** Host header injection attacks, potential cache poisoning.
**Fix:** Set `ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')` and configure in production.

### 2. **DEBUG Mode** ⚠️ CRITICAL
**Location:** `core/settings.py:30`
**Issue:** `DEBUG = os.getenv('DEBUG') == 'True'` - string comparison may fail.
**Risk:** Debug mode exposes sensitive information, stack traces, and internal paths.
**Fix:** Use `DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'` and ensure it's False in production.

### 3. **SECRET_KEY Default** ⚠️ CRITICAL
**Location:** `core/settings.py:27`
**Issue:** `SECRET_KEY = os.getenv('SECRET_KEY', 'default-insecure-key-for-dev')`
**Risk:** If SECRET_KEY is not set, uses insecure default. Session hijacking, password reset token compromise.
**Fix:** Remove default or raise error if not set in production.

### 4. **File Upload Validation** ⚠️ HIGH
**Location:** `core/views/findings.py:158`, `core/api/views.py:102`
**Issue:** Only checks file extension (`.json`), not actual file content or size.
**Risk:** 
- Malicious files with `.json` extension
- DoS via large file uploads
- Path traversal in filenames
**Fix:** 
- Validate file content (MIME type, magic bytes)
- Set file size limits
- Sanitize filenames
- Use Django's `FileField` with proper storage

### 5. **JSON Parsing Without Limits** ⚠️ HIGH
**Location:** `core/services/sbom.py:14`, `core/scanners/trivy.py:12`
**Issue:** `json.load()` without size limits can cause DoS.
**Risk:** Memory exhaustion from large JSON files.
**Fix:** Implement file size limits and streaming JSON parsing for large files.

### 6. **No Rate Limiting** ⚠️ MEDIUM
**Issue:** No rate limiting on API endpoints or file uploads.
**Risk:** DoS attacks, brute force attempts.
**Fix:** Implement rate limiting using `django-ratelimit` or DRF throttling.

## Medium Issues

### 7. **Missing Security Headers** ⚠️ MEDIUM
**Issue:** No security headers configured (HSTS, CSP, X-Frame-Options, etc.)
**Risk:** Clickjacking, XSS, MITM attacks.
**Fix:** Use `django-security` or configure headers manually.

### 8. **No HTTPS Enforcement** ⚠️ MEDIUM
**Issue:** No HTTPS redirect or enforcement.
**Risk:** Man-in-the-middle attacks, credential theft.
**Fix:** Set `SECURE_SSL_REDIRECT = True` in production.

### 9. **File Size Limits Missing** ⚠️ MEDIUM
**Issue:** No `DATA_UPLOAD_MAX_MEMORY_SIZE` or `FILE_UPLOAD_MAX_MEMORY_SIZE` configured.
**Risk:** DoS via large uploads.
**Fix:** Set appropriate limits in settings.

### 10. **URL Validation** ⚠️ MEDIUM
**Location:** `core/models.py:357`, `core/views/settings.py`
**Issue:** PlatformSettings URLs are validated as URLField but not checked for malicious schemes.
**Risk:** SSRF (Server-Side Request Forgery) if URLs are used in requests.
**Fix:** Validate URLs, whitelist allowed schemes (http, https), validate domains.

## Good Security Practices Found ✅

1. ✅ **Django ORM Usage** - All database queries use ORM (SQL injection protected)
2. ✅ **CSRF Protection** - CSRF middleware enabled
3. ✅ **Authentication Required** - All views use `@login_required` or `IsAuthenticated`
4. ✅ **Password Validators** - Django's built-in validators configured
5. ✅ **No Command Injection** - No `eval()`, `exec()`, or `subprocess` with user input
6. ✅ **Template Auto-escaping** - Django templates auto-escape by default
7. ✅ **UUID Primary Keys** - Prevents ID enumeration attacks
8. ✅ **Admin Checks** - Proper authorization checks for admin functions
9. ✅ **No Raw SQL** - No `.raw()` or `.extra()` queries found
10. ✅ **Token Authentication** - Secure API token implementation with hashing

## Recommendations

### Immediate Actions (Before Production):
1. Configure `ALLOWED_HOSTS` properly
2. Ensure `DEBUG = False` in production
3. Set strong `SECRET_KEY` in environment
4. Implement file upload validation and size limits
5. Add rate limiting
6. Configure security headers
7. Enable HTTPS enforcement

### Short-term Improvements:
1. Add file content validation (magic bytes, MIME type)
2. Implement request size limits
3. Add URL validation for PlatformSettings
4. Add logging and monitoring
5. Implement API versioning
6. Add input sanitization for user-generated content

### Long-term Enhancements:
1. Implement WAF (Web Application Firewall)
2. Add security scanning in CI/CD
3. Regular dependency updates
4. Security testing and penetration testing
5. Implement audit logging
6. Add IP whitelisting for admin functions

## Testing Checklist

- [ ] Test file upload with malicious content
- [ ] Test file upload with oversized files
- [ ] Test API rate limiting
- [ ] Test CSRF protection
- [ ] Test authentication bypass attempts
- [ ] Test authorization checks
- [ ] Test SQL injection attempts (should all fail)
- [ ] Test XSS in user inputs
- [ ] Test path traversal in file uploads
- [ ] Test SSRF in URL fields


