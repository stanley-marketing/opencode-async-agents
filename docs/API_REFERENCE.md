# 📡 API Reference Documentation

**Complete API reference for OpenCode-Slack system integration**

## 🎯 Overview

OpenCode-Slack provides comprehensive REST API and WebSocket interfaces for programmatic access to all system functionality. This reference covers all endpoints, message formats, and integration patterns.

## 🌐 Base Configuration

### Server Endpoints
```
HTTP API:     http://localhost:8080
WebSocket:    ws://localhost:8765
Health Check: http://localhost:8080/health
```

### Authentication
Currently, the system operates in trusted environment mode. Future versions will include:
- API key authentication
- JWT token support
- Role-based access control

## 🔗 REST API Reference

### 🏥 Health & Status

#### GET /health
**Purpose**: System health check and status information

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-10T14:30:00Z",
  "version": "1.0.0",
  "components": {
    "database": "healthy",
    "websocket": "healthy",
    "agents": "healthy",
    "file_system": "healthy"
  },
  "metrics": {
    "active_employees": 5,
    "active_sessions": 3,
    "websocket_connections": 12,
    "uptime_seconds": 86400
  }
}
```

**Status Codes:**
- `200`: System healthy
- `503`: System unhealthy or degraded

#### GET /status
**Purpose**: Detailed system status and statistics

**Response:**
```json
{
  "employees": {
    "total": 5,
    "active": 3,
    "idle": 2
  },
  "tasks": {
    "active": 3,
    "completed_today": 15,
    "average_completion_time": "12.5 minutes"
  },
  "files": {
    "locked": 8,
    "pending_requests": 2
  },
  "communication": {
    "transport": "websocket",
    "connected_clients": 12,
    "messages_today": 245
  }
}
```

### 👥 Employee Management

#### POST /employees
**Purpose**: Hire a new AI employee

**Request Body:**
```json
{
  "name": "alice",
  "role": "FS-developer",
  "smartness_level": "smart"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Employee alice hired successfully",
  "employee": {
    "name": "alice",
    "role": "FS-developer",
    "smartness_level": "smart",
    "hired_date": "2025-08-10T14:30:00Z",
    "status": "idle"
  }
}
```

**Status Codes:**
- `201`: Employee hired successfully
- `400`: Invalid request data
- `409`: Employee already exists

#### GET /employees
**Purpose**: List all employees

**Query Parameters:**
- `status` (optional): Filter by status (`active`, `idle`, `working`)
- `role` (optional): Filter by role

**Response:**
```json
{
  "employees": [
    {
      "name": "alice",
      "role": "FS-developer",
      "smartness_level": "smart",
      "hired_date": "2025-08-10T14:30:00Z",
      "status": "working",
      "current_task": "implement authentication system"
    },
    {
      "name": "bob",
      "role": "designer",
      "smartness_level": "normal",
      "hired_date": "2025-08-10T15:00:00Z",
      "status": "idle",
      "current_task": null
    }
  ],
  "total": 2
}
```

#### GET /employees/{name}
**Purpose**: Get specific employee details

**Response:**
```json
{
  "name": "alice",
  "role": "FS-developer",
  "smartness_level": "smart",
  "hired_date": "2025-08-10T14:30:00Z",
  "status": "working",
  "current_task": "implement authentication system",
  "expertise": ["python", "javascript", "html", "css"],
  "performance": {
    "tasks_completed": 15,
    "average_completion_time": "18.5 minutes",
    "success_rate": 0.95
  }
}
```

**Status Codes:**
- `200`: Employee found
- `404`: Employee not found

#### DELETE /employees/{name}
**Purpose**: Fire an employee

**Response:**
```json
{
  "success": true,
  "message": "Employee alice fired successfully"
}
```

**Status Codes:**
- `200`: Employee fired successfully
- `404`: Employee not found
- `409`: Employee currently working (cannot fire)

### 📋 Task Management

#### POST /tasks
**Purpose**: Assign a task to an employee

**Request Body:**
```json
{
  "employee": "alice",
  "task": "implement user authentication system",
  "priority": "high",
  "files": ["src/auth.py", "templates/login.html"],
  "model": "claude-3.5-sonnet"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Task assigned to alice successfully",
  "task_id": "task_001",
  "estimated_completion": "2025-08-10T16:30:00Z"
}
```

**Status Codes:**
- `201`: Task assigned successfully
- `400`: Invalid request data
- `404`: Employee not found
- `409`: Employee already working on a task

#### GET /tasks
**Purpose**: List all active tasks

**Query Parameters:**
- `employee` (optional): Filter by employee name
- `status` (optional): Filter by status (`active`, `completed`, `failed`)

**Response:**
```json
{
  "tasks": [
    {
      "task_id": "task_001",
      "employee": "alice",
      "task": "implement user authentication system",
      "status": "active",
      "progress": 65,
      "started_at": "2025-08-10T14:30:00Z",
      "estimated_completion": "2025-08-10T16:30:00Z",
      "files": [
        {
          "path": "src/auth.py",
          "status": "in_progress",
          "progress": 80
        },
        {
          "path": "templates/login.html",
          "status": "pending",
          "progress": 0
        }
      ]
    }
  ],
  "total": 1
}
```

#### GET /tasks/{employee}
**Purpose**: Get specific employee's current task

**Response:**
```json
{
  "task_id": "task_001",
  "employee": "alice",
  "task": "implement user authentication system",
  "status": "active",
  "progress": 65,
  "started_at": "2025-08-10T14:30:00Z",
  "estimated_completion": "2025-08-10T16:30:00Z",
  "files": [
    {
      "path": "src/auth.py",
      "status": "in_progress",
      "progress": 80,
      "last_update": "2025-08-10T15:45:00Z"
    }
  ],
  "recent_updates": [
    {
      "timestamp": "2025-08-10T15:45:00Z",
      "message": "Implemented password hashing functionality"
    },
    {
      "timestamp": "2025-08-10T15:30:00Z",
      "message": "Created user model and database schema"
    }
  ]
}
```

**Status Codes:**
- `200`: Task found
- `404`: Employee not found or no active task

#### DELETE /tasks/{employee}
**Purpose**: Stop employee's current task

**Response:**
```json
{
  "success": true,
  "message": "Task stopped for alice successfully"
}
```

**Status Codes:**
- `200`: Task stopped successfully
- `404`: Employee not found or no active task

### 📁 File Management

#### GET /files
**Purpose**: List all file locks and ownership

**Query Parameters:**
- `employee` (optional): Filter by employee name
- `status` (optional): Filter by lock status

**Response:**
```json
{
  "file_locks": [
    {
      "id": 1,
      "employee": "alice",
      "file_path": "src/auth.py",
      "description": "implementing authentication",
      "locked_at": "2025-08-10T14:30:00Z",
      "status": "active"
    },
    {
      "id": 2,
      "employee": "bob",
      "file_path": "static/styles.css",
      "description": "updating design",
      "locked_at": "2025-08-10T15:00:00Z",
      "status": "active"
    }
  ],
  "total": 2
}
```

#### POST /files/lock
**Purpose**: Lock files for an employee

**Request Body:**
```json
{
  "employee": "alice",
  "files": ["src/auth.py", "templates/login.html"],
  "description": "implementing authentication system"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Files locked successfully",
  "locked_files": [
    {
      "id": 3,
      "file_path": "src/auth.py",
      "locked_at": "2025-08-10T16:00:00Z"
    },
    {
      "id": 4,
      "file_path": "templates/login.html",
      "locked_at": "2025-08-10T16:00:00Z"
    }
  ]
}
```

**Status Codes:**
- `201`: Files locked successfully
- `400`: Invalid request data
- `404`: Employee not found
- `409`: One or more files already locked

#### POST /files/release
**Purpose**: Release files from an employee

**Request Body:**
```json
{
  "employee": "alice",
  "files": ["src/auth.py"]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Files released successfully",
  "released_files": ["src/auth.py"]
}
```

**Status Codes:**
- `200`: Files released successfully
- `400`: Invalid request data
- `404`: Employee or files not found

#### GET /files/requests
**Purpose**: List pending file requests

**Response:**
```json
{
  "requests": [
    {
      "id": 1,
      "requester": "bob",
      "file_path": "src/auth.py",
      "reason": "need for API integration",
      "status": "pending",
      "requested_at": "2025-08-10T15:30:00Z",
      "current_owner": "alice"
    }
  ],
  "total": 1
}
```

#### POST /files/requests/{id}/approve
**Purpose**: Approve a file request

**Response:**
```json
{
  "success": true,
  "message": "File request approved successfully",
  "transferred_file": "src/auth.py",
  "from_employee": "alice",
  "to_employee": "bob"
}
```

**Status Codes:**
- `200`: Request approved successfully
- `404`: Request not found
- `409`: Request already processed

#### POST /files/requests/{id}/deny
**Purpose**: Deny a file request

**Request Body:**
```json
{
  "reason": "Still working on authentication implementation"
}
```

**Response:**
```json
{
  "success": true,
  "message": "File request denied",
  "reason": "Still working on authentication implementation"
}
```

### 🔧 System Configuration

#### GET /project-root
**Purpose**: Get current project root directory

**Response:**
```json
{
  "project_root": "/home/user/my-project",
  "set_at": "2025-08-10T14:00:00Z"
}
```

#### POST /project-root
**Purpose**: Set project root directory

**Request Body:**
```json
{
  "project_root": "/home/user/my-project"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Project root updated successfully",
  "project_root": "/home/user/my-project"
}
```

**Status Codes:**
- `200`: Project root updated successfully
- `400`: Invalid directory path

### 💬 Communication

#### GET /communication/info
**Purpose**: Get communication system information

**Response:**
```json
{
  "transport_type": "websocket",
  "status": "active",
  "configuration": {
    "websocket_host": "localhost",
    "websocket_port": 8765,
    "max_connections": 100
  },
  "agents": [
    {
      "name": "alice-bot",
      "role": "FS-developer",
      "status": "active",
      "last_message": "2025-08-10T15:45:00Z"
    },
    {
      "name": "bob-bot",
      "role": "designer",
      "status": "idle",
      "last_message": "2025-08-10T15:30:00Z"
    }
  ]
}
```

#### GET /communication/stats
**Purpose**: Get communication statistics

**Response:**
```json
{
  "websocket": {
    "active_connections": 12,
    "total_messages_today": 245,
    "average_response_time": "150ms",
    "connection_uptime": "99.8%"
  },
  "agents": {
    "total_responses": 89,
    "average_response_time": "2.3s",
    "help_requests": 5,
    "task_completions": 12
  },
  "performance": {
    "messages_per_second": 15.2,
    "peak_concurrent_users": 25,
    "error_rate": "0.1%"
  }
}
```

## 🔌 WebSocket API Reference

### Connection

**Endpoint**: `ws://localhost:8765`

