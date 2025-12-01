# Docker Setup Guide for WellQ

This guide explains how to set up and run WellQ using Docker and Docker Compose.

## Prerequisites

- Docker Engine 20.10 or later
- Docker Compose 2.0 or later

## Quick Start

1. **Copy the environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file** and set your configuration:
   - Change `SECRET_KEY` to a secure random string
   - Update database credentials if needed
   - Set `ALLOWED_HOSTS` to your domain(s)
   - Set `DEBUG=False` for production

3. **Build and start services:**
   ```bash
   docker-compose up -d --build
   ```

4. **Create a superuser:**
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

5. **Access the application:**
   - Web UI: http://localhost:8000
   - Admin: http://localhost:8000/admin

## Services

The Docker Compose setup includes:

- **web**: Django application (Gunicorn in production)
- **db**: PostgreSQL database
- **redis**: Redis for Celery broker/result backend
- **celery**: Celery worker for background tasks
- **celery-beat**: Celery beat scheduler for periodic tasks

## Development Mode

For development with auto-reload:

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

This will:
- Use Django's development server instead of Gunicorn
- Enable DEBUG mode
- Mount code as volumes for live reloading

## Production Deployment

### Pre-deployment Checks

Before deploying to production, run:

```bash
docker-compose exec web python manage.py check_production
```

This will verify:
- DEBUG is False
- SECRET_KEY is set
- ALLOWED_HOSTS is configured
- Security settings are enabled
- Database is PostgreSQL (not SQLite)

### Environment Variables

Ensure these are set in your `.env` file for production:

```env
DEBUG=False
ENVIRONMENT=production
SECRET_KEY=<strong-random-secret-key>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DB_PASSWORD=<strong-database-password>
SECURE_SSL_REDIRECT=True  # If using HTTPS
USE_PROXY=True  # If behind a reverse proxy
```

### Static Files

Static files are automatically collected in the Docker container. If you need to collect them manually:

```bash
docker-compose exec web python manage.py collectstatic --noinput
```

### Database Migrations

Migrations run automatically on container startup. To run manually:

```bash
docker-compose exec web python manage.py migrate
```

## Common Commands

### View logs
```bash
docker-compose logs -f web
docker-compose logs -f celery
```

### Stop services
```bash
docker-compose down
```

### Stop and remove volumes (⚠️ deletes data)
```bash
docker-compose down -v
```

### Rebuild after code changes
```bash
docker-compose up -d --build
```

### Access Django shell
```bash
docker-compose exec web python manage.py shell
```

### Run management commands
```bash
docker-compose exec web python manage.py <command>
```

## Database Backup

### Backup
```bash
docker-compose exec db pg_dump -U wellq wellq > backup.sql
```

### Restore
```bash
docker-compose exec -T db psql -U wellq wellq < backup.sql
```

## Troubleshooting

### Database connection errors

If you see database connection errors, wait a few seconds for PostgreSQL to start:

```bash
docker-compose logs db
```

### Permission issues

If you encounter permission issues with static files or media:

```bash
docker-compose exec web chown -R www-data:www-data /app/staticfiles /app/media
```

### Reset everything

To start fresh (⚠️ deletes all data):

```bash
docker-compose down -v
docker-compose up -d --build
```

## Production Considerations

1. **Use a reverse proxy** (nginx/traefik) in front of the web service
2. **Set up SSL/TLS** certificates
3. **Use secrets management** for sensitive environment variables
4. **Configure backups** for PostgreSQL data
5. **Set resource limits** in docker-compose.yml
6. **Use Docker secrets** for passwords in production
7. **Monitor logs** and set up log aggregation
8. **Configure health checks** for all services

## Health Checks

All services include health checks. Check status:

```bash
docker-compose ps
```

## Network

Services communicate on the `wellq-network` bridge network. The web service is accessible on port 8000 by default.




