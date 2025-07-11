# DataOps Monitoring Platform - Deployment Guide

This guide covers different deployment options for the DataOps Monitoring Platform.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- PostgreSQL 12+
- Redis 6+
- Docker & Docker Compose (for containerized deployment)

### Option 1: Local Development Setup

1. **Clone the repository:**
```bash
git clone <repository-url>
cd DataOps-Monitoring
```

2. **Run the setup script:**
```bash
./setup.sh
```

3. **Start the services:**
```bash
./setup.sh start
```

4. **Access the application:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000
- Admin login: admin@dataops.com / admin123

### Option 2: Docker Compose Deployment

1. **Clone and setup:**
```bash
git clone <repository-url>
cd DataOps-Monitoring
```

2. **Configure environment:**
```bash
cp backend/env.example backend/.env
# Edit backend/.env with your configuration
```

3. **Start with Docker Compose:**
```bash
docker-compose up -d
```

4. **Run database migrations:**
```bash
docker-compose exec backend flask db upgrade
```

5. **Create admin user:**
```bash
docker-compose exec backend python3 -c "
from app import create_app, db
from app.models.user import User
from app.models.organization import Organization
from flask_bcrypt import Bcrypt

app = create_app()
bcrypt = Bcrypt(app)

with app.app_context():
    org = Organization.query.first()
    if not org:
        org = Organization(name='Default Organization', plan='professional', max_pipelines=50, max_users=10)
        db.session.add(org)
        db.session.commit()
    
    admin = User.query.filter_by(email='admin@dataops.com').first()
    if not admin:
        admin = User(email='admin@dataops.com', first_name='Admin', last_name='User', role='admin', organization_id=org.id, is_active=True)
        admin.password_hash = bcrypt.generate_password_hash('admin123').decode('utf-8')
        db.session.add(admin)
        db.session.commit()
        print('Admin user created: admin@dataops.com / admin123')
"
```

## 🔧 Configuration

### Environment Variables

#### Backend Configuration (`backend/.env`)

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/dataops_monitoring

# Redis
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-change-in-production

# External Services
SLACK_WEBHOOK_URL=your-slack-webhook-url
SENDGRID_API_KEY=your-sendgrid-api-key
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=your-twilio-phone-number

# Email Configuration
SMTP_HOST=your-smtp-host
SMTP_PORT=587
SMTP_USER=your-email
SMTP_PASS=your-password

# Monitoring Settings
DEFAULT_CHECK_INTERVAL=300
MAX_RETRY_ATTEMPTS=3
ALERT_COOLDOWN=3600
DATA_RETENTION_DAYS=90
```

#### Frontend Configuration (`frontend/.env`)

```bash
REACT_APP_API_URL=http://localhost:5000
REACT_APP_ENVIRONMENT=production
```

### Database Setup

1. **Create PostgreSQL database:**
```bash
createdb dataops_monitoring
```

2. **Run migrations:**
```bash
cd backend
source venv/bin/activate
flask db upgrade
```

### Redis Setup

1. **Install Redis:**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# Start Redis
redis-server
```

## 🌐 Production Deployment

### Option 1: Cloud Deployment (AWS/GCP/Azure)

#### AWS Deployment with ECS

1. **Create ECR repositories:**
```bash
aws ecr create-repository --repository-name dataops-backend
aws ecr create-repository --repository-name dataops-frontend
```

2. **Build and push images:**
```bash
# Backend
docker build -t dataops-backend ./backend
docker tag dataops-backend:latest <account-id>.dkr.ecr.<region>.amazonaws.com/dataops-backend:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/dataops-backend:latest

# Frontend
docker build -t dataops-frontend ./frontend
docker tag dataops-frontend:latest <account-id>.dkr.ecr.<region>.amazonaws.com/dataops-frontend:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/dataops-frontend:latest
```

3. **Deploy with ECS:**
```bash
# Create ECS cluster
aws ecs create-cluster --cluster-name dataops-cluster

# Create task definitions and services
# (Use AWS Console or CloudFormation for full setup)
```

#### GCP Deployment with GKE

1. **Create GKE cluster:**
```bash
gcloud container clusters create dataops-cluster \
    --zone=us-central1-a \
    --num-nodes=3 \
    --machine-type=e2-medium
```

2. **Deploy with kubectl:**
```bash
kubectl apply -f k8s/
```

### Option 2: Self-Hosted Server

1. **Server requirements:**
- Ubuntu 20.04+ or CentOS 8+
- 4GB RAM minimum (8GB recommended)
- 50GB storage
- Domain name (optional but recommended)

2. **Install dependencies:**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Nginx
sudo apt install nginx -y
```

3. **Deploy application:**
```bash
# Clone repository
git clone <repository-url>
cd DataOps-Monitoring

# Configure environment
cp backend/env.example backend/.env
# Edit backend/.env

# Start services
docker-compose up -d

# Setup Nginx reverse proxy
sudo cp nginx.conf /etc/nginx/nginx.conf
sudo systemctl restart nginx
```

4. **Setup SSL with Let's Encrypt:**
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 📊 Monitoring & Logging

### Application Monitoring

1. **Health Checks:**
```bash
# Backend health
curl http://localhost:5000/health

