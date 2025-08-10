# 🔧 Troubleshooting Guide

**Comprehensive troubleshooting guide for OpenCode-Slack system issues**

## 🎯 Quick Diagnosis

### System Health Check
```bash
# Quick health check
curl http://localhost:8080/health

# Detailed status
curl http://localhost:8080/status

# Communication status
curl http://localhost:8080/communication/info
```

### Common Quick Fixes
```bash
# Restart the system
sudo systemctl restart opencode-slack

# Check logs
sudo journalctl -u opencode-slack -f

# Clean up sessions
python -c "from src.managers.file_ownership import FileOwnershipManager; FileOwnershipManager().cleanup_completed_sessions()"
```

## 🚨 Common Issues & Solutions

### 1. Service Won't Start

#### **Symptoms:**
- Service fails to start
- "Connection refused" errors
- No response from health endpoint

#### **Diagnosis:**
```bash
# Check service status
sudo systemctl status opencode-slack

# View detailed logs
sudo journalctl -u opencode-slack -n 50

# Check port availability
sudo netstat -tlnp | grep :8080
sudo netstat -tlnp | grep :8765
```

#### **Common Causes & Solutions:**

**Port Already in Use:**
```bash
# Find process using port
sudo lsof -i :8080
sudo lsof -i :8765

# Kill conflicting process
sudo kill -9 <PID>

# Or change port in configuration
export HTTP_PORT=8081
export WEBSOCKET_PORT=8766
```

**Permission Issues:**
```bash
# Fix file permissions
sudo chown -R opencode:opencode /home/opencode/opencode-slack
chmod 600 .env
chmod 700 data/ sessions/ logs/

# Fix database permissions
chmod 600 data/employees.db
```

**Missing Dependencies:**
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Check Python version
python3 --version  # Should be 3.8+

# Install missing system packages
sudo apt update
sudo apt install python3-dev sqlite3 curl
```

**Configuration Errors:**
```bash
# Validate configuration
python -c "
import os
from src.config.config_loader import load_config
try:
    config = load_config()
    print('Configuration valid')
except Exception as e:
    print(f'Configuration error: {e}')
"

# Check environment variables
env | grep OPENCODE
```

### 2. Database Issues

#### **Symptoms:**
- "Database is locked" errors
- Employee operations fail
- File lock operations fail

#### **Diagnosis:**
```bash
# Check database file
ls -la data/employees.db

# Check for locks
lsof data/employees.db

# Test database connectivity
sqlite3 data/employees.db "SELECT COUNT(*) FROM employees;"
```

#### **Solutions:**

**Database Locked:**
```bash
# Find processes using database
sudo lsof data/employees.db

# Kill processes if safe
sudo pkill -f opencode

# Wait for locks to clear
sleep 5

# Restart service
sudo systemctl restart opencode-slack
```

**Database Corruption:**
```bash
# Check integrity
sqlite3 data/employees.db "PRAGMA integrity_check;"

# Backup current database
cp data/employees.db data/employees.db.backup.$(date +%s)

# Repair database
sqlite3 data/employees.db ".recover" | sqlite3 data/employees_recovered.db

# Replace if recovery successful
mv data/employees.db data/employees.db.corrupted
mv data/employees_recovered.db data/employees.db

# Restart service
sudo systemctl restart opencode-slack
```

**Database Missing:**
```bash
# Recreate database
python -c "
from src.managers.file_ownership import FileOwnershipManager
manager = FileOwnershipManager()
print('Database recreated')
"
```

### 3. WebSocket Connection Issues

#### **Symptoms:**
- Frontend can't connect to WebSocket
- "WebSocket connection failed" errors
- Frequent disconnections

#### **Diagnosis:**
```bash
# Test WebSocket server
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Key: test" -H "Sec-WebSocket-Version: 13" \
  http://localhost:8765/

# Check WebSocket logs
grep -i websocket /var/log/opencode/opencode.log

# Test from browser console
# Open browser dev tools and run:
# new WebSocket('ws://localhost:8765')
```

#### **Solutions:**

**WebSocket Server Not Running:**
```bash
# Check if WebSocket port is open
sudo netstat -tlnp | grep :8765

