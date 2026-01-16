# Production Deployment Guide

## Prerequisites

- PostgreSQL 12+ (with UTF-8 encoding)
- Redis (for caching)
- Python 3.9+
- Linux server (Ubuntu 20.04+ recommended)

## Step 1: Database Setup

```bash
# Install PostgreSQL
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE DATABASE nepal_times ENCODING 'UTF8';
CREATE USER nepal_times_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE nepal_times TO nepal_times_user;
\q

# Run schema
psql -U nepal_times_user -d nepal_times -f database/schema.sql
```

## Step 2: Redis Setup

```bash
# Install Redis
sudo apt-get install redis-server

# Configure Redis (optional)
sudo nano /etc/redis/redis.conf
# Set: maxmemory 256mb
# Set: maxmemory-policy allkeys-lru

# Start Redis
sudo systemctl start redis
sudo systemctl enable redis
```

## Step 3: Application Setup

```bash
# Clone/upload code
cd /var/www/nepal_times

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements-prod.txt

# Configure environment
cp .env.example .env
nano .env  # Edit with your settings
```

## Step 4: Initialize Database

```bash
# Run migrations (if using Alembic)
alembic upgrade head

# Or initialize directly
python -c "from database import init_db; init_db()"
```

## Step 5: Run with Gunicorn

```bash
# Create systemd service
sudo nano /etc/systemd/system/nepal-times.service

[Unit]
Description=Nepal Times News API
After=network.target postgresql.service redis.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/nepal_times
Environment="PATH=/var/www/nepal_times/venv/bin"
ExecStart=/var/www/nepal_times/venv/bin/gunicorn \
    --workers 4 \
    --bind 0.0.0.0:5000 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    app:app

[Install]
WantedBy=multi-user.target

# Start service
sudo systemctl daemon-reload
sudo systemctl start nepal-times
sudo systemctl enable nepal-times
```

## Step 6: Nginx Configuration

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /var/www/nepal_times/static;
        expires 30d;
    }
}
```

## Step 7: SSL with Let's Encrypt

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Monitoring

- Use systemd logs: `journalctl -u nepal-times -f`
- Set up Sentry for error tracking
- Monitor PostgreSQL and Redis
- Use PM2 or supervisor for process management

## Backup Strategy

```bash
# Database backup
pg_dump -U nepal_times_user nepal_times > backup_$(date +%Y%m%d).sql

# Automated daily backup (cron)
0 2 * * * pg_dump -U nepal_times_user nepal_times > /backups/nepal_times_$(date +\%Y\%m\%d).sql
```






