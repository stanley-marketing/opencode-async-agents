# 🚀 Production Deployment Guide

**Complete guide for deploying OpenCode-Slack in production environments**

## 🎯 Overview

This guide covers production deployment of OpenCode-Slack, including infrastructure setup, security hardening, monitoring, and scaling considerations. The system is production-ready for core operations with 95% validation coverage.

## 📋 Prerequisites

### System Requirements

**Minimum Requirements:**
- CPU: 2 cores, 2.4 GHz
- RAM: 4 GB
- Storage: 20 GB SSD
- Network: 100 Mbps
- OS: Ubuntu 20.04+ / CentOS 8+ / Docker

**Recommended Production:**
- CPU: 4+ cores, 3.0 GHz
- RAM: 8+ GB
- Storage: 50+ GB SSD
- Network: 1 Gbps
- Load balancer for high availability

**Software Dependencies:**
- Python 3.8+
- Node.js 16+ (for WebSocket interface)
- SQLite 3.35+ (or PostgreSQL for enterprise)
- Nginx (recommended reverse proxy)
- Docker & Docker Compose (optional)

## 🏗️ Deployment Architectures

### 1. Single Server Deployment (Small Teams)

**Architecture:**
```
Internet → Nginx → OpenCode-Slack Server
                 ├── WebSocket (8765)
                 ├── HTTP API (8080)
                 └── React Frontend (3000)
```

**Capacity:**
- 10-50 concurrent users
- 20+ AI employees
- 100+ file operations/hour
- 1000+ messages/hour

### 2. Load Balanced Deployment (Medium Teams)

**Architecture:**
```
Internet → Load Balancer → Multiple OpenCode-Slack Instances
                        ├── Shared Database
                        ├── Shared File Storage
                        └── Session Affinity (WebSocket)
```

**Capacity:**
- 50-200 concurrent users
- 100+ AI employees
- 1000+ file operations/hour
- 10,000+ messages/hour

### 3. Enterprise Deployment (Large Organizations)

**Architecture:**
```
Internet → CDN → Load Balancer → App Servers
                               ├── Database Cluster
                               ├── Redis Cache
                               ├── Message Queue
                               └── Monitoring Stack
```

**Capacity:**
- 200+ concurrent users
- 500+ AI employees
- 10,000+ file operations/hour
- 100,000+ messages/hour

## 🐳 Docker Deployment (Recommended)

### Quick Start with Docker Compose

**1. Create docker-compose.yml:**
```yaml
version: '3.8'

services:
  opencode-slack:
    build: .
    ports:
      - "8080:8080"
      - "8765:8765"
    environment:
      - OPENCODE_TRANSPORT=websocket
      - DATABASE_PATH=/data/employees.db
      - WEBSOCKET_HOST=0.0.0.0
      - WEBSOCKET_PORT=8765
    volumes:
      - ./data:/data
      - ./sessions:/app/sessions
      - ./config:/app/config
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_WEBSOCKET_URL=ws://localhost:8765
      - NEXT_PUBLIC_API_URL=http://localhost:8080
    depends_on:
      - opencode-slack
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - opencode-slack
      - frontend
    restart: unless-stopped

volumes:
  data:
  sessions:
```

**2. Create Dockerfile:**
```dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /data /app/sessions /app/config

# Set permissions
RUN chmod +x scripts/*.sh

# Expose ports
EXPOSE 8080 8765

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Start server
CMD ["python", "src/server_websocket.py", "--host", "0.0.0.0", "--port", "8080", "--websocket-port", "8765"]
```

**3. Deploy:**
```bash
# Clone repository
git clone https://github.com/your-repo/opencode-slack
cd opencode-slack

# Create environment file
cp .env.example .env
# Edit .env with your configuration

# Build and start services
docker-compose up -d

# Verify deployment
curl http://localhost:8080/health
```

### Production Docker Configuration

**docker-compose.prod.yml:**
```yaml
version: '3.8'

services:
  opencode-slack:
    image: opencode-slack:latest
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
    environment:
      - OPENCODE_TRANSPORT=websocket
      - DATABASE_PATH=/data/employees.db
      - REDIS_URL=redis://redis:6379
      - LOG_LEVEL=INFO
    volumes:
      - data:/data
      - sessions:/app/sessions
    networks:
      - opencode-network
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    networks:
      - opencode-network
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.prod.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    networks:
      - opencode-network
    restart: unless-stopped

volumes:
  data:
  sessions:
  redis_data:

networks:
  opencode-network:
    driver: bridge
```

