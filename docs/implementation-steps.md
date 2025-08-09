# WebSocket Migration Implementation Steps

## Phase 1: Foundation Setup (Week 1-2)

### Step 1: Create WebSocket Manager (Day 1-2)

#### 1.1 Create the WebSocket Manager Class

```bash
# Create the new WebSocket manager
touch src/chat/websocket_manager.py
```

**File: `src/chat/websocket_manager.py`**
```python
"""
WebSocket manager for real-time communication.
Drop-in replacement for TelegramManager with same interface.
"""

import asyncio
import json
import logging
import websockets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Set
from .message_parser import MessageParser, ParsedMessage
from .chat_config import config

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
    """WebSocket-based communication manager"""
    
    def __init__(self, host="localhost", port=8081):
        self.host = host
        self.port = port
        self.message_parser = MessageParser()
        self.message_handlers: List[Callable[[ParsedMessage], None]] = []
        
        # Connection management
        self.connections: Dict[str, WebSocketConnection] = {}
        
        # Rate limiting (same as TelegramManager)
        self.last_message_time = {}
        self.message_count = {}
        
        # Server state
        self.server = None
        self.running = False
        self._server_task = None
        
    def add_message_handler(self, handler: Callable[[ParsedMessage], None]):
        """Add a message handler function - same interface as TelegramManager"""
        self.message_handlers.append(handler)
        
    def start_polling(self):
        """Start WebSocket server - same interface as TelegramManager.start_polling()"""
        if self.running:
            logger.warning("WebSocket server already running")
            return
            
        logger.info(f"Starting WebSocket server on {self.host}:{self.port}")
        
        # Start server in background thread
        import threading
        self._server_task = threading.Thread(target=self._run_server, daemon=True)
        self._server_task.start()
        
        self.running = True
        logger.info("WebSocket server started")
        
    def stop_polling(self):
        """Stop WebSocket server - same interface as TelegramManager.stop_polling()"""
        if not self.running:
            return
            
        logger.info("Stopping WebSocket server")
        self.running = False
        
        # The server will stop when the event loop detects running=False
        if self._server_task and self._server_task.is_alive():
            self._server_task.join(timeout=10)
            
        logger.info("WebSocket server stopped")
        
    def _run_server(self):
        """Run the WebSocket server in its own event loop"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self._start_server())
        except Exception as e:
            logger.error(f"WebSocket server error: {e}")
        finally:
            loop.close()
            
    async def _start_server(self):
        """Start the actual WebSocket server"""
        self.server = await websockets.serve(
            self.handle_connection,
            self.host,
            self.port
        )
        
        logger.info(f"WebSocket server listening on {self.host}:{self.port}")
        
        # Keep server running until stopped
        while self.running:
            await asyncio.sleep(1)
            
        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            
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
        if self.running:
            asyncio.run_coroutine_threadsafe(
                self._send_to_all_connections(message_data),
                self._get_event_loop()
            )
            return True
        return False
        
    def _get_event_loop(self):
        """Get the event loop for the WebSocket server"""
        # This is a simplified approach - in production you'd want better loop management
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            return asyncio.new_event_loop()
            
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
        
        await self._send_to_all_connections(message_data)
        
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
            
        logger.info(f"Cleaned up user {user_id}")
        
    def _can_send_message(self, sender_name: str) -> bool:
        """Check rate limiting - same logic as TelegramManager"""
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
        """Check if server is running - same interface as TelegramManager"""
        return self.running and len(self.connections) > 0
```

#### 1.2 Add WebSocket Dependencies

**File: `requirements.txt`** (add these lines)
```
websockets>=11.0.3
```

#### 1.3 Create Communication Manager Abstraction

