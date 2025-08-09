# Telegram to WebSocket + React Migration Plan

## Executive Summary

This document outlines a comprehensive migration strategy to transform the current Telegram-based employee communication system into a modern Next.js + React + WebSocket client. The migration follows the brownfield UI workflow pattern from `.bmad-core/workflows/brownfield-ui.yaml` to ensure safe integration while maintaining existing agent communication patterns.

## 1. Current System Analysis

### 1.1 Architecture Overview

The current system uses a Telegram-based communication layer with the following key components:

#### Core Communication Components
- **TelegramManager** (`src/chat/telegram_manager.py`): Handles bot communication, message sending/receiving, polling
- **ParsedMessage** (`src/chat/message_parser.py`): Message abstraction layer with mentions, commands, timestamps
- **BaseCommunicationAgent** (`src/agents/base_communication_agent.py`): Interface for all communication agents
- **AgentManager** (`src/agents/agent_manager.py`): Coordinates agent interactions and message routing

#### Integration Points
- **Multiple Servers**: All servers (`cli_server.py`, `enhanced_server.py`, `server.py`, etc.) instantiate TelegramManager
- **Dependency Injection**: AgentManager takes TelegramManager as constructor parameter
- **Message Handlers**: TelegramManager uses callback pattern for message handling
- **Rate Limiting**: Built-in message throttling and user management

#### Current Message Flow
```
Telegram API → TelegramManager → MessageParser → ParsedMessage → AgentManager → CommunicationAgent
```

### 1.2 Key Abstractions to Preserve

1. **ParsedMessage**: Well-designed message abstraction
2. **BaseCommunicationAgent**: Clean agent interface
3. **Message Handler Pattern**: Callback-based message routing
4. **Rate Limiting**: User-based throttling mechanisms
5. **Agent Lifecycle**: Creation, task assignment, status tracking

### 1.3 Current Limitations

1. **External Dependency**: Requires Telegram bot setup and external service
2. **Testing Complexity**: Difficult to E2E test without real Telegram integration
3. **User Experience**: Limited to Telegram interface, no rich UI
4. **Deployment Complexity**: Webhook/polling configuration challenges

## 2. Migration Strategy (Brownfield Pattern)

Following the brownfield UI workflow pattern:

### 2.1 Phase 1: UI Analysis & Planning
- **Agent**: architect
- **Action**: analyze existing project and document current system
- **Creates**: System analysis documents

### 2.2 Phase 2: Product Requirements
- **Agent**: pm  
- **Creates**: prd.md
- **Focus**: WebSocket + React frontend requirements with existing system integration

### 2.3 Phase 3: Frontend Specification
- **Agent**: ux-expert
- **Creates**: front-end-spec.md
- **Focus**: Real-time chat UI that mirrors current Telegram functionality

### 2.4 Phase 4: Architecture Design
- **Agent**: architect
- **Creates**: architecture.md
- **Focus**: WebSocket transport layer with minimal disruption to existing agents

### 2.5 Phase 5: Implementation
- **Agent**: dev
- **Action**: Implement in phases with parallel operation capability

## 3. Technical Architecture

### 3.1 New Components

#### WebSocket Communication Manager
```python
class WebSocketManager:
    """Drop-in replacement for TelegramManager"""
    
    def __init__(self):
        self.message_parser = MessageParser()  # Reuse existing
        self.message_handlers: List[Callable[[ParsedMessage], None]] = []
        self.connected_clients: Dict[str, WebSocketConnection] = {}
        
    def add_message_handler(self, handler: Callable[[ParsedMessage], None]):
        """Same interface as TelegramManager"""
        
    def send_message(self, text: str, sender_name: str = "system", 
                    reply_to: Optional[int] = None) -> bool:
        """Same interface as TelegramManager"""
        
    def start_server(self):
        """Start WebSocket server instead of polling"""
```

#### React Frontend Components
```typescript
// Core chat interface
interface ChatMessage {
  id: number;
  text: string;
  sender: string;
  timestamp: Date;
  mentions: string[];
  isCommand: boolean;
  replyTo?: number;
}

// Real-time message handling
const useChatWebSocket = () => {
  // WebSocket connection management
  // Message sending/receiving
  // Connection state management
}
```

### 3.2 Migration Architecture

