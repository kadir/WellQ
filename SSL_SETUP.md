# SSL Certificate Setup Guide for demo.wellq.io

This guide will help you set up SSL/TLS certificate for `demo.wellq.io` using Let's Encrypt and certbot.

## Prerequisites

1. **Domain DNS configured**: `demo.wellq.io` must point to your server's IP address
2. **Port 80 and 443 open**: Firewall must allow HTTP (80) and HTTPS (443) traffic
3. **Django running**: Your WellQ application should be running on port 8000
4. **Root/sudo access**: You need root privileges to install nginx and certbot

## Quick Setup (Automated)

### Step 1: Prepare Your Server

```bash
# Navigate to your project directory
cd /opt/WellQ

# Make sure Django is running
docker-compose -f docker-compose.simple.yml up -d

# Verify Django is accessible
curl http://localhost:8000/health/
```

### Step 2: Run the SSL Setup Script

```bash
# Make the script executable
chmod +x scripts/setup-ssl.sh

# Run the setup script (as root)
sudo ./scripts/setup-ssl.sh
```

The script will:
- Install nginx and certbot if not already installed
- Create nginx configuration
- Obtain SSL certificate from Let's Encrypt
- Configure nginx to serve HTTPS
- Set up automatic certificate renewal

### Step 3: Update Django Configuration

Update your `docker-compose.simple.yml` or `.env` file:

```yaml
environment:
  ALLOWED_HOSTS: demo.wellq.io,localhost,127.0.0.1
  SERVE_STATIC: "false"  # nginx will serve static files
  DEBUG: "False"  # Important for production
```

Or set environment variables:

```bash
export ALLOWED_HOSTS="demo.wellq.io,localhost,127.0.0.1"
export SERVE_STATIC="false"
export DEBUG="False"
```

### Step 4: Restart Django

```bash
docker-compose -f docker-compose.simple.yml restart web
```

## Manual Setup

If you prefer to set up SSL manually:

### Step 1: Install Nginx and Certbot

```bash
sudo apt-get update
sudo apt-get install -y nginx certbot python3-certbot-nginx
```

### Step 2: Configure Nginx

Copy the nginx configuration:

```bash
sudo cp nginx/wellq.conf /etc/nginx/sites-available/wellq
sudo ln -s /etc/nginx/sites-available/wellq /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Step 3: Obtain SSL Certificate

```bash
# Using certbot with nginx plugin (easiest)
sudo certbot --nginx -d demo.wellq.io

# Or using webroot method
sudo certbot certonly --webroot \
  --webroot-path=/var/www/certbot \
  -d demo.wellq.io \
  --email your-email@example.com \
  --agree-tos
```

### Step 4: Set Up Auto-Renewal

```bash
# Test renewal
sudo certbot renew --dry-run

# Add to crontab (runs daily at 3 AM)
sudo crontab -e
# Add this line:
0 3 * * * certbot renew --quiet --post-hook 'systemctl reload nginx'
```

## Verify SSL Setup

### Check Certificate

```bash
# Check certificate details
sudo certbot certificates

# Test SSL connection
openssl s_client -connect demo.wellq.io:443 -servername demo.wellq.io
```

### Test HTTPS

```bash
# Test with curl
curl -I https://demo.wellq.io

# Test in browser
# Visit: https://demo.wellq.io
```

### Check SSL Rating

Visit [SSL Labs SSL Test](https://www.ssllabs.com/ssltest/) and enter `demo.wellq.io` to get an SSL rating.

## Troubleshooting

### Certificate Not Obtained

**Issue**: `certbot` fails with "Failed to obtain certificate"

**Solutions**:
1. **Check DNS**: Verify domain points to your server
   ```bash
   dig demo.wellq.io
   nslookup demo.wellq.io
   ```

2. **Check Firewall**: Ensure ports 80 and 443 are open
   ```bash
   sudo ufw status
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   ```

3. **Check Nginx**: Ensure nginx is running and accessible
   ```bash
   sudo systemctl status nginx
   curl http://demo.wellq.io/.well-known/acme-challenge/test
   ```

4. **Check Django**: Ensure Django is running on port 8000
   ```bash
   curl http://localhost:8000/health/
   ```

### Nginx Configuration Errors

**Issue**: `nginx -t` fails

**Solutions**:
1. Check syntax errors in config file
2. Ensure all paths exist (staticfiles, media)
3. Check file permissions

### Certificate Renewal Fails

**Issue**: Auto-renewal doesn't work

**Solutions**:
1. Test renewal manually: `sudo certbot renew --dry-run`
2. Check cron logs: `sudo grep CRON /var/log/syslog`
3. Ensure nginx is running: `sudo systemctl status nginx`

### Mixed Content Warnings

**Issue**: Browser shows "Mixed Content" warnings

**Solutions**:
1. Ensure all static files are served over HTTPS
2. Check Django `SECURE_SSL_REDIRECT` setting
3. Update any hardcoded HTTP URLs in templates

## Nginx Configuration Details

The nginx configuration (`nginx/wellq.conf`) includes:

- **HTTP to HTTPS redirect**: All HTTP traffic redirects to HTTPS
- **SSL/TLS configuration**: Strong ciphers and protocols
- **Security headers**: HSTS, X-Frame-Options, etc.
- **Static file serving**: Direct nginx serving (faster than Django)
- **Proxy configuration**: Proper headers for Django
- **File upload support**: 100MB max body size

## Maintenance

### Renew Certificate Manually

```bash
sudo certbot renew
sudo systemctl reload nginx
```

### Check Certificate Expiry

```bash
sudo certbot certificates
```

### Update Nginx Config

After updating `nginx/wellq.conf`:

```bash
sudo cp nginx/wellq.conf /etc/nginx/sites-available/wellq
sudo nginx -t
sudo systemctl reload nginx
```

## Security Best Practices

1. **Keep certificates updated**: Auto-renewal is set up, but monitor it
2. **Use strong SSL settings**: Already configured in nginx config
3. **Enable security headers**: Already configured
4. **Monitor logs**: Check nginx and certbot logs regularly
5. **Keep software updated**: Regularly update nginx and certbot

## Additional Resources

- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Certbot Documentation](https://certbot.eff.org/)
- [Nginx SSL Configuration](https://nginx.org/en/docs/http/configuring_https_servers.html)