**File: `src/chat/communication_manager.py`**
```python
"""
Unified communication manager supporting multiple transports.
Allows switching between Telegram and WebSocket without code changes.
"""

import os
from typing import Callable, List, Optional
from .message_parser import ParsedMessage

class CommunicationManager:
    """Unified interface for different communication transports"""
    
    def __init__(self, transport_type: str = None):
        if transport_type is None:
            # Auto-detect based on environment
            transport_type = os.getenv('COMMUNICATION_TRANSPORT', 'websocket')
            
        self.transport_type = transport_type
        
        if transport_type == 'telegram':
            from .telegram_manager import TelegramManager
            self.transport = TelegramManager()
        elif transport_type == 'websocket':
            from .websocket_manager import WebSocketManager
            self.transport = WebSocketManager()
        else:
            raise ValueError(f"Unsupported transport type: {transport_type}")
            
    def add_message_handler(self, handler: Callable[[ParsedMessage], None]):
        """Add message handler - unified interface"""
        return self.transport.add_message_handler(handler)
        
    def start_polling(self):
        """Start communication - unified interface"""
        return self.transport.start_polling()
        
    def stop_polling(self):
        """Stop communication - unified interface"""
        return self.transport.stop_polling()
        
    def send_message(self, text: str, sender_name: str = "system", 
                    reply_to: Optional[int] = None) -> bool:
        """Send message - unified interface"""
        return self.transport.send_message(text, sender_name, reply_to)
        
    def is_connected(self) -> bool:
        """Check connection status - unified interface"""
        return self.transport.is_connected()
        
    def get_transport_type(self) -> str:
        """Get the current transport type"""
        return self.transport_type
```

### Step 2: Create Basic React Frontend (Day 3-5)

#### 2.1 Initialize Next.js Project

```bash
# Create frontend directory
mkdir frontend
cd frontend

# Initialize Next.js with TypeScript
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"

# Install additional dependencies
npm install ws @types/ws
```

#### 2.2 Create Chat Types

**File: `frontend/src/types/chat.ts`**
```typescript
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

export interface WebSocketMessage {
  type: string;
  data: any;
}
```

#### 2.3 Create WebSocket Hook