# Start WebSocket server manually
python src/server_websocket.py --websocket-port 8765

# Check configuration
grep WEBSOCKET .env
```

**Firewall Blocking Connections:**
```bash
# Check firewall status
sudo ufw status

# Allow WebSocket port
sudo ufw allow 8765

# For iptables
sudo iptables -A INPUT -p tcp --dport 8765 -j ACCEPT
```

**Nginx Configuration Issues:**
```bash
# Test nginx configuration
sudo nginx -t

# Check WebSocket proxy configuration
grep -A 10 "location /ws" /etc/nginx/sites-enabled/opencode-slack

# Reload nginx
sudo systemctl reload nginx
```

**CORS Issues:**
```bash
# Check browser console for CORS errors
# Add to nginx configuration:
add_header Access-Control-Allow-Origin "*";
add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
add_header Access-Control-Allow-Headers "Origin, Content-Type, Accept";
```

### 4. Agent Communication Problems

#### **Symptoms:**
- Agents don't respond to mentions
- Messages not being processed
- Agent status shows as inactive

#### **Diagnosis:**
```bash
# Check agent status
curl http://localhost:8080/communication/info

# Test message handling
python -c "
from src.chat.message_parser import MessageParser
parser = MessageParser()
msg = parser.parse_message({
    'text': '@alice test message',
    'from': {'username': 'test'},
    'chat': {'id': '1'},
    'message_id': 1,
    'date': 1234567890
})
print(f'Parsed mentions: {msg.mentions}')
"

# Check agent manager
python -c "
from src.agents.agent_manager import AgentManager
from src.managers.file_ownership import FileOwnershipManager
manager = AgentManager(FileOwnershipManager(), None)
print(f'Active agents: {list(manager.agents.keys())}')
"
```

#### **Solutions:**

**No Agents Created:**
```bash
# Create agents manually
python -c "
from src.managers.file_ownership import FileOwnershipManager
from src.agents.agent_manager import AgentManager

file_manager = FileOwnershipManager()
agent_manager = AgentManager(file_manager, None)

# Hire employees first
file_manager.hire_employee('alice', 'FS-developer')
file_manager.hire_employee('bob', 'designer')

# Create agents
agent_manager.create_agent('alice', 'FS-developer', ['python', 'javascript'])
agent_manager.create_agent('bob', 'designer', ['css', 'html'])

print('Agents created successfully')
"
```

**Message Parsing Issues:**
```bash
# Test message parsing
python -c "
from src.chat.message_parser import MessageParser
parser = MessageParser()

# Test various message formats
test_messages = [
    '@alice hello',
    'alice: please help',
    'hey @alice can you help?'
]

for msg_text in test_messages:
    msg = parser.parse_message({
        'text': msg_text,
        'from': {'username': 'test'},
        'chat': {'id': '1'},
        'message_id': 1,
        'date': 1234567890
    })
    print(f'Text: {msg_text} -> Mentions: {msg.mentions}')
"
```

**Communication Manager Issues:**
```bash
# Check communication manager
python -c "
from src.communication.communication_manager import CommunicationManager
manager = CommunicationManager()
print(f'Transport type: {manager.transport_type}')
print(f'Manager status: {manager.is_connected()}')
"

# Reset communication manager
sudo systemctl restart opencode-slack
```

### 5. File Ownership & Locking Issues

#### **Symptoms:**
- "File already locked" errors
- Can't release files
- File requests not working

#### **Diagnosis:**
```bash
# Check file locks
curl http://localhost:8080/files

# Check specific employee's files
python -c "
from src.managers.file_ownership import FileOwnershipManager
manager = FileOwnershipManager()
locks = manager.get_locked_files()
for lock in locks:
    print(f'{lock.employee_name}: {lock.file_path}')
"

# Check file requests
curl http://localhost:8080/files/requests
```

#### **Solutions:**

**Stuck File Locks:**
```bash
# Force release all files for employee
python -c "
from src.managers.file_ownership import FileOwnershipManager
manager = FileOwnershipManager()
released = manager.release_files('alice')  # Replace with employee name
print(f'Released files: {released}')
"

