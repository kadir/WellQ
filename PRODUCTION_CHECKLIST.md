# Production Deployment Checklist

Use this checklist before deploying WellQ to production.

## Pre-Deployment

### 1. Environment Configuration

- [ ] Copy `.env.example` to `.env`
- [ ] Set `SECRET_KEY` to a strong random string (use `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
- [ ] Set `DEBUG=False`
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure `ALLOWED_HOSTS` with your domain(s)
- [ ] Set strong `DB_PASSWORD`
- [ ] Configure `SECURE_SSL_REDIRECT=True` if using HTTPS
- [ ] Set `USE_PROXY=True` if behind a reverse proxy (nginx/traefik)

### 2. Database

- [ ] Using PostgreSQL (not SQLite)
- [ ] Database credentials are secure
- [ ] Database backups are configured
- [ ] Connection pooling is enabled (CONN_MAX_AGE in settings)

### 3. Security

- [ ] `DEBUG=False` is set
- [ ] `SECRET_KEY` is unique and secure
- [ ] `ALLOWED_HOSTS` is properly configured
- [ ] HTTPS is enabled (if applicable)
- [ ] SSL certificates are valid
- [ ] Security headers are enabled (HSTS, XSS protection, etc.)
- [ ] API tokens are rotated regularly
- [ ] Strong passwords for database and services

### 4. Static Files

- [ ] `STATIC_ROOT` is configured
- [ ] Static files are collected (`python manage.py collectstatic`)
- [ ] Static files are served via CDN or web server (not Django)
- [ ] Media files directory has proper permissions

### 5. Docker (if using)

- [ ] Docker images are built with production settings
- [ ] Environment variables are set correctly
- [ ] Volumes are properly configured
- [ ] Health checks are working
- [ ] Resource limits are set
- [ ] Logs are configured

## Deployment Steps

### 1. Run Production Checks

```bash
# Using Docker
docker-compose exec web python manage.py check_production

# Or manually
python manage.py check_production
```

This will verify:
- ✅ DEBUG is False
- ✅ SECRET_KEY is set
- ✅ ALLOWED_HOSTS is configured
- ✅ Database is PostgreSQL
- ✅ Security settings are enabled

### 2. Database Migrations

```bash
# Using Docker
docker-compose exec web python manage.py migrate

# Or manually
python manage.py migrate
```

### 3. Collect Static Files

```bash
# Using Docker
docker-compose exec web python manage.py collectstatic --noinput

# Or manually
python manage.py collectstatic --noinput
```

### 4. Create Superuser (if needed)

```bash
# Using Docker
docker-compose exec web python manage.py createsuperuser

# Or manually
python manage.py createsuperuser
```

### 5. Verify Services

- [ ] Web server is running
- [ ] Database is accessible
- [ ] Redis is accessible
- [ ] Celery worker is running
- [ ] Celery beat is running
- [ ] All health checks pass

## Post-Deployment

### 1. Verification

- [ ] Application is accessible
- [ ] Login works
- [ ] Dashboard loads
- [ ] API endpoints respond
- [ ] Static files are served
- [ ] Media uploads work
- [ ] Celery tasks are processing

### 2. Monitoring

- [ ] Logs are being collected
- [ ] Error tracking is configured (if applicable)
- [ ] Performance monitoring is set up
- [ ] Database monitoring is active
- [ ] Disk space is monitored

### 3. Backup

- [ ] Database backups are automated
- [ ] Backup restoration is tested
- [ ] Media files are backed up
- [ ] Backup retention policy is set

### 4. Documentation

- [ ] Deployment process is documented
- [ ] Rollback procedure is documented
- [ ] Emergency contacts are available
- [ ] Runbooks are created

## Common Issues

### Issue: "DEBUG is True in production"

**Solution:** Set `DEBUG=False` in `.env` file

### Issue: "ALLOWED_HOSTS is empty"

**Solution:** Set `ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com` in `.env`

### Issue: Static files not loading

**Solution:** 
1. Run `python manage.py collectstatic --noinput`
2. Configure web server to serve static files
3. Check `STATIC_ROOT` is set correctly

### Issue: Database connection errors

**Solution:**
1. Verify database credentials
2. Check database server is running
3. Verify network connectivity
4. Check firewall rules

### Issue: Celery tasks not processing

**Solution:**
1. Verify Redis is running
2. Check Celery worker is running
3. Verify `CELERY_BROKER_URL` is correct
4. Check worker logs for errors

## Security Best Practices

1. **Never commit `.env` files** to version control
2. **Use secrets management** for sensitive data
3. **Rotate credentials** regularly
4. **Keep dependencies updated**: `pip list --outdated`
5. **Use HTTPS** in production
6. **Enable security headers** (already configured in settings)
7. **Monitor logs** for suspicious activity
8. **Regular security audits**

## Performance Optimization

1. **Database**: Use connection pooling, add indexes
2. **Caching**: Configure Redis caching
3. **Static Files**: Use CDN
4. **Celery**: Scale workers horizontally
5. **Gunicorn**: Adjust worker count based on CPU cores

## Rollback Procedure

If deployment fails:

1. Stop new containers: `docker-compose down`
2. Restore database from backup
3. Revert code changes
4. Restart services: `docker-compose up -d`
5. Verify application is working

## Support

For issues:
- Check logs: `docker-compose logs -f web`
- Review error messages
- Check health status: `docker-compose ps`
- Consult documentation

---

**Remember:** Always test in a staging environment before deploying to production!



