# Deployment Guide

## Production Deployment Guide for SaaS Auth API

### Table of Contents
1. [Prerequisites](#prerequisites)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Application Deployment](#application-deployment)
4. [Database Migration](#database-migration)
5. [Monitoring & Logging](#monitoring--logging)
6. [Security Checklist](#security-checklist)
7. [Scaling Strategies](#scaling-strategies)

---

## Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu 20.04 LTS or CentOS 8 recommended)
- **CPU**: 2+ cores
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 50GB SSD
- **Network**: Static IP, ports 80/443/8000 open

### Software Requirements
- Docker 20.10+
- Docker Compose 2.0+
- PostgreSQL 14+
- Redis 6.2+
- Nginx 1.18+ (or Traefik)
- SSL Certificate (Let's Encrypt recommended)

---

## Infrastructure Setup

### 1. Server Preparation

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install essential packages
sudo apt-get install -y curl wget git nano htop nginx certbot

# Configure firewall
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. Docker Installation

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.5.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 3. SSL Certificate Setup

```bash
# Obtain SSL certificate
sudo certbot certonly --standalone -d api.yourdomain.com

# Auto-renewal
echo "0 0,12 * * * root python -c 'import random; import time; time.sleep(random.random() * 3600)' && certbot renew -q" | sudo tee -a /etc/crontab
```

---

## Application Deployment

### 1. Environment Configuration

Create `.env.production`:

```bash
# Application
APP_NAME="SaaS Auth API"
APP_ENV=production
DEBUG=false
APP_VERSION=1.1.0
APP_PORT=8000

# Security
SECRET_KEY=<generate-with-openssl-rand-base64-32>
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database
DATABASE_URL=postgresql://user:password@postgres:5432/saas_auth
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30

# Redis
REDIS_URL=redis://redis:6379/0
REDIS_POOL_SIZE=50

# Email
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=<sendgrid-api-key>
EMAIL_FROM=noreply@yourdomain.com

# Monitoring
SENTRY_DSN=<sentry-dsn>
LOG_LEVEL=INFO

# Feature Flags
ENABLE_WEBHOOKS=true
ENABLE_ANALYTICS=true
ENABLE_REAL_TIME_NOTIFICATIONS=true

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_MONTHLY_QUOTA=10000
```

### 2. Docker Compose Production

Create `docker-compose.production.yml`:

```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: docker/Dockerfile
    restart: always
    env_file:
      - .env.production
    environment:
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    networks:
      - app-network
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  postgres:
    image: postgres:14-alpine
    restart: always
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    networks:
      - app-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:6.2-alpine
    restart: always
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    networks:
      - app-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - static_files:/var/www/static:ro
    depends_on:
      - app
    networks:
      - app-network

  celery_worker:
    build:
      context: .
      dockerfile: docker/Dockerfile
    command: celery -A app.tasks worker --loglevel=info --concurrency=4
    restart: always
    env_file:
      - .env.production
    environment:
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    networks:
      - app-network
    deploy:
      replicas: 2

  celery_beat:
    build:
      context: .
      dockerfile: docker/Dockerfile
    command: celery -A app.tasks beat --loglevel=info
    restart: always
    env_file:
      - .env.production
    depends_on:
      - postgres
      - redis
    networks:
      - app-network

  prometheus:
    image: prom/prometheus:latest
    restart: always
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - app-network

  grafana:
    image: grafana/grafana:latest
    restart: always
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
    networks:
      - app-network
    ports:
      - "3000:3000"

volumes:
  postgres_data:
  redis_data:
  static_files:
  prometheus_data:
  grafana_data:

networks:
  app-network:
    driver: bridge
```

### 3. Nginx Configuration

```nginx
upstream app_servers {
    least_conn;
    server app:8000 weight=5;
    server app:8000 weight=5;
    server app:8000 weight=5;
}

server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    client_max_body_size 10M;

    location / {
        proxy_pass http://app_servers;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    location /static {
        alias /var/www/static;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }

    location /health {
        proxy_pass http://app_servers/health;
        access_log off;
    }
}
```

---

## Database Migration

### Initial Migration

```bash
# Start database only
docker-compose -f docker-compose.production.yml up -d postgres

# Run migrations
docker-compose -f docker-compose.production.yml run --rm app alembic upgrade head

# Verify
docker-compose -f docker-compose.production.yml run --rm app alembic current
```

### Backup Strategy

```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
DB_NAME="saas_auth"

# Create backup
docker-compose -f docker-compose.production.yml exec -T postgres \
    pg_dump -U postgres $DB_NAME | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# Keep only last 7 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete

# Sync to S3 (optional)
aws s3 sync $BACKUP_DIR s3://your-backup-bucket/db-backups/
```

---

## Monitoring & Logging

### Application Monitoring

1. **Prometheus Metrics**
   - Request latency
   - Error rates
   - Active users
   - Database connections
   - Cache hit/miss rates

2. **Grafana Dashboards**
   - System overview
   - API performance
   - Business metrics
   - Error tracking

3. **Health Checks**
```bash
# Application health
curl https://api.yourdomain.com/health

# Database health
docker-compose exec postgres pg_isready

# Redis health
docker-compose exec redis redis-cli ping
```

### Log Aggregation

```yaml
# docker-compose logging
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
    labels: "service_name,environment"
```

---

## Security Checklist

### Pre-Deployment

- [ ] Generate strong SECRET_KEY
- [ ] Enable HTTPS only
- [ ] Configure firewall rules
- [ ] Set up DDoS protection (CloudFlare)
- [ ] Enable database encryption at rest
- [ ] Configure Redis AUTH
- [ ] Set up log monitoring
- [ ] Enable 2FA for admin accounts

### Runtime Security

- [ ] Rate limiting enabled
- [ ] SQL injection protection
- [ ] XSS protection headers
- [ ] CSRF tokens for state-changing operations
- [ ] Input validation on all endpoints
- [ ] Password complexity requirements
- [ ] Account lockout after failed attempts
- [ ] Audit logging enabled

---

## Scaling Strategies

### Horizontal Scaling

```yaml
# Scale application instances
docker-compose up -d --scale app=5

# Load balancing
# Nginx automatically distributes requests
```

### Database Scaling

1. **Read Replicas**
   - Separate read and write operations
   - Use replica for analytics queries

2. **Connection Pooling**
   - PgBouncer for connection management
   - Reduces database load

3. **Sharding** (for >10M users)
   - User ID based sharding
   - Separate databases by region

### Cache Optimization

1. **Redis Cluster**
   - Master-replica setup
   - Automatic failover

2. **CDN Integration**
   - CloudFlare or AWS CloudFront
   - Static asset caching

---

## Maintenance Procedures

### Zero-Downtime Deployment

```bash
#!/bin/bash
# deploy.sh

# 1. Build new images
docker-compose -f docker-compose.production.yml build

# 2. Start new containers alongside old ones
docker-compose -f docker-compose.production.yml up -d --no-deps --scale app=6 app

# 3. Verify new containers healthy
sleep 10

# 4. Remove old containers
docker-compose -f docker-compose.production.yml up -d --no-deps --scale app=3 app

# 5. Cleanup
docker system prune -f
```

### Database Maintenance

```sql
-- Monthly maintenance
VACUUM ANALYZE;
REINDEX TABLE users;
REINDEX TABLE usage_logs;

-- Partition old data
CREATE TABLE usage_logs_2024_01 PARTITION OF usage_logs
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

---

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   ```bash
   # Check memory hogs
docker stats --no-stream
   
   # Restart services
   docker-compose restart app
   ```

2. **Database Connection Pool Exhausted**
   ```bash
   # Check active connections
   docker-compose exec postgres psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"
   
   # Restart application to reset pools
   docker-compose restart app
   ```

3. **Slow Response Times**
   - Check query performance
   - Verify index usage
   - Review slow query log

---

## Support & Contacts

- **Technical Issues**: devops@yourcompany.com
- **Security Concerns**: security@yourcompany.com
- **Emergency Contact**: +1-xxx-xxx-xxxx

---

## Additional Resources

- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [PostgreSQL Tuning](https://wiki.postgresql.org/wiki/Tuning_Your_PostgreSQL_Server)