## 🖥️ Native Deployment

### Ubuntu/Debian Installation

**1. System Setup:**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-venv nodejs npm nginx sqlite3 curl

# Create application user
sudo useradd -m -s /bin/bash opencode
sudo usermod -aG sudo opencode
```

**2. Application Setup:**
```bash
# Switch to application user
sudo su - opencode

# Clone repository
git clone https://github.com/your-repo/opencode-slack
cd opencode-slack

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies (for frontend)
cd frontend
npm install
npm run build
cd ..

# Create directories
mkdir -p data sessions logs config
```

**3. Configuration:**
```bash
# Create environment file
cp .env.example .env

# Edit configuration
nano .env
```

**Environment Configuration (.env):**
```bash
# Core Configuration
OPENCODE_TRANSPORT=websocket
DATABASE_PATH=/home/opencode/opencode-slack/data/employees.db
SESSIONS_DIR=/home/opencode/opencode-slack/sessions
PROJECT_ROOT=/home/opencode/projects

# Server Configuration
WEBSOCKET_HOST=0.0.0.0
WEBSOCKET_PORT=8765
HTTP_PORT=8080

# Performance
MAX_CONCURRENT_SESSIONS=20
STUCK_TIMEOUT_MINUTES=10
MAX_MESSAGES_PER_HOUR=100

# Security
OPENCODE_SAFE_MODE=false
ENABLE_RATE_LIMITING=true

# Logging
LOG_LEVEL=INFO
LOG_FILE=/home/opencode/opencode-slack/logs/opencode.log
```

**4. Systemd Service Setup:**
```bash
# Create systemd service file
sudo nano /etc/systemd/system/opencode-slack.service
```

**Service Configuration:**
```ini
[Unit]
Description=OpenCode-Slack AI Employee Management System
After=network.target

[Service]
Type=simple
User=opencode
Group=opencode
WorkingDirectory=/home/opencode/opencode-slack
Environment=PATH=/home/opencode/opencode-slack/venv/bin
ExecStart=/home/opencode/opencode-slack/venv/bin/python src/server_websocket.py --host 0.0.0.0 --port 8080 --websocket-port 8765
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/opencode/opencode-slack/data /home/opencode/opencode-slack/sessions /home/opencode/opencode-slack/logs

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
```

**5. Start Services:**
```bash
# Enable and start service
sudo systemctl enable opencode-slack
sudo systemctl start opencode-slack

# Check status
sudo systemctl status opencode-slack

# View logs
sudo journalctl -u opencode-slack -f
```

### Nginx Configuration

**Create nginx configuration:**
```bash
sudo nano /etc/nginx/sites-available/opencode-slack
```

**Nginx Configuration:**
```nginx
upstream opencode_backend {
    server 127.0.0.1:8080;
    # Add more servers for load balancing
    # server 127.0.0.1:8081;
    # server 127.0.0.1:8082;
}

upstream opencode_websocket {
    server 127.0.0.1:8765;
    # Add more servers for load balancing
    # server 127.0.0.1:8766;
    # server 127.0.0.1:8767;
}

