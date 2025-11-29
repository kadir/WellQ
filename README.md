# WellQ

Open-source ASPM (Application Security Posture Management) platform built with Django. Aggregates SAST, SCA, DAST, container, and malware scan results; normalizes and deduplicates findings; enriches them with threat intel; manages SBOMs; and provides dashboards, risk scoring, and CI/CD integrations for full AppSec visibility.

## Features

- 🔍 **Multi-Scanner Support**: Aggregates results from Trivy, Grype, Snyk, and more
- 📊 **Unified Dashboard**: Centralized view of all security findings across products
- 🔄 **Deduplication**: Hash-based fingerprinting to track vulnerabilities across scans
- 🎯 **Threat Intelligence**: Automatic enrichment with EPSS scores and CISA KEV data
- 📦 **SBOM Management**: Upload, parse, and export Software Bill of Materials (CycloneDX)
- 🚀 **REST API**: Full API with Swagger documentation for CI/CD integration
- 🔐 **API Token Authentication**: Secure token-based API access with revocation
- 📈 **Vulnerability Status Management**: Track findings as Active, Fixed, Risk Accepted, False Positive, or Duplicate
- ⚡ **Async Processing**: Background task processing with Celery for scalability
- 🎨 **Modern UI**: Clean, responsive interface built with Tailwind CSS

## Architecture

- **Backend**: Django 5.2 + Django REST Framework
- **Task Queue**: Celery with Redis broker
- **Database**: PostgreSQL (production) / SQLite (development)
- **API Documentation**: drf-spectacular (Swagger/OpenAPI)
- **Frontend**: Django Templates + Tailwind CSS

## Prerequisites

- Python 3.10+
- Redis 6.0+ (for Celery task queue)
- PostgreSQL 12+ (for production)
- pip and virtualenv

## Installation

### Option 1: Docker (Recommended)

See [DOCKER_SETUP.md](DOCKER_SETUP.md) for detailed Docker setup instructions.

**Quick Start:**
```bash
# Copy environment file
cp .env.example .env
# Edit .env with your settings

# Build and start
docker-compose up -d --build

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Access at http://localhost:8000
```

### Option 2: Manual Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd WellQ
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file in the project root:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (SQLite for development)
# For production, use PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost:5432/wellq

# Celery/Redis
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 5. Database Setup

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 6. Install and Start Redis

**Windows:**
- Download Redis from: https://github.com/microsoftarchive/redis/releases
- Or use WSL2 with Redis
- Or use Docker: `docker run -d -p 6379:6379 redis:latest`

**Linux:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

**Mac:**
```bash
brew install redis
brew services start redis
```

**Docker (Recommended):**
```bash
docker run -d -p 6379:6379 --name redis redis:latest
```

## Running the Application

### Development Mode

You need to run **3 processes** simultaneously:

#### Terminal 1: Django Development Server
```bash
python manage.py runserver
```
Access the application at: http://localhost:8000

#### Terminal 2: Celery Worker
```bash
celery -A core worker -l info
```
This processes background tasks (scan uploads, SBOM parsing, etc.)

#### Terminal 3: Celery Beat (Scheduler)
```bash
celery -A core beat -l info
```
This runs scheduled tasks (daily threat intel enrichment)

### Production Mode

#### Using systemd (Linux)

Create service files:

**`/etc/systemd/system/wellq-celery.service`**
```ini
[Unit]
Description=WellQ Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/path/to/WellQ
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/celery -A core worker --loglevel=info --logfile=/var/log/celery/worker.log --pidfile=/var/run/celery/worker.pid --detach
ExecStop=/bin/kill -s TERM $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/wellq-celery-beat.service`**
```ini
[Unit]
Description=WellQ Celery Beat Scheduler
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/path/to/WellQ
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/celery -A core beat --loglevel=info --logfile=/var/log/celery/beat.log --pidfile=/var/run/celery/beat.pid --detach
ExecStop=/bin/kill -s TERM $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start services:
```bash
sudo systemctl enable wellq-celery.service
sudo systemctl enable wellq-celery-beat.service
sudo systemctl start wellq-celery.service
sudo systemctl start wellq-celery-beat.service
```

#### Using Gunicorn + Nginx

**Gunicorn:**
```bash
pip install gunicorn
gunicorn core.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