**Connection Flow:**
```javascript
const socket = new WebSocket('ws://localhost:8765');

socket.onopen = () => {
  console.log('Connected to OpenCode-Slack');
  // Send authentication if required
};

socket.onmessage = (event) => {
  const message = JSON.parse(event.data);
  handleMessage(message);
};

socket.onclose = () => {
  console.log('Disconnected from OpenCode-Slack');
  // Implement reconnection logic
};
```

### Message Types

#### User Message
**Direction**: Client → Server

```json
{
  "type": "message",
  "user_id": "user123",
  "text": "@alice please implement authentication",
  "timestamp": 1691234567890,
  "message_id": "msg_001"
}
```

#### Agent Response
**Direction**: Server → Client

```json
{
  "type": "agent_response",
  "agent_name": "alice-bot",
  "text": "Got it! Working on authentication implementation now.",
  "timestamp": 1691234567890,
  "message_id": "msg_002",
  "reply_to": "msg_001"
}
```

#### System Notification
**Direction**: Server → Client

```json
{
  "type": "system_notification",
  "notification_type": "task_completed",
  "message": "alice has completed the authentication implementation",
  "timestamp": 1691234567890,
  "data": {
    "employee": "alice",
    "task": "implement authentication",
    "completion_time": "18.5 minutes"
  }
}
```