server {
    listen 80;
    server_name your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Frontend (React app)
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # API endpoints
    location /api/ {
        proxy_pass http://opencode_backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # WebSocket endpoint
    location /ws {
        proxy_pass http://opencode_websocket;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket specific settings
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
        proxy_connect_timeout 60s;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://opencode_backend/health;
        access_log off;
    }
    
    # Static files caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

**Enable site:**
```bash
sudo ln -s /etc/nginx/sites-available/opencode-slack /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 🔐 Security Hardening

### SSL/TLS Configuration

**1. Generate SSL Certificate:**
```bash
# Using Let's Encrypt (recommended)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com

# Or generate self-signed certificate for testing
sudo mkdir -p /etc/nginx/ssl
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/key.pem \
  -out /etc/nginx/ssl/cert.pem
```

**2. SSL Security Configuration:**
```nginx
# Strong SSL configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
ssl_stapling on;
ssl_stapling_verify on;

# HSTS
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

### Firewall Configuration

**UFW Setup (Ubuntu):**
```bash
# Enable firewall
sudo ufw enable

# Allow SSH
sudo ufw allow ssh

# Allow HTTP/HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Allow specific application ports (if needed)
sudo ufw allow 8080  # API
sudo ufw allow 8765  # WebSocket

# Check status
sudo ufw status
```

**iptables Setup (Advanced):**
```bash
# Basic iptables rules
sudo iptables -A INPUT -i lo -j ACCEPT
sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -A INPUT -j DROP

# Save rules
sudo iptables-save > /etc/iptables/rules.v4
```

### Application Security

**1. Environment Security:**
```bash
# Secure file permissions
chmod 600 .env
chmod 700 data/ sessions/ logs/
chown -R opencode:opencode /home/opencode/opencode-slack
```

**2. Database Security:**
```bash
# SQLite security
chmod 600 data/employees.db
# For PostgreSQL, use proper user authentication and SSL
```

**3. Rate Limiting Configuration:**
```python
# In .env file
ENABLE_RATE_LIMITING=true
MAX_REQUESTS_PER_HOUR=100
MAX_WEBSOCKET_CONNECTIONS=50
MAX_MESSAGES_PER_MINUTE=60
```

## 📊 Monitoring & Logging

### Application Monitoring

**1. Health Check Monitoring:**
```bash
# Create health check script
cat > /home/opencode/health_check.sh << 'EOF'
#!/bin/bash
HEALTH_URL="http://localhost:8080/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ $RESPONSE -eq 200 ]; then
    echo "OpenCode-Slack is healthy"
    exit 0
else
    echo "OpenCode-Slack health check failed (HTTP $RESPONSE)"
    exit 1
fi
EOF

chmod +x /home/opencode/health_check.sh
```

**2. Cron Job for Health Monitoring:**
```bash
# Add to crontab
crontab -e

# Add this line to check every 5 minutes
*/5 * * * * /home/opencode/health_check.sh >> /home/opencode/health.log 2>&1
```

### Log Management

**1. Logrotate Configuration:**
```bash
sudo nano /etc/logrotate.d/opencode-slack
```

**Logrotate Config:**
```
/home/opencode/opencode-slack/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 opencode opencode
    postrotate
        systemctl reload opencode-slack
    endscript
}
```

**2. Centralized Logging (Optional):**
```yaml
# Add to docker-compose.yml for ELK stack
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:7.15.0
    environment:
      - discovery.type=single-node
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data

  logstash:
    image: docker.elastic.co/logstash/logstash:7.15.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf

  kibana:
    image: docker.elastic.co/kibana/kibana:7.15.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
```

### Performance Monitoring

**1. System Metrics:**
```bash
# Install monitoring tools
sudo apt install htop iotop nethogs

# Monitor system resources
htop                    # CPU and memory
iotop                   # Disk I/O
nethogs                 # Network usage
```

**2. Application Metrics:**
```python
# Add to application for custom metrics
import psutil
import time

def get_system_metrics():
    return {
        'cpu_percent': psutil.cpu_percent(),
        'memory_percent': psutil.virtual_memory().percent,
        'disk_usage': psutil.disk_usage('/').percent,
        'network_io': psutil.net_io_counters()._asdict()
    }
```

## 🔄 Backup & Recovery

### Database Backup

**1. SQLite Backup Script:**
```bash
cat > /home/opencode/backup_db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/opencode/backups"
DB_PATH="/home/opencode/opencode-slack/data/employees.db"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Create backup
sqlite3 $DB_PATH ".backup $BACKUP_DIR/employees_$DATE.db"

# Compress backup
gzip $BACKUP_DIR/employees_$DATE.db

# Keep only last 30 days of backups
find $BACKUP_DIR -name "employees_*.db.gz" -mtime +30 -delete

echo "Database backup completed: employees_$DATE.db.gz"
EOF

chmod +x /home/opencode/backup_db.sh
```

**2. Automated Backup Cron:**
```bash
# Add to crontab for daily backups
0 2 * * * /home/opencode/backup_db.sh >> /home/opencode/backup.log 2>&1
```

### Session Data Backup

**1. Session Backup Script:**
```bash
cat > /home/opencode/backup_sessions.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/opencode/backups"
SESSIONS_DIR="/home/opencode/opencode-slack/sessions"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Create compressed archive of sessions
tar -czf $BACKUP_DIR/sessions_$DATE.tar.gz -C $SESSIONS_DIR .

# Keep only last 7 days of session backups
find $BACKUP_DIR -name "sessions_*.tar.gz" -mtime +7 -delete

echo "Sessions backup completed: sessions_$DATE.tar.gz"
EOF

chmod +x /home/opencode/backup_sessions.sh
```

### Recovery Procedures

**1. Database Recovery:**
```bash
# Stop service
sudo systemctl stop opencode-slack

# Restore database
gunzip -c /home/opencode/backups/employees_YYYYMMDD_HHMMSS.db.gz > /home/opencode/opencode-slack/data/employees.db

# Set permissions
chown opencode:opencode /home/opencode/opencode-slack/data/employees.db
chmod 600 /home/opencode/opencode-slack/data/employees.db

# Start service
sudo systemctl start opencode-slack
```

**2. Full System Recovery:**
```bash
# Restore from backup
tar -xzf system_backup.tar.gz -C /home/opencode/

# Restore database
gunzip -c database_backup.db.gz > /home/opencode/opencode-slack/data/employees.db

# Restore sessions
tar -xzf sessions_backup.tar.gz -C /home/opencode/opencode-slack/sessions/

# Set permissions
chown -R opencode:opencode /home/opencode/opencode-slack
chmod 600 /home/opencode/opencode-slack/.env
chmod 600 /home/opencode/opencode-slack/data/employees.db

# Restart services
sudo systemctl restart opencode-slack
sudo systemctl restart nginx
```

## 📈 Scaling & Performance

### Horizontal Scaling

**1. Load Balancer Setup (HAProxy):**
```
# /etc/haproxy/haproxy.cfg
global
    daemon
    maxconn 4096

defaults
    mode http
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms

frontend opencode_frontend
    bind *:80
    bind *:443 ssl crt /etc/ssl/certs/opencode.pem
    redirect scheme https if !{ ssl_fc }
    default_backend opencode_backend

backend opencode_backend
    balance roundrobin
    option httpchk GET /health
    server app1 10.0.1.10:8080 check
    server app2 10.0.1.11:8080 check
    server app3 10.0.1.12:8080 check

frontend websocket_frontend
    bind *:8765
    default_backend websocket_backend

backend websocket_backend
    balance source  # Session affinity for WebSocket
    option httpchk GET /health
    server ws1 10.0.1.10:8765 check
    server ws2 10.0.1.11:8765 check
    server ws3 10.0.1.12:8765 check
```

**2. Shared Storage Setup:**
```bash
# NFS setup for shared sessions
sudo apt install nfs-common

# Mount shared storage
sudo mount -t nfs 10.0.1.100:/shared/sessions /home/opencode/opencode-slack/sessions
sudo mount -t nfs 10.0.1.100:/shared/data /home/opencode/opencode-slack/data

# Add to /etc/fstab for persistence
echo "10.0.1.100:/shared/sessions /home/opencode/opencode-slack/sessions nfs defaults 0 0" >> /etc/fstab
echo "10.0.1.100:/shared/data /home/opencode/opencode-slack/data nfs defaults 0 0" >> /etc/fstab
```

### Database Scaling

**1. PostgreSQL Migration:**
```python
# Update configuration for PostgreSQL
DATABASE_URL=postgresql://opencode:password@localhost:5432/opencode_db

# Migration script
import sqlite3
import psycopg2

def migrate_to_postgresql():
    # Connect to SQLite
    sqlite_conn = sqlite3.connect('data/employees.db')
    
    # Connect to PostgreSQL
    pg_conn = psycopg2.connect(DATABASE_URL)
    
    # Migrate data
    # ... migration logic
```

**2. Redis Caching:**
```python
# Add Redis for caching
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Cache employee status
def get_employee_status(name):
    cached = redis_client.get(f"employee:{name}:status")
    if cached:
        return json.loads(cached)
    
    # Fetch from database and cache
    status = fetch_from_db(name)
    redis_client.setex(f"employee:{name}:status", 300, json.dumps(status))
    return status
```

### Performance Optimization

**1. Application Tuning:**
```python
# Optimize database connections
import sqlite3
from contextlib import contextmanager

@contextmanager
def get_db_connection():
    conn = sqlite3.connect('data/employees.db', timeout=30.0)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA cache_size=10000')
    try:
        yield conn
    finally:
        conn.close()
```

**2. WebSocket Optimization:**
```python
# Connection pooling and message batching
class OptimizedWebSocketManager:
    def __init__(self):
        self.message_queue = asyncio.Queue(maxsize=1000)
        self.batch_size = 10
        self.batch_timeout = 0.1
    
    async def batch_message_processor(self):
        while True:
            messages = []
            try:
                # Collect messages for batching
                for _ in range(self.batch_size):
                    message = await asyncio.wait_for(
                        self.message_queue.get(), 
                        timeout=self.batch_timeout
                    )
                    messages.append(message)
            except asyncio.TimeoutError:
                pass
            
            if messages:
                await self.process_message_batch(messages)
```

## 🚨 Troubleshooting

### Common Issues

**1. Service Won't Start:**
```bash
# Check service status
sudo systemctl status opencode-slack

# Check logs
sudo journalctl -u opencode-slack -f

# Common fixes
sudo systemctl daemon-reload
sudo systemctl restart opencode-slack
```

**2. Database Lock Issues:**
```bash
# Check for database locks
lsof /home/opencode/opencode-slack/data/employees.db

# Kill processes if needed
sudo pkill -f opencode

# Restart service
sudo systemctl restart opencode-slack
```

**3. WebSocket Connection Issues:**
```bash
# Test WebSocket connectivity
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Sec-WebSocket-Key: test" -H "Sec-WebSocket-Version: 13" http://localhost:8765/

# Check nginx WebSocket configuration
sudo nginx -t
sudo systemctl reload nginx
```

**4. High Memory Usage:**
```bash
# Monitor memory usage
ps aux | grep python
free -h

# Restart service to clear memory
sudo systemctl restart opencode-slack
```

### Performance Issues

**1. Slow Response Times:**
```bash
# Check system resources
htop
iotop

# Check database performance
sqlite3 data/employees.db ".timer on" "SELECT COUNT(*) FROM employees;"

# Optimize database
sqlite3 data/employees.db "VACUUM; ANALYZE;"
```

**2. WebSocket Disconnections:**
```bash
# Check connection limits
ulimit -n

# Increase limits if needed
echo "opencode soft nofile 65536" >> /etc/security/limits.conf
echo "opencode hard nofile 65536" >> /etc/security/limits.conf
```

### Recovery Procedures

**1. Emergency Restart:**
```bash
#!/bin/bash
# emergency_restart.sh

echo "Stopping OpenCode-Slack..."
sudo systemctl stop opencode-slack

echo "Backing up current state..."
cp data/employees.db data/employees.db.emergency.$(date +%s)

echo "Cleaning up sessions..."
find sessions/ -name "*.json" -mtime +1 -delete

echo "Starting OpenCode-Slack..."
sudo systemctl start opencode-slack

echo "Checking health..."
sleep 10
curl -f http://localhost:8080/health || echo "Health check failed!"
```

**2. Data Corruption Recovery:**
```bash
# Check database integrity
sqlite3 data/employees.db "PRAGMA integrity_check;"

# Repair if needed
sqlite3 data/employees.db ".recover" | sqlite3 data/employees_recovered.db

# Replace corrupted database
mv data/employees.db data/employees.db.corrupted
mv data/employees_recovered.db data/employees.db
```

## 📋 Maintenance

### Regular Maintenance Tasks

**1. Daily Tasks:**
- Monitor system health and logs
- Check disk space and cleanup old files
- Verify backup completion
- Monitor performance metrics

**2. Weekly Tasks:**
- Update system packages
- Review security logs
- Optimize database (VACUUM, ANALYZE)
- Test backup restoration

**3. Monthly Tasks:**
- Security audit and updates
- Performance analysis and optimization
- Capacity planning review
- Documentation updates

### Maintenance Scripts

**1. Cleanup Script:**
```bash
cat > /home/opencode/maintenance.sh << 'EOF'
#!/bin/bash

echo "Starting maintenance tasks..."

# Clean old sessions
find /home/opencode/opencode-slack/sessions -name "*.json" -mtime +7 -delete

# Clean old logs
find /home/opencode/opencode-slack/logs -name "*.log.*" -mtime +30 -delete

# Optimize database
sqlite3 /home/opencode/opencode-slack/data/employees.db "VACUUM; ANALYZE;"

# Check disk space
df -h /home/opencode

echo "Maintenance completed."
EOF

chmod +x /home/opencode/maintenance.sh
```

**2. Weekly Maintenance Cron:**
```bash
# Add to crontab
0 3 * * 0 /home/opencode/maintenance.sh >> /home/opencode/maintenance.log 2>&1
```

---

This deployment guide provides comprehensive instructions for production deployment of OpenCode-Slack. Follow the security hardening and monitoring sections carefully to ensure a robust, secure, and maintainable production environment.

*Last updated: August 2025*