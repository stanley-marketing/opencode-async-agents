# WebSocket + React Architecture Specification

## 1. System Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   React Client  │    │  WebSocket       │    │  Agent System   │
│   (Next.js)     │◄──►│  Server          │◄──►│  (Existing)     │
│                 │    │  (Python)        │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
    ┌────▼────┐             ┌────▼────┐             ┌────▼────┐
    │ Chat UI │             │ Message │             │ Agent   │
    │ State   │             │ Router  │             │ Manager │
    │ Mgmt    │             │         │             │         │
    └─────────┘             └─────────┘             └─────────┘
```

### 1.2 Component Responsibilities

#### React Frontend (Next.js)
- **Chat Interface**: Real-time message display and input
- **User Management**: Authentication and role-based access
- **Agent Status**: Live agent status and task tracking
- **File Sharing**: Upload and share files with agents
- **Notifications**: Real-time alerts and mentions

#### WebSocket Server (Python)
- **Connection Management**: Handle client connections and authentication
- **Message Routing**: Route messages between clients and agents
- **Protocol Translation**: Convert between WebSocket and internal message format
- **Rate Limiting**: Enforce user-based message throttling
- **Session Management**: Track user sessions and state

#### Agent System (Existing)
- **No Changes Required**: Existing AgentManager and agents work unchanged
- **Interface Compatibility**: WebSocketManager implements TelegramManager interface
- **Message Processing**: Same ParsedMessage format and handler patterns

## 2. WebSocket Protocol Specification

### 2.1 Connection Establishment

#### Client Connection
```typescript
// Client connects with authentication
const ws = new WebSocket('ws://localhost:8080/ws');

// Send authentication message
ws.send(JSON.stringify({
  type: 'auth',
  data: {
    userId: 'alice',
    token: 'jwt-token-here',
    role: 'developer'
  }
}));
```

#### Server Response
```json
{
  "type": "auth_response",
  "data": {
    "success": true,
    "userId": "alice",
    "sessionId": "session-123",
    "agents": ["alice", "bob", "charlie"]
  }
}
```

### 2.2 Message Types

#### Chat Message
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

#### Agent Response
```json
{
  "type": "agent_response",
  "data": {
    "id": 12346,
    "text": "Got it! I'll review the login component.",
    "sender": "alice",
    "timestamp": "2025-01-10T15:30:05Z",
    "replyTo": 12345,
    "agentStatus": "working"
  }
}
```

#### Status Update
```json
{
  "type": "status_update",
  "data": {
    "userId": "alice",
    "status": "working",
    "currentTask": "Reviewing login component",
    "progress": 25
  }
}
```

#### User Presence
```json
{
  "type": "user_presence",
  "data": {
    "userId": "bob",
    "status": "online",
    "lastSeen": "2025-01-10T15:30:00Z"
  }
}
```

### 2.3 Error Handling

#### Error Response
```json
{
  "type": "error",
  "data": {
    "code": "RATE_LIMITED",
    "message": "Too many messages sent",
    "retryAfter": 30
  }
}
```

## 3. Implementation Details

### 3.1 WebSocket Manager Implementation

```python
# src/chat/websocket_manager.py
import asyncio
import json
import logging
import websockets
from datetime import datetime
from typing import Dict, List, Optional, Callable, Set
from .message_parser import MessageParser, ParsedMessage

logger = logging.getLogger(__name__)

class WebSocketConnection:
    """Represents a single WebSocket connection"""
    
    def __init__(self, websocket, user_id: str, role: str):
        self.websocket = websocket
        self.user_id = user_id
        self.role = role
        self.connected_at = datetime.now()
        self.last_activity = datetime.now()
        
    async def send(self, message: dict):
        """Send message to this connection"""
        try:
            await self.websocket.send(json.dumps(message))
            self.last_activity = datetime.now()
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"Connection closed for user {self.user_id}")
            raise

