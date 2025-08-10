# 🏗️ Technical Architecture Documentation

**Comprehensive technical documentation for OpenCode-Slack system architecture**

## 🎯 System Overview

OpenCode-Slack is a production-ready AI employee management system built with a modern, scalable architecture supporting multiple communication transports and real-time collaboration.

### Core Principles
- **Modular Design**: Loosely coupled components with clear interfaces
- **Transport Agnostic**: Support for WebSocket, Telegram, and future protocols
- **Conflict-Free Collaboration**: Database-backed file locking and ownership
- **Real-time Communication**: Sub-100ms message delivery and status updates
- **Production Ready**: Comprehensive testing, monitoring, and error handling

## 🏛️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    OpenCode-Slack System                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────┐ │
│  │   Frontend      │    │   Server Core    │    │  AI Models  │ │
│  │                 │    │                  │    │             │ │
│  │ • React UI      │◄──►│ • REST API       │◄──►│ • OpenCode  │ │
│  │ • WebSocket     │    │ • WebSocket      │    │ • Claude    │ │
│  │ • Real-time     │    │ • Agent Manager  │    │ • GPT       │ │
│  └─────────────────┘    └──────────────────┘    └─────────────┘ │
│           │                       │                       │     │
│           │              ┌──────────────────┐             │     │
│           └──────────────►│ Communication    │◄────────────┘     │
│                          │ Manager          │                   │
│                          │                  │                   │
│                          │ • Transport      │                   │
│                          │   Abstraction    │                   │
│                          │ • Auto-detection │                   │
│                          │ • Runtime Switch │                   │
│                          └──────────────────┘                   │
│                                   │                             │
│                      ┌─────────────┴─────────────┐               │
│                      │                           │               │
│              ┌───────▼────────┐         ┌───────▼────────┐       │
│              │ WebSocketMgr   │         │ TelegramMgr    │       │
│              │                │         │                │       │
│              │ • WebSocket    │         │ • Bot API      │       │
│              │   Server       │         │ • Polling      │       │
│              │ • Real-time    │         │ • Webhooks     │       │
│              └────────────────┘         └────────────────┘       │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                        Data Layer                               │
│                                                                 │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────┐ │
│  │   SQLite DB     │    │   File System    │    │  Sessions   │ │
│  │                 │    │                  │    │             │ │
│  │ • Employees     │    │ • Project Files  │    │ • Task Data │ │
│  │ • File Locks    │    │ • Ownership      │    │ • Progress  │ │
│  │ • Requests      │    │ • Conflicts      │    │ • History   │ │
│  └─────────────────┘    └──────────────────┘    └─────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 🔧 Core Components

### 1. Communication Layer

#### CommunicationManager
**Purpose**: Unified transport abstraction supporting multiple communication protocols

**Key Features:**
- Transport auto-detection and switching
- Consistent interface across all transports
- Runtime configuration changes
- Health monitoring and failover

**Implementation:**
```python
class CommunicationManager:
    def __init__(self):
        self.transport_type = self._detect_transport()
        self.manager = self._create_manager()
    
    def _detect_transport(self) -> str:
        # Auto-detect based on environment and availability
        if os.getenv('OPENCODE_TRANSPORT') == 'websocket':
            return 'websocket'
        elif os.getenv('TELEGRAM_BOT_TOKEN'):
            return 'telegram'
        return 'websocket'  # Default
    
    def send_message(self, text: str, sender: str = "system") -> bool:
        return self.manager.send_message(text, sender)
```

#### WebSocketManager
**Purpose**: Real-time web communication with React frontend

**Architecture:**
```python
class WebSocketManager:
    def __init__(self):
        self.server = None
        self.clients = set()
        self.message_handlers = []
        self.message_parser = MessageParser()
    
    async def handle_client(self, websocket, path):
        # Client connection handling
        # Message routing and broadcasting
        # Error handling and recovery
```

**Features:**
- Real-time bidirectional communication
- Client connection management
- Message broadcasting and routing
- Auto-reconnection support
- Rate limiting and authentication

#### TelegramManager
**Purpose**: Traditional bot-based chat integration

**Features:**
- Telegram Bot API integration
- Polling and webhook support
- Group chat management
- Message parsing and routing
- Rate limiting and error handling

### 2. Agent System

#### AgentManager
**Purpose**: Manages communication agents and their interactions