#### Status Update
**Direction**: Server → Client

```json
{
  "type": "status_update",
  "update_type": "employee_status",
  "timestamp": 1691234567890,
  "data": {
    "employee": "alice",
    "status": "working",
    "task": "implement authentication",
    "progress": 65
  }
}
```

#### Typing Indicator
**Direction**: Bidirectional

```json
{
  "type": "typing",
  "user_id": "user123",
  "is_typing": true,
  "timestamp": 1691234567890
}
```

#### Connection Status
**Direction**: Server → Client

```json
{
  "type": "connection_status",
  "status": "connected",
  "client_count": 12,
  "timestamp": 1691234567890
}
```

### WebSocket Events

#### User Events
```javascript
// Send message
socket.send(JSON.stringify({
  type: 'message',
  user_id: 'user123',
  text: '@alice implement login feature',
  timestamp: Date.now(),
  message_id: generateMessageId()
}));

// Send typing indicator
socket.send(JSON.stringify({
  type: 'typing',
  user_id: 'user123',
  is_typing: true,
  timestamp: Date.now()
}));
```

#### Server Events
```javascript
socket.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  switch (message.type) {
    case 'agent_response':
      displayAgentMessage(message);
      break;
    case 'system_notification':
      showNotification(message);
      break;
    case 'status_update':
      updateEmployeeStatus(message.data);
      break;
    case 'typing':
      showTypingIndicator(message);
      break;
  }
};
```