class WebSocketManager:
    """WebSocket-based communication manager - drop-in replacement for TelegramManager"""
    
    def __init__(self, host="localhost", port=8081):
        self.host = host
        self.port = port
        self.message_parser = MessageParser()
        self.message_handlers: List[Callable[[ParsedMessage], None]] = []
        
        # Connection management
        self.connections: Dict[str, WebSocketConnection] = {}
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
        
        # Rate limiting (reuse TelegramManager logic)
        self.last_message_time = {}
        self.message_count = {}
        
        # Server state
        self.server = None
        self.running = False
        
    def add_message_handler(self, handler: Callable[[ParsedMessage], None]):
        """Add a message handler function - same interface as TelegramManager"""
        self.message_handlers.append(handler)
        
    async def start_server(self):
        """Start the WebSocket server"""
        if self.running:
            logger.warning("WebSocket server already running")
            return
            
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        
        self.server = await websockets.serve(
            self.handle_connection,
            self.host,
            self.port
        )
        
        self.running = True
        logger.info("WebSocket server started successfully")
        
    async def stop_server(self):
        """Stop the WebSocket server"""
        if not self.running:
            return
            
        logger.info("Stopping WebSocket server")
        
        # Close all connections
        for connection in list(self.connections.values()):
            await connection.websocket.close()
            
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            
        self.running = False
        logger.info("WebSocket server stopped")
        
    async def handle_connection(self, websocket, path):
        """Handle new WebSocket connection"""
        logger.info(f"New WebSocket connection from {websocket.remote_address}")
        
        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error handling WebSocket connection: {e}")
        finally:
            await self.cleanup_connection(websocket)
            
    async def handle_message(self, websocket, raw_message: str):
        """Handle incoming WebSocket message"""
        try:
            message_data = json.loads(raw_message)
            message_type = message_data.get('type')
            data = message_data.get('data', {})
            
            if message_type == 'auth':
                await self.handle_auth(websocket, data)
            elif message_type == 'message':
                await self.handle_chat_message(websocket, data)
            elif message_type == 'ping':
                await self.handle_ping(websocket)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
            await self.send_error(websocket, "INVALID_JSON", "Invalid JSON format")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self.send_error(websocket, "INTERNAL_ERROR", str(e))
            
    async def handle_auth(self, websocket, data: dict):
        """Handle user authentication"""
        user_id = data.get('userId')
        role = data.get('role', 'user')
        
        if not user_id:
            await self.send_error(websocket, "MISSING_USER_ID", "User ID required")
            return
            
        # Create connection
        connection = WebSocketConnection(websocket, user_id, role)
        self.connections[user_id] = connection
        
        # Send auth response
        await connection.send({
            'type': 'auth_response',
            'data': {
                'success': True,
                'userId': user_id,
                'sessionId': f"session-{user_id}-{int(datetime.now().timestamp())}",
                'agents': list(self.connections.keys())
            }
        })
        
        # Notify other users
        await self.broadcast_user_presence(user_id, 'online')
        
        logger.info(f"User {user_id} authenticated successfully")
        
    async def handle_chat_message(self, websocket, data: dict):
        """Handle chat message from user"""
        # Find connection
        connection = None
        for conn in self.connections.values():
            if conn.websocket == websocket:
                connection = conn
                break
                
        if not connection:
            await self.send_error(websocket, "NOT_AUTHENTICATED", "Authentication required")
            return
            
        # Check rate limiting
        if not self._can_send_message(connection.user_id):
            await self.send_error(websocket, "RATE_LIMITED", "Too many messages")
            return
            
        # Create ParsedMessage (reuse existing logic)
        message_id = data.get('id', int(datetime.now().timestamp() * 1000))
        text = data.get('text', '')
        mentions = data.get('mentions', [])
        
        parsed_message = ParsedMessage(
            message_id=message_id,
            text=text,
            sender=connection.user_id,
            timestamp=datetime.now(),
            mentions=mentions,
            is_command=text.startswith('/'),
            reply_to=data.get('replyTo')
        )
        
        # Broadcast to all connections
        await self.broadcast_message(parsed_message)
        
        # Notify message handlers (existing agent system)
        for handler in self.message_handlers:
            try:
                handler(parsed_message)
            except Exception as e:
                logger.error(f"Error in message handler: {e}")
                
        self._record_message_sent(connection.user_id)
        
    async def broadcast_message(self, message: ParsedMessage):
        """Broadcast message to all connected clients"""
        message_data = {
            'type': 'message',
            'data': {
                'id': message.message_id,
                'text': message.text,
                'sender': message.sender,
                'timestamp': message.timestamp.isoformat(),
                'mentions': message.mentions,
                'isCommand': message.is_command,
                'replyTo': message.reply_to
            }
        }
        
        # Send to all connections
        disconnected = []
        for user_id, connection in self.connections.items():
            try:
                await connection.send(message_data)
            except websockets.exceptions.ConnectionClosed:
                disconnected.append(user_id)
                
        # Clean up disconnected users
        for user_id in disconnected:
            await self.cleanup_user(user_id)
            
    def send_message(self, text: str, sender_name: str = "system", 
                    reply_to: Optional[int] = None) -> bool:
        """Send message from agent - same interface as TelegramManager"""
        
        # Create message data
        message_data = {
            'type': 'agent_response',
            'data': {
                'id': int(datetime.now().timestamp() * 1000),
                'text': text,
                'sender': sender_name,
                'timestamp': datetime.now().isoformat(),
                'replyTo': reply_to
            }
        }
        
        # Send to all connections (async operation in sync context)
        asyncio.create_task(self._send_to_all_connections(message_data))
        return True
        
    async def _send_to_all_connections(self, message_data: dict):
        """Helper to send message to all connections"""
        disconnected = []
        for user_id, connection in self.connections.items():
            try:
                await connection.send(message_data)
            except websockets.exceptions.ConnectionClosed:
                disconnected.append(user_id)
                
        # Clean up disconnected users
        for user_id in disconnected:
            await self.cleanup_user(user_id)
            
    async def broadcast_user_presence(self, user_id: str, status: str):
        """Broadcast user presence change"""
        presence_data = {
            'type': 'user_presence',
            'data': {
                'userId': user_id,
                'status': status,
                'timestamp': datetime.now().isoformat()
            }
        }
        
        await self._send_to_all_connections(presence_data)
        
    async def send_error(self, websocket, code: str, message: str):
        """Send error message to specific connection"""
        error_data = {
            'type': 'error',
            'data': {
                'code': code,
                'message': message,
                'timestamp': datetime.now().isoformat()
            }
        }
        
        try:
            await websocket.send(json.dumps(error_data))
        except websockets.exceptions.ConnectionClosed:
            pass
            
    async def handle_ping(self, websocket):
        """Handle ping message"""
        pong_data = {
            'type': 'pong',
            'data': {
                'timestamp': datetime.now().isoformat()
            }
        }
        
        try:
            await websocket.send(json.dumps(pong_data))
        except websockets.exceptions.ConnectionClosed:
            pass
            
    async def cleanup_connection(self, websocket):
        """Clean up when connection is closed"""
        # Find and remove connection
        user_to_remove = None
        for user_id, connection in self.connections.items():
            if connection.websocket == websocket:
                user_to_remove = user_id
                break
                
        if user_to_remove:
            await self.cleanup_user(user_to_remove)
            
    async def cleanup_user(self, user_id: str):
        """Clean up user data"""
        if user_id in self.connections:
            del self.connections[user_id]
            
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
            
        # Notify other users
        await self.broadcast_user_presence(user_id, 'offline')
        
        logger.info(f"Cleaned up user {user_id}")
        
    def _can_send_message(self, sender_name: str) -> bool:
        """Check rate limiting - reuse TelegramManager logic"""
        from datetime import timedelta
        from src.chat.chat_config import config
        
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        # Clean old message counts
        if sender_name in self.message_count:
            self.message_count[sender_name] = [
                timestamp for timestamp in self.message_count[sender_name]
                if timestamp > hour_ago
            ]
        else:
            self.message_count[sender_name] = []
            
        # Check rate limit
        if len(self.message_count[sender_name]) >= config.max_messages_per_hour:
            return False
            
        # Check minimum delay between messages
        if sender_name in self.last_message_time:
            time_since_last = now - self.last_message_time[sender_name]
            if time_since_last.total_seconds() < config.response_delay_seconds:
                return False
                
        return True
        
    def _record_message_sent(self, sender_name: str):
        """Record message for rate limiting"""
        now = datetime.now()
        self.last_message_time[sender_name] = now
        
        if sender_name not in self.message_count:
            self.message_count[sender_name] = []
        self.message_count[sender_name].append(now)
        
    def is_connected(self) -> bool:
        """Check if server is running"""
        return self.running and len(self.connections) > 0