# Clear all locks (emergency only)
python -c "
from src.managers.file_ownership import FileOwnershipManager
manager = FileOwnershipManager()
with manager.get_db_connection() as conn:
    conn.execute('DELETE FROM file_locks')
    conn.commit()
print('All file locks cleared')
"
```

**File Request Issues:**
```bash
# Check pending requests
python -c "
from src.managers.file_ownership import FileOwnershipManager
manager = FileOwnershipManager()
requests = manager.get_pending_requests()
for req in requests:
    print(f'Request {req.id}: {req.requester_name} wants {req.file_path}')
"

# Approve all pending requests (if safe)
python -c "
from src.managers.file_ownership import FileOwnershipManager
manager = FileOwnershipManager()
requests = manager.get_pending_requests()
for req in requests:
    manager.approve_file_request(req.id)
    print(f'Approved request {req.id}')
"
```

### 6. Task & Session Management Issues

#### **Symptoms:**
- Tasks not starting
- Sessions stuck in "running" state
- Progress not updating

#### **Diagnosis:**
```bash
# Check active sessions
curl http://localhost:8080/tasks

# Check session files
ls -la sessions/

# Check task progress files
find sessions/ -name "*.md" -exec head -5 {} \;
```

#### **Solutions:**

**Stuck Sessions:**
```bash
# Clean up completed sessions
python -c "
from src.trackers.task_progress import TaskProgressTracker
tracker = TaskProgressTracker('sessions')
tracker.cleanup_completed_tasks()
print('Completed sessions cleaned up')
"

# Force stop all sessions
python -c "
from src.utils.opencode_wrapper import OpencodeSessionManager
manager = OpencodeSessionManager('sessions')
active = manager.get_active_sessions()
for session in active:
    manager.stop_employee_task(session['employee'])
    print(f'Stopped session for {session[\"employee\"]}')
"
```

**Task Assignment Issues:**
```bash
# Check employee status
python -c "
from src.managers.file_ownership import FileOwnershipManager
manager = FileOwnershipManager()
employees = manager.get_all_employees()
for emp in employees:
    print(f'{emp.name}: {emp.role} - Status: {getattr(emp, \"status\", \"unknown\")}')
"

# Manually assign task
python -c "
from src.bridge.agent_bridge import AgentBridge
from src.managers.file_ownership import FileOwnershipManager

file_manager = FileOwnershipManager()
bridge = AgentBridge(file_manager, None, None)

# Assign task
bridge.assign_task_to_worker('alice', 'test task')
print('Task assigned')
"
```

### 7. Performance Issues

#### **Symptoms:**
- Slow response times
- High memory usage
- System becomes unresponsive

#### **Diagnosis:**
```bash
# Check system resources
htop
free -h
df -h

# Check process memory usage
ps aux | grep python | sort -k4 -nr

# Check database performance
time sqlite3 data/employees.db "SELECT COUNT(*) FROM employees;"

# Check WebSocket connections
ss -tuln | grep :8765
```

#### **Solutions:**

**High Memory Usage:**
```bash
# Restart service to clear memory
sudo systemctl restart opencode-slack

# Check for memory leaks
valgrind --tool=memcheck python src/server_websocket.py

# Optimize database
sqlite3 data/employees.db "VACUUM; ANALYZE;"
```

**Slow Database Operations:**
```bash
# Add database indexes
sqlite3 data/employees.db "
CREATE INDEX IF NOT EXISTS idx_file_locks_employee ON file_locks(employee_name);
CREATE INDEX IF NOT EXISTS idx_file_locks_file ON file_locks(file_path);
CREATE INDEX IF NOT EXISTS idx_file_requests_status ON file_requests(status);
"

# Optimize database settings
sqlite3 data/employees.db "
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=10000;
"
```

**Too Many WebSocket Connections:**
```bash
# Check connection limits
ulimit -n

# Increase limits
echo "opencode soft nofile 65536" >> /etc/security/limits.conf
echo "opencode hard nofile 65536" >> /etc/security/limits.conf

# Restart session to apply limits
```

### 8. Frontend Issues

#### **Symptoms:**
- React frontend won't load
- WebSocket connection fails in browser
- UI not updating

#### **Diagnosis:**
```bash
# Check frontend server
curl http://localhost:3000

