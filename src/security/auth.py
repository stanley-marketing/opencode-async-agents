"""
Authentication system for OpenCode-Slack API.
Supports JWT tokens and API keys for secure access.
"""

from datetime import datetime, timedelta
from flask import request, jsonify, current_app
from functools import wraps
from typing import Dict, Optional, List, Tuple
import hashlib
import jwt
import logging
import secrets
import time

logger = logging.getLogger(__name__)

class AuthenticationError(Exception):
    """Custom exception for authentication errors"""
    pass

class AuthorizationError(Exception):
    """Custom exception for authorization errors"""
    pass

class AuthManager:
    """Manages authentication and authorization for the API"""

    def __init__(self, secret_key: str = None, token_expiry_hours: int = 24):
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.token_expiry_hours = token_expiry_hours
        self.api_keys: Dict[str, Dict] = {}
        self.users: Dict[str, Dict] = {}
        self.sessions: Dict[str, Dict] = {}

        # Default admin user
        self._create_default_admin()

        logger.info("Authentication manager initialized")

    def _create_default_admin(self):
        """Create default admin user if none exists"""
        import os
        admin_username = "admin"
        # Use environment variable or generate secure password
        admin_password = os.getenv('ADMIN_PASSWORD')
        if not admin_password:
            admin_password = secrets.token_urlsafe(16)
            logger.warning(f"Generated random admin password. Set ADMIN_PASSWORD environment variable.")

        self.users[admin_username] = {
            "username": admin_username,
            "password_hash": self._hash_password(admin_password),
            "roles": ["admin", "user"],
            "permissions": ["*"],  # All permissions
            "created_at": datetime.utcnow().isoformat(),
            "active": True
        }

        logger.info(f"Default admin user created: {admin_username}")

    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256 with salt"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}:{password_hash}"

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            salt, hash_value = password_hash.split(":")
            return hashlib.sha256((password + salt).encode()).hexdigest() == hash_value
        except ValueError:
            return False

    def create_user(self, username: str, password: str, roles: List[str] = None,
                   permissions: List[str] = None) -> bool:
        """Create a new user"""
        if username in self.users:
            return False

        self.users[username] = {
            "username": username,
            "password_hash": self._hash_password(password),
            "roles": roles or ["user"],
            "permissions": permissions or ["read"],
            "created_at": datetime.utcnow().isoformat(),
            "active": True
        }

        logger.info(f"User created: {username}")
        return True

    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user with username and password"""
        user = self.users.get(username)
        if not user or not user.get("active"):
            return None

        if self._verify_password(password, user["password_hash"]):
            logger.info(f"User authenticated: {username}")
            return user

        logger.warning(f"Failed authentication attempt for user: {username}")
        return None

    def generate_jwt_token(self, username: str) -> str:
        """Generate JWT token for authenticated user"""
        user = self.users.get(username)
        if not user:
            raise AuthenticationError("User not found")

        payload = {
            "username": username,
            "roles": user["roles"],
            "permissions": user["permissions"],
            "exp": datetime.utcnow() + timedelta(hours=self.token_expiry_hours),
            "iat": datetime.utcnow(),
            "iss": "opencode-slack"
        }

        token = jwt.encode(payload, self.secret_key, algorithm="HS256")

        # Store session
        self.sessions[token] = {
            "username": username,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat()
        }

        logger.info(f"JWT token generated for user: {username}")
        return token

    def verify_jwt_token(self, token: str) -> Optional[Dict]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])

            # Update last activity
            if token in self.sessions:
                self.sessions[token]["last_activity"] = datetime.utcnow().isoformat()

            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            # Clean up expired session
            if token in self.sessions:
                del self.sessions[token]
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None

    def generate_api_key(self, name: str, permissions: List[str] = None,
                        expires_days: int = None) -> str:
        """Generate API key with optional expiration"""
        api_key = f"ocs_{secrets.token_urlsafe(32)}"

        self.api_keys[api_key] = {
            "name": name,
            "permissions": permissions or ["read"],
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=expires_days)).isoformat() if expires_days else None,
            "active": True,
            "last_used": None
        }

        logger.info(f"API key generated: {name}")
        return api_key

    def verify_api_key(self, api_key: str) -> Optional[Dict]:
        """Verify API key and return its info"""
        key_info = self.api_keys.get(api_key)
        if not key_info or not key_info.get("active"):
            return None

        # Check expiration
        if key_info.get("expires_at"):
            expires_at = datetime.fromisoformat(key_info["expires_at"])
            if datetime.utcnow() > expires_at:
                logger.warning(f"API key expired: {key_info['name']}")
                return None

        # Update last used
        key_info["last_used"] = datetime.utcnow().isoformat()

        logger.debug(f"API key verified: {key_info['name']}")
        return key_info

    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key"""
        if api_key in self.api_keys:
            self.api_keys[api_key]["active"] = False
            logger.info(f"API key revoked: {self.api_keys[api_key]['name']}")
            return True
        return False

    def check_permission(self, user_permissions: List[str], required_permission: str) -> bool:
        """Check if user has required permission"""
        if "*" in user_permissions:  # Admin has all permissions
            return True

        # Check exact match
        if required_permission in user_permissions:
            return True

        # Check wildcard permissions
        for perm in user_permissions:
            if perm.endswith("*"):
                prefix = perm[:-1]
                if required_permission.startswith(prefix):
                    return True

        return False

    def get_auth_info(self) -> Dict:
        """Get authentication system information"""
        active_sessions = len([s for s in self.sessions.values()])
        active_api_keys = len([k for k in self.api_keys.values() if k.get("active")])

        return {
            "total_users": len(self.users),
            "active_sessions": active_sessions,
            "active_api_keys": active_api_keys,
            "token_expiry_hours": self.token_expiry_hours
        }