```

### 3.2 React Frontend Implementation

```typescript
// types/chat.ts
export interface ChatMessage {
  id: number;
  text: string;
  sender: string;
  timestamp: Date;
  mentions: string[];
  isCommand: boolean;
  replyTo?: number;
}

export interface User {
  id: string;
  role: string;
  status: 'online' | 'offline' | 'working';
  lastSeen?: Date;
}

export interface AgentStatus {
  userId: string;
  status: 'idle' | 'working' | 'stuck' | 'completed';
  currentTask?: string;
  progress?: number;
}
```

```typescript
// hooks/useChatWebSocket.ts
import { useEffect, useState, useCallback, useRef } from 'react';
import { ChatMessage, User, AgentStatus } from '../types/chat';

interface WebSocketMessage {
  type: string;
  data: any;
}

export const useChatWebSocket = (userId: string, role: string) => {
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [agentStatuses, setAgentStatuses] = useState<AgentStatus[]>([]);
  const [error, setError] = useState<string | null>(null);
  
  const ws = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  
  const connect = useCallback(() => {
    try {
      ws.current = new WebSocket('ws://localhost:8081');
      
      ws.current.onopen = () => {
        console.log('WebSocket connected');
        setConnected(true);
        setError(null);
        reconnectAttempts.current = 0;
        
        // Send authentication
        ws.current?.send(JSON.stringify({
          type: 'auth',
          data: { userId, role }
        }));
      };
      
      ws.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          handleMessage(message);
        } catch (err) {
          console.error('Error parsing message:', err);
        }
      };
      
      ws.current.onclose = () => {
        console.log('WebSocket disconnected');
        setConnected(false);
        
        // Attempt reconnection
        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current++;
          setTimeout(() => {
            console.log(`Reconnection attempt ${reconnectAttempts.current}`);
            connect();
          }, 1000 * reconnectAttempts.current);
        } else {
          setError('Connection lost. Please refresh the page.');
        }
      };
      
      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('Connection error occurred');
      };
      
    } catch (err) {
      console.error('Error creating WebSocket:', err);
      setError('Failed to connect to server');
    }
  }, [userId, role]);
  
  const handleMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case 'auth_response':
        if (message.data.success) {
          console.log('Authentication successful');
          // Load initial data
          setUsers(message.data.agents?.map((id: string) => ({
            id,
            role: 'unknown',
            status: 'online' as const
          })) || []);
        } else {
          setError('Authentication failed');
        }
        break;
        
      case 'message':
      case 'agent_response':
        const chatMessage: ChatMessage = {
          id: message.data.id,
          text: message.data.text,
          sender: message.data.sender,
          timestamp: new Date(message.data.timestamp),
          mentions: message.data.mentions || [],
          isCommand: message.data.isCommand || false,
          replyTo: message.data.replyTo
        };
        
        setMessages(prev => [...prev, chatMessage]);
        break;
        
      case 'user_presence':
        setUsers(prev => prev.map(user => 
          user.id === message.data.userId
            ? { ...user, status: message.data.status, lastSeen: new Date(message.data.timestamp) }
            : user
        ));
        break;
        
      case 'status_update':
        setAgentStatuses(prev => {
          const existing = prev.find(s => s.userId === message.data.userId);
          const updated: AgentStatus = {
            userId: message.data.userId,
            status: message.data.status,
            currentTask: message.data.currentTask,
            progress: message.data.progress
          };
          
          if (existing) {
            return prev.map(s => s.userId === message.data.userId ? updated : s);
          } else {
            return [...prev, updated];
          }
        });
        break;
        
      case 'error':
        setError(message.data.message);
        break;
        
      case 'pong':
        // Handle ping/pong for connection health
        break;
        
      default:
        console.warn('Unknown message type:', message.type);
    }
  }, []);
  
  const sendMessage = useCallback((text: string, mentions: string[] = [], replyTo?: number) => {
    if (!connected || !ws.current) {
      setError('Not connected to server');
      return false;
    }
    
    const message = {
      type: 'message',
      data: {
        id: Date.now(),
        text,
        mentions,
        replyTo
      }
    };
    
    try {
      ws.current.send(JSON.stringify(message));
      return true;
    } catch (err) {
      console.error('Error sending message:', err);
      setError('Failed to send message');
      return false;
    }
  }, [connected]);
  
  const disconnect = useCallback(() => {
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
    setConnected(false);
  }, []);
  
  // Ping/pong for connection health
  useEffect(() => {
    if (!connected) return;
    
    const interval = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000); // Ping every 30 seconds
    
    return () => clearInterval(interval);
  }, [connected]);
  
  // Connect on mount
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);
  
  return {
    connected,
    messages,
    users,
    agentStatuses,
    error,
    sendMessage,
    connect,
    disconnect
  };
};
```

```tsx
// components/ChatInterface.tsx
import React, { useState, useRef, useEffect } from 'react';
import { useChatWebSocket } from '../hooks/useChatWebSocket';
import { ChatMessage } from '../types/chat';