## 🔧 Integration Examples

### Python Client

```python
import requests
import json

class OpenCodeSlackClient:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
    
    def hire_employee(self, name, role, smartness_level="normal"):
        response = requests.post(f"{self.base_url}/employees", json={
            "name": name,
            "role": role,
            "smartness_level": smartness_level
        })
        return response.json()
    
    def assign_task(self, employee, task, files=None):
        data = {"employee": employee, "task": task}
        if files:
            data["files"] = files
        
        response = requests.post(f"{self.base_url}/tasks", json=data)
        return response.json()
    
    def get_status(self):
        response = requests.get(f"{self.base_url}/status")
        return response.json()

# Usage
client = OpenCodeSlackClient()

# Hire employees
client.hire_employee("alice", "FS-developer", "smart")
client.hire_employee("bob", "designer")

# Assign tasks
client.assign_task("alice", "implement user authentication")
client.assign_task("bob", "design login page")

# Check status
status = client.get_status()
print(f"Active employees: {status['employees']['active']}")
```

### JavaScript/Node.js Client

```javascript
class OpenCodeSlackClient {
  constructor(baseUrl = 'http://localhost:8080') {
    this.baseUrl = baseUrl;
  }
  
  async hireEmployee(name, role, smartnessLevel = 'normal') {
    const response = await fetch(`${this.baseUrl}/employees`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        role,
        smartness_level: smartnessLevel
      })
    });
    return response.json();
  }
  
  async assignTask(employee, task, files = null) {
    const data = { employee, task };
    if (files) data.files = files;
    
    const response = await fetch(`${this.baseUrl}/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return response.json();
  }
  
  async getStatus() {
    const response = await fetch(`${this.baseUrl}/status`);
    return response.json();
  }
}

// Usage
const client = new OpenCodeSlackClient();

// Hire employees
await client.hireEmployee('alice', 'FS-developer', 'smart');
await client.hireEmployee('bob', 'designer');

// Assign tasks
await client.assignTask('alice', 'implement user authentication');
await client.assignTask('bob', 'design login page');

// Check status
const status = await client.getStatus();
console.log(`Active employees: ${status.employees.active}`);
```

### WebSocket Client

```javascript
class WebSocketClient {
  constructor(url = 'ws://localhost:8765') {
    this.url = url;
    this.socket = null;
    this.messageHandlers = new Map();
  }
  
  connect() {
    this.socket = new WebSocket(this.url);
    
    this.socket.onopen = () => {
      console.log('Connected to OpenCode-Slack WebSocket');
      this.onConnect();
    };
    
    this.socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };
    