**Nginx Configuration:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /path/to/WellQ/core/static/;
    }

    location /media/ {
        alias /path/to/WellQ/media/;
    }
}
```

#### Using Docker Compose

Docker Compose configuration is included in the repository. See [DOCKER_SETUP.md](DOCKER_SETUP.md) for detailed instructions.

**Quick Start:**
```bash
cp .env.example .env
# Edit .env file
docker-compose up -d --build
docker-compose exec web python manage.py createsuperuser
```

The Docker setup includes:
- PostgreSQL database
- Redis for Celery
- Django web application (Gunicorn)
- Celery worker
- Celery beat scheduler

## Configuration

### Database (Production)

Update `core/settings.py` or use environment variable:

```python
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3')
    )
}
```

### Celery Settings

Configured in `core/settings.py`:
- **Broker**: Redis (default: `redis://localhost:6379/0`)
- **Result Backend**: Redis (default: `redis://localhost:6379/0`)
- **Task Timeout**: 30 minutes
- **Scheduled Tasks**: Daily threat intel enrichment at 2 AM

### Static Files

```bash
# Collect static files for production
python manage.py collectstatic --noinput
```

## API Documentation

### Access Swagger UI

Once the server is running:
- **Swagger UI**: http://localhost:8000/api/swagger/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

### API Authentication

1. Create an API token via the web UI: `/profile/api-tokens/create/`
2. Use the token in API requests:
```bash
curl -H "Authorization: Token your-token-here" \
     -F "workspace_id=..." \
     -F "product_name=..." \
     -F "release_name=..." \
     -F "scanner_name=Trivy" \
     -F "scan_file=@scan.json" \
     http://localhost:8000/api/v1/scans/upload/
```

### Key API Endpoints

- `POST /api/v1/scans/upload/` - Upload scan results (async)
- `POST /api/v1/sbom/upload/` - Upload SBOM file (async)
- `GET /api/v1/releases/{id}/sbom/export/` - Export SBOM
- `GET /api/v1/findings/` - List findings with filters
- `GET /api/v1/workspaces/` - List workspaces
- `GET /api/v1/products/` - List products

## Management Commands

### Enrich Findings with Threat Intel

```bash
# Manual enrichment (also runs automatically via Celery Beat)
python manage.py enrich_db
```

## Development

### Running Tests

```bash
python manage.py test
```

### Code Style

```bash
# Install black and flake8
pip install black flake8

# Format code
black .

# Lint code
flake8 .
```

### Database Migrations

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate
```

## Monitoring

### Celery Monitoring

Install Flower for Celery monitoring:
```bash
pip install flower
celery -A core flower
```

Access at: http://localhost:5555

### Check Celery Status

```bash
# Check worker status
celery -A core inspect active

# Check scheduled tasks
celery -A core inspect scheduled
```

## Troubleshooting

### Celery Worker Not Starting

1. Check Redis is running: `redis-cli ping` (should return `PONG`)
2. Check Celery broker URL in settings
3. Check logs: `celery -A core worker -l debug`

### Tasks Not Processing

1. Verify worker is running: `celery -A core inspect active`
2. Check Redis connection
3. Review worker logs for errors

### Database Connection Issues

1. Verify database credentials in `.env`
2. Check database server is running
3. Run migrations: `python manage.py migrate`

## Security Considerations

- **Never commit `.env` file** to version control
- Use strong `SECRET_KEY` in production
- Set `DEBUG=False` in production
- Use HTTPS in production
- Regularly rotate API tokens
- Keep dependencies updated: `pip list --outdated`

## Performance Optimization

For 100+ concurrent users:

1. **Database**: Use PostgreSQL with connection pooling
2. **Caching**: Configure Redis caching (Django cache framework)
3. **Static Files**: Serve via CDN or Nginx
4. **Celery Workers**: Scale horizontally (multiple workers)
5. **Database Indexes**: Ensure indexes on frequently queried fields

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

See LICENSE file for details.

## Support

For issues and questions:
- Open an issue on GitHub
- Check the API documentation at `/api/swagger/`

---

**Built with ❤️ for the security community**
