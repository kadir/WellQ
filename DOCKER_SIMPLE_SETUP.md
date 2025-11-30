# Simple Docker Setup - WellQ

This is the **easiest way** to get WellQ running with Docker. No configuration needed!

## 🚀 One-Command Setup

### Windows (PowerShell)
```powershell
.\setup-docker.ps1
```

### Linux/Mac
```bash
chmod +x setup-docker.sh
./setup-docker.sh
```

### Manual Setup (If scripts don't work)

```bash
# 1. Build and start (that's it!)
docker-compose -f docker-compose.simple.yml up -d --build

# 2. Create superuser
docker-compose -f docker-compose.simple.yml exec web python manage.py createsuperuser

# 3. Access at http://localhost:8000
```

## ✨ What's Different?

### Simple Setup (`docker-compose.simple.yml`)
- ✅ **No .env file needed** - Everything has sensible defaults
- ✅ **Auto-configured** - PostgreSQL and Redis are pre-configured
- ✅ **Works out of the box** - Just run and go!
- ✅ **Perfect for development** - Quick setup, easy to use

### Full Setup (`docker-compose.yml`)
- 🔧 **Requires .env file** - More control over configuration
- 🔧 **Production-ready** - Better for production deployments
- 🔧 **More flexible** - Can customize everything

## 📋 What Gets Configured Automatically

### PostgreSQL
- **Database:** `wellq`
- **User:** `wellq`
- **Password:** `wellq_dev_password` (change in production!)
- **Host:** `db` (internal Docker network)
- **Port:** `5432` (internal)

### Redis
- **Host:** `redis` (internal Docker network)
- **Port:** `6379` (internal)
- **Database:** `0`

### Django
- **SECRET_KEY:** Auto-generated (or from .env if exists)
- **DEBUG:** `True` (development mode)
- **ALLOWED_HOSTS:** `localhost,127.0.0.1,0.0.0.0`

## 🎯 Quick Commands

```bash
# Start everything
docker-compose -f docker-compose.simple.yml up -d

# View logs
docker-compose -f docker-compose.simple.yml logs -f

# Stop everything
docker-compose -f docker-compose.simple.yml down

# Restart a service
docker-compose -f docker-compose.simple.yml restart web

# Access Django shell
docker-compose -f docker-compose.simple.yml exec web python manage.py shell

# Run migrations
docker-compose -f docker-compose.simple.yml exec web python manage.py migrate

# Create superuser
docker-compose -f docker-compose.simple.yml exec web python manage.py createsuperuser
```

## 🔒 For Production

When deploying to production, use the full `docker-compose.yml` and:

1. **Create .env file** with secure values:
```env
SECRET_KEY=your-very-secure-secret-key-here
DEBUG=False
ENVIRONMENT=production
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DB_PASSWORD=strong-database-password
```

2. **Use the full compose file:**
```bash
docker-compose up -d --build
```

## 🆚 Comparison

| Feature | Simple Setup | Full Setup |
|---------|-------------|------------|
| Configuration | Auto | Manual (.env) |
| Best For | Development | Production |
| Setup Time | 1 command | 2-3 steps |
| Flexibility | Limited | Full control |
| Security | Dev defaults | Production-ready |

## 🐛 Troubleshooting

### Port already in use?
```bash
# Change ports in docker-compose.simple.yml
# Or stop the conflicting service
```

### Database connection errors?
```bash
# Wait a bit longer for PostgreSQL to start
docker-compose -f docker-compose.simple.yml logs db

# Check if database is ready
docker-compose -f docker-compose.simple.yml exec db pg_isready -U wellq
```

### Services won't start?
```bash
# Check logs
docker-compose -f docker-compose.simple.yml logs

# Rebuild
docker-compose -f docker-compose.simple.yml up -d --build --force-recreate
```

## 📚 Next Steps

1. ✅ Run setup script
2. ✅ Create superuser
3. ✅ Access http://localhost:8000
4. ✅ Start using WellQ!

That's it! No complex PostgreSQL configuration needed. 🎉


