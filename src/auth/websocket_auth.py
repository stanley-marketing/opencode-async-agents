# SPDX-License-Identifier: MIT
"""
WebSocket Authentication Module
Provides secure authentication and session management for WebSocket connections.
"""

import asyncio
import hashlib
import hmac
import json
import jwt
import logging
import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Set, List
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class UserSession:
    """Represents an authenticated user session"""
    user_id: str
    role: str
    permissions: List[str]
    created_at: datetime
    last_activity: datetime
    session_token: str
    device_info: Dict[str, Any]
    ip_address: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['last_activity'] = self.last_activity.isoformat()
        return data
        
    def is_expired(self, timeout_minutes: int = 60) -> bool:
        """Check if session is expired"""
        return (datetime.now() - self.last_activity).total_seconds() > (timeout_minutes * 60)
        
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()


class WebSocketAuthenticator:
    """
    Handles WebSocket authentication, session management, and authorization.
    Supports multiple authentication methods and role-based access control.
    """
    
    def __init__(self, secret_key: str = None, session_timeout: int = 60):
        """
        Initialize WebSocket authenticator.
        
        Args:
            secret_key: Secret key for JWT signing (auto-generated if None)
            session_timeout: Session timeout in minutes
        """
        self.secret_key = secret_key or self._generate_secret_key()
        self.session_timeout = session_timeout
        
        # Active sessions
        self.active_sessions: Dict[str, UserSession] = {}
        self.user_sessions: Dict[str, Set[str]] = {}  # user_id -> set of session_tokens
        
        # Authentication methods
        self.auth_methods = {
            'token': self._authenticate_token,
            'api_key': self._authenticate_api_key,
            'guest': self._authenticate_guest,
            'development': self._authenticate_development
        }
        
        # Role permissions
        self.role_permissions = {
            'admin': ['read', 'write', 'execute', 'manage_users', 'manage_system'],
            'developer': ['read', 'write', 'execute', 'manage_tasks'],
            'analyst': ['read', 'write', 'analyze'],
            'viewer': ['read'],
            'guest': ['read_limited'],
            'system': ['read', 'write', 'execute', 'manage_system']
        }
        
        # Rate limiting
        self.auth_attempts: Dict[str, List[float]] = {}
        self.max_auth_attempts = 5
        self.auth_window_minutes = 15
        
        logger.info("WebSocket authenticator initialized")
        
    def _generate_secret_key(self) -> str:
        """Generate a secure secret key"""
        return secrets.token_urlsafe(32)
        
    async def authenticate_connection(self, auth_data: Dict[str, Any], 
                                    websocket_info: Dict[str, Any]) -> Optional[UserSession]:
        """
        Authenticate a WebSocket connection.
        
        Args:
            auth_data: Authentication data from client
            websocket_info: WebSocket connection information
            
        Returns:
            UserSession if authentication successful, None otherwise
        """
        try:
            # Extract connection info
            ip_address = websocket_info.get('remote_address', 'unknown')
            user_agent = websocket_info.get('user_agent', 'unknown')
            
            # Rate limiting check
            if not self._check_rate_limit(ip_address):
                logger.warning(f"Rate limit exceeded for {ip_address}")
                return None
                
            # Get authentication method
            auth_method = auth_data.get('method', 'token')
            
            if auth_method not in self.auth_methods:
                logger.warning(f"Unknown authentication method: {auth_method}")
                return None
                
            # Authenticate using specified method
            auth_result = await self.auth_methods[auth_method](auth_data, websocket_info)
            
            if not auth_result:
                self._record_auth_attempt(ip_address, False)
                return None
                
            # Create session
            session = self._create_session(
                user_id=auth_result['user_id'],
                role=auth_result['role'],
                permissions=auth_result.get('permissions'),
                device_info={'user_agent': user_agent},
                ip_address=ip_address
            )
            
            self._record_auth_attempt(ip_address, True)
            logger.info(f"User {session.user_id} authenticated successfully from {ip_address}")
            
            return session
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
            
    async def _authenticate_token(self, auth_data: Dict[str, Any], 
                                websocket_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Authenticate using JWT token"""
        try:
            token = auth_data.get('token')
            if not token:
                return None
                
            # Decode JWT token
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            
            # Validate token
            if payload.get('exp', 0) < time.time():
                logger.warning("Expired token")
                return None
                
            return {
                'user_id': payload.get('user_id'),
                'role': payload.get('role', 'viewer'),
                'permissions': payload.get('permissions')
            }
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token authentication error: {e}")
            return None
            
    async def _authenticate_api_key(self, auth_data: Dict[str, Any], 
                                  websocket_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Authenticate using API key"""
        try:
            api_key = auth_data.get('api_key')
            if not api_key:
                return None
                
            # Check against environment variable or database
            valid_api_keys = {
                os.environ.get('OPENCODE_API_KEY'): {'user_id': 'api_user', 'role': 'developer'},
                os.environ.get('OPENCODE_ADMIN_KEY'): {'user_id': 'admin_user', 'role': 'admin'}
            }
            
            if api_key in valid_api_keys:
                return valid_api_keys[api_key]
                
            return None
            
        except Exception as e:
            logger.error(f"API key authentication error: {e}")
            return None
            
    async def _authenticate_guest(self, auth_data: Dict[str, Any], 
                                websocket_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Authenticate as guest user"""
        try:
            # Check if guest access is enabled
            if not os.environ.get('OPENCODE_ALLOW_GUEST', '').lower() in ['true', '1', 'yes']:
                return None
                
            guest_id = auth_data.get('guest_id', f"guest_{secrets.token_hex(4)}")
            
            return {
                'user_id': guest_id,
                'role': 'guest',
                'permissions': self.role_permissions.get('guest', [])
            }
            
        except Exception as e:
            logger.error(f"Guest authentication error: {e}")
            return None
            
    async def _authenticate_development(self, auth_data: Dict[str, Any], 
                                      websocket_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Authenticate in development mode (less secure)"""
        try:
            # Only allow in development mode
            if not os.environ.get('OPENCODE_DEV_MODE', '').lower() in ['true', '1', 'yes']:
                return None
                
            user_id = auth_data.get('user_id', 'dev_user')
            role = auth_data.get('role', 'developer')
            
            return {
                'user_id': user_id,
                'role': role,
                'permissions': self.role_permissions.get(role, ['read'])
            }
            
        except Exception as e:
            logger.error(f"Development authentication error: {e}")
            return None
            
    def _create_session(self, user_id: str, role: str, permissions: List[str] = None,
                       device_info: Dict[str, Any] = None, ip_address: str = 'unknown') -> UserSession:
        """Create a new user session"""
        session_token = secrets.token_urlsafe(32)
        now = datetime.now()
        
        # Get permissions for role
        if permissions is None:
            permissions = self.role_permissions.get(role, ['read'])
            
        session = UserSession(
            user_id=user_id,
            role=role,
            permissions=permissions,
            created_at=now,
            last_activity=now,
            session_token=session_token,
            device_info=device_info or {},
            ip_address=ip_address
        )
        
        # Store session
        self.active_sessions[session_token] = session
        
        # Track user sessions
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = set()
        self.user_sessions[user_id].add(session_token)
        
        return session
        
    def validate_session(self, session_token: str) -> Optional[UserSession]:
        """Validate and return session if valid"""
        session = self.active_sessions.get(session_token)
        
        if not session:
            return None
            
        if session.is_expired(self.session_timeout):
            self.invalidate_session(session_token)
            return None
            
        session.update_activity()
        return session
        
    def invalidate_session(self, session_token: str) -> bool:
        """Invalidate a session"""
        session = self.active_sessions.get(session_token)
        
        if session:
            # Remove from active sessions
            del self.active_sessions[session_token]
            
            # Remove from user sessions
            if session.user_id in self.user_sessions:
                self.user_sessions[session.user_id].discard(session_token)
                if not self.user_sessions[session.user_id]:
                    del self.user_sessions[session.user_id]
                    
            logger.info(f"Session invalidated for user {session.user_id}")
            return True
            
        return False
        
    def invalidate_user_sessions(self, user_id: str) -> int:
        """Invalidate all sessions for a user"""
        if user_id not in self.user_sessions:
            return 0
            
        session_tokens = list(self.user_sessions[user_id])
        count = 0
        
        for token in session_tokens:
            if self.invalidate_session(token):
                count += 1
                
        return count
        
    def check_permission(self, session_token: str, permission: str) -> bool:
        """Check if session has specific permission"""
        session = self.validate_session(session_token)
        
        if not session:
            return False
            
        return permission in session.permissions
        
    def _check_rate_limit(self, ip_address: str) -> bool:
        """Check if IP address is within rate limits"""
        now = time.time()
        window_start = now - (self.auth_window_minutes * 60)
        
        # Clean old attempts
        if ip_address in self.auth_attempts:
            self.auth_attempts[ip_address] = [
                attempt for attempt in self.auth_attempts[ip_address]
                if attempt > window_start
            ]
        else:
            self.auth_attempts[ip_address] = []
            
        # Check limit
        return len(self.auth_attempts[ip_address]) < self.max_auth_attempts
        
    def _record_auth_attempt(self, ip_address: str, success: bool):
        """Record authentication attempt"""
        if not success:  # Only record failed attempts for rate limiting
            if ip_address not in self.auth_attempts:
                self.auth_attempts[ip_address] = []
            self.auth_attempts[ip_address].append(time.time())
            
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        expired_tokens = []
        
        for token, session in self.active_sessions.items():
            if session.is_expired(self.session_timeout):
                expired_tokens.append(token)
                
        for token in expired_tokens:
            self.invalidate_session(token)
            
        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired sessions")
            
    def generate_token(self, user_id: str, role: str, expires_in_hours: int = 24) -> str:
        """Generate a JWT token for a user"""
        payload = {
            'user_id': user_id,
            'role': role,
            'permissions': self.role_permissions.get(role, ['read']),
            'iat': time.time(),
            'exp': time.time() + (expires_in_hours * 3600)
        }
        
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
        
    def get_session_info(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        session = self.validate_session(session_token)
        
        if session:
            return session.to_dict()
            
        return None
        
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get all active sessions"""
        return [session.to_dict() for session in self.active_sessions.values()]
        
    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all sessions for a specific user"""
        if user_id not in self.user_sessions:
            return []
            
        sessions = []
        for token in self.user_sessions[user_id]:
            session = self.active_sessions.get(token)
            if session:
                sessions.append(session.to_dict())
                
        return sessions
        
    def get_auth_stats(self) -> Dict[str, Any]:
        """Get authentication statistics"""
        return {
            'active_sessions': len(self.active_sessions),
            'unique_users': len(self.user_sessions),
            'auth_methods': list(self.auth_methods.keys()),
            'available_roles': list(self.role_permissions.keys()),
            'session_timeout_minutes': self.session_timeout,
            'rate_limit_attempts': self.max_auth_attempts,
            'rate_limit_window_minutes': self.auth_window_minutes
        }


# Global authenticator instance
_authenticator = None


def get_authenticator() -> WebSocketAuthenticator:
    """Get the global authenticator instance"""
    global _authenticator
    
    if _authenticator is None:
        secret_key = os.environ.get('OPENCODE_SECRET_KEY')
        session_timeout = int(os.environ.get('OPENCODE_SESSION_TIMEOUT', 60))
        _authenticator = WebSocketAuthenticator(secret_key, session_timeout)
        
    return _authenticator


def create_authenticator(secret_key: str = None, session_timeout: int = 60) -> WebSocketAuthenticator:
    """Create a new authenticator instance"""
    return WebSocketAuthenticator(secret_key, session_timeout)


# Decorator for WebSocket message handlers that require authentication
def require_auth(permission: str = None):
    """
    Decorator to require authentication for WebSocket message handlers.
    
    Args:
        permission: Required permission (optional)
    """
    def decorator(func):
        async def wrapper(connection, message_data, *args, **kwargs):
            # Extract session token from connection or message
            session_token = getattr(connection, 'session_token', None)
            
            if not session_token:
                return {'error': 'Authentication required'}
                
            authenticator = get_authenticator()
            
            # Validate session
            session = authenticator.validate_session(session_token)
            if not session:
                return {'error': 'Invalid or expired session'}
                
            # Check permission if specified
            if permission and not authenticator.check_permission(session_token, permission):
                return {'error': f'Permission denied: {permission} required'}
                
            # Add session to kwargs
            kwargs['session'] = session
            
            return await func(connection, message_data, *args, **kwargs)
            
        return wrapper
    return decorator