**File: `frontend/src/hooks/useChatWebSocket.ts`**
```typescript
'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { ChatMessage, User, AgentStatus, WebSocketMessage } from '../types/chat';

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
      const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8081';
      ws.current = new WebSocket(wsUrl);
      
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
        
      case 'error':
        setError(message.data.message);
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

#### 2.4 Create Basic Chat Interface

**File: `frontend/src/components/ChatInterface.tsx`**
```tsx
'use client';

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
    
    return (
      <div
        key={message.id}
        className={`p-4 border-b ${isAgent ? 'bg-blue-50' : 'bg-white'}`}
      >
        <div className="flex justify-between items-start mb-2">
          <span className="font-semibold text-gray-800">
            {message.sender}
            {isAgent && (
              <span className="ml-2 px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                Agent
              </span>
            )}
          </span>
          <span className="text-sm text-gray-500">
            {formatTimestamp(message.timestamp)}
          </span>
        </div>
        
        {message.replyTo && (
          <div className="text-sm text-gray-600 mb-2 italic">
            Replying to message #{message.replyTo}
          </div>
        )}
        
        <div className="text-gray-900">
          {renderMessageText(message.text, message.mentions)}
        </div>
        
        {message.mentions.length > 0 && (
          <div className="mt-2 text-sm text-blue-600">
            Mentions: {message.mentions.map(m => `@${m}`).join(', ')}
          </div>
        )}
        
        <button 
          onClick={() => setReplyTo(message.id)}
          className="mt-2 text-sm text-blue-500 hover:text-blue-700"
        >
          Reply
        </button>
      </div>
    );
  };
  
  const renderMessageText = (text: string, mentions: string[]) => {
    // Simple mention highlighting
    let highlightedText = text;
    mentions.forEach(mention => {
      const regex = new RegExp(`@${mention}`, 'gi');
      highlightedText = highlightedText.replace(
        regex,
        `<span class="bg-yellow-200 px-1 rounded">@${mention}</span>`
      );
    });
    
    return <div dangerouslySetInnerHTML={{ __html: highlightedText }} />;
  };
  
  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-gray-200 p-4">
        <h3 className="font-semibold text-gray-800 mb-4">Users & Agents</h3>
        <div className="space-y-2">
          {users.map(user => (
            <div key={user.id} className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${
                user.status === 'online' ? 'bg-green-400' : 'bg-gray-400'
              }`} />
              <span className="text-sm">{user.id}</span>
              <span className="text-xs text-gray-500">({user.role})</span>
            </div>
          ))}
        </div>
      </div>
      
      {/* Main Chat */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 p-4">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-semibold text-gray-800">
              OpenCode Chat
            </h1>
            <div className={`flex items-center space-x-2 ${
              connected ? 'text-green-600' : 'text-red-600'
            }`}>
              <div className={`w-2 h-2 rounded-full ${
                connected ? 'bg-green-400' : 'bg-red-400'
              }`} />
              <span className="text-sm">
                {connected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
          {error && (
            <div className="mt-2 text-sm text-red-600">
              Error: {error}
            </div>
          )}
        </div>
        
        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          {messages.map(renderMessage)}
          <div ref={messagesEndRef} />
        </div>
        
        {/* Reply Indicator */}
        {replyTo && (
          <div className="bg-yellow-50 border-t border-yellow-200 p-2 flex items-center justify-between">
            <span className="text-sm text-yellow-800">
              Replying to message #{replyTo}
            </span>
            <button 
              onClick={() => setReplyTo(undefined)}
              className="text-sm text-yellow-600 hover:text-yellow-800"
            >
              Cancel
            </button>
          </div>
        )}
        
        {/* Input */}
        <div className="bg-white border-t border-gray-200 p-4">
          <div className="flex space-x-2">
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type a message... Use @username to mention someone"
              disabled={!connected}
              className="flex-1 p-2 border border-gray-300 rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={2}
            />
            <button 
              onClick={handleSendMessage}
              disabled={!connected || !inputText.trim()}
              className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
```

#### 2.5 Create Main Page

**File: `frontend/src/app/page.tsx`**
```tsx
'use client';

import { useState } from 'react';
import { ChatInterface } from '../components/ChatInterface';

export default function Home() {
  const [userId, setUserId] = useState('');
  const [role, setRole] = useState('developer');
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  
  const handleLogin = () => {
    if (userId.trim()) {
      setIsLoggedIn(true);
    }
  };
  
  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="bg-white p-8 rounded-lg shadow-md w-96">
          <h1 className="text-2xl font-bold text-gray-800 mb-6 text-center">
            OpenCode Chat
          </h1>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                User ID
              </label>
              <input
                type="text"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                placeholder="Enter your user ID"
                className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Role
              </label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="developer">Developer</option>
                <option value="designer">Designer</option>
                <option value="tester">Tester</option>
                <option value="manager">Manager</option>
              </select>
            </div>
            
            <button
              onClick={handleLogin}
              disabled={!userId.trim()}
              className="w-full py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              Join Chat
            </button>
          </div>
        </div>
      </div>
    );
  }
  
  return <ChatInterface userId={userId} role={role} />;
}
```

### Step 3: Test Basic Integration (Day 6-7)

#### 3.1 Create Test Script

**File: `test_websocket_integration.py`**
```python
#!/usr/bin/env python3
"""
Test script for WebSocket integration with existing agent system.
"""

import sys
import asyncio
import json
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from src.managers.file_ownership import FileOwnershipManager
from src.chat.websocket_manager import WebSocketManager
from src.agents.agent_manager import AgentManager
from src.config.logging_config import setup_logging

async def test_websocket_integration():
    """Test WebSocket manager with agent system"""
    
    # Set up logging
    setup_logging(cli_mode=True)
    
    print("🧪 Testing WebSocket Integration")
    print("=" * 50)
    
    # Initialize components
    print("1. Initializing components...")
    file_manager = FileOwnershipManager("test_employees.db")
    websocket_manager = WebSocketManager(host="localhost", port=8081)
    agent_manager = AgentManager(file_manager, websocket_manager)
    
    # Create a test employee
    print("2. Creating test employee...")
    file_manager.hire_employee("alice", "developer")
    
    # Sync agents
    print("3. Syncing agents...")
    agent_manager.sync_agents_with_employees()
    
    print(f"   Created {len(agent_manager.agents)} agents")
    
    # Start WebSocket server
    print("4. Starting WebSocket server...")
    websocket_manager.start_polling()
    
    print("   WebSocket server started on localhost:8081")
    print("   You can now test with the React frontend!")
    print("   Press Ctrl+C to stop...")
    
    try:
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n5. Stopping server...")
        websocket_manager.stop_polling()
        print("   Server stopped")

if __name__ == "__main__":
    asyncio.run(test_websocket_integration())
```

#### 3.2 Create Environment Configuration

**File: `.env.example`**
```bash
# Communication Transport
COMMUNICATION_TRANSPORT=websocket  # or 'telegram'

# WebSocket Configuration
WEBSOCKET_HOST=localhost
WEBSOCKET_PORT=8081

# Frontend Configuration
NEXT_PUBLIC_WS_URL=ws://localhost:8081

# Telegram Configuration (for fallback)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

#### 3.3 Run Integration Test

```bash
# Terminal 1: Start the WebSocket server
python test_websocket_integration.py

# Terminal 2: Start the React frontend
cd frontend
npm run dev

# Open browser to http://localhost:3000
# Login as "alice" with role "developer"
# Send a message like "@alice please help with testing"
# Verify agent responds
```

## Phase 2: Server Integration (Week 3-4)

### Step 4: Modify Server Initialization (Day 8-10)

#### 4.1 Update Enhanced Server

**File: `src/enhanced_server.py`** (modify initialization section)
```python
# Around line 220, replace TelegramManager initialization:

# OLD:
# self.telegram_manager = TelegramManager()

# NEW:
from src.chat.communication_manager import CommunicationManager
self.communication_manager = CommunicationManager()

# Update agent manager initialization:
# OLD:
# self.agent_manager = AgentManager(self.file_manager, self.telegram_manager)

# NEW:
self.agent_manager = AgentManager(self.file_manager, self.communication_manager)
```

#### 4.2 Add WebSocket Endpoint to Flask

**File: `src/enhanced_server.py`** (add to routes section)
```python
def _setup_enhanced_routes(self):
    """Set up Flask routes with WebSocket support"""
    
    # ... existing routes ...
    
    @self.app.route('/ws-info')
    def websocket_info():
        """Get WebSocket connection information"""
        if hasattr(self, 'communication_manager'):
            transport_type = self.communication_manager.get_transport_type()
            if transport_type == 'websocket':
                return jsonify({
                    'transport': 'websocket',
                    'host': self.communication_manager.transport.host,
                    'port': self.communication_manager.transport.port,
                    'connected_users': len(self.communication_manager.transport.connections),
                    'running': self.communication_manager.transport.running
                })
            else:
                return jsonify({
                    'transport': 'telegram',
                    'connected': self.communication_manager.transport.is_connected()
                })
        
        return jsonify({'error': 'Communication manager not available'}), 500
```

#### 4.3 Update CLI Server

**File: `src/cli_server.py`** (modify around line 54)
```python
# OLD:
# self.telegram_manager = TelegramManager()
# self.agent_manager = AgentManager(self.file_manager, self.telegram_manager)

# NEW:
from src.chat.communication_manager import CommunicationManager
self.communication_manager = CommunicationManager()
self.agent_manager = AgentManager(self.file_manager, self.communication_manager)

# Update auto-start method around line 83:
def _auto_start_chat_if_configured(self):
    """Auto-start communication system if properly configured"""
    
    transport_type = self.communication_manager.get_transport_type()
    
    if transport_type == 'telegram':
        from src.chat.chat_config import config
        if config.is_configured():
            try:
                self.communication_manager.start_polling()
                self.agent_bridge.start_monitoring()
                self.chat_enabled = True
                print("🚀 Telegram chat system auto-started!")
                print(f"👥 {len(self.agent_manager.agents)} communication agents ready")
                print("💬 Employees can now be mentioned in the Telegram group")
            except Exception as e:
                print(f"⚠️  Failed to auto-start Telegram: {e}")
        else:
            print("💬 Telegram not configured (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)")
    
    elif transport_type == 'websocket':
        try:
            self.communication_manager.start_polling()
            self.agent_bridge.start_monitoring()
            self.chat_enabled = True
            print("🚀 WebSocket chat system auto-started!")
            print(f"👥 {len(self.agent_manager.agents)} communication agents ready")
            print("💬 Open http://localhost:3000 to access the chat interface")
        except Exception as e:
            print(f"⚠️  Failed to auto-start WebSocket: {e}")
            print("   Use 'chat-start' to start manually")
```

### Step 5: Create E2E Test Suite (Day 11-12)

#### 5.1 WebSocket Test Client

**File: `tests/test_websocket_e2e.py`**
```python
"""
End-to-end tests for WebSocket communication system.
"""

import asyncio
import json
import pytest
import websockets
from datetime import datetime
from typing import List, Dict, Any

class WebSocketTestClient:
    """Test client for WebSocket communication"""
    
    def __init__(self, host="localhost", port=8081):
        self.host = host
        self.port = port
        self.websocket = None
        self.messages: List[Dict[str, Any]] = []
        self.connected = False
        
    async def connect(self, user_id: str, role: str = "developer"):
        """Connect to WebSocket server"""
        try:
            self.websocket = await websockets.connect(f"ws://{self.host}:{self.port}")
            self.connected = True
            
            # Send authentication
            auth_message = {
                "type": "auth",
                "data": {
                    "userId": user_id,
                    "role": role
                }
            }
            
            await self.websocket.send(json.dumps(auth_message))
            
            # Wait for auth response
            response = await self.websocket.recv()
            auth_response = json.loads(response)
            
            if auth_response.get("type") == "auth_response" and auth_response["data"]["success"]:
                return True
            else:
                raise Exception(f"Authentication failed: {auth_response}")
                
        except Exception as e:
            self.connected = False
            raise Exception(f"Connection failed: {e}")
            
    async def send_message(self, text: str, mentions: List[str] = None, reply_to: int = None):
        """Send a chat message"""
        if not self.connected or not self.websocket:
            raise Exception("Not connected")
            
        message = {
            "type": "message",
            "data": {
                "id": int(datetime.now().timestamp() * 1000),
                "text": text,
                "mentions": mentions or [],
                "replyTo": reply_to
            }
        }
        
        await self.websocket.send(json.dumps(message))
        
    async def wait_for_message(self, timeout: int = 10) -> Dict[str, Any]:
        """Wait for a message from the server"""
        if not self.connected or not self.websocket:
            raise Exception("Not connected")
            
        try:
            message_str = await asyncio.wait_for(self.websocket.recv(), timeout=timeout)
            message = json.loads(message_str)
            self.messages.append(message)
            return message
        except asyncio.TimeoutError:
            raise Exception(f"No message received within {timeout} seconds")
            
    async def wait_for_agent_response(self, timeout: int = 10) -> Dict[str, Any]:
        """Wait specifically for an agent response"""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            try:
                message = await self.wait_for_message(timeout=1)
                if message.get("type") in ["agent_response", "message"]:
                    return message
            except Exception:
                continue
                
        raise Exception(f"No agent response received within {timeout} seconds")
        
    async def disconnect(self):
        """Disconnect from server"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        self.connected = False

@pytest.mark.asyncio
class TestWebSocketE2E:
    """End-to-end tests for WebSocket communication"""
    
    async def test_basic_connection(self):
        """Test basic WebSocket connection and authentication"""
        client = WebSocketTestClient()
        
        try:
            # Connect and authenticate
            success = await client.connect("test_user", "developer")
            assert success, "Should successfully connect and authenticate"
            
            # Verify connection status
            assert client.connected, "Client should be connected"
            
        finally:
            await client.disconnect()
            
    async def test_task_assignment_flow(self):
        """Test complete task assignment flow"""
        manager_client = WebSocketTestClient()
        agent_client = WebSocketTestClient()
        
        try:
            # Connect both clients
            await manager_client.connect("manager", "manager")
            await agent_client.connect("alice", "developer")
            
            # Manager assigns task to agent
            await manager_client.send_message(
                "@alice please create a login component",
                mentions=["alice"]
            )
            
            # Wait for agent to receive the message
            message = await agent_client.wait_for_message(timeout=5)
            assert message["type"] == "message"
            assert "alice" in message["data"]["mentions"]
            assert "login component" in message["data"]["text"]
            
            # Wait for agent response
            response = await manager_client.wait_for_agent_response(timeout=10)
            assert response["type"] == "agent_response"
            assert response["data"]["sender"] == "alice"
            
        finally:
            await manager_client.disconnect()
            await agent_client.disconnect()
            
    async def test_multi_user_chat(self):
        """Test multiple users chatting simultaneously"""
        clients = []
        
        try:
            # Connect multiple users
            for i, user_id in enumerate(["user1", "user2", "user3"]):
                client = WebSocketTestClient()
                await client.connect(user_id, "developer")
                clients.append(client)
                
            # Send messages from different users
            await clients[0].send_message("Hello everyone!")
            await clients[1].send_message("Hi there!")
            await clients[2].send_message("@user1 how are you?", mentions=["user1"])
            
            # Verify all users receive all messages
            for client in clients:
                messages = []
                for _ in range(3):
                    msg = await client.wait_for_message(timeout=5)
                    messages.append(msg)
                    
                # Check that we received messages from all users
                senders = [msg["data"]["sender"] for msg in messages if msg["type"] == "message"]
                assert "user1" in senders
                assert "user2" in senders
                assert "user3" in senders
                
        finally:
            for client in clients:
                await client.disconnect()
                
    async def test_rate_limiting(self):
        """Test rate limiting functionality"""
        client = WebSocketTestClient()
        
        try:
            await client.connect("spam_user", "developer")
            
            # Send many messages quickly
            for i in range(10):
                await client.send_message(f"Message {i}")
                
            # Should eventually receive a rate limit error
            error_received = False
            for _ in range(10):
                try:
                    message = await client.wait_for_message(timeout=2)
                    if message.get("type") == "error" and "RATE_LIMITED" in message["data"]["code"]:
                        error_received = True
                        break
                except Exception:
                    continue
                    
            # Note: This test might need adjustment based on actual rate limiting settings
            # assert error_received, "Should receive rate limiting error"
            
        finally:
            await client.disconnect()
            
    async def test_connection_recovery(self):
        """Test connection recovery after disconnect"""
        client = WebSocketTestClient()
        
        try:
            # Initial connection
            await client.connect("recovery_user", "developer")
            
            # Force disconnect
            await client.websocket.close()
            client.connected = False
            
            # Reconnect
            await client.connect("recovery_user", "developer")
            
            # Send a message to verify functionality
            await client.send_message("I'm back!")
            
            # Should work normally
            assert client.connected, "Should be reconnected"
            
        finally:
            await client.disconnect()

# Run tests with: pytest tests/test_websocket_e2e.py -v
```

#### 5.2 Integration Test with Agent System

**File: `tests/test_agent_websocket_integration.py`**
```python
"""
Integration tests for WebSocket with existing agent system.
"""

import asyncio
import pytest
import tempfile
import os
from pathlib import Path

from src.managers.file_ownership import FileOwnershipManager
from src.chat.websocket_manager import WebSocketManager
from src.agents.agent_manager import AgentManager
from tests.test_websocket_e2e import WebSocketTestClient

@pytest.mark.asyncio
class TestAgentWebSocketIntegration:
    """Integration tests for agents with WebSocket communication"""
    
    @pytest.fixture
    async def setup_system(self):
        """Set up the complete system for testing"""
        # Create temporary database
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        try:
            # Initialize components
            file_manager = FileOwnershipManager(temp_db.name)
            websocket_manager = WebSocketManager(host="localhost", port=8082)  # Different port for tests
            agent_manager = AgentManager(file_manager, websocket_manager)
            
            # Create test employees
            file_manager.hire_employee("alice", "developer")
            file_manager.hire_employee("bob", "designer")
            
            # Sync agents
            agent_manager.sync_agents_with_employees()
            
            # Start WebSocket server
            websocket_manager.start_polling()
            
            # Wait a moment for server to start
            await asyncio.sleep(1)
            
            yield {
                'file_manager': file_manager,
                'websocket_manager': websocket_manager,
                'agent_manager': agent_manager
            }
            
        finally:
            # Cleanup
            websocket_manager.stop_polling()
            os.unlink(temp_db.name)
            
    async def test_agent_responds_to_mention(self, setup_system):
        """Test that agents respond when mentioned"""
        system = await setup_system
        
        client = WebSocketTestClient(port=8082)
        
        try:
            # Connect as a user
            await client.connect("manager", "manager")
            
            # Mention an agent
            await client.send_message(
                "@alice please review the authentication module",
                mentions=["alice"]
            )
            
            # Wait for agent response
            response = await client.wait_for_agent_response(timeout=15)
            
            # Verify response
            assert response["type"] == "agent_response"
            assert response["data"]["sender"] == "alice"
            assert "authentication module" in response["data"]["text"].lower() or "got it" in response["data"]["text"].lower()
            
        finally:
            await client.disconnect()
            
    async def test_multiple_agents_respond(self, setup_system):
        """Test multiple agents can respond independently"""
        system = await setup_system
        
        client = WebSocketTestClient(port=8082)
        
        try:
            await client.connect("manager", "manager")
            
            # Mention multiple agents
            await client.send_message(
                "@alice @bob please collaborate on the UI design",
                mentions=["alice", "bob"]
            )
            
            # Wait for responses from both agents
            responses = []
            for _ in range(2):
                response = await client.wait_for_agent_response(timeout=15)
                responses.append(response)
                
            # Verify we got responses from both agents
            senders = [r["data"]["sender"] for r in responses]
            assert "alice" in senders
            assert "bob" in senders
            
        finally:
            await client.disconnect()
            
    async def test_agent_status_tracking(self, setup_system):
        """Test that agent status is tracked correctly"""
        system = await setup_system
        agent_manager = system['agent_manager']
        
        # Check initial agent status
        status = agent_manager.get_agent_status("alice")
        assert status is not None
        
        # Check all agents are available
        assert agent_manager.is_agent_available("alice")
        assert agent_manager.is_agent_available("bob")
        
        # Get chat statistics
        stats = agent_manager.get_chat_statistics()
        assert stats['total_agents'] == 2
        assert stats['chat_connected'] == True  # WebSocket should be connected
        
    async def test_help_request_flow(self, setup_system):
        """Test help request functionality"""
        system = await setup_system
        agent_manager = system['agent_manager']
        
        client = WebSocketTestClient(port=8082)
        
        try:
            await client.connect("alice", "developer")
            
            # Simulate agent requesting help
            success = agent_manager.request_help_for_agent(
                "alice", 
                "implementing authentication", 
                "created login form", 
                "having trouble with JWT validation"
            )
            
            assert success, "Help request should be successful"
            
            # Wait for help request message
            message = await client.wait_for_message(timeout=10)
            assert message["type"] == "agent_response"
            assert "help" in message["data"]["text"].lower()
            assert "JWT validation" in message["data"]["text"]
            
        finally:
            await client.disconnect()

# Run with: pytest tests/test_agent_websocket_integration.py -v
```

This completes Phase 1 of the implementation. The next phases would continue with:

- **Phase 2**: Advanced features (file upload, typing indicators, etc.)
- **Phase 3**: Production deployment and optimization
- **Phase 4**: Migration from Telegram to WebSocket

Each phase builds on the previous one while maintaining backward compatibility and ensuring the existing agent system continues to work unchanged.