**Architecture:**
```python
class AgentManager:
    def __init__(self, file_manager, communication_manager):
        self.file_manager = file_manager
        self.communication_manager = communication_manager
        self.agents = {}
        self.expertise_map = {}
    
    def create_agent(self, name: str, role: str, expertise: List[str]):
        agent = CommunicationAgent(name, role, expertise)
        self.agents[name] = agent
        self._update_expertise_map(name, expertise)
```

**Key Responsibilities:**
- Agent lifecycle management (create, update, remove)
- Message routing and handling
- Expertise matching and task assignment
- Help request coordination
- Status monitoring and reporting

#### CommunicationAgent
**Purpose**: Individual AI agent with personality and expertise

**Features:**
- Role-based personalities and behaviors
- Expertise-based task routing
- Memory management and conversation history
- Help request and collaboration workflows
- Performance metrics and monitoring

### 3. Task Management

#### TaskProgressTracker
**Purpose**: Real-time task progress monitoring and reporting

**Architecture:**
```python
class TaskProgressTracker:
    def __init__(self, sessions_dir: str):
        self.sessions_dir = Path(sessions_dir)
        self.active_tasks = {}
    
    def create_task_file(self, employee: str, task: str, files: List[str]):
        # Create markdown task file
        # Initialize progress tracking
        # Set up file monitoring
```

**Features:**
- Markdown-based progress files
- Real-time progress updates
- File-level progress tracking
- Completion detection and archival
- Historical task data

#### OpencodeSessionManager
**Purpose**: Manages actual code execution sessions

**Features:**
- Isolated work environments per employee
- Session lifecycle management
- Progress monitoring and reporting
- Error handling and recovery
- Resource cleanup

### 4. File Management

#### FileOwnershipManager
**Purpose**: Conflict-free file collaboration system

**Database Schema:**
```sql
-- Employees table
CREATE TABLE employees (
    name TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    smartness_level TEXT DEFAULT 'normal',
    hired_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- File locks table
CREATE TABLE file_locks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    description TEXT,
    locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_name) REFERENCES employees (name)
);

-- File requests table
CREATE TABLE file_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requester_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    reason TEXT,
    status TEXT DEFAULT 'pending',
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (requester_name) REFERENCES employees (name)
);
```

**Key Features:**
- Database-backed file locking
- Request/approval workflow
- Conflict detection and resolution
- Automatic cleanup on task completion
- Thread-safe operations

## 🌐 WebSocket Implementation

### Server Architecture

**WebSocket Server:**
```python
class WebSocketServer:
    def __init__(self, host='localhost', port=8765):
        self.host = host
        self.port = port
        self.clients = set()
        self.message_handlers = []
    
    async def start_server(self):
        self.server = await websockets.serve(
            self.handle_client, 
            self.host, 
            self.port
        )
        logger.info(f"WebSocket server started on {self.host}:{self.port}")
    
    async def handle_client(self, websocket, path):
        self.clients.add(websocket)
        try:
            async for message in websocket:
                await self.process_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)
```

**Message Protocol:**
```json
{
  "type": "message",
  "user_id": "user123",
  "text": "@elad please implement authentication",
  "timestamp": 1691234567890,
  "message_id": "msg_001"
}
```

### Frontend Architecture

**React Components:**
```typescript
// Main chat interface
const ChatInterface: React.FC = () => {
  const { messages, sendMessage, connectionStatus } = useWebSocket();
  const { users, agents } = useChatStore();
  
  return (
    <div className="chat-container">
      <ConnectionStatus status={connectionStatus} />
      <MessageList messages={messages} />
      <UserList users={users} agents={agents} />
      <MessageInput onSend={sendMessage} />
    </div>
  );
};

// WebSocket hook
const useWebSocket = () => {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  
  useEffect(() => {
    const ws = new WebSocket(WEBSOCKET_URL);
    
    ws.onopen = () => setConnectionStatus('connected');
    ws.onclose = () => setConnectionStatus('disconnected');
    ws.onmessage = (event) => handleMessage(JSON.parse(event.data));
    
    setSocket(ws);
    return () => ws.close();
  }, []);
  
  return { socket, connectionStatus, sendMessage };
};
```

**State Management (Zustand):**
```typescript
interface ChatState {
  messages: Message[];
  users: User[];
  agents: Agent[];
  connectionStatus: ConnectionStatus;
  addMessage: (message: Message) => void;
  updateConnectionStatus: (status: ConnectionStatus) => void;
}

const useChatStore = create<ChatState>((set) => ({
  messages: [],
  users: [],
  agents: [],
  connectionStatus: 'disconnected',
  addMessage: (message) => set((state) => ({ 
    messages: [...state.messages, message] 
  })),
  updateConnectionStatus: (status) => set({ connectionStatus: status }),
}));
```