#### Dual Transport Support
```python
class CommunicationManager:
    """Unified interface supporting both Telegram and WebSocket"""
    
    def __init__(self, transport_type: str = "websocket"):
        if transport_type == "telegram":
            self.transport = TelegramManager()
        elif transport_type == "websocket":
            self.transport = WebSocketManager()
        else:
            raise ValueError(f"Unsupported transport: {transport_type}")
            
    def add_message_handler(self, handler):
        return self.transport.add_message_handler(handler)
        
    def send_message(self, text, sender_name="system", reply_to=None):
        return self.transport.send_message(text, sender_name, reply_to)
```

#### Server Integration
```python
# Minimal changes to existing servers
class EnhancedOpencodeSlackServer:
    def __init__(self, transport="websocket"):
        # ... existing initialization ...
        
        if transport == "telegram":
            self.communication_manager = TelegramManager()
        else:
            self.communication_manager = WebSocketManager()
            
        self.agent_manager = AgentManager(self.file_manager, self.communication_manager)
```

### 3.3 WebSocket Protocol Design

#### Message Format
```json
{
  "type": "message",
  "data": {
    "id": 12345,
    "text": "@alice please review the login component",
    "sender": "bob",
    "timestamp": "2025-01-10T15:30:00Z",
    "mentions": ["alice"],
    "isCommand": false,
    "replyTo": null
  }
}
```

#### Connection Management
```json
{
  "type": "user_connected",
  "data": {
    "userId": "alice",
    "role": "developer",
    "expertise": ["react", "typescript"]
  }
}
```

## 4. Implementation Plan

### 4.1 Phase 1: Foundation (Week 1-2)

#### Step 1: Create WebSocket Manager
- Implement `WebSocketManager` class with same interface as `TelegramManager`
- Reuse existing `MessageParser` and `ParsedMessage`
- Add WebSocket server using `websockets` library
- Implement basic message routing

#### Step 2: Create Communication Abstraction
- Implement `CommunicationManager` wrapper
- Add transport selection mechanism
- Ensure backward compatibility with existing code

#### Step 3: Basic React Frontend
- Set up Next.js project structure
- Create basic chat interface components
- Implement WebSocket client connection
- Add message display and input functionality

### 4.2 Phase 2: Integration (Week 3-4)

#### Step 4: Server Integration
- Modify server initialization to support transport selection
- Add WebSocket endpoints to Flask servers
- Implement connection management and user authentication
- Add environment variable configuration

#### Step 5: Agent Integration
- Test AgentManager with WebSocketManager
- Verify message handler callbacks work correctly
- Ensure rate limiting and user management functions
- Test agent creation and task assignment flows

#### Step 6: Frontend Enhancement
- Add user authentication and role display
- Implement @mention functionality with autocomplete
- Add message history and persistence
- Create agent status indicators

### 4.3 Phase 3: Feature Parity (Week 5-6)

#### Step 7: Advanced Features
- Implement command parsing and execution
- Add file upload and sharing capabilities
- Create task assignment and tracking UI
- Add notification system

#### Step 8: Real-time Features
- Implement typing indicators
- Add online/offline status
- Create real-time agent status updates
- Add message reactions and threading

#### Step 9: Testing & Validation
- Create comprehensive E2E test suite
- Test agent communication patterns
- Validate message parsing and routing
- Performance testing with multiple users

### 4.4 Phase 4: Migration & Deployment (Week 7-8)

#### Step 10: Parallel Operation
- Deploy both systems simultaneously
- Add configuration toggle for transport selection
- Create migration scripts for existing data
- Monitor system performance and stability

#### Step 11: Gradual Migration
- Migrate development environment first
- Test with subset of users
- Gather feedback and iterate
- Full production migration

#### Step 12: Cleanup
- Remove Telegram dependencies (optional)
- Update documentation
- Archive old configuration files
- Optimize WebSocket performance

## 5. E2E Testing Strategy

### 5.1 Test Architecture

#### WebSocket Test Client
```python
class WebSocketTestClient:
    """Test client for E2E testing"""
    
    async def connect(self, user_id: str, role: str):
        """Connect as specific user"""
        
    async def send_message(self, text: str, mentions: List[str] = None):
        """Send test message"""
        
    async def wait_for_response(self, timeout: int = 10):
        """Wait for agent response"""
```

