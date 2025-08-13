# SPDX-License-Identifier: MIT
"""
WebSocket authentication and authorization manager.
Handles JWT tokens, session management, and role-based access control.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
import jwt
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from .auth import auth_manager
from ..config.secure_config import get_config

logger = logging.getLogger(__name__)

@dataclass
class AuthResult:
    """Result of authentication attempt"""
    success: bool
    user_id: Optional[str] = None
    role: Optional[str] = None
    permissions: Optional[List[str]] = None
    session_token: Optional[str] = None
    error_message: Optional[str] = None

class WebSocketAuthManager:
    """
    WebSocket-specific authentication manager with enhanced security features.
    Integrates with existing auth system while adding WebSocket-specific protections.
    """
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.auth_manager = auth_manager  # Use existing auth manager
        
        # WebSocket-specific settings
        self.ws_secret_key = self._derive_ws_secret()
        self.session_timeout = 30 * 60  # 30 minutes
        self.max_sessions_per_user = 5
        
        # Session tracking
        self.active_sessions: Dict[str, Dict] = {}
        self.user_sessions: Dict[str, Set[str]] = {}
        
        # Authentication methods
        self.auth_methods = {
            'jwt': self._authenticate_jwt,
            'api_key': self._authenticate_api_key,
            'session': self._authenticate_session,
            'oauth': self._authenticate_oauth  # For future OAuth integration
        }
        
        # Role hierarchy for permission inheritance
        self.role_hierarchy = {
            'admin': ['admin', 'moderator', 'user'],
            'moderator': ['moderator', 'user'],
            'user': ['user'],
            'guest': ['guest']
        }
        
        # Default permissions by role
        self.default_permissions = {
            'admin': ['*'],  # All permissions
            'moderator': [
                'chat.*', 'tasks.read', 'tasks.create', 'tasks.update',
                'employees.read', 'monitoring.read'
            ],
            'user': [
                'chat.send', 'chat.read', 'tasks.read', 'tasks.create',
                'employees.read'
            ],
            'guest': ['chat.read']
        }
        
        logger.info("WebSocket authentication manager initialized")
    
    async def authenticate(self, auth_data: Dict) -> AuthResult:
        """
        Authenticate WebSocket connection using provided credentials.
        
        Args:
            auth_data: Authentication data containing method and credentials
            
        Returns:
            AuthResult with authentication outcome
        """
        auth_method = auth_data.get('method', 'jwt')
        
        if auth_method not in self.auth_methods:
            return AuthResult(
                success=False,
                error_message=f"Unsupported authentication method: {auth_method}"
            )
        
        try:
            # Call appropriate authentication method
            result = await self.auth_methods[auth_method](auth_data)
            
            if result.success:
                # Create session
                session_token = await self._create_session(result.user_id, result.role, result.permissions)
                result.session_token = session_token
                
                # Enforce session limits
                await self._enforce_session_limits(result.user_id)
                
                logger.info(f"WebSocket authentication successful: {result.user_id} via {auth_method}")
            else:
                logger.warning(f"WebSocket authentication failed: {result.error_message}")
            
            return result
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return AuthResult(
                success=False,
                error_message="Authentication system error"
            )
    
    async def _authenticate_jwt(self, auth_data: Dict) -> AuthResult:
        """Authenticate using JWT token"""
        token = auth_data.get('token')
        if not token:
            return AuthResult(success=False, error_message="JWT token required")
        
        # Verify token with existing auth manager
        payload = self.auth_manager.verify_jwt_token(token)
        if not payload:
            return AuthResult(success=False, error_message="Invalid or expired JWT token")
        
        # Extract user information
        username = payload.get('username')
        roles = payload.get('roles', [])
        permissions = payload.get('permissions', [])
        
        # Get primary role
        primary_role = self._get_primary_role(roles)
        
        # Expand permissions based on role
        expanded_permissions = self._expand_permissions(primary_role, permissions)
        
        return AuthResult(
            success=True,
            user_id=username,
            role=primary_role,
            permissions=expanded_permissions
        )
    
    async def _authenticate_api_key(self, auth_data: Dict) -> AuthResult:
        """Authenticate using API key"""
        api_key = auth_data.get('api_key')
        if not api_key:
            return AuthResult(success=False, error_message="API key required")
        
        # Verify API key with existing auth manager
        key_info = self.auth_manager.verify_api_key(api_key)
        if not key_info:
            return AuthResult(success=False, error_message="Invalid or expired API key")
        
        # API keys get 'user' role by default
        role = 'user'
        permissions = key_info.get('permissions', [])
        
        # Expand permissions
        expanded_permissions = self._expand_permissions(role, permissions)
        
        return AuthResult(
            success=True,
            user_id=f"api_key_{key_info['name']}",
            role=role,
            permissions=expanded_permissions
        )
    
    async def _authenticate_session(self, auth_data: Dict) -> AuthResult:
        """Authenticate using existing session token"""
        session_token = auth_data.get('session_token')
        if not session_token:
            return AuthResult(success=False, error_message="Session token required")
        
        # Verify session
        session_info = self.active_sessions.get(session_token)
        if not session_info:
            return AuthResult(success=False, error_message="Invalid session token")
        
        # Check session expiry
        if datetime.utcnow() > session_info['expires_at']:
            await self.invalidate_session(session_token)
            return AuthResult(success=False, error_message="Session expired")
        
        # Update last activity
        session_info['last_activity'] = datetime.utcnow()
        
        return AuthResult(
            success=True,
            user_id=session_info['user_id'],
            role=session_info['role'],
            permissions=session_info['permissions']
        )
    
    async def _authenticate_oauth(self, auth_data: Dict) -> AuthResult:
        """Authenticate using OAuth (placeholder for future implementation)"""
        return AuthResult(
            success=False,
            error_message="OAuth authentication not yet implemented"
        )
    
    async def _create_session(self, user_id: str, role: str, permissions: List[str]) -> str:
        """Create new WebSocket session"""
        session_token = self._generate_session_token(user_id)
        
        session_info = {
            'user_id': user_id,
            'role': role,
            'permissions': permissions,
            'created_at': datetime.utcnow(),
            'last_activity': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(seconds=self.session_timeout)
        }
        
        # Store session
        self.active_sessions[session_token] = session_info
        
        # Track user sessions
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = set()
        self.user_sessions[user_id].add(session_token)
        
        return session_token
    
    async def _enforce_session_limits(self, user_id: str):
        """Enforce maximum sessions per user"""
        user_session_tokens = self.user_sessions.get(user_id, set())
        
        if len(user_session_tokens) > self.max_sessions_per_user:
            # Remove oldest sessions
            sessions_with_time = [
                (token, self.active_sessions[token]['created_at'])
                for token in user_session_tokens
                if token in self.active_sessions
            ]
            
            # Sort by creation time and remove oldest
            sessions_with_time.sort(key=lambda x: x[1])
            sessions_to_remove = sessions_with_time[:-self.max_sessions_per_user]
            
            for token, _ in sessions_to_remove:
                await self.invalidate_session(token)
                
            logger.info(f"Enforced session limit for user {user_id}, removed {len(sessions_to_remove)} sessions")
    
    async def invalidate_session(self, session_token: str):
        """Invalidate a session"""
        session_info = self.active_sessions.get(session_token)
        if not session_info:
            return
        
        user_id = session_info['user_id']
        
        # Remove from active sessions
        del self.active_sessions[session_token]
        
        # Remove from user sessions
        if user_id in self.user_sessions:
            self.user_sessions[user_id].discard(session_token)
            if not self.user_sessions[user_id]:
                del self.user_sessions[user_id]
        
        logger.debug(f"Session invalidated: {session_token} for user {user_id}")
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        current_time = datetime.utcnow()
        expired_tokens = []
        
        for token, session_info in self.active_sessions.items():
            if current_time > session_info['expires_at']:
                expired_tokens.append(token)
        
        for token in expired_tokens:
            await self.invalidate_session(token)
        
        if expired_tokens:
            logger.info(f"Cleaned up {len(expired_tokens)} expired sessions")
    
    def check_permission(self, user_permissions: List[str], required_permission: str) -> bool:
        """
        Check if user has required permission.
        Supports wildcard permissions and hierarchical checking.
        """
        # Admin wildcard
        if '*' in user_permissions:
            return True
        
        # Exact match
        if required_permission in user_permissions:
            return True
        
        # Wildcard matching
        for perm in user_permissions:
            if perm.endswith('*'):
                prefix = perm[:-1]
                if required_permission.startswith(prefix):
                    return True
        
        return False
    
    def get_user_roles(self, primary_role: str) -> List[str]:
        """Get all roles for a user based on hierarchy"""
        return self.role_hierarchy.get(primary_role, [primary_role])
    
    def _get_primary_role(self, roles: List[str]) -> str:
        """Get primary role from list of roles"""
        role_priority = ['admin', 'moderator', 'user', 'guest']
        
        for role in role_priority:
            if role in roles:
                return role
        
        return 'guest'  # Default role
    
    def _expand_permissions(self, role: str, explicit_permissions: List[str]) -> List[str]:
        """Expand permissions based on role and explicit permissions"""
        # Start with role-based permissions
        role_permissions = self.default_permissions.get(role, [])
        
        # Add explicit permissions
        all_permissions = set(role_permissions + explicit_permissions)
        
        return list(all_permissions)
    
    def _derive_ws_secret(self) -> str:
        """Derive WebSocket-specific secret key"""
        base_secret = self.config.get('SECRET_KEY', 'default_secret')
        
        # Use PBKDF2 to derive a WebSocket-specific key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'websocket_salt',
            iterations=100000,
        )
        
        derived_key = kdf.derive(base_secret.encode())
        return base64.urlsafe_b64encode(derived_key).decode()
    
    def _generate_session_token(self, user_id: str) -> str:
        """Generate secure session token"""
        # Create token with user ID, timestamp, and random component
        timestamp = str(int(time.time()))
        random_part = secrets.token_urlsafe(16)
        
        # Create HMAC signature
        message = f"{user_id}:{timestamp}:{random_part}"
        signature = hmac.new(
            self.ws_secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"{user_id}:{timestamp}:{random_part}:{signature}"
    
    def _verify_session_token(self, token: str) -> bool:
        """Verify session token integrity"""
        try:
            parts = token.split(':')
            if len(parts) != 4:
                return False
            
            user_id, timestamp, random_part, signature = parts
            
            # Recreate message and verify signature
            message = f"{user_id}:{timestamp}:{random_part}"
            expected_signature = hmac.new(
                self.ws_secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception:
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get authentication statistics"""
        return {
            'active_sessions': len(self.active_sessions),
            'users_with_sessions': len(self.user_sessions),
            'session_timeout_minutes': self.session_timeout // 60,
            'max_sessions_per_user': self.max_sessions_per_user,
            'supported_auth_methods': list(self.auth_methods.keys()),
            'role_hierarchy': self.role_hierarchy
        }