    this.socket.onclose = () => {
      console.log('Disconnected from OpenCode-Slack WebSocket');
      this.reconnect();
    };
  }
  
  sendMessage(text, userId = 'user123') {
    const message = {
      type: 'message',
      user_id: userId,
      text: text,
      timestamp: Date.now(),
      message_id: this.generateMessageId()
    };
    
    this.socket.send(JSON.stringify(message));
  }
  
  onMessage(type, handler) {
    this.messageHandlers.set(type, handler);
  }
  
  handleMessage(message) {
    const handler = this.messageHandlers.get(message.type);
    if (handler) {
      handler(message);
    }
  }
  
  generateMessageId() {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
  
  reconnect() {
    setTimeout(() => {
      console.log('Attempting to reconnect...');
      this.connect();
    }, 5000);
  }
}

// Usage
const wsClient = new WebSocketClient();

// Set up message handlers
wsClient.onMessage('agent_response', (message) => {
  console.log(`${message.agent_name}: ${message.text}`);
});

wsClient.onMessage('system_notification', (message) => {
  console.log(`System: ${message.message}`);
});

wsClient.onMessage('status_update', (message) => {
  console.log(`Status update: ${JSON.stringify(message.data)}`);
});

// Connect and send messages
wsClient.connect();

// Send task assignment
wsClient.sendMessage('@alice please implement user authentication');
wsClient.sendMessage('@bob can you design the login page?');
```

## 🔍 Error Handling

### HTTP Error Responses

**Standard Error Format:**
```json
{
  "error": true,
  "message": "Employee not found",
  "code": "EMPLOYEE_NOT_FOUND",
  "details": {
    "employee_name": "nonexistent",
    "available_employees": ["alice", "bob"]
  },
  "timestamp": "2025-08-10T15:30:00Z"
}
```

**Common Error Codes:**
- `EMPLOYEE_NOT_FOUND`: Employee does not exist
- `EMPLOYEE_ALREADY_EXISTS`: Employee name already taken
- `EMPLOYEE_BUSY`: Employee currently working on another task
- `FILE_LOCKED`: File is locked by another employee
- `INVALID_REQUEST`: Request data validation failed
- `SYSTEM_ERROR`: Internal system error

### WebSocket Error Handling

**Error Message Format:**
```json
{
  "type": "error",
  "error_code": "INVALID_MESSAGE_FORMAT",
  "message": "Message must include user_id and text fields",
  "timestamp": 1691234567890,
  "original_message": "..."
}
```

**Connection Error Handling:**
```javascript
socket.onerror = (error) => {
  console.error('WebSocket error:', error);
  // Implement error recovery
};

socket.onclose = (event) => {
  if (event.code !== 1000) {
    console.error('WebSocket closed unexpectedly:', event.code, event.reason);
    // Implement reconnection logic
  }
};
```

## 📊 Rate Limiting

### HTTP API Rate Limits
- **Default**: 100 requests per hour per IP
- **Employee operations**: 10 requests per minute
- **Task operations**: 5 requests per minute
- **File operations**: 20 requests per minute

### WebSocket Rate Limits
- **Messages**: 60 messages per minute per connection
- **Typing indicators**: 10 per minute per connection
- **Connection attempts**: 5 per minute per IP

### Rate Limit Headers
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1691234567
```

## 🔐 Security Considerations

### Input Validation
- All text inputs are sanitized
- File paths are validated and restricted
- Employee names must match pattern: `^[a-zA-Z0-9_-]+$`
- Task descriptions limited to 1000 characters

### CORS Configuration
```javascript
// Allowed origins for WebSocket connections
const allowedOrigins = [
  'http://localhost:3000',
  'https://your-domain.com'
];
```

### Security Headers
```
Content-Security-Policy: default-src 'self'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
```

## 📈 Performance Optimization

### Caching
- Employee status cached for 30 seconds
- File ownership cached for 60 seconds
- System status cached for 10 seconds

### Connection Management
- WebSocket connections pooled and reused
- Automatic cleanup of inactive connections
- Connection heartbeat every 30 seconds

### Database Optimization
- Indexed queries for employee and file operations
- Connection pooling for concurrent requests
- Automatic cleanup of old task data

---

This API reference provides complete documentation for integrating with OpenCode-Slack. For additional examples and advanced usage patterns, see the User Guide and Technical Architecture documentation.

*Last updated: August 2025*