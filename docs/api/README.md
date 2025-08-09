# OpenCode-Slack API Documentation

## Overview

OpenCode-Slack provides a comprehensive REST API for managing AI employees, tasks, and system operations. The API follows RESTful principles and returns JSON responses.

## Base URL

```
http://localhost:8080
```

## Authentication

Currently, the API does not require authentication. This may change in future versions for production deployments.

## Core Endpoints

### Health Check
```http
GET /health
```

Returns the health status of the server.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-09T12:00:00Z",
  "version": "1.0.0"
}
```

### Employee Management

#### List Employees
```http
GET /employees
```

Returns a list of all hired employees.

**Response:**
```json
{
  "employees": [
    {
      "name": "elad",
      "role": "FS-developer",
      "status": "available",
      "current_task": null,
      "hired_at": "2025-08-09T10:00:00Z"
    }
  ]
}
```

#### Hire Employee
```http
POST /employees
Content-Type: application/json

{
  "name": "alice",
  "role": "developer",
  "smartness": "smart"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Employee alice hired as developer",
  "employee": {
    "name": "alice",
    "role": "developer",
    "smartness": "smart",
    "hired_at": "2025-08-09T12:00:00Z"
  }
}
```

#### Fire Employee
```http
DELETE /employees/{name}
```

**Response:**
```json
{
  "success": true,
  "message": "Employee alice has been fired"
}
```

### Task Management

#### Assign Task
```http
POST /tasks
Content-Type: application/json

{
  "name": "alice",
  "task": "implement authentication system",
  "model": "claude-3.5-sonnet"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Task assigned to alice",
  "task_id": "task_123",
  "employee": "alice",
  "task": "implement authentication system"
}
```

#### Get Task Status
```http
GET /tasks/{employee_name}
```

**Response:**
```json
{
  "employee": "alice",
  "current_task": "implement authentication system",
  "status": "in_progress",
  "progress": 45,
  "started_at": "2025-08-09T11:30:00Z",
  "files": ["src/auth.py", "src/models.py"]
}
```

#### Stop Task
```http
DELETE /tasks/{employee_name}
```

**Response:**
```json
{
  "success": true,
  "message": "Task stopped for employee alice"
}
```

### System Status

#### Get System Status
```http
GET /status
```

**Response:**
```json
{
  "system": {
    "status": "running",
    "uptime": "2h 30m",
    "active_employees": 3,
    "active_tasks": 2
  },
  "employees": [
    {
      "name": "alice",
      "status": "working",
      "task": "implement authentication"
    }
  ],
  "chat": {
    "status": "connected",
    "platform": "telegram",
    "active_agents": 3
  }
}
```

### Project Management

#### Get Project Root
```http
GET /project-root
```

**Response:**
```json
{
  "project_root": "/path/to/project",
  "set_at": "2025-08-09T10:00:00Z"
}
```

#### Set Project Root
```http
POST /project-root
Content-Type: application/json

{
  "project_root": "/new/path/to/project"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Project root updated",
  "project_root": "/new/path/to/project"
}
```

### File Management

#### Get Locked Files
```http
GET /files
```

**Response:**
```json
{
  "locked_files": [
    {
      "file": "src/auth.py",
      "locked_by": "alice",
      "locked_at": "2025-08-09T11:30:00Z",
      "description": "implementing authentication"
    }
  ]
}
```

#### Lock Files
```http
POST /files/lock
Content-Type: application/json

{
  "employee": "alice",
  "files": ["src/auth.py", "src/models.py"],
  "description": "implementing authentication system"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Files locked for alice",
  "locked_files": ["src/auth.py", "src/models.py"]
}
```

#### Release Files
```http
POST /files/release
Content-Type: application/json

{
  "employee": "alice",
  "files": ["src/auth.py"]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Files released by alice",
  "released_files": ["src/auth.py"]
}
```

## Error Responses

All endpoints return appropriate HTTP status codes and error messages:

### 400 Bad Request
```json
{
  "error": "Invalid request",
  "message": "Employee name is required",
  "code": "MISSING_PARAMETER"
}
```

### 404 Not Found
```json
{
  "error": "Not found",
  "message": "Employee 'alice' not found",
  "code": "EMPLOYEE_NOT_FOUND"
}
```

### 409 Conflict
```json
{
  "error": "Conflict",
  "message": "Employee 'alice' is already hired",
  "code": "EMPLOYEE_EXISTS"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error",
  "message": "An unexpected error occurred",
  "code": "INTERNAL_ERROR"
}
```

## Rate Limiting

The API implements basic rate limiting:
- Maximum 100 requests per minute per client
- Burst limit of 20 requests per 10 seconds

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1691582400
```

## WebSocket Support

For real-time updates, the API supports WebSocket connections:

```javascript
const ws = new WebSocket('ws://localhost:8080/ws');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Real-time update:', data);
};
```

### WebSocket Events

- `employee_hired`: New employee hired
- `employee_fired`: Employee fired
- `task_assigned`: Task assigned to employee
- `task_completed`: Task completed
- `task_progress`: Task progress update
- `system_status`: System status change

## Examples

### Complete Workflow Example

```bash
# 1. Check system health
curl http://localhost:8080/health

# 2. Hire an employee
curl -X POST http://localhost:8080/employees \
  -H "Content-Type: application/json" \
  -d '{"name": "alice", "role": "developer"}'

# 3. Assign a task
curl -X POST http://localhost:8080/tasks \
  -H "Content-Type: application/json" \
  -d '{"name": "alice", "task": "add login functionality"}'

# 4. Check task progress
curl http://localhost:8080/tasks/alice

# 5. Check system status
curl http://localhost:8080/status
```

### Python Client Example

```python
import requests
import json

# Base URL
base_url = "http://localhost:8080"

# Hire employee
response = requests.post(f"{base_url}/employees", 
                        json={"name": "alice", "role": "developer"})
print(response.json())

# Assign task
response = requests.post(f"{base_url}/tasks",
                        json={"name": "alice", "task": "implement feature"})
print(response.json())

# Check status
response = requests.get(f"{base_url}/status")
print(response.json())
```

## SDK and Libraries

Official SDKs are planned for:
- Python
- JavaScript/Node.js
- Go
- Rust

Community contributions for other languages are welcome.

---

For more information, see the [main documentation](../README.md) or [development guide](../development/AGENTS.md).