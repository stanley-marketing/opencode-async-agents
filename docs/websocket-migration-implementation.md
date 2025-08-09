# WebSocket Migration Implementation Guide

## Overview

This document provides a complete implementation guide for migrating from Telegram to WebSocket + React communication in the OpenCode-Slack system. The implementation maintains full backward compatibility while enabling modern real-time web communication.

## Architecture Summary

### Core Components

1. **WebSocketManager** (`src/chat/websocket_manager.py`)
   - Drop-in replacement for TelegramManager
   - Identical interface for seamless integration
   - Real-time bidirectional communication
   - Connection management and heartbeat

2. **CommunicationManager** (`src/chat/communication_manager.py`)
   - Unified interface supporting both transports
   - Auto-detection of transport type
   - Runtime transport switching
   - Graceful fallback mechanisms

3. **WebSocket Server** (`src/server_websocket.py`)
   - Enhanced server with WebSocket support
   - Dual HTTP + WebSocket endpoints
   - Transport switching API
   - Comprehensive monitoring

4. **React Frontend** (`frontend/`)
   - Real-time chat interface
   - TypeScript implementation
   - WebSocket hooks and state management
   - Agent communication UI

5. **Testing Framework** (`tests/test_websocket_integration.py`)
   - Comprehensive E2E tests
   - Agent communication validation
   - Performance and load testing
   - No external dependencies

## Implementation Details

### 1. WebSocket Transport Layer

#### WebSocketManager Interface Compatibility
```python
# Identical interface to TelegramManager
class WebSocketManager:
    def add_message_handler(self, handler: Callable[[ParsedMessage], None])
    def start_polling(self)  # Starts WebSocket server
    def stop_polling(self)   # Stops WebSocket server
    def send_message(self, text: str, sender_name: str = "system", reply_to: Optional[int] = None) -> bool
    def is_connected(self) -> bool
```

#### Key Features
- **Message Format Compatibility**: Converts WebSocket messages to ParsedMessage format
- **Rate Limiting**: Same rate limiting logic as Telegram
- **Connection Management**: Automatic reconnection and heartbeat
- **User Authentication**: WebSocket authentication flow
- **Broadcast Messaging**: Real-time message distribution

### 2. Unified Communication Layer

#### Transport Auto-Detection
```python
def _detect_transport_type(self) -> str:
    # 1. Check OPENCODE_TRANSPORT environment variable
    # 2. Check OPENCODE_SAFE_MODE (prefers WebSocket)
    # 3. Check Telegram configuration
    # 4. Default to WebSocket
```

#### Runtime Transport Switching
```python
# Switch between transports without restart
comm_manager.switch_transport('websocket', host='localhost', port=8765)
```

### 3. Server Integration

#### Enhanced Server Features
- **Dual Protocol Support**: HTTP API + WebSocket real-time
- **Transport Management**: Switch transports via API
- **Health Monitoring**: WebSocket connection status
- **CORS Configuration**: React development support

#### New API Endpoints
```
GET  /communication/info     - Get transport information
POST /communication/switch   - Switch transport type
GET  /communication/stats    - Get communication statistics
```

### 4. React Frontend Architecture

#### Component Structure
```
frontend/src/
├── components/
│   └── Chat/
│       ├── ChatInterface.tsx      # Main chat component
│       ├── MessageList.tsx        # Message display
│       ├── MessageItem.tsx        # Individual messages
│       ├── MessageInput.tsx       # Input with mentions
│       ├── UserList.tsx          # Online users
│       └── ConnectionStatus.tsx   # Connection indicator
├── hooks/
│   └── useWebSocket.ts           # WebSocket connection hook
├── stores/
│   └── chatStore.ts              # Zustand state management
└── types/
    └── chat.ts                   # TypeScript definitions
```

#### Key Features
- **Real-time Messaging**: Instant message delivery
- **@Mention Support**: Autocomplete and highlighting
- **Typing Indicators**: Live typing status
- **Connection Management**: Auto-reconnection
- **Message Threading**: Reply functionality
- **Agent Status**: Online/offline indicators

### 5. Testing Framework

#### Test Categories
1. **Basic Communication**: Connection, authentication, messaging
2. **Agent Integration**: Mentions, task assignment, help requests
3. **Message Parsing**: Commands, mentions, replies
4. **Error Handling**: Invalid auth, connection recovery
5. **Performance**: High-frequency messages, concurrent users

#### Test Client
```python
class WebSocketTestClient:
    async def connect(self)
    async def send_message(self, text: str, reply_to: Optional[int] = None)
    async def wait_for_message(self, timeout: int = 10) -> Optional[Dict]
    async def send_typing(self, is_typing: bool)
```

## Migration Process

### 1. Automated Migration Script

```bash
# Run migration with default settings
python scripts/migrate_to_websocket.py

# Custom configuration
python scripts/migrate_to_websocket.py --host 0.0.0.0 --port 8765

# Test mode (no rollback on failure)
python scripts/migrate_to_websocket.py --test-mode

# Rollback migration
python scripts/migrate_to_websocket.py --rollback
```

### 2. Migration Steps

1. **Backup Configuration**: Save current Telegram settings
2. **Test WebSocket**: Verify WebSocket server functionality
3. **Update Environment**: Set WebSocket transport variables
4. **Test Communication**: Validate agent communication
5. **Update Scripts**: Modify startup scripts
6. **Create Frontend Config**: Generate React configuration

### 3. Environment Configuration

```bash
# .env file updates
OPENCODE_TRANSPORT=websocket
WEBSOCKET_HOST=localhost
WEBSOCKET_PORT=8765
OPENCODE_SAFE_MODE=false
```