# Frontend health
curl http://localhost:3000
```

2. **Log Monitoring:**
```bash
# View logs
./setup.sh logs backend
./setup.sh logs celery
./setup.sh logs frontend

# Or with Docker
docker-compose logs -f backend
docker-compose logs -f celery
docker-compose logs -f frontend
```

3. **Database Monitoring:**
```bash
# Connect to database
psql -h localhost -U dataops -d dataops_monitoring

# Check table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Performance Monitoring

1. **Backend Performance:**
- Monitor response times
- Check Celery queue length
- Monitor database connections

2. **Frontend Performance:**
- Monitor bundle size
- Check loading times
- Monitor API calls

3. **Infrastructure Monitoring:**
- CPU and memory usage
- Disk space
- Network traffic

## 🔒 Security

### Security Best Practices

1. **Environment Variables:**
- Never commit secrets to version control
- Use strong, unique passwords
- Rotate secrets regularly

2. **Network Security:**
- Use HTTPS in production
- Configure firewall rules
- Use VPN for admin access

3. **Application Security:**
- Keep dependencies updated
- Use security headers
- Implement rate limiting
- Regular security audits

4. **Database Security:**
- Use strong passwords
- Limit database access
- Regular backups
- Encrypt sensitive data

### SSL/TLS Configuration

1. **Generate SSL certificates:**
```bash
# Self-signed (development)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ssl/private.key -out ssl/certificate.crt

# Let's Encrypt (production)
sudo certbot --nginx -d your-domain.com
```

2. **Configure Nginx SSL:**
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    # ... rest of configuration
}
```

## 🔄 Backup & Recovery

### Database Backup

1. **Automated backups:**
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"
DB_NAME="dataops_monitoring"

pg_dump -h localhost -U dataops $DB_NAME > $BACKUP_DIR/backup_$DATE.sql

# Keep only last 7 days
find $BACKUP_DIR -name "backup_*.sql" -mtime +7 -delete
```

2. **Setup cron job:**
```bash
# Add to crontab
0 2 * * * /path/to/backup.sh
```

### Application Backup

1. **Configuration backup:**
```bash
# Backup configuration files
tar -czf config_backup_$(date +%Y%m%d).tar.gz \
    backend/.env \
    frontend/.env \
    nginx.conf \
    docker-compose.yml
```

2. **Docker volumes backup:**
```bash
# Backup PostgreSQL data
docker run --rm -v dataops_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup_$(date +%Y%m%d).tar.gz -C /data .

# Backup Redis data
docker run --rm -v dataops_redis_data:/data -v $(pwd):/backup alpine tar czf /backup/redis_backup_$(date +%Y%m%d).tar.gz -C /data .
```

## 🚀 Scaling

### Horizontal Scaling

1. **Load Balancer Setup:**
```nginx
upstream backend {
    server backend1:5000;
    server backend2:5000;
    server backend3:5000;
}
```

2. **Database Scaling:**
- Use read replicas for read-heavy workloads
- Implement connection pooling
- Consider database sharding for large datasets

3. **Celery Scaling:**
```bash
# Start multiple Celery workers
celery -A app.celery worker --loglevel=info --concurrency=4 -n worker1@%h
celery -A app.celery worker --loglevel=info --concurrency=4 -n worker2@%h
```

### Vertical Scaling

1. **Resource Allocation:**
- Increase CPU and memory for containers
- Optimize database configuration
- Use SSD storage for better I/O performance

2. **Performance Tuning:**
- Optimize database queries
- Implement caching strategies
- Use CDN for static assets

## 🛠️ Troubleshooting

### Common Issues

1. **Database Connection Issues:**
```bash
# Check database status
sudo systemctl status postgresql

# Test connection
psql -h localhost -U dataops -d dataops_monitoring -c "SELECT 1;"
```

2. **Redis Connection Issues:**
```bash
# Check Redis status
redis-cli ping

# Check Redis logs
sudo journalctl -u redis
```

3. **Application Issues:**
```bash
# Check application logs
./setup.sh logs backend

# Check service status
./setup.sh status

# Restart services
./setup.sh restart
```

### Performance Issues

1. **Slow Database Queries:**
```sql
-- Enable query logging
ALTER SYSTEM SET log_statement = 'all';
SELECT pg_reload_conf();

-- Analyze slow queries
SELECT query, mean_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

2. **High Memory Usage:**
```bash
# Check memory usage
free -h
docker stats

# Optimize Celery workers
celery -A app.celery worker --loglevel=info --concurrency=2
```

## 📞 Support

For additional support:

- **Documentation:** [docs.dataops-monitoring.com](https://docs.dataops-monitoring.com)
- **Email:** support@dataops-monitoring.com
- **Slack:** [Join our community](https://slack.dataops-monitoring.com)
- **GitHub Issues:** [Report bugs](https://github.com/your-org/dataops-monitoring/issues)

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 