# OpenCode-Slack Operations Guide

This guide covers deployment, monitoring, maintenance, and troubleshooting for production OpenCode-Slack installations.

## 🚀 Production Deployment

### System Requirements

#### Minimum Requirements
- **CPU**: 2 cores
- **RAM**: 4GB
- **Storage**: 10GB SSD
- **Network**: Stable internet connection
- **OS**: Ubuntu 20.04+ / CentOS 8+ / RHEL 8+

#### Recommended Requirements
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Storage**: 20GB+ SSD
- **Network**: High-speed internet
- **Load Balancer**: For high availability

### Docker Deployment

#### Using Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  opencode-slack:
    build: .
    ports:
      - "8080:8080"
    environment:
      - SERVER_HOST=0.0.0.0
      - SERVER_PORT=8080
      - DATABASE_PATH=/data/employees.db
      - SESSIONS_DIR=/data/sessions
    volumes:
      - ./data:/data
      - ./config:/app/config
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

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
    restart: unless-stopped
```

#### Deployment Commands

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Scale services
docker-compose up -d --scale opencode-slack=3

# Update deployment
docker-compose pull
docker-compose up -d
```

### Kubernetes Deployment

#### Deployment Manifest

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: opencode-slack
spec:
  replicas: 3
  selector:
    matchLabels:
      app: opencode-slack
  template:
    metadata:
      labels:
        app: opencode-slack
    spec:
      containers:
      - name: opencode-slack
        image: opencode-slack:latest
        ports:
        - containerPort: 8080
        env:
        - name: SERVER_HOST
          value: "0.0.0.0"
        - name: DATABASE_PATH
          value: "/data/employees.db"
        volumeMounts:
        - name: data-volume
          mountPath: /data
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: data-volume
        persistentVolumeClaim:
          claimName: opencode-slack-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: opencode-slack-service
spec:
  selector:
    app: opencode-slack
  ports:
  - port: 80
    targetPort: 8080
  type: LoadBalancer
```

## 📊 Monitoring & Observability

### Health Checks

#### Built-in Health Endpoint

```bash
# Basic health check
curl http://localhost:8080/health

# Detailed system status
curl http://localhost:8080/status

# Response format
{
  "status": "healthy",
  "timestamp": "2025-08-09T12:00:00Z",
  "version": "1.0.0",
  "uptime": "2h 30m",
  "components": {
    "database": "healthy",
    "chat_system": "connected",
    "agent_bridge": "running",
    "file_system": "accessible"
  }
}
```

#### Custom Health Checks

```bash
#!/bin/bash
# health-check.sh

# Check server response
if ! curl -f -s http://localhost:8080/health > /dev/null; then
    echo "ERROR: Server not responding"
    exit 1
fi

# Check database
if ! sqlite3 employees.db "SELECT 1;" > /dev/null 2>&1; then
    echo "ERROR: Database not accessible"
    exit 1
fi

# Check sessions directory
if [ ! -d "sessions" ]; then
    echo "ERROR: Sessions directory missing"
    exit 1
fi

echo "All health checks passed"
```

### Prometheus Monitoring

#### Metrics Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'opencode-slack'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
    scrape_interval: 10s
```

#### Key Metrics to Monitor

- **System Metrics**
  - `opencode_active_employees_total`
  - `opencode_active_tasks_total`
  - `opencode_system_uptime_seconds`
  - `opencode_request_duration_seconds`

- **Performance Metrics**
  - `opencode_task_completion_time_seconds`
  - `opencode_file_lock_duration_seconds`
  - `opencode_chat_response_time_seconds`

- **Error Metrics**
  - `opencode_errors_total`
  - `opencode_failed_tasks_total`
  - `opencode_connection_failures_total`

### Logging

#### Log Configuration

```python
# logging_config.py
import logging
import logging.handlers

def setup_logging():
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # File handler for all logs
    file_handler = logging.handlers.RotatingFileHandler(
        'logs/opencode-slack.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(detailed_formatter)
    
    # Error file handler
    error_handler = logging.handlers.RotatingFileHandler(
        'logs/errors.log',
        maxBytes=10*1024*1024,
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
```

#### Log Analysis

```bash
# Monitor real-time logs
tail -f logs/opencode-slack.log

# Search for errors
grep "ERROR" logs/opencode-slack.log

# Analyze task completion times
grep "Task completed" logs/opencode-slack.log | awk '{print $NF}'

# Monitor employee activity
grep "Employee" logs/opencode-slack.log | tail -20
```

## 🔧 Maintenance

### Database Maintenance

#### Backup Procedures

```bash
#!/bin/bash
# backup-database.sh

BACKUP_DIR="/backups/opencode-slack"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_FILE="employees.db"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup database
sqlite3 "$DB_FILE" ".backup $BACKUP_DIR/employees_$TIMESTAMP.db"

# Compress backup
gzip "$BACKUP_DIR/employees_$TIMESTAMP.db"

# Clean old backups (keep 30 days)
find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete

echo "Database backup completed: employees_$TIMESTAMP.db.gz"
```

#### Database Optimization

