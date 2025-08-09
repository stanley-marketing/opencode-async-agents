"""
Message validation and sanitization for WebSocket communications.
Implements comprehensive input validation, XSS protection, and content filtering.
"""

import html
import json
import logging
import re
import urllib.parse
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Set
import bleach
from bleach.css_sanitizer import CSSSanitizer

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of message validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if not self.is_valid and not self.error_message:
            self.error_message = "; ".join(self.errors) if self.errors else "Validation failed"

class MessageValidator:
    """
    Comprehensive message validator with security-focused validation and sanitization.
    Protects against XSS, injection attacks, and malformed content.
    """
    
    def __init__(self):
        # Allowed HTML tags and attributes for rich content
        self.allowed_tags = {
            'b', 'i', 'u', 'strong', 'em', 'code', 'pre', 'blockquote',
            'p', 'br', 'span', 'div', 'a', 'ul', 'ol', 'li'
        }
        
        self.allowed_attributes = {
            'a': ['href', 'title'],
            'span': ['class'],
            'div': ['class'],
            'code': ['class'],
            'pre': ['class']
        }
        
        # CSS sanitizer for safe styling
        self.css_sanitizer = CSSSanitizer(
            allowed_css_properties=['color', 'background-color', 'font-weight', 'font-style']
        )
        
        # Dangerous patterns to detect
        self.dangerous_patterns = [
            # Script injection
            re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
            re.compile(r'javascript:', re.IGNORECASE),
            re.compile(r'vbscript:', re.IGNORECASE),
            re.compile(r'data:text/html', re.IGNORECASE),
            
            # Event handlers
            re.compile(r'on\w+\s*=', re.IGNORECASE),
            
            # SQL injection patterns
            re.compile(r'(union|select|insert|update|delete|drop|create|alter)\s+', re.IGNORECASE),
            re.compile(r'(\-\-|\#|\/\*|\*\/)', re.IGNORECASE),
            
            # Command injection
            re.compile(r'[;&|`$(){}[\]\\]'),
            
            # Path traversal
            re.compile(r'\.\.\/|\.\.\\'),
        ]
        
        # Suspicious content patterns
        self.suspicious_patterns = [
            re.compile(r'<iframe[^>]*>', re.IGNORECASE),
            re.compile(r'<object[^>]*>', re.IGNORECASE),
            re.compile(r'<embed[^>]*>', re.IGNORECASE),
            re.compile(r'<form[^>]*>', re.IGNORECASE),
            re.compile(r'<input[^>]*>', re.IGNORECASE),
        ]
        
        # Message type schemas
        self.message_schemas = {
            'auth': {
                'required': ['type', 'method'],
                'optional': ['token', 'api_key', 'session_token', 'user_id', 'password'],
                'max_length': 2048
            },
            'chat_message': {
                'required': ['type', 'text'],
                'optional': ['reply_to', 'mentions', 'attachments', 'csrf_token'],
                'max_length': 4096
            },
            'typing': {
                'required': ['type'],
                'optional': ['is_typing'],
                'max_length': 256
            },
            'ping': {
                'required': ['type'],
                'optional': ['timestamp'],
                'max_length': 256
            },
            'create_task': {
                'required': ['type', 'title', 'csrf_token'],
                'optional': ['description', 'assignee', 'priority', 'due_date'],
                'max_length': 8192
            },
            'update_task': {
                'required': ['type', 'task_id', 'csrf_token'],
                'optional': ['title', 'description', 'status', 'assignee', 'priority'],
                'max_length': 8192
            },
            'delete_task': {
                'required': ['type', 'task_id', 'csrf_token'],
                'optional': [],
                'max_length': 512
            },
            'admin_command': {
                'required': ['type', 'command', 'csrf_token'],
                'optional': ['args', 'target'],
                'max_length': 2048
            }
        }
        
        # Rate limiting for validation (prevent DoS)
        self.validation_cache = {}
        self.max_cache_size = 1000
        
        logger.info("Message validator initialized")
    
    def validate_auth_message(self, message: Dict) -> ValidationResult:
        """Validate authentication message"""
        return self._validate_message_structure(message, 'auth')
    
    def validate_message(self, message: Dict) -> ValidationResult:
        """Validate any message type"""
        message_type = message.get('type', 'unknown')
        
        # Check if we have a schema for this message type
        if message_type not in self.message_schemas:
            return ValidationResult(
                is_valid=False,
                errors=[f"Unknown message type: {message_type}"],
                warnings=[]
            )
        
        return self._validate_message_structure(message, message_type)
    
    def sanitize_message(self, message: Dict) -> Dict:
        """Sanitize message content to prevent XSS and other attacks"""
        sanitized = {}
        
        for key, value in message.items():
            if isinstance(value, str):
                sanitized[key] = self._sanitize_string(value, key)
            elif isinstance(value, dict):
                sanitized[key] = self.sanitize_message(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_string(item, key) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _validate_message_structure(self, message: Dict, message_type: str) -> ValidationResult:
        """Validate message structure against schema"""
        errors = []
        warnings = []
        
        schema = self.message_schemas.get(message_type, {})
        required_fields = schema.get('required', [])
        optional_fields = schema.get('optional', [])
        max_length = schema.get('max_length', 4096)
        
        # Check message size
        message_str = json.dumps(message)
        if len(message_str) > max_length:
            errors.append(f"Message too large: {len(message_str)} > {max_length}")
        
        # Check required fields
        for field in required_fields:
            if field not in message:
                errors.append(f"Missing required field: {field}")
            elif not message[field]:  # Check for empty values
                errors.append(f"Empty required field: {field}")
        
        # Check for unknown fields
        allowed_fields = set(required_fields + optional_fields)
        for field in message.keys():
            if field not in allowed_fields:
                warnings.append(f"Unknown field: {field}")
        
        # Validate field content
        for field, value in message.items():
            field_errors = self._validate_field_content(field, value, message_type)
            errors.extend(field_errors)
        
        # Check for dangerous content
        dangerous_content = self._check_dangerous_content(message)
        if dangerous_content:
            errors.extend(dangerous_content)
        
        # Check for suspicious patterns
        suspicious_content = self._check_suspicious_content(message)
        warnings.extend(suspicious_content)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_field_content(self, field: str, value: Any, message_type: str) -> List[str]:
        """Validate specific field content"""
        errors = []
        
        if not isinstance(value, (str, int, float, bool, list, dict, type(None))):
            errors.append(f"Invalid data type for field {field}")
            return errors
        
        # String field validation
        if isinstance(value, str):
            # Check length limits
            max_lengths = {
                'text': 4000,
                'title': 200,
                'description': 2000,
                'command': 100,
                'user_id': 50,
                'token': 1000,
                'api_key': 100
            }
            
            max_len = max_lengths.get(field, 500)
            if len(value) > max_len:
                errors.append(f"Field {field} too long: {len(value)} > {max_len}")
            
            # Validate specific field formats
            if field == 'user_id':
                if not re.match(r'^[a-zA-Z0-9_.-]+$', value):
                    errors.append("Invalid user_id format")
            
            elif field == 'email':
                if not re.match(r'^[^@]+@[^@]+\.[^@]+$', value):
                    errors.append("Invalid email format")
            
            elif field == 'url' or field == 'href':
                if not self._is_safe_url(value):
                    errors.append("Unsafe URL detected")
            
            elif field == 'command':
                if not re.match(r'^[a-zA-Z0-9_-]+$', value):
                    errors.append("Invalid command format")
        
        # List field validation
        elif isinstance(value, list):
            if field == 'mentions':
                for mention in value:
                    if not isinstance(mention, str) or not re.match(r'^[a-zA-Z0-9_.-]+$', mention):
                        errors.append(f"Invalid mention format: {mention}")
            
            elif field == 'attachments':
                for attachment in value:
                    if not isinstance(attachment, dict):
                        errors.append("Invalid attachment format")
                    elif 'url' in attachment and not self._is_safe_url(attachment['url']):
                        errors.append("Unsafe attachment URL")
        
        # Integer field validation
        elif isinstance(value, int):
            if field in ['task_id', 'reply_to', 'message_id']:
                if value < 0:
                    errors.append(f"Invalid {field}: must be positive")
        
        return errors
    
    def _check_dangerous_content(self, message: Dict) -> List[str]:
        """Check for dangerous content patterns"""
        errors = []
        message_str = json.dumps(message).lower()
        
        for pattern in self.dangerous_patterns:
            if pattern.search(message_str):
                errors.append(f"Dangerous content detected: {pattern.pattern[:50]}...")
        
        return errors
    
    def _check_suspicious_content(self, message: Dict) -> List[str]:
        """Check for suspicious content patterns"""
        warnings = []
        message_str = json.dumps(message).lower()
        
        for pattern in self.suspicious_patterns:
            if pattern.search(message_str):
                warnings.append(f"Suspicious content detected: {pattern.pattern[:50]}...")
        
        return warnings
    
    def _sanitize_string(self, text: str, field_name: str) -> str:
        """Sanitize string content based on field type"""
        if not isinstance(text, str):
            return text
        
        # Fields that allow HTML content
        html_fields = {'text', 'description', 'content'}
        
        if field_name in html_fields:
            # Sanitize HTML content
            sanitized = bleach.clean(
                text,
                tags=self.allowed_tags,
                attributes=self.allowed_attributes,
                css_sanitizer=self.css_sanitizer,
                strip=True
            )
        else:
            # Escape HTML for non-HTML fields
            sanitized = html.escape(text)
        
        # Additional sanitization
        sanitized = self._remove_dangerous_sequences(sanitized)
        
        return sanitized
    
    def _remove_dangerous_sequences(self, text: str) -> str:
        """Remove dangerous character sequences"""
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Remove control characters except common whitespace
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\t\n\r')
        
        # Normalize Unicode
        text = text.encode('utf-8', errors='ignore').decode('utf-8')
        
        return text
    
    def _is_safe_url(self, url: str) -> bool:
        """Check if URL is safe"""
        try:
            parsed = urllib.parse.urlparse(url)
            
            # Only allow http/https schemes
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Block localhost and private IPs
            hostname = parsed.hostname
            if hostname:
                hostname = hostname.lower()
                if (hostname in ['localhost', '127.0.0.1', '::1'] or
                    hostname.startswith('192.168.') or
                    hostname.startswith('10.') or
                    hostname.startswith('172.')):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        return {
            'cache_size': len(self.validation_cache),
            'max_cache_size': self.max_cache_size,
            'supported_message_types': list(self.message_schemas.keys()),
            'allowed_html_tags': list(self.allowed_tags),
            'dangerous_patterns_count': len(self.dangerous_patterns),
            'suspicious_patterns_count': len(self.suspicious_patterns)
        }