# Check browser console for errors
# Open browser dev tools (F12) and check Console tab

# Check WebSocket connection in browser
# In browser console: new WebSocket('ws://localhost:8765')

# Check frontend build
cd frontend && npm run build
```

#### **Solutions:**

**Frontend Server Not Running:**
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Or build and start production
npm run build
npm start
```

**WebSocket Connection Issues:**
```bash
# Check WebSocket URL in frontend
grep -r "ws://" frontend/src/

# Update WebSocket URL if needed
# In frontend/.env.local:
echo "NEXT_PUBLIC_WEBSOCKET_URL=ws://localhost:8765" > frontend/.env.local

# Restart frontend
cd frontend && npm run dev
```

**CORS Issues:**
```bash
# Add CORS headers to nginx
# In /etc/nginx/sites-enabled/opencode-slack:
add_header Access-Control-Allow-Origin "*";
add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
add_header Access-Control-Allow-Headers "Origin, Content-Type, Accept";

sudo systemctl reload nginx
```

## 🔍 Diagnostic Tools

### System Diagnostics

**1. Health Check Script:**
```bash
cat > diagnostic_check.sh << 'EOF'
#!/bin/bash

echo "=== OpenCode-Slack System Diagnostics ==="
echo

echo "1. Service Status:"
systemctl is-active opencode-slack
echo

echo "2. Port Status:"
netstat -tlnp | grep -E ":(8080|8765)"
echo

echo "3. Health Endpoint:"
curl -s http://localhost:8080/health | python -m json.tool 2>/dev/null || echo "Health check failed"
echo

echo "4. Database Status:"
if [ -f "data/employees.db" ]; then
    echo "Database file exists"
    sqlite3 data/employees.db "SELECT COUNT(*) as employee_count FROM employees;" 2>/dev/null || echo "Database query failed"
else
    echo "Database file missing"
fi
echo

echo "5. WebSocket Test:"
timeout 5 curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Key: test" -H "Sec-WebSocket-Version: 13" \
  http://localhost:8765/ 2>/dev/null | head -1 || echo "WebSocket test failed"
echo

echo "6. Disk Space:"
df -h . | tail -1
echo

echo "7. Memory Usage:"
free -h | grep Mem
echo

echo "8. Recent Errors:"
journalctl -u opencode-slack --since "1 hour ago" | grep -i error | tail -5
EOF

chmod +x diagnostic_check.sh
./diagnostic_check.sh
```

**2. Performance Monitor:**
```bash
cat > performance_monitor.sh << 'EOF'
#!/bin/bash

echo "=== Performance Monitoring ==="
echo

echo "CPU Usage:"
top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1

echo "Memory Usage:"
free | grep Mem | awk '{printf "%.2f%%\n", $3/$2 * 100.0}'

echo "Disk I/O:"
iostat -x 1 1 | tail -n +4

echo "Network Connections:"
ss -tuln | grep -E ":(8080|8765)" | wc -l

echo "Database Size:"
du -h data/employees.db 2>/dev/null || echo "Database not found"

echo "Session Count:"
find sessions/ -name "*.json" 2>/dev/null | wc -l

echo "Log File Size:"
du -h logs/*.log 2>/dev/null | tail -5
EOF

chmod +x performance_monitor.sh
```

### Application Diagnostics

**1. Database Diagnostic:**
```python
# database_diagnostic.py
import sqlite3
import os
from datetime import datetime

def diagnose_database():
    db_path = "data/employees.db"
    
    if not os.path.exists(db_path):
        print("❌ Database file does not exist")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"✅ Database tables: {[t[0] for t in tables]}")
        
        # Check employee count
        cursor.execute("SELECT COUNT(*) FROM employees")
        emp_count = cursor.fetchone()[0]
        print(f"✅ Employee count: {emp_count}")
        
        # Check file locks
        cursor.execute("SELECT COUNT(*) FROM file_locks")
        lock_count = cursor.fetchone()[0]
        print(f"✅ Active file locks: {lock_count}")
        
        # Check file requests
        cursor.execute("SELECT COUNT(*) FROM file_requests WHERE status='pending'")
        req_count = cursor.fetchone()[0]
        print(f"✅ Pending file requests: {req_count}")
        
        # Check integrity
        cursor.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()[0]
        print(f"✅ Database integrity: {integrity}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    diagnose_database()
```