```bash
# Vacuum database to reclaim space
sqlite3 employees.db "VACUUM;"

# Analyze database for query optimization
sqlite3 employees.db "ANALYZE;"

# Check database integrity
sqlite3 employees.db "PRAGMA integrity_check;"
```

### Session Cleanup

```bash
#!/bin/bash
# cleanup-sessions.sh

SESSIONS_DIR="sessions"
DAYS_TO_KEEP=7

# Remove old completed sessions
find "$SESSIONS_DIR" -name "*.completed" -mtime +$DAYS_TO_KEEP -delete

# Remove empty session directories
find "$SESSIONS_DIR" -type d -empty -delete

# Clean up temporary files
find "$SESSIONS_DIR" -name "*.tmp" -delete
find "$SESSIONS_DIR" -name "*.log" -mtime +$DAYS_TO_KEEP -delete

echo "Session cleanup completed"
```

### Log Rotation

```bash
# /etc/logrotate.d/opencode-slack
/path/to/opencode-slack/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 opencode opencode
    postrotate
        systemctl reload opencode-slack
    endscript
}
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Server Won't Start

**Symptoms**: Server fails to start or exits immediately

**Diagnosis**:
```bash
# Check port availability
netstat -tlnp | grep 8080

# Check permissions
ls -la employees.db sessions/

# Check logs
tail -50 logs/opencode-slack.log
```

**Solutions**:
```bash
# Kill process using port
sudo kill $(lsof -t -i:8080)

# Fix permissions
chmod 644 employees.db
chmod 755 sessions/

# Use different port
./scripts/run.sh server --port 8081
```

#### 2. Database Corruption

**Symptoms**: SQLite errors, data inconsistency

**Diagnosis**:
```bash
# Check database integrity
sqlite3 employees.db "PRAGMA integrity_check;"

# Check database schema
sqlite3 employees.db ".schema"
```

**Solutions**:
```bash
# Restore from backup
cp /backups/opencode-slack/employees_latest.db employees.db

# Rebuild database
rm employees.db
python3 -c "from src.managers.file_ownership import FileOwnershipManager; FileOwnershipManager()"
```

#### 3. Chat System Disconnected

**Symptoms**: Telegram bot not responding

**Diagnosis**:
```bash
# Check chat status
curl http://localhost:8080/chat/status

# Test bot token
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe"
```

**Solutions**:
```bash
# Restart chat system
curl -X POST http://localhost:8080/chat/restart

# Update bot token
export TELEGRAM_BOT_TOKEN=new_token
```

#### 4. High Memory Usage

**Symptoms**: System running out of memory

**Diagnosis**:
```bash
# Check memory usage
ps aux | grep python
free -h

# Check session count
ls sessions/ | wc -l
```

**Solutions**:
```bash
# Clean up sessions
./scripts/cleanup-sessions.sh

# Restart server
systemctl restart opencode-slack

# Increase memory limits
# Edit docker-compose.yml or k8s deployment
```

### Performance Optimization

#### Database Optimization

```sql
-- Add indexes for common queries
CREATE INDEX IF NOT EXISTS idx_employees_name ON employees(name);
CREATE INDEX IF NOT EXISTS idx_file_locks_employee ON file_locks(employee_name);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
```

#### Memory Optimization

```python
# config/performance.py
PERFORMANCE_CONFIG = {
    'max_concurrent_tasks': 10,
    'session_timeout': 3600,  # 1 hour
    'cleanup_interval': 300,  # 5 minutes
    'max_memory_per_session': '512MB',
    'enable_session_pooling': True
}
```

#### Network Optimization

```nginx
# nginx.conf optimization
upstream opencode_backend {
    server 127.0.0.1:8080;
    keepalive 32;
}

server {
    location / {
        proxy_pass http://opencode_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering on;
        proxy_cache_valid 200 1m;
    }
}
```

## 🔐 Security

### Security Hardening

#### Network Security

```bash
# Firewall configuration
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw deny 8080/tcp   # Block direct access to app
ufw enable
```

#### SSL/TLS Configuration

```nginx
# nginx SSL configuration
server {
    listen 443 ssl http2;
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Access Control

```bash
# Create dedicated user
useradd -r -s /bin/false opencode

# Set file ownership
chown -R opencode:opencode /opt/opencode-slack
chmod 750 /opt/opencode-slack

# Secure sensitive files
chmod 600 .env
chmod 600 employees.db
```

## 📋 Maintenance Checklist

### Daily Tasks
- [ ] Check system health endpoints
- [ ] Monitor error logs
- [ ] Verify chat system connectivity
- [ ] Check disk space usage

### Weekly Tasks
- [ ] Review performance metrics
- [ ] Clean up old sessions
- [ ] Backup database
- [ ] Update security patches

### Monthly Tasks
- [ ] Analyze usage patterns
- [ ] Optimize database
- [ ] Review and rotate logs
- [ ] Update documentation

### Quarterly Tasks
- [ ] Security audit
- [ ] Performance review
- [ ] Capacity planning
- [ ] Disaster recovery testing

---

*For additional support, consult the [development documentation](../development/AGENTS.md) or create an issue on GitHub.*