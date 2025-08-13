# SPDX-License-Identifier: MIT
"""
WebSocket manager for handling real-time communication.
Drop-in replacement for TelegramManager with identical interface.
"""

import asyncio
import json
import logging
import threading
import time
import uuid
from datetime import datetime, timedelta
from queue import Queue, Empty
from typing import Dict, List, Optional, Callable, Any, Set
import websockets
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed, WebSocketException

from .chat_config import config
from .message_parser import MessageParser, ParsedMessage

logger = logging.getLogger(__name__)


class WebSocketConnection:
    """Represents a WebSocket connection with user context"""
    
    def __init__(self, websocket: WebSocketServerProtocol, user_id: str, role: str = "user"):
        self.websocket = websocket
        self.user_id = user_id
        self.role = role
        self.connected_at = datetime.now()
        self.last_activity = datetime.now()
        self.message_count = 0
        
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()
        
    async def send_message(self, message: dict):
        """Send message to this connection"""
        try:
            await self.websocket.send(json.dumps(message))
            self.update_activity()
            return True
        except (ConnectionClosed, WebSocketException) as e:
            logger.warning(f"Failed to send message to {self.user_id}: {e}")
            return False
            
    def is_alive(self) -> bool:
        """Check if connection is still alive"""
        return not self.websocket.closed