**2. Communication Diagnostic:**
```python
# communication_diagnostic.py
import asyncio
import websockets
import json
import requests
from datetime import datetime

async def test_websocket():
    try:
        uri = "ws://localhost:8765"
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connection successful")
            
            # Send test message
            test_message = {
                "type": "message",
                "user_id": "diagnostic",
                "text": "test message",
                "timestamp": int(datetime.now().timestamp())
            }
            
            await websocket.send(json.dumps(test_message))
            print("✅ Message sent successfully")
            
            # Wait for response (with timeout)
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"✅ Received response: {response[:100]}...")
            except asyncio.TimeoutError:
                print("⚠️ No response received (timeout)")
                
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")

def test_http_api():
    try:
        # Test health endpoint
        response = requests.get("http://localhost:8080/health", timeout=5)
        if response.status_code == 200:
            print("✅ HTTP API health check passed")
        else:
            print(f"❌ HTTP API health check failed: {response.status_code}")
        
        # Test status endpoint
        response = requests.get("http://localhost:8080/status", timeout=5)
        if response.status_code == 200:
            print("✅ Status endpoint accessible")
        else:
            print(f"❌ Status endpoint failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ HTTP API test failed: {e}")

if __name__ == "__main__":
    print("=== Communication Diagnostics ===")
    test_http_api()
    asyncio.run(test_websocket())
```

## 🚨 Emergency Procedures

### Emergency Restart

**1. Safe Restart Procedure:**
```bash
#!/bin/bash
# emergency_restart.sh

echo "🚨 Emergency restart procedure initiated"

# 1. Backup current state
echo "📦 Creating emergency backup..."
timestamp=$(date +%Y%m%d_%H%M%S)
mkdir -p emergency_backups/$timestamp

cp data/employees.db emergency_backups/$timestamp/ 2>/dev/null
cp -r sessions emergency_backups/$timestamp/ 2>/dev/null
cp .env emergency_backups/$timestamp/ 2>/dev/null

# 2. Stop service gracefully
echo "🛑 Stopping service..."
sudo systemctl stop opencode-slack
sleep 5

# 3. Kill any remaining processes
echo "🔪 Cleaning up processes..."
sudo pkill -f "python.*opencode" 2>/dev/null
sleep 2

# 4. Clean up locks and temporary files
echo "🧹 Cleaning up..."
find sessions/ -name "*.lock" -delete 2>/dev/null
find sessions/ -name "*.tmp" -delete 2>/dev/null

# 5. Start service
echo "🚀 Starting service..."
sudo systemctl start opencode-slack
sleep 10

# 6. Verify health
echo "🏥 Checking health..."
if curl -f http://localhost:8080/health >/dev/null 2>&1; then
    echo "✅ Emergency restart successful"
else
    echo "❌ Emergency restart failed - check logs"
    echo "📋 Recent logs:"
    sudo journalctl -u opencode-slack -n 10
fi
```

### Data Recovery

**1. Database Recovery:**
```bash
#!/bin/bash
# database_recovery.sh

echo "🔧 Database recovery procedure"

# Stop service
sudo systemctl stop opencode-slack

# Backup corrupted database
cp data/employees.db data/employees.db.corrupted.$(date +%s)

# Try to recover
echo "🔄 Attempting database recovery..."
sqlite3 data/employees.db ".recover" | sqlite3 data/employees_recovered.db

# Verify recovered database
if sqlite3 data/employees_recovered.db "PRAGMA integrity_check;" | grep -q "ok"; then
    echo "✅ Database recovery successful"
    mv data/employees.db data/employees.db.backup
    mv data/employees_recovered.db data/employees.db
else
    echo "❌ Database recovery failed"
    echo "🔄 Restoring from latest backup..."
    
    # Find latest backup
    latest_backup=$(ls -t emergency_backups/*/employees.db 2>/dev/null | head -1)
    if [ -n "$latest_backup" ]; then
        cp "$latest_backup" data/employees.db
        echo "✅ Restored from backup: $latest_backup"
    else
        echo "❌ No backup found - creating new database"
        rm -f data/employees.db
        python -c "from src.managers.file_ownership import FileOwnershipManager; FileOwnershipManager()"
    fi
fi

# Restart service
sudo systemctl start opencode-slack
```

