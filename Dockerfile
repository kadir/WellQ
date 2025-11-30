# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    gcc \
    python3-dev \
    libpq-dev \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy project
COPY . .

# Create directories for static files and media
RUN mkdir -p /app/staticfiles /app/media

# Collect static files (will be run again in entrypoint for production)
RUN python manage.py collectstatic --noinput || true

# Create entrypoint scripts
COPY docker-entrypoint.sh /docker-entrypoint.sh
COPY docker-entrypoint-simple.sh /docker-entrypoint-simple.sh
RUN chmod +x /docker-entrypoint.sh /docker-entrypoint-simple.sh

# Expose port
EXPOSE 8000

# Use entrypoint script
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]

