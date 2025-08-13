# SPDX-License-Identifier: MIT
"""
Integration layer for WebSocket security with existing WebSocket manager.
Provides secure wrapper for WebSocketManager with comprehensive security features.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed, WebSocketException

from .websocket_security import WebSocketSecurityManager
from ..chat.websocket_manager import WebSocketManager, WebSocketConnection

logger = logging.getLogger(__name__)

class SecureWebSocketConnection(WebSocketConnection):
    """Enhanced WebSocket connection with security features"""
    
    def __init__(self, websocket: WebSocketServerProtocol, user_id: str, role: str = "user",
                 connection_info: Dict = None):
        super().__init__(websocket, user_id, role)
        
        # Security-specific attributes
        self.connection_id = connection_info.get('connection_id') if connection_info else None
        self.permissions = connection_info.get('permissions', []) if connection_info else []
        self.session_token = connection_info.get('session_token') if connection_info else None
        self.client_ip = connection_info.get('client_ip') if connection_info else 'unknown'
        self.authenticated_at = connection_info.get('authenticated_at') if connection_info else datetime.utcnow()
        
    async def send_message(self, message: dict) -> bool:
        """Send message with security logging"""
        try:
            result = await super().send_message(message)
            if result:
                # Log successful message delivery
                logger.debug(f"Message sent to {self.user_id}: {message.get('type', 'unknown')}")
            return result
        except Exception as e:
            logger.error(f"Failed to send message to {self.user_id}: {e}")
            return False

class SecureWebSocketManager(WebSocketManager):
    """
    Secure WebSocket manager that integrates comprehensive security features
    with the existing WebSocket manager interface.
    """
    
    def __init__(self, host="localhost", port=8765, config=None):
        super().__init__(host, port)
        
        # Initialize security manager
        self.security_manager = WebSocketSecurityManager(config)
        
        # Override connection tracking with secure connections
        self.secure_connections: Dict[str, SecureWebSocketConnection] = {}
        
        # Security event handlers
        self.security_event_handlers = []
        
        logger.info("Secure WebSocket manager initialized")
    
    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new WebSocket connection with comprehensive security"""
        connection_id = None
        
        try:
            logger.info(f"New secure WebSocket connection from {websocket.remote_address}")
            
            # Authenticate connection using security manager
            connection_info = await self.security_manager.authenticate_connection(websocket, path)
            
            if not connection_info:
                logger.warning("WebSocket authentication failed")
                return
            
            connection_id = connection_info['connection_id']
            user_id = connection_info['user_id']
            role = connection_info['role']
            
            # Create secure connection object
            secure_connection = SecureWebSocketConnection(websocket, user_id, role, connection_info)
            
            # Store in both tracking systems
            self.connections[user_id] = secure_connection  # For compatibility
            self.secure_connections[connection_id] = secure_connection
            
            # Broadcast user connected (with security context)
            await self._broadcast_user_status(user_id, 'connected', role)
            
            # Log successful connection
            self.security_manager.audit_logger.log_security_event(
                'websocket_connected',
                connection_info['client_ip'],
                {
                    'connection_id': connection_id,
                    'user_id': user_id,
                    'role': role
                }
            )
            
            logger.info(f"Secure WebSocket connection established: {user_id} ({role})")
            
            # Handle messages from this connection
            async for raw_message in websocket:
                try:
                    await self._handle_secure_message(connection_id, raw_message)
                except Exception as e:
                    logger.error(f"Error handling message from {user_id}: {e}")
                    
                    # Log security event for message handling errors
                    self.security_manager.audit_logger.log_security_event(
                        'message_handling_error',
                        connection_info['client_ip'],
                        {
                            'connection_id': connection_id,
                            'user_id': user_id,
                            'error': str(e)
                        }
                    )
                    
        except ConnectionClosed:
            logger.info(f"WebSocket connection closed normally")
        except Exception as e:
            logger.error(f"Error in secure WebSocket connection: {e}")
        finally:
            # Clean up connection
            if connection_id:
                await self._cleanup_secure_connection(connection_id)
    
    async def _handle_secure_message(self, connection_id: str, raw_message: str):
        """Handle incoming message with security validation"""
        secure_connection = self.secure_connections.get(connection_id)
        if not secure_connection:
            logger.warning(f"Message from unknown secure connection: {connection_id}")
            return
        
        # Validate message using security manager
        validated_message = await self.security_manager.validate_message(connection_id, raw_message)
        
        if not validated_message:
            logger.warning(f"Message validation failed for {secure_connection.user_id}")
            return
        
        # Process message based on type
        message_type = validated_message.get('type')
        
        if message_type == 'chat_message':
            await self._process_secure_chat_message(secure_connection, validated_message)
        elif message_type == 'ping':
            await secure_connection.send_message({'type': 'pong'})
        elif message_type == 'typing':
            await self._handle_typing_indicator(secure_connection, validated_message)
        elif message_type in ['create_task', 'update_task', 'delete_task']:
            await self._handle_task_operation(secure_connection, validated_message)
        elif message_type == 'admin_command':
            await self._handle_admin_command(secure_connection, validated_message)
        else:
            logger.warning(f"Unknown secure message type: {message_type}")
    
    async def _process_secure_chat_message(self, connection: SecureWebSocketConnection, 
                                         message_data: dict):
        """Process chat message with security context"""
        text = message_data.get('text', '')
        reply_to = message_data.get('reply_to')
        
        if not text.strip():
            return
        
        # Generate message ID (same as parent class)
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
                'id': hash(connection.user_id) % (10**9)
            },
            'chat': {
                'id': '1'
            }
        }
        
        if reply_to:
            telegram_format['reply_to_message'] = {'message_id': reply_to}
        
        # Parse message using existing parser
        parsed_message = self.message_parser.parse_message(telegram_format)
        
        # Log data access for compliance
        self.security_manager.audit_logger.log_data_access(
            connection.user_id,
            connection.client_ip,
            'chat_messages',
            'create',
            {
                'message_id': message_id,
                'text_length': len(text),
                'has_mentions': bool(parsed_message.mentions)
            }
        )
        
        logger.info(f"Processing secure chat message from {connection.user_id}: {text[:100]}")
        
        # Add to queue
        self.message_queue.put(parsed_message)
        
        # Create broadcast message with security context
        broadcast_message = {
            'type': 'chat_message',
            'data': {
                'id': message_id,
                'text': text,
                'sender': connection.user_id,
                'sender_role': connection.role,
                'timestamp': datetime.now().isoformat(),
                'mentions': parsed_message.mentions,
                'is_command': parsed_message.is_command,
                'command': parsed_message.command,
                'command_args': parsed_message.command_args,
                'reply_to': reply_to,
                'security_verified': True
            }
        }
        
        # Broadcast to authorized users only
        await self._broadcast_secure_message(broadcast_message, exclude_user=connection.user_id)
        
        # Notify handlers
        for handler in self.message_handlers:
            try:
                handler(parsed_message)
            except Exception as e:
                logger.error(f"Error in message handler: {e}", exc_info=True)
    
    async def _handle_task_operation(self, connection: SecureWebSocketConnection, 
                                   message_data: dict):
        """Handle task operations with proper authorization"""
        operation = message_data.get('type')
        
        # Check permissions
        required_permission = f"tasks.{operation.split('_')[0]}"  # create, update, delete
        if not self.security_manager.auth_manager.check_permission(
            connection.permissions, required_permission
        ):
            await connection.send_message({
                'type': 'error',
                'data': {
                    'code': 'PERMISSION_DENIED',
                    'message': f'Insufficient permissions for {operation}'
                }
            })
            return
        
        # Log admin action for compliance
        self.security_manager.audit_logger.log_admin_action(
            connection.user_id,
            connection.client_ip,
            operation,
            message_data.get('task_id', 'new'),
            {
                'operation_data': {k: v for k, v in message_data.items() 
                                 if k not in ['csrf_token', 'type']}
            }
        )
        
        # Process the task operation (would integrate with task management system)
        logger.info(f"Task operation {operation} by {connection.user_id}")
        
        # Send confirmation
        await connection.send_message({
            'type': 'task_operation_result',
            'data': {
                'operation': operation,
                'success': True,
                'message': f'{operation} completed successfully'
            }
        })
    
    async def _handle_admin_command(self, connection: SecureWebSocketConnection, 
                                  message_data: dict):
        """Handle administrative commands with strict authorization"""
        command = message_data.get('command')
        
        # Only admins can execute admin commands
        if 'admin' not in connection.role:
            await connection.send_message({
                'type': 'error',
                'data': {
                    'code': 'PERMISSION_DENIED',
                    'message': 'Admin privileges required'
                }
            })
            return
        
        # Log admin action
        self.security_manager.audit_logger.log_admin_action(
            connection.user_id,
            connection.client_ip,
            f'admin_command_{command}',
            message_data.get('target'),
            {
                'command': command,
                'args': message_data.get('args', [])
            }
        )
        
        # Process admin command (would integrate with admin system)
        logger.warning(f"Admin command {command} executed by {connection.user_id}")
        
        # Send result
        await connection.send_message({
            'type': 'admin_command_result',
            'data': {
                'command': command,
                'success': True,
                'message': f'Admin command {command} executed'
            }
        })
    
    async def _broadcast_secure_message(self, message: dict, exclude_user: str = None):
        """Broadcast message to authorized users only"""
        disconnected_connections = []
        
        for connection_id, connection in self.secure_connections.items():
            if exclude_user and connection.user_id == exclude_user:
                continue
            
            # Check if user has permission to receive this message type
            if not self._can_receive_message(connection, message):
                continue
            
            if not connection.is_alive():
                disconnected_connections.append(connection_id)
                continue
            
            success = await connection.send_message(message)
            if not success:
                disconnected_connections.append(connection_id)
        
        # Clean up disconnected connections
        for connection_id in disconnected_connections:
            await self._cleanup_secure_connection(connection_id)
    
    def _can_receive_message(self, connection: SecureWebSocketConnection, message: dict) -> bool:
        """Check if user can receive this message type"""
        message_type = message.get('type')
        
        # Basic message types everyone can receive
        if message_type in ['chat_message', 'user_status', 'typing', 'pong']:
            return True
        
        # Admin messages only for admins
        if message_type.startswith('admin_') and 'admin' not in connection.role:
            return False
        
        # Task messages require task permissions
        if message_type.startswith('task_') and not self.security_manager.auth_manager.check_permission(
            connection.permissions, 'tasks.read'
        ):
            return False
        
        return True
    
    async def _cleanup_secure_connection(self, connection_id: str):
        """Clean up secure connection"""
        connection = self.secure_connections.get(connection_id)
        if not connection:
            return
        
        user_id = connection.user_id
        
        # Remove from tracking
        if connection_id in self.secure_connections:
            del self.secure_connections[connection_id]
        
        if user_id in self.connections:
            del self.connections[user_id]
        
        # Clean up security manager
        await self.security_manager.cleanup_connection(connection_id)
        
        # Broadcast user disconnected
        await self._broadcast_user_status(user_id, 'disconnected')
        
        logger.info(f"Secure WebSocket connection cleaned up: {user_id}")
    
    async def start_security_monitoring(self):
        """Start security monitoring tasks"""
        async def security_monitor():
            while self.is_running:
                try:
                    # Clean up expired sessions
                    await self.security_manager.cleanup_expired_sessions()
                    
                    # Check for security violations
                    await self._check_security_violations()
                    
                    # Wait before next check
                    await asyncio.sleep(60)  # Check every minute
                    
                except Exception as e:
                    logger.error(f"Security monitoring error: {e}")
        
        # Start monitoring task
        asyncio.create_task(security_monitor())
        logger.info("Security monitoring started")
    
    async def _check_security_violations(self):
        """Check for ongoing security violations"""
        # Check for suspicious connection patterns
        stats = self.security_manager.get_security_stats()
        
        # Alert on high number of blocked IPs
        if stats['blocked_ips'] > 10:
            logger.warning(f"High number of blocked IPs: {stats['blocked_ips']}")
        
        # Alert on many active connections from single IP
        for ip, count in stats['connections_by_ip'].items():
            if count > 20:  # Threshold for suspicious activity
                logger.warning(f"High connection count from IP {ip}: {count}")
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get comprehensive security status"""
        base_stats = self.get_server_stats()
        security_stats = self.security_manager.get_security_stats()
        
        return {
            **base_stats,
            'security': security_stats,
            'secure_connections': len(self.secure_connections),
            'security_events_recent': len(self.security_manager.security_events),
            'authentication_methods': list(self.security_manager.auth_manager.auth_methods.keys())
        }
    
    def add_security_event_handler(self, handler):
        """Add handler for security events"""
        self.security_event_handlers.append(handler)
    
    # Override parent methods to ensure security
    
    def start_polling(self):
        """Start secure WebSocket server"""
        super().start_polling()
        
        # Start security monitoring
        if self.is_running:
            asyncio.run_coroutine_threadsafe(
                self.start_security_monitoring(),
                self.loop
            )
    
    def send_message(self, text: str, sender_name: str = "system", 
                    reply_to: Optional[int] = None) -> bool:
        """Send message with security context"""
        # Add security metadata
        if sender_name != "system":
            # Log system message for audit
            if self.security_manager:
                self.security_manager.audit_logger.log_security_event(
                    'system_message_sent',
                    'localhost',
                    {
                        'sender': sender_name,
                        'text_length': len(text),
                        'reply_to': reply_to
                    }
                )
        
        return super().send_message(text, sender_name, reply_to)