class WebSocketManager:
    """WebSocket-based communication manager - drop-in replacement for TelegramManager"""
    
    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        
        # Core components (same interface as TelegramManager)
        self.message_parser = MessageParser()
        self.message_queue = Queue()
        self.message_handlers: List[Callable[[ParsedMessage], None]] = []
        
        # WebSocket-specific components
        self.connections: Dict[str, WebSocketConnection] = {}
        self.server = None
        self.server_task = None
        self.is_running = False
        
        # Rate limiting (same as TelegramManager)
        self.last_message_time = {}
        self.message_count = {}
        
        # Message ID tracking
        self.next_message_id = 1
        self.message_id_lock = threading.Lock()
        
        # Event loop for async operations
        self.loop = None
        self.loop_thread = None
        
    def add_message_handler(self, handler: Callable[[ParsedMessage], None]):
        """Add a message handler function - same interface as TelegramManager"""
        self.message_handlers.append(handler)
        
    def start_polling(self):
        """Start WebSocket server - same interface as TelegramManager"""
        if self.is_running:
            logger.warning("WebSocket server is already running")
            return
            
        logger.info("Starting WebSocket server...")
        
        # Start event loop in separate thread
        self.loop_thread = threading.Thread(target=self._run_server_loop, daemon=True)
        self.loop_thread.start()
        
        # Wait for server to start
        timeout = 10
        start_time = time.time()
        while not self.is_running and (time.time() - start_time) < timeout:
            time.sleep(0.1)
            
        if self.is_running:
            logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")
        else:
            logger.error("Failed to start WebSocket server within timeout")
            
    def stop_polling(self):
        """Stop WebSocket server - same interface as TelegramManager"""
        if not self.is_running:
            return
            
        logger.info("Stopping WebSocket server...")
        self.is_running = False
        
        # Cancel server task
        if self.server_task and self.loop:
            self.loop.call_soon_threadsafe(self.server_task.cancel)
            
        # Close all connections
        if self.loop:
            asyncio.run_coroutine_threadsafe(self._close_all_connections(), self.loop)
            
        # Wait for thread to finish
        if self.loop_thread and self.loop_thread.is_alive():
            self.loop_thread.join(timeout=5)
            
        logger.info("WebSocket server stopped")
        
    def _run_server_loop(self):
        """Run the WebSocket server in its own event loop"""
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Start the server
            self.server_task = self.loop.create_task(self._start_websocket_server())
            self.loop.run_until_complete(self.server_task)
            
        except asyncio.CancelledError:
            logger.info("WebSocket server task cancelled")
        except Exception as e:
            logger.error(f"WebSocket server error: {e}")
        finally:
            if self.loop:
                self.loop.close()
                
    async def _start_websocket_server(self):
        """Start the WebSocket server"""
        try:
            self.server = await websockets.serve(
                self._handle_connection,
                self.host,
                self.port,
                ping_interval=30,
                ping_timeout=10
            )
            
            self.is_running = True
            logger.info(f"WebSocket server listening on {self.host}:{self.port}")
            
            # Keep server running
            await self.server.wait_closed()
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            self.is_running = False
            
    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new WebSocket connection"""
        connection_id = str(uuid.uuid4())
        user_id = None
        
        try:
            logger.info(f"New WebSocket connection: {connection_id}")
            
            # Wait for authentication message
            auth_message = await asyncio.wait_for(websocket.recv(), timeout=30)
            auth_data = json.loads(auth_message)
            
            if auth_data.get('type') != 'auth':
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': 'Authentication required'
                }))
                return
                
            user_id = auth_data.get('user_id')
            role = auth_data.get('role', 'user')
            
            if not user_id:
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': 'User ID required'
                }))
                return
                
            # Create connection object
            connection = WebSocketConnection(websocket, user_id, role)
            self.connections[user_id] = connection
            
            # Send authentication success
            await websocket.send(json.dumps({
                'type': 'auth_success',
                'user_id': user_id,
                'role': role,
                'server_time': datetime.now().isoformat()
            }))
            
            # Broadcast user connected
            await self._broadcast_user_status(user_id, 'connected', role)
            
            logger.info(f"User {user_id} authenticated successfully")
            
            # Handle messages from this connection
            async for message in websocket:
                try:
                    await self._handle_message(connection, message)
                except Exception as e:
                    logger.error(f"Error handling message from {user_id}: {e}")
                    
        except asyncio.TimeoutError:
            logger.warning(f"Authentication timeout for connection {connection_id}")
        except ConnectionClosed:
            logger.info(f"Connection {connection_id} closed")
        except Exception as e:
            logger.error(f"Error in connection {connection_id}: {e}")
        finally:
            # Clean up connection
            if user_id and user_id in self.connections:
                del self.connections[user_id]
                await self._broadcast_user_status(user_id, 'disconnected')
                logger.info(f"User {user_id} disconnected")
                
    async def _handle_message(self, connection: WebSocketConnection, raw_message: str):
        """Handle incoming message from WebSocket connection"""
        try:
            message_data = json.loads(raw_message)
            connection.update_activity()
            connection.message_count += 1
            
            if message_data.get('type') == 'chat_message':
                await self._process_chat_message(connection, message_data)
            elif message_data.get('type') == 'ping':
                await connection.send_message({'type': 'pong'})
            elif message_data.get('type') == 'typing':
                await self._handle_typing_indicator(connection, message_data)
            else:
                logger.warning(f"Unknown message type: {message_data.get('type')}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from {connection.user_id}: {e}")
        except Exception as e:
            logger.error(f"Error processing message from {connection.user_id}: {e}")
            
    async def _process_chat_message(self, connection: WebSocketConnection, message_data: dict):
        """Process chat message and convert to ParsedMessage format"""
        text = message_data.get('text', '')
        reply_to = message_data.get('reply_to')
        
        if not text.strip():
            return
            
        # Generate message ID
        with self.message_id_lock:
            message_id = self.next_message_id
            self.next_message_id += 1
            
        # Create message data in Telegram format for compatibility
        telegram_format = {
            'message_id': message_id,
            'text': text,
            'date': int(datetime.now().timestamp()),
            'from': {
                'username': connection.user_id,
                'first_name': connection.user_id,
                'id': hash(connection.user_id) % (10**9)  # Generate consistent ID
            },
            'chat': {
                'id': '1'  # Single chat room
            }
        }
        
        if reply_to:
            telegram_format['reply_to_message'] = {'message_id': reply_to}
            
        # Parse message using existing parser
        parsed_message = self.message_parser.parse_message(telegram_format)
        
        logger.info(f"Processing message from {connection.user_id}: {text[:100]}")
        
        # Add to queue
        self.message_queue.put(parsed_message)
        
        # Broadcast message to all connected users
        broadcast_message = {
            'type': 'chat_message',
            'data': {
                'id': message_id,
                'text': text,
                'sender': connection.user_id,
                'timestamp': datetime.now().isoformat(),
                'mentions': parsed_message.mentions,
                'is_command': parsed_message.is_command,
                'command': parsed_message.command,
                'command_args': parsed_message.command_args,
                'reply_to': reply_to
            }
        }
        
        await self._broadcast_message(broadcast_message, exclude_user=connection.user_id)
        
        # Notify handlers (same as TelegramManager)
        for handler in self.message_handlers:
            try:
                handler(parsed_message)
            except Exception as e:
                logger.error(f"Error in message handler: {e}", exc_info=True)
                
    async def _handle_typing_indicator(self, connection: WebSocketConnection, message_data: dict):
        """Handle typing indicator"""
        typing_message = {
            'type': 'typing',
            'data': {
                'user_id': connection.user_id,
                'is_typing': message_data.get('is_typing', False)
            }
        }
        
        await self._broadcast_message(typing_message, exclude_user=connection.user_id)
        
    async def _broadcast_message(self, message: dict, exclude_user: str = None):
        """Broadcast message to all connected users"""
        disconnected_users = []
        
        for user_id, connection in self.connections.items():
            if exclude_user and user_id == exclude_user:
                continue
                
            if not connection.is_alive():
                disconnected_users.append(user_id)
                continue
                
            success = await connection.send_message(message)
            if not success:
                disconnected_users.append(user_id)
                
        # Clean up disconnected users
        for user_id in disconnected_users:
            if user_id in self.connections:
                del self.connections[user_id]
                logger.info(f"Removed disconnected user: {user_id}")
                
    async def _broadcast_user_status(self, user_id: str, status: str, role: str = None):
        """Broadcast user connection status"""
        status_message = {
            'type': 'user_status',
            'data': {
                'user_id': user_id,
                'status': status,
                'role': role,
                'timestamp': datetime.now().isoformat()
            }
        }
        
        await self._broadcast_message(status_message)
        
    async def _close_all_connections(self):
        """Close all WebSocket connections"""
        for connection in list(self.connections.values()):
            try:
                await connection.websocket.close()
            except Exception as e:
                logger.warning(f"Error closing connection for {connection.user_id}: {e}")
                
        self.connections.clear()
        
    def send_message(self, text: str, sender_name: str = "system", 
                    reply_to: Optional[int] = None) -> bool:
        """Send a message to all connected clients - same interface as TelegramManager"""
        
        # Rate limiting check (same as TelegramManager)
        if not self._can_send_message(sender_name):
            logger.warning(f"Rate limit exceeded for {sender_name}")
            return False
            
        # Format message with sender (same as TelegramManager)
        if sender_name != "system":
            formatted_text = f"{config.get_bot_name(sender_name)}: {text}"
        else:
            formatted_text = text
            
        # Handle special characters (same as TelegramManager)
        formatted_text = formatted_text.replace('_', '\\_')
        formatted_text = formatted_text.replace('*', '\\*')
        formatted_text = formatted_text.replace('[', '\\[')
        formatted_text = formatted_text.replace(']', '\\]')
        formatted_text = formatted_text.replace('(', '\\(')
        formatted_text = formatted_text.replace(')', '\\)')
        
        # Truncate if too long
        if len(formatted_text) > config.max_message_length:
            formatted_text = formatted_text[:config.max_message_length-3] + "..."
            
        # Generate message ID
        with self.message_id_lock:
            message_id = self.next_message_id
            self.next_message_id += 1
            
        # Create broadcast message
        broadcast_message = {
            'type': 'chat_message',
            'data': {
                'id': message_id,
                'text': formatted_text,
                'sender': sender_name,
                'timestamp': datetime.now().isoformat(),
                'mentions': [],
                'is_command': False,
                'reply_to': reply_to,
                'is_bot_message': True
            }
        }
        
        # Send via event loop
        if self.loop and self.is_running:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self._broadcast_message(broadcast_message), 
                    self.loop
                )
                future.result(timeout=5)  # Wait up to 5 seconds
                
                self._record_message_sent(sender_name)
                logger.info(f"Message sent by {sender_name}")
                return True
                
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                return False
        else:
            logger.warning("WebSocket server not running, cannot send message")
            return False
            
    def _can_send_message(self, sender_name: str) -> bool:
        """Check if sender can send a message (rate limiting) - same as TelegramManager"""
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
        """Record that a message was sent for rate limiting - same as TelegramManager"""
        now = datetime.now()
        self.last_message_time[sender_name] = now
        
        if sender_name not in self.message_count:
            self.message_count[sender_name] = []
        self.message_count[sender_name].append(now)
        
    def is_connected(self) -> bool:
        """Check if server is running and has connections - same interface as TelegramManager"""
        return self.is_running and len(self.connections) > 0
        
    def get_connected_users(self) -> List[Dict[str, Any]]:
        """Get list of connected users"""
        return [
            {
                'user_id': conn.user_id,
                'role': conn.role,
                'connected_at': conn.connected_at.isoformat(),
                'last_activity': conn.last_activity.isoformat(),
                'message_count': conn.message_count
            }
            for conn in self.connections.values()
        ]
        
    def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        return {
            'is_running': self.is_running,
            'host': self.host,
            'port': self.port,
            'connected_users': len(self.connections),
            'total_messages': sum(conn.message_count for conn in self.connections.values()),
            'uptime_seconds': (datetime.now() - datetime.now()).total_seconds() if self.is_running else 0
        }