#!/bin/bash
# SSL Certificate Setup Script for WellQ
# This script sets up Let's Encrypt SSL certificate using certbot

set -e

DOMAIN="demo.wellq.io"
EMAIL="${CERTBOT_EMAIL:-admin@wellq.io}"  # Change this to your email
NGINX_CONF="/etc/nginx/sites-available/wellq"
NGINX_ENABLED="/etc/nginx/sites-enabled/wellq"
CERTBOT_WEBROOT="/var/www/certbot"

echo "🔒 Setting up SSL certificate for $DOMAIN"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (use sudo)"
    exit 1
fi

# Check if nginx is installed
if ! command -v nginx &> /dev/null; then
    echo "📦 Installing nginx..."
    apt-get update
    apt-get install -y nginx
fi

# Check if certbot is installed
if ! command -v certbot &> /dev/null; then
    echo "📦 Installing certbot..."
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
fi

# Create certbot webroot directory
echo "📁 Creating certbot webroot directory..."
mkdir -p "$CERTBOT_WEBROOT"
chmod 755 "$CERTBOT_WEBROOT"

# Check if nginx config exists
if [ ! -f "$NGINX_CONF" ]; then
    echo "📝 Creating nginx configuration..."
    
    # Copy nginx config from project
    if [ -f "/opt/WellQ/nginx/wellq.conf" ]; then
        cp /opt/WellQ/nginx/wellq.conf "$NGINX_CONF"
    else
        echo "⚠️  Warning: nginx config not found at /opt/WellQ/nginx/wellq.conf"
        echo "   Please copy nginx/wellq.conf to $NGINX_CONF manually"
        exit 1
    fi
fi

# Create temporary HTTP-only config for initial certbot run
echo "📝 Creating temporary HTTP-only nginx config..."
cat > /tmp/wellq-temp.conf <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;

    location /.well-known/acme-challenge/ {
        root $CERTBOT_WEBROOT;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Backup existing config if it exists
if [ -f "$NGINX_CONF" ]; then
    cp "$NGINX_CONF" "${NGINX_CONF}.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Use temporary config for initial setup
cp /tmp/wellq-temp.conf "$NGINX_CONF"

# Enable site
if [ ! -L "$NGINX_ENABLED" ]; then
    ln -s "$NGINX_CONF" "$NGINX_ENABLED"
fi

# Test nginx configuration
echo "🧪 Testing nginx configuration..."
nginx -t || {
    echo "❌ Nginx configuration test failed!"
    exit 1
}

# Reload nginx
echo "🔄 Reloading nginx..."
systemctl reload nginx || systemctl start nginx

# Check if Django is running
echo "🔍 Checking if Django is running on port 8000..."
if ! curl -f http://127.0.0.1:8000/health/ > /dev/null 2>&1; then
    echo "⚠️  Warning: Django doesn't seem to be running on port 8000"
    echo "   Please start your Django application first:"
    echo "   docker-compose -f docker-compose.simple.yml up -d"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Obtain SSL certificate
echo ""
echo "🔐 Obtaining SSL certificate from Let's Encrypt..."
echo "   Domain: $DOMAIN"
echo "   Email: $EMAIL"
echo ""

certbot certonly \
    --webroot \
    --webroot-path="$CERTBOT_WEBROOT" \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --non-interactive \
    -d "$DOMAIN" || {
    echo ""
    echo "❌ Failed to obtain certificate!"
    echo ""
    echo "Common issues:"
    echo "1. Domain $DOMAIN must point to this server's IP"
    echo "2. Port 80 must be open and accessible"
    echo "3. Django must be running on port 8000"
    echo ""
    echo "Check DNS: dig $DOMAIN"
    echo "Check firewall: sudo ufw status"
    exit 1
}

# Restore full nginx config
echo "📝 Restoring full nginx configuration with SSL..."
if [ -f "/opt/WellQ/nginx/wellq.conf" ]; then
    cp /opt/WellQ/nginx/wellq.conf "$NGINX_CONF"
else
    echo "⚠️  Warning: Full nginx config not found. Using basic SSL config..."
    # Create basic SSL config
    cat > "$NGINX_CONF" <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /static/ {
        alias /opt/WellQ/staticfiles/;
    }

    location /media/ {
        alias /opt/WellQ/media/;
    }
}
EOF
fi

# Test nginx configuration again
echo "🧪 Testing nginx configuration with SSL..."
nginx -t || {
    echo "❌ Nginx configuration test failed!"
    exit 1
}

# Reload nginx
echo "🔄 Reloading nginx with SSL configuration..."
systemctl reload nginx

# Set up auto-renewal
echo "🔄 Setting up automatic certificate renewal..."
(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet --post-hook 'systemctl reload nginx'") | crontab -

echo ""
echo "✅ SSL certificate setup complete!"
echo ""
echo "🌐 Your site should now be accessible at: https://$DOMAIN"
echo ""
echo "📋 Next steps:"
echo "1. Update ALLOWED_HOSTS in Django to include: $DOMAIN"
echo "2. Set SERVE_STATIC=false in your environment (nginx will serve static files)"
echo "3. Restart your Django application"
echo ""
echo "🔍 Test your setup:"
echo "   curl -I https://$DOMAIN"
echo ""