interface ChatInterfaceProps {
  userId: string;
  role: string;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ userId, role }) => {
  const [inputText, setInputText] = useState('');
  const [replyTo, setReplyTo] = useState<number | undefined>();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const {
    connected,
    messages,
    users,
    agentStatuses,
    error,
    sendMessage
  } = useChatWebSocket(userId, role);
  
  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  const handleSendMessage = () => {
    if (!inputText.trim()) return;
    
    // Extract mentions
    const mentions = extractMentions(inputText);
    
    if (sendMessage(inputText, mentions, replyTo)) {
      setInputText('');
      setReplyTo(undefined);
    }
  };
  
  const extractMentions = (text: string): string[] => {
    const mentionRegex = /@(\w+)/g;
    const mentions: string[] = [];
    let match;
    
    while ((match = mentionRegex.exec(text)) !== null) {
      mentions.push(match[1]);
    }
    
    return mentions;
  };
  
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };
  
  const formatTimestamp = (timestamp: Date): string => {
    return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };
  
  const renderMessage = (message: ChatMessage) => {
    const isAgent = users.some(u => u.id === message.sender);
    const agentStatus = agentStatuses.find(s => s.userId === message.sender);
    
    return (
      <div
        key={message.id}
        className={`message ${isAgent ? 'agent-message' : 'user-message'}`}
      >
        <div className="message-header">
          <span className="sender">
            {message.sender}
            {isAgent && (
              <span className={`status-indicator ${agentStatus?.status || 'idle'}`}>
                {agentStatus?.status || 'idle'}
              </span>
            )}
          </span>
          <span className="timestamp">{formatTimestamp(message.timestamp)}</span>
        </div>
        
        <div className="message-content">
          {message.replyTo && (
            <div className="reply-indicator">
              Replying to message #{message.replyTo}
            </div>
          )}
          
          <div className="message-text">
            {renderMessageText(message.text, message.mentions)}
          </div>
          
          {message.mentions.length > 0 && (
            <div className="mentions">
              Mentions: {message.mentions.map(m => `@${m}`).join(', ')}
            </div>
          )}
        </div>
        
        <div className="message-actions">
          <button onClick={() => setReplyTo(message.id)}>Reply</button>
        </div>
      </div>
    );
  };
  
  const renderMessageText = (text: string, mentions: string[]) => {
    // Highlight mentions
    let highlightedText = text;
    mentions.forEach(mention => {
      const regex = new RegExp(`@${mention}`, 'gi');
      highlightedText = highlightedText.replace(
        regex,
        `<span class="mention">@${mention}</span>`
      );
    });
    
    return <div dangerouslySetInnerHTML={{ __html: highlightedText }} />;
  };
  
  return (
    <div className="chat-interface">
      {/* Connection Status */}
      <div className={`connection-status ${connected ? 'connected' : 'disconnected'}`}>
        {connected ? '🟢 Connected' : '🔴 Disconnected'}
        {error && <span className="error"> - {error}</span>}
      </div>
      
      {/* User List */}
      <div className="sidebar">
        <h3>Users & Agents</h3>
        <div className="user-list">
          {users.map(user => {
            const agentStatus = agentStatuses.find(s => s.userId === user.id);
            return (
              <div key={user.id} className={`user-item ${user.status}`}>
                <span className="user-name">{user.id}</span>
                <span className="user-role">({user.role})</span>
                {agentStatus && (
                  <div className="agent-status">
                    <span className={`status ${agentStatus.status}`}>
                      {agentStatus.status}
                    </span>
                    {agentStatus.currentTask && (
                      <div className="current-task">
                        {agentStatus.currentTask}
                        {agentStatus.progress && (
                          <div className="progress-bar">
                            <div 
                              className="progress-fill"
                              style={{ width: `${agentStatus.progress}%` }}
                            />
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
      
      {/* Messages */}
      <div className="messages-container">
        <div className="messages">
          {messages.map(renderMessage)}
          <div ref={messagesEndRef} />
        </div>
        
        {/* Reply Indicator */}
        {replyTo && (
          <div className="reply-indicator">
            Replying to message #{replyTo}
            <button onClick={() => setReplyTo(undefined)}>Cancel</button>
          </div>
        )}
        
        {/* Input */}
        <div className="message-input">
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type a message... Use @username to mention someone"
            disabled={!connected}
          />
          <button 
            onClick={handleSendMessage}
            disabled={!connected || !inputText.trim()}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
};
```

This architecture provides:

1. **Drop-in Compatibility**: WebSocketManager implements the same interface as TelegramManager
2. **Real-time Communication**: WebSocket-based bidirectional communication
3. **Rich UI**: React-based chat interface with user presence, agent status, and mentions
4. **Robust Connection Management**: Automatic reconnection and error handling
5. **Rate Limiting**: Preserves existing rate limiting logic
6. **Message Compatibility**: Uses existing ParsedMessage format
7. **Agent Integration**: No changes required to existing agent system

The implementation maintains all existing patterns while providing a modern, testable, and user-friendly interface.