# Global auth manager instance
auth_manager = AuthManager()

def require_auth(permission: str = "read"):
    """Decorator to require authentication and authorization"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Get token from header or query parameter
                token = None
                auth_header = request.headers.get("Authorization")

                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header[7:]  # Remove "Bearer " prefix
                elif request.headers.get("X-API-Key"):
                    # API Key authentication
                    api_key = request.headers.get("X-API-Key")
                    key_info = auth_manager.verify_api_key(api_key)

                    if not key_info:
                        return jsonify({"error": "Invalid or expired API key"}), 401

                    # Check permission
                    if not auth_manager.check_permission(key_info["permissions"], permission):
                        return jsonify({"error": "Insufficient permissions"}), 403

                    # Add auth info to request context
                    request.auth_info = {
                        "type": "api_key",
                        "name": key_info["name"],
                        "permissions": key_info["permissions"]
                    }

                    return f(*args, **kwargs)
                else:
                    # Check for token in query parameter (for testing)
                    token = request.args.get("token")

                if not token:
                    return jsonify({"error": "Authentication required"}), 401

                # Verify JWT token
                payload = auth_manager.verify_jwt_token(token)
                if not payload:
                    return jsonify({"error": "Invalid or expired token"}), 401

                # Check permission
                if not auth_manager.check_permission(payload["permissions"], permission):
                    return jsonify({"error": "Insufficient permissions"}), 403

                # Add auth info to request context
                request.auth_info = {
                    "type": "jwt",
                    "username": payload["username"],
                    "roles": payload["roles"],
                    "permissions": payload["permissions"]
                }

                return f(*args, **kwargs)

            except Exception as e:
                logger.error(f"Authentication error: {e}")
                return jsonify({"error": "Authentication failed"}), 500

        return decorated_function
    return decorator

def optional_auth():
    """Decorator for optional authentication (adds auth info if present)"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Try to get auth info but don't require it
                token = None
                auth_header = request.headers.get("Authorization")

                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header[7:]
                    payload = auth_manager.verify_jwt_token(token)
                    if payload:
                        request.auth_info = {
                            "type": "jwt",
                            "username": payload["username"],
                            "roles": payload["roles"],
                            "permissions": payload["permissions"]
                        }
                elif request.headers.get("X-API-Key"):
                    api_key = request.headers.get("X-API-Key")
                    key_info = auth_manager.verify_api_key(api_key)
                    if key_info:
                        request.auth_info = {
                            "type": "api_key",
                            "name": key_info["name"],
                            "permissions": key_info["permissions"]
                        }

                return f(*args, **kwargs)

            except Exception as e:
                logger.error(f"Optional auth error: {e}")
                return f(*args, **kwargs)

        return decorated_function
    return decorator