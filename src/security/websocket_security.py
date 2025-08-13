# SPDX-License-Identifier: MIT
"""
Production-ready WebSocket security manager.
Implements comprehensive security measures for WebSocket communication.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from urllib.parse import parse_qs, urlparse
import websockets
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed, WebSocketException

from .websocket_auth import WebSocketAuthManager
from .message_validation import MessageValidator
from .audit_logger import SecurityAuditLogger
from ..config.secure_config import get_config

logger = logging.getLogger(__name__)

class SecurityViolation(Exception):
    """Raised when a security violation is detected"""
    pass

class WebSocketSecurityManager:
    """
    Comprehensive WebSocket security manager implementing:
    - Authentication and authorization
    - Rate limiting and abuse prevention
    - Message validation and sanitization
    - Session management and timeout handling
    - Audit logging and monitoring
    """
    
    def __init__(self, config=None):
        self.config = config or get_config()
        
        # Initialize security components
        self.auth_manager = WebSocketAuthManager(self.config)
        self.message_validator = MessageValidator()
        self.audit_logger = SecurityAuditLogger()
        
        # Connection tracking
        self.active_connections: Dict[str, Dict] = {}
        self.connection_metadata: Dict[str, Dict] = {}
        
        # Rate limiting (per connection)
        self.rate_limits = {
            'messages_per_minute': 60,
            'auth_attempts_per_minute': 5,
            'max_message_size': 8192,  # 8KB
            'max_connections_per_ip': 10,
            'session_timeout_minutes': 30
        }
        
        # Rate limiting tracking
        self.message_counts: Dict[str, deque] = defaultdict(deque)
        self.auth_attempts: Dict[str, deque] = defaultdict(deque)
        self.ip_connections: Dict[str, Set[str]] = defaultdict(set)
        
        # Security monitoring
        self.security_events: deque = deque(maxlen=1000)
        self.blocked_ips: Dict[str, datetime] = {}
        self.suspicious_patterns: Dict[str, int] = defaultdict(int)
        
        # CSRF protection
        self.csrf_tokens: Dict[str, datetime] = {}
        
        logger.info("WebSocket security manager initialized")
    
    async def authenticate_connection(self, websocket: WebSocketServerProtocol, 
                                    path: str) -> Optional[Dict]:
        """
        Authenticate WebSocket connection with comprehensive security checks.
        
        Returns:
            Dict with connection info if successful, None if failed
        """
        client_ip = self._get_client_ip(websocket)
        connection_id = self._generate_connection_id()
        
        try:
            # Check if IP is blocked
            if self._is_ip_blocked(client_ip):
                await self._send_error(websocket, "IP_BLOCKED", 
                                     "Your IP address has been temporarily blocked")
                self.audit_logger.log_security_event(
                    "blocked_ip_attempt", client_ip, {"connection_id": connection_id}
                )
                return None
            
            # Check connection limits per IP
            if len(self.ip_connections[client_ip]) >= self.rate_limits['max_connections_per_ip']:
                await self._send_error(websocket, "CONNECTION_LIMIT", 
                                     "Too many connections from this IP")
                self._record_security_event("connection_limit_exceeded", client_ip)
                return None
            
            # Wait for authentication message with timeout
            try:
                auth_message = await asyncio.wait_for(
                    websocket.recv(), 
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                await self._send_error(websocket, "AUTH_TIMEOUT", 
                                     "Authentication timeout")
                self._record_security_event("auth_timeout", client_ip)
                return None
            
            # Validate message format
            try:
                auth_data = json.loads(auth_message)
            except json.JSONDecodeError:
                await self._send_error(websocket, "INVALID_JSON", 
                                     "Invalid JSON format")
                self._record_security_event("invalid_auth_json", client_ip)
                return None
            
            # Check rate limiting for auth attempts
            if not self._check_auth_rate_limit(client_ip):
                await self._send_error(websocket, "RATE_LIMITED", 
                                     "Too many authentication attempts")
                self._record_security_event("auth_rate_limit", client_ip)
                return None
            
            # Record auth attempt
            self._record_auth_attempt(client_ip)
            
            # Validate authentication data
            validation_result = self.message_validator.validate_auth_message(auth_data)
            if not validation_result.is_valid:
                await self._send_error(websocket, "INVALID_AUTH", 
                                     validation_result.error_message)
                self._record_security_event("invalid_auth_data", client_ip, 
                                          {"errors": validation_result.errors})
                return None
            
            # Authenticate with auth manager
            auth_result = await self.auth_manager.authenticate(auth_data)
            if not auth_result.success:
                await self._send_error(websocket, "AUTH_FAILED", 
                                     auth_result.error_message)
                self._record_security_event("auth_failed", client_ip, 
                                          {"reason": auth_result.error_message})
                return None
            
            # Create connection info
            connection_info = {
                'connection_id': connection_id,
                'user_id': auth_result.user_id,
                'role': auth_result.role,
                'permissions': auth_result.permissions,
                'client_ip': client_ip,
                'authenticated_at': datetime.utcnow(),
                'last_activity': datetime.utcnow(),
                'session_token': auth_result.session_token,
                'websocket': websocket
            }
            
            # Store connection
            self.active_connections[connection_id] = connection_info
            self.ip_connections[client_ip].add(connection_id)
            
            # Generate CSRF token
            csrf_token = self._generate_csrf_token(connection_id)
            
            # Send authentication success
            await websocket.send(json.dumps({
                'type': 'auth_success',
                'data': {
                    'connection_id': connection_id,
                    'user_id': auth_result.user_id,
                    'role': auth_result.role,
                    'permissions': auth_result.permissions,
                    'csrf_token': csrf_token,
                    'server_time': datetime.utcnow().isoformat(),
                    'session_expires_at': (datetime.utcnow() + 
                                         timedelta(minutes=self.rate_limits['session_timeout_minutes'])).isoformat()
                }
            }))
            
            # Log successful authentication
            self.audit_logger.log_security_event(
                "websocket_auth_success", 
                client_ip, 
                {
                    "connection_id": connection_id,
                    "user_id": auth_result.user_id,
                    "role": auth_result.role
                }
            )
            
            logger.info(f"WebSocket connection authenticated: {auth_result.user_id} from {client_ip}")
            return connection_info
            
        except Exception as e:
            logger.error(f"Authentication error for {client_ip}: {e}")
            await self._send_error(websocket, "AUTH_ERROR", "Authentication failed")
            self._record_security_event("auth_exception", client_ip, {"error": str(e)})
            return None
    
    async def validate_message(self, connection_id: str, raw_message: str) -> Optional[Dict]:
        """
        Validate incoming message with comprehensive security checks.
        
        Returns:
            Validated message dict if successful, None if failed
        """
        connection_info = self.active_connections.get(connection_id)
        if not connection_info:
            logger.warning(f"Message from unknown connection: {connection_id}")
            return None
        
        client_ip = connection_info['client_ip']
        user_id = connection_info['user_id']
        
        try:
            # Check message size
            if len(raw_message) > self.rate_limits['max_message_size']:
                await self._send_error(connection_info['websocket'], "MESSAGE_TOO_LARGE", 
                                     "Message exceeds maximum size")
                self._record_security_event("message_too_large", client_ip, 
                                          {"user_id": user_id, "size": len(raw_message)})
                return None
            
            # Check rate limiting
            if not self._check_message_rate_limit(connection_id):
                await self._send_error(connection_info['websocket'], "RATE_LIMITED", 
                                     "Message rate limit exceeded")
                self._record_security_event("message_rate_limit", client_ip, 
                                          {"user_id": user_id})
                return None
            
            # Parse JSON
            try:
                message_data = json.loads(raw_message)
            except json.JSONDecodeError as e:
                await self._send_error(connection_info['websocket'], "INVALID_JSON", 
                                     "Invalid JSON format")
                self._record_security_event("invalid_message_json", client_ip, 
                                          {"user_id": user_id, "error": str(e)})
                return None
            
            # Validate message structure and content
            validation_result = self.message_validator.validate_message(message_data)
            if not validation_result.is_valid:
                await self._send_error(connection_info['websocket'], "INVALID_MESSAGE", 
                                     validation_result.error_message)
                self._record_security_event("invalid_message", client_ip, 
                                          {"user_id": user_id, "errors": validation_result.errors})
                return None
            
            # Check CSRF token for state-changing operations
            if self._requires_csrf_protection(message_data):
                csrf_token = message_data.get('csrf_token')
                if not self._validate_csrf_token(connection_id, csrf_token):
                    await self._send_error(connection_info['websocket'], "CSRF_INVALID", 
                                         "Invalid CSRF token")
                    self._record_security_event("csrf_violation", client_ip, 
                                              {"user_id": user_id})
                    return None
            
            # Check permissions for the message type
            if not self._check_message_permissions(connection_info, message_data):
                await self._send_error(connection_info['websocket'], "PERMISSION_DENIED", 
                                     "Insufficient permissions")
                self._record_security_event("permission_denied", client_ip, 
                                          {"user_id": user_id, "message_type": message_data.get('type')})
                return None
            
            # Sanitize message content
            sanitized_message = self.message_validator.sanitize_message(message_data)
            
            # Record message for rate limiting
            self._record_message(connection_id)
            
            # Update last activity
            connection_info['last_activity'] = datetime.utcnow()
            
            return sanitized_message
            
        except Exception as e:
            logger.error(f"Message validation error for {user_id}: {e}")
            await self._send_error(connection_info['websocket'], "VALIDATION_ERROR", 
                                 "Message validation failed")
            self._record_security_event("validation_exception", client_ip, 
                                      {"user_id": user_id, "error": str(e)})
            return None
    
    async def cleanup_connection(self, connection_id: str):
        """Clean up connection and associated resources"""
        connection_info = self.active_connections.get(connection_id)
        if not connection_info:
            return
        
        client_ip = connection_info['client_ip']
        user_id = connection_info['user_id']
        
        # Remove from tracking
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        if client_ip in self.ip_connections:
            self.ip_connections[client_ip].discard(connection_id)
            if not self.ip_connections[client_ip]:
                del self.ip_connections[client_ip]
        
        # Clean up rate limiting data
        if connection_id in self.message_counts:
            del self.message_counts[connection_id]
        
        # Invalidate session
        await self.auth_manager.invalidate_session(connection_info.get('session_token'))
        
        # Log disconnection
        self.audit_logger.log_security_event(
            "websocket_disconnect", 
            client_ip, 
            {
                "connection_id": connection_id,
                "user_id": user_id,
                "session_duration": (datetime.utcnow() - connection_info['authenticated_at']).total_seconds()
            }
        )
        
        logger.info(f"WebSocket connection cleaned up: {user_id} from {client_ip}")
    
    def check_session_timeout(self, connection_id: str) -> bool:
        """Check if session has timed out"""
        connection_info = self.active_connections.get(connection_id)
        if not connection_info:
            return True
        
        timeout_minutes = self.rate_limits['session_timeout_minutes']
        timeout_threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        
        return connection_info['last_activity'] < timeout_threshold
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        expired_connections = []
        
        for connection_id, connection_info in self.active_connections.items():
            if self.check_session_timeout(connection_id):
                expired_connections.append(connection_id)
        
        for connection_id in expired_connections:
            connection_info = self.active_connections[connection_id]
            await self._send_error(connection_info['websocket'], "SESSION_EXPIRED", 
                                 "Session has expired")
            await self.cleanup_connection(connection_id)
            
        if expired_connections:
            logger.info(f"Cleaned up {len(expired_connections)} expired sessions")
    
    def get_security_stats(self) -> Dict[str, Any]:
        """Get comprehensive security statistics"""
        current_time = datetime.utcnow()
        
        # Clean up old events
        self._cleanup_old_events()
        
        return {
            'active_connections': len(self.active_connections),
            'connections_by_ip': {ip: len(connections) for ip, connections in self.ip_connections.items()},
            'blocked_ips': len(self.blocked_ips),
            'recent_security_events': len(self.security_events),
            'auth_manager_stats': self.auth_manager.get_stats(),
            'rate_limits': self.rate_limits,
            'csrf_tokens_active': len(self.csrf_tokens),
            'suspicious_patterns': dict(self.suspicious_patterns),
            'uptime': current_time.isoformat()
        }
    
    # Private helper methods
    
    def _get_client_ip(self, websocket: WebSocketServerProtocol) -> str:
        """Extract client IP from WebSocket connection"""
        # Try to get real IP from headers (for proxy setups)
        if hasattr(websocket, 'request_headers'):
            forwarded_for = websocket.request_headers.get('X-Forwarded-For')
            if forwarded_for:
                return forwarded_for.split(',')[0].strip()
            
            real_ip = websocket.request_headers.get('X-Real-IP')
            if real_ip:
                return real_ip.strip()
        
        # Fall back to remote address
        return websocket.remote_address[0] if websocket.remote_address else 'unknown'
    
    def _generate_connection_id(self) -> str:
        """Generate unique connection ID"""
        return f"ws_{secrets.token_urlsafe(16)}_{int(time.time())}"
    
    def _is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is currently blocked"""
        if ip not in self.blocked_ips:
            return False
        
        # Check if block has expired (24 hours)
        block_time = self.blocked_ips[ip]
        if datetime.utcnow() - block_time > timedelta(hours=24):
            del self.blocked_ips[ip]
            return False
        
        return True
    
    def _check_auth_rate_limit(self, ip: str) -> bool:
        """Check authentication rate limit"""
        current_time = time.time()
        auth_times = self.auth_attempts[ip]
        
        # Clean old attempts
        while auth_times and auth_times[0] < current_time - 60:
            auth_times.popleft()
        
        return len(auth_times) < self.rate_limits['auth_attempts_per_minute']
    
    def _record_auth_attempt(self, ip: str):
        """Record authentication attempt"""
        self.auth_attempts[ip].append(time.time())
    
    def _check_message_rate_limit(self, connection_id: str) -> bool:
        """Check message rate limit"""
        current_time = time.time()
        message_times = self.message_counts[connection_id]
        
        # Clean old messages
        while message_times and message_times[0] < current_time - 60:
            message_times.popleft()
        
        return len(message_times) < self.rate_limits['messages_per_minute']
    
    def _record_message(self, connection_id: str):
        """Record message for rate limiting"""
        self.message_counts[connection_id].append(time.time())
    
    def _generate_csrf_token(self, connection_id: str) -> str:
        """Generate CSRF token for connection"""
        token = secrets.token_urlsafe(32)
        self.csrf_tokens[f"{connection_id}:{token}"] = datetime.utcnow()
        return token
    
    def _validate_csrf_token(self, connection_id: str, token: str) -> bool:
        """Validate CSRF token"""
        if not token:
            return False
        
        token_key = f"{connection_id}:{token}"
        if token_key not in self.csrf_tokens:
            return False
        
        # Check if token is expired (1 hour)
        token_time = self.csrf_tokens[token_key]
        if datetime.utcnow() - token_time > timedelta(hours=1):
            del self.csrf_tokens[token_key]
            return False
        
        return True
    
    def _requires_csrf_protection(self, message_data: Dict) -> bool:
        """Check if message type requires CSRF protection"""
        state_changing_types = {
            'create_task', 'update_task', 'delete_task',
            'create_employee', 'update_employee', 'delete_employee',
            'admin_command', 'system_command'
        }
        return message_data.get('type') in state_changing_types
    
    def _check_message_permissions(self, connection_info: Dict, message_data: Dict) -> bool:
        """Check if user has permission for message type"""
        user_permissions = connection_info.get('permissions', [])
        message_type = message_data.get('type')
        
        # Admin has all permissions
        if 'admin' in connection_info.get('role', []):
            return True
        
        # Map message types to required permissions
        permission_map = {
            'chat_message': 'chat.send',
            'create_task': 'tasks.create',
            'update_task': 'tasks.update',
            'delete_task': 'tasks.delete',
            'create_employee': 'employees.create',
            'update_employee': 'employees.update',
            'delete_employee': 'employees.delete',
            'admin_command': 'admin.execute',
            'system_command': 'system.execute'
        }
        
        required_permission = permission_map.get(message_type, 'chat.send')
        
        # Check exact permission or wildcard
        return (required_permission in user_permissions or 
                any(perm.endswith('*') and required_permission.startswith(perm[:-1]) 
                    for perm in user_permissions))
    
    def _record_security_event(self, event_type: str, ip: str, details: Dict = None):
        """Record security event"""
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': event_type,
            'ip': ip,
            'details': details or {}
        }
        
        self.security_events.append(event)
        
        # Check for suspicious patterns
        self.suspicious_patterns[f"{ip}:{event_type}"] += 1
        
        # Auto-block IPs with too many violations
        if self.suspicious_patterns[f"{ip}:{event_type}"] >= 10:
            self.blocked_ips[ip] = datetime.utcnow()
            logger.warning(f"Auto-blocked IP {ip} for repeated {event_type}")
    
    def _cleanup_old_events(self):
        """Clean up old security events and tracking data"""
        current_time = datetime.utcnow()
        
        # Clean up CSRF tokens older than 1 hour
        expired_tokens = [
            token_key for token_key, token_time in self.csrf_tokens.items()
            if current_time - token_time > timedelta(hours=1)
        ]
        for token_key in expired_tokens:
            del self.csrf_tokens[token_key]
        
        # Clean up suspicious patterns older than 24 hours
        # (This is simplified - in production, you'd want more sophisticated cleanup)
        if len(self.suspicious_patterns) > 1000:
            # Keep only the most recent patterns
            sorted_patterns = sorted(self.suspicious_patterns.items(), key=lambda x: x[1], reverse=True)
            self.suspicious_patterns = dict(sorted_patterns[:500])
    
    async def _send_error(self, websocket: WebSocketServerProtocol, error_code: str, message: str):
        """Send error message to WebSocket client"""
        try:
            await websocket.send(json.dumps({
                'type': 'error',
                'data': {
                    'code': error_code,
                    'message': message,
                    'timestamp': datetime.utcnow().isoformat()
                }
            }))
        except (ConnectionClosed, WebSocketException):
            # Connection already closed, ignore
            pass
        except Exception as e:
            logger.error(f"Error sending error message: {e}")