## 🔄 Message Flow

### WebSocket Message Flow
```
1. User types message in React frontend
2. Frontend sends WebSocket message to server
3. WebSocketManager receives and parses message
4. Message converted to ParsedMessage format
5. AgentManager routes message to appropriate agents
6. Agents process message and generate responses
7. Responses sent back through WebSocket
8. Frontend receives and displays responses
```

### Telegram Message Flow
```
1. User sends message in Telegram group
2. TelegramManager receives via polling/webhook
3. Message parsed and converted to ParsedMessage
4. AgentManager routes to appropriate agents
5. Agents process and generate responses
6. Responses sent back to Telegram group
```

### Task Assignment Flow
```
1. Task assigned via CLI, WebSocket, or Telegram
2. AgentBridge coordinates task assignment
3. OpencodeSessionManager creates isolated session
4. TaskProgressTracker creates progress file
5. FileOwnershipManager locks required files
6. Agent begins work in isolated environment
7. Real-time progress updates via communication layer
8. Completion notification and cleanup
```

## 📊 Data Models

### Core Data Structures

**ParsedMessage:**
```python
@dataclass
class ParsedMessage:
    text: str
    sender_name: str
    mentions: List[str]
    is_command: bool
    timestamp: datetime
    message_id: str
    reply_to: Optional[str] = None
```

**Employee:**
```python
@dataclass
class Employee:
    name: str
    role: str
    smartness_level: str
    hired_date: datetime
    status: str
    current_task: Optional[str] = None
```

**FileLock:**
```python
@dataclass
class FileLock:
    id: int
    employee_name: str
    file_path: str
    description: str
    locked_at: datetime
```

**TaskProgress:**
```python
@dataclass
class TaskProgress:
    employee: str
    task: str
    status: str
    progress_percentage: int
    files: List[FileProgress]
    started_at: datetime
    updated_at: datetime
```

## 🔐 Security Architecture

### Authentication & Authorization

**WebSocket Authentication:**
```python
async def authenticate_websocket(websocket, message):
    # User validation
    # Session management
    # Permission checking
    return is_authenticated
```

**API Security:**
```python
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # Rate limiting
    # Input validation
    # CORS handling
    response = await call_next(request)
    return response
```

### File Access Control

**Permission System:**
```python
class FilePermissionManager:
    def check_file_access(self, employee: str, file_path: str) -> bool:
        # Check file ownership
        # Validate employee permissions
        # Ensure no conflicts
        return has_access
```

## 🚀 Performance Architecture

### Scalability Features

**Concurrent Operations:**
- Thread-safe database operations
- Async WebSocket handling
- Connection pooling
- Resource cleanup

**Performance Optimizations:**
- Message batching and queuing
- Connection keep-alive
- Efficient database queries
- Memory management

**Load Handling:**
```python
class PerformanceManager:
    def __init__(self):
        self.connection_pool = ConnectionPool(max_size=100)
        self.message_queue = asyncio.Queue(maxsize=1000)
        self.rate_limiter = RateLimiter(max_requests=100, window=60)
    
    async def handle_high_load(self):
        # Connection throttling
        # Message queuing
        # Resource monitoring
        # Graceful degradation
```

## 🔍 Monitoring & Observability

### Health Monitoring

**System Health Checks:**
```python
class HealthMonitor:
    def get_system_health(self) -> Dict[str, Any]:
        return {
            'database': self.check_database_health(),
            'websocket': self.check_websocket_health(),
            'agents': self.check_agent_health(),
            'file_system': self.check_file_system_health(),
            'memory': self.get_memory_usage(),
            'connections': self.get_connection_count()
        }
```

**Metrics Collection:**
- Response times and latency
- Connection counts and stability
- Message throughput
- Error rates and types
- Resource usage (CPU, memory)
- Agent performance metrics

### Logging Architecture

**Structured Logging:**
```python
import structlog

logger = structlog.get_logger()

# Usage throughout system
logger.info("Agent created", 
           agent_name=name, 
           role=role, 
           expertise=expertise)

logger.error("WebSocket connection failed", 
            client_id=client_id, 
            error=str(e))
```

## 🧪 Testing Architecture

### Test Categories

**Unit Tests:**
- Individual component testing
- Mock external dependencies
- Fast execution and isolation

**Integration Tests:**
- Component interaction testing
- Database integration
- API endpoint testing