#### Integration Test Suite
```python
class TestAgentCommunication:
    """E2E tests for agent communication"""
    
    async def test_task_assignment_flow(self):
        # Connect as manager
        # Send task assignment to agent
        # Verify agent acknowledgment
        # Check task creation in system
        
    async def test_help_request_flow(self):
        # Connect as agent
        # Send help request
        # Verify other agents can respond
        # Check help tracking
        
    async def test_multi_user_chat(self):
        # Connect multiple users
        # Test concurrent messaging
        # Verify message ordering
        # Check rate limiting
```

### 5.2 Test Scenarios

1. **Basic Communication**
   - User sends message
   - Agent receives and responds
   - Message history persistence

2. **Task Assignment**
   - Manager assigns task to agent
   - Agent acknowledges task
   - Task tracking integration

3. **Help Requests**
   - Agent requests help
   - Other agents offer assistance
   - Help resolution tracking

4. **Multi-user Scenarios**
   - Multiple users online
   - Concurrent message handling
   - Rate limiting enforcement

5. **Error Handling**
   - Connection failures
   - Message parsing errors
   - Agent unavailability

### 5.3 Performance Testing

#### Load Testing
- Simulate 50+ concurrent users
- Test message throughput
- Monitor memory usage
- Validate connection stability

#### Stress Testing
- High-frequency message sending
- Large message payloads
- Connection drop/reconnect scenarios
- Agent overload conditions

## 6. Risk Mitigation

### 6.1 Technical Risks

1. **WebSocket Connection Stability**
   - **Risk**: Connection drops, reconnection issues
   - **Mitigation**: Implement robust reconnection logic, heartbeat mechanism

2. **Message Ordering**
   - **Risk**: Out-of-order message delivery
   - **Mitigation**: Add message sequencing, client-side ordering

3. **Performance Degradation**
   - **Risk**: Slower than Telegram integration
   - **Mitigation**: Optimize WebSocket handling, implement message batching

### 6.2 Migration Risks

1. **Data Loss**
   - **Risk**: Message history or agent state loss
   - **Mitigation**: Comprehensive backup strategy, parallel operation period

2. **User Adoption**
   - **Risk**: Users prefer Telegram interface
   - **Mitigation**: Feature parity first, then enhancement, gradual migration

3. **Integration Issues**
   - **Risk**: Existing agent patterns break
   - **Mitigation**: Extensive testing, interface compatibility layer

## 7. Success Metrics

### 7.1 Technical Metrics
- **Message Latency**: < 100ms for local messages
- **Connection Uptime**: > 99.9%
- **Test Coverage**: > 90% for communication layer
- **Performance**: Handle 100+ concurrent users

### 7.2 User Experience Metrics
- **Feature Parity**: 100% of Telegram features replicated
- **Response Time**: Faster than Telegram for task assignment
- **Error Rate**: < 1% message delivery failures
- **User Satisfaction**: Improved UI/UX over Telegram

### 7.3 Development Metrics
- **E2E Test Coverage**: 100% of user workflows
- **Deployment Time**: < 5 minutes for updates
- **Bug Resolution**: < 24 hours for critical issues
- **Documentation**: Complete API and user guides

## 8. Timeline Summary

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| 1: Foundation | 2 weeks | WebSocketManager, Basic React UI |
| 2: Integration | 2 weeks | Server integration, Agent compatibility |
| 3: Feature Parity | 2 weeks | Advanced features, Real-time capabilities |
| 4: Migration | 2 weeks | Deployment, Testing, Migration |

**Total Duration**: 8 weeks

## 9. Next Steps

1. **Immediate Actions**:
   - Set up Next.js project structure
   - Create WebSocketManager skeleton
   - Design React component architecture

2. **Week 1 Goals**:
   - Working WebSocket server
   - Basic React chat interface
   - Message parsing integration

3. **Validation Points**:
   - End of Week 2: Basic communication working
   - End of Week 4: Agent integration complete
   - End of Week 6: Feature parity achieved
   - End of Week 8: Production ready

This migration plan ensures a smooth transition from Telegram to WebSocket + React while preserving all existing agent communication patterns and providing a superior user experience for development teams.