### System Reset

**1. Complete System Reset (Last Resort):**
```bash
#!/bin/bash
# system_reset.sh

echo "⚠️ COMPLETE SYSTEM RESET - This will delete all data!"
read -p "Are you sure? Type 'RESET' to continue: " confirm

if [ "$confirm" != "RESET" ]; then
    echo "Reset cancelled"
    exit 1
fi

echo "🚨 Performing complete system reset..."

# Stop all services
sudo systemctl stop opencode-slack
sudo systemctl stop nginx 2>/dev/null

# Backup everything
timestamp=$(date +%Y%m%d_%H%M%S)
mkdir -p full_backup_$timestamp
cp -r data sessions logs .env full_backup_$timestamp/ 2>/dev/null

# Clean everything
rm -rf data/* sessions/* logs/*

# Recreate directories
mkdir -p data sessions logs

# Recreate database
python -c "from src.managers.file_ownership import FileOwnershipManager; FileOwnershipManager()"

# Reset configuration
cp .env.example .env

# Restart services
sudo systemctl start opencode-slack
sudo systemctl start nginx 2>/dev/null

echo "✅ System reset complete"
echo "📦 Backup saved in: full_backup_$timestamp/"
echo "⚙️ Please update configuration in .env file"
```

## 📞 Getting Help

### Log Collection

**1. Collect All Logs:**
```bash
#!/bin/bash
# collect_logs.sh

timestamp=$(date +%Y%m%d_%H%M%S)
log_dir="support_logs_$timestamp"
mkdir -p $log_dir

echo "📋 Collecting logs for support..."

# System logs
sudo journalctl -u opencode-slack --since "24 hours ago" > $log_dir/systemd.log

# Application logs
cp logs/*.log $log_dir/ 2>/dev/null

# System information
uname -a > $log_dir/system_info.txt
free -h >> $log_dir/system_info.txt
df -h >> $log_dir/system_info.txt

# Configuration (sanitized)
cp .env $log_dir/config.txt 2>/dev/null
sed -i 's/TOKEN=.*/TOKEN=***REDACTED***/g' $log_dir/config.txt
sed -i 's/PASSWORD=.*/PASSWORD=***REDACTED***/g' $log_dir/config.txt

# Database info
sqlite3 data/employees.db "
.schema
SELECT 'Employees: ' || COUNT(*) FROM employees;
SELECT 'File locks: ' || COUNT(*) FROM file_locks;
SELECT 'File requests: ' || COUNT(*) FROM file_requests;
" > $log_dir/database_info.txt 2>/dev/null

# Create archive
tar -czf $log_dir.tar.gz $log_dir
rm -rf $log_dir

echo "✅ Logs collected: $log_dir.tar.gz"
echo "📧 Please attach this file when requesting support"
```

### Support Information

**When requesting support, please include:**

1. **System Information:**
   - Operating system and version
   - Python version
   - OpenCode-Slack version/commit
   - Hardware specifications

2. **Problem Description:**
   - What you were trying to do
   - What happened instead
   - Error messages (exact text)
   - When the problem started

3. **Logs:**
   - System logs (journalctl output)
   - Application logs
   - Browser console errors (for frontend issues)

4. **Configuration:**
   - Environment variables (sanitized)
   - Deployment method (Docker, native, etc.)
   - Network setup

5. **Reproduction Steps:**
   - Step-by-step instructions to reproduce the issue
   - Frequency of the problem
   - Workarounds that work

### Contact Information

- **GitHub Issues**: https://github.com/your-repo/opencode-slack/issues
- **Documentation**: https://github.com/your-repo/opencode-slack/docs
- **Community**: https://github.com/your-repo/opencode-slack/discussions

---

This troubleshooting guide covers the most common issues and their solutions. For issues not covered here, please collect logs using the provided scripts and open a GitHub issue with detailed information.

*Last updated: August 2025*