**E2E Tests:**
- Complete workflow validation
- Real system testing
- Performance validation

**Load Tests:**
- Concurrent user simulation
- High-frequency messaging
- Resource usage validation

### Test Infrastructure

**Test Database:**
```python
@pytest.fixture
def test_db():
    db_path = ":memory:"  # In-memory SQLite
    manager = FileOwnershipManager(db_path)
    yield manager
    # Cleanup handled automatically
```

**WebSocket Testing:**
```python
@pytest.mark.asyncio
async def test_websocket_communication():
    async with websockets.connect("ws://localhost:8765") as websocket:
        # Send test message
        await websocket.send(json.dumps(test_message))
        
        # Verify response
        response = await websocket.recv()
        assert json.loads(response)['status'] == 'success'
```

## 🔧 Configuration Management

### Environment Configuration

**Configuration Hierarchy:**
1. Environment variables (highest priority)
2. .env file
3. Configuration files
4. Default values (lowest priority)

**Configuration Schema:**
```python
@dataclass
class SystemConfig:
    # Communication
    transport_type: str = 'websocket'
    websocket_host: str = 'localhost'
    websocket_port: int = 8765
    
    # Database
    database_path: str = 'employees.db'
    
    # Performance
    max_concurrent_sessions: int = 10
    stuck_timeout_minutes: int = 10
    
    # Security
    rate_limit_per_hour: int = 100
    enable_authentication: bool = True
```

### Runtime Configuration

**Dynamic Configuration Updates:**
```python
class ConfigManager:
    def update_config(self, key: str, value: Any):
        # Validate configuration change
        # Apply changes safely
        # Notify affected components
        # Log configuration change
```

## 🚀 Deployment Architecture

### Production Deployment

**Docker Configuration:**
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8080 8765

CMD ["python", "src/server_websocket.py"]
```

**Docker Compose:**
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
    volumes:
      - ./data:/data
      - ./sessions:/app/sessions
```

### Scaling Considerations

**Horizontal Scaling:**
- Load balancer for multiple instances
- Shared database for state consistency
- Session affinity for WebSocket connections
- Message queue for async processing

**Vertical Scaling:**
- Resource monitoring and alerting
- Automatic scaling based on load
- Performance optimization
- Memory and CPU management

## 📋 API Reference

### REST API Endpoints

**Employee Management:**
```
POST /employees
GET /employees
DELETE /employees/{name}
GET /employees/{name}/status
```

**Task Management:**
```
POST /tasks
GET /tasks
GET /tasks/{employee}
DELETE /tasks/{employee}
```

**File Management:**
```
GET /files
POST /files/lock
POST /files/release
GET /files/requests
POST /files/requests/{id}/approve
```

**System Status:**
```
GET /health
GET /status
GET /communication/info
GET /communication/stats
```

### WebSocket API

**Message Types:**
```typescript
// Incoming messages
interface UserMessage {
  type: 'message';
  user_id: string;
  text: string;
  timestamp: number;
}

// Outgoing messages
interface AgentResponse {
  type: 'agent_response';
  agent_name: string;
  text: string;
  timestamp: number;
}

interface SystemStatus {
  type: 'status_update';
  employees: Employee[];
  active_tasks: Task[];
  file_locks: FileLock[];
}
```

## 🔮 Future Architecture

### Planned Enhancements

**Message Persistence:**
- Database storage for chat history
- Message search and filtering
- Conversation threading
- Export capabilities

**Advanced Agent Features:**
- Learning and adaptation
- Custom agent personalities
- Plugin system for extensions
- Advanced reasoning capabilities

**Collaboration Features:**
- File sharing and version control
- Code review workflows
- Project templates
- Team analytics

**Integration Capabilities:**
- Git integration
- CI/CD pipeline integration
- External API connections
- Webhook support

### Extensibility Points

**Plugin Architecture:**
```python
class PluginManager:
    def register_plugin(self, plugin: Plugin):
        # Plugin validation
        # Capability registration
        # Event subscription
        # Resource allocation
```

**Custom Transports:**
```python
class CustomTransportManager(BaseTransportManager):
    def send_message(self, text: str, sender: str) -> bool:
        # Custom implementation
        pass
    
    def add_message_handler(self, handler: Callable):
        # Custom implementation
        pass
```

---

This technical architecture provides a comprehensive foundation for understanding, maintaining, and extending the OpenCode-Slack system. The modular design ensures scalability, maintainability, and adaptability to future requirements.

*Last updated: August 2025*