## Deployment Guide

### 1. Server Deployment

#### Start WebSocket Server
```bash
# Development
python src/server_websocket.py

# Production
python src/server_websocket.py --host 0.0.0.0 --port 8080 --websocket-port 8765
```

#### Docker Deployment
```yaml
# docker-compose.yml
services:
  opencode-slack:
    ports:
      - "8080:8080"    # HTTP API
      - "8765:8765"    # WebSocket
    environment:
      - OPENCODE_TRANSPORT=websocket
      - WEBSOCKET_HOST=0.0.0.0
      - WEBSOCKET_PORT=8765
```

### 2. Frontend Deployment

#### Development
```bash
cd frontend
npm install
npm run dev
```

#### Production Build
```bash
cd frontend
npm run build
npm start
```

#### Environment Configuration
```bash
# frontend/.env.local
NEXT_PUBLIC_WEBSOCKET_URL=ws://localhost:8765
NEXT_PUBLIC_API_URL=http://localhost:8080
```

### 3. Nginx Configuration

```nginx
# WebSocket proxy
location /ws {
    proxy_pass http://localhost:8765;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
}

# API proxy
location /api {
    proxy_pass http://localhost:8080;
    proxy_set_header Host $host;
}
```

## Testing and Validation

### 1. Run Integration Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio websockets

# Run WebSocket tests
python -m pytest tests/test_websocket_integration.py -v

# Run specific test categories
python -m pytest tests/test_websocket_integration.py::TestAgentCommunication -v
```

### 2. Manual Testing Checklist

- [ ] WebSocket server starts successfully
- [ ] React frontend connects to WebSocket
- [ ] Messages send and receive correctly
- [ ] @mentions work with autocomplete
- [ ] Agents respond to mentions
- [ ] Task assignment flow works
- [ ] Help requests generate responses
- [ ] Typing indicators function
- [ ] Connection recovery works
- [ ] Multiple users can chat simultaneously

### 3. Performance Validation

```bash
# Load testing with multiple clients
python tests/test_websocket_integration.py::TestPerformance::test_concurrent_users

# High-frequency message testing
python tests/test_websocket_integration.py::TestPerformance::test_high_frequency_messages
```

## Monitoring and Maintenance

### 1. Health Monitoring

```bash
# Check server health
curl http://localhost:8080/health

# Check communication status
curl http://localhost:8080/communication/info

# Get communication statistics
curl http://localhost:8080/communication/stats
```

### 2. Log Monitoring

```bash
# Server logs
tail -f logs/server.log

# WebSocket connection logs
grep "WebSocket" logs/server.log

# Agent communication logs
grep "agent" logs/server.log
```

### 3. Performance Metrics

- **Connection Count**: Number of active WebSocket connections
- **Message Throughput**: Messages per second
- **Response Time**: Agent response latency
- **Error Rate**: Connection failures and message errors

## Troubleshooting

### Common Issues

1. **WebSocket Connection Fails**
   - Check firewall settings for port 8765
   - Verify WEBSOCKET_HOST and WEBSOCKET_PORT
   - Check server logs for binding errors

2. **Agents Not Responding**
   - Verify agent manager initialization
   - Check message handler registration
   - Validate ParsedMessage format conversion

3. **Frontend Connection Issues**
   - Check CORS configuration
   - Verify WebSocket URL in frontend config
   - Check browser console for errors

4. **Performance Issues**
   - Monitor connection count
   - Check message queue size
   - Validate rate limiting settings

### Debug Commands

```bash
# Test WebSocket connection
wscat -c ws://localhost:8765

# Check server processes
ps aux | grep python

# Monitor network connections
netstat -an | grep 8765

# Test API endpoints
curl -X POST http://localhost:8080/communication/switch \
  -H "Content-Type: application/json" \
  -d '{"transport_type": "websocket"}'
```

## Rollback Procedure

### 1. Automatic Rollback

```bash
# Use migration script rollback
python scripts/migrate_to_websocket.py --rollback
```

### 2. Manual Rollback

1. Restore backed up configuration files
2. Set `OPENCODE_TRANSPORT=telegram`
3. Restart server with original command
4. Verify Telegram functionality

### 3. Rollback Validation

- [ ] Telegram bot responds to messages
- [ ] Agent mentions work in Telegram
- [ ] Task assignment functions
- [ ] Server health check passes

## Future Enhancements

### 1. Planned Features

- **Message Persistence**: Database storage for chat history
- **File Sharing**: Upload and share files in chat
- **Voice Messages**: Audio message support
- **Video Calls**: WebRTC integration for video communication
- **Mobile App**: React Native mobile client

### 2. Performance Optimizations

- **Message Batching**: Batch multiple messages for efficiency
- **Connection Pooling**: Optimize WebSocket connection management
- **Caching**: Redis cache for frequently accessed data
- **Load Balancing**: Multiple WebSocket server instances

### 3. Security Enhancements

- **Authentication**: JWT token-based authentication
- **Encryption**: End-to-end message encryption
- **Rate Limiting**: Advanced rate limiting per user
- **Audit Logging**: Comprehensive audit trail

## Conclusion

This WebSocket migration implementation provides a complete, production-ready solution for transitioning from Telegram to modern web-based communication. The architecture maintains full backward compatibility while enabling rich real-time features and improved user experience.

The implementation includes:
- ✅ Drop-in replacement for TelegramManager
- ✅ Unified communication interface
- ✅ Complete React frontend
- ✅ Comprehensive testing framework
- ✅ Automated migration tools
- ✅ Production deployment guide

The system is ready for immediate deployment and provides a solid foundation for future enhancements.