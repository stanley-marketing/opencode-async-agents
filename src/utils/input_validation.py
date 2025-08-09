"""
Input validation and sanitization utilities for API endpoints.
"""
import re
import html
import logging
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Raised when input validation fails"""
    pass

class InputValidator:
    """Comprehensive input validation and sanitization"""
    
    # Regular expressions for common validations
    PATTERNS = {
        'employee_name': re.compile(r'^[a-zA-Z0-9_-]{1,50}$'),
        'role': re.compile(r'^[a-zA-Z0-9_\s-]{1,100}$'),
        'task_description': re.compile(r'^.{1,5000}$', re.DOTALL),
        'model_name': re.compile(r'^[a-zA-Z0-9_/.-]{1,100}$'),
        'session_id': re.compile(r'^[a-zA-Z0-9_-]{1,100}$'),
        'file_path': re.compile(r'^[a-zA-Z0-9_/.-]{1,500}$'),
        'mode': re.compile(r'^(build|chat|edit)$'),
        'log_level': re.compile(r'^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$'),
    }
    
    # Dangerous patterns to reject
    DANGEROUS_PATTERNS = [
        re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'on\w+\s*=', re.IGNORECASE),
        re.compile(r'eval\s*\(', re.IGNORECASE),
        re.compile(r'exec\s*\(', re.IGNORECASE),
        re.compile(r'__import__', re.IGNORECASE),
        re.compile(r'\.\./', re.IGNORECASE),  # Path traversal
        re.compile(r'\\\\', re.IGNORECASE),   # Windows path traversal
    ]
    
    @classmethod
    def validate_employee_name(cls, name: str) -> str:
        """Validate and sanitize employee name"""
        if not name:
            raise ValidationError("Employee name is required")
        
        name = cls._sanitize_string(name)
        
        if not cls.PATTERNS['employee_name'].match(name):
            raise ValidationError(
                "Employee name must be 1-50 characters, alphanumeric, underscore, or hyphen only"
            )
        
        return name
    
    @classmethod
    def validate_role(cls, role: str) -> str:
        """Validate and sanitize employee role"""
        if not role:
            raise ValidationError("Employee role is required")
        
        role = cls._sanitize_string(role)
        
        if not cls.PATTERNS['role'].match(role):
            raise ValidationError(
                "Role must be 1-100 characters, alphanumeric, spaces, underscore, or hyphen only"
            )
        
        return role
    
    @classmethod
    def validate_task_description(cls, task: str) -> str:
        """Validate and sanitize task description"""
        if not task:
            raise ValidationError("Task description is required")
        
        task = cls._sanitize_string(task)
        
        if not cls.PATTERNS['task_description'].match(task):
            raise ValidationError("Task description must be 1-5000 characters")
        
        # Check for dangerous patterns
        cls._check_dangerous_patterns(task)
        
        return task
    
    @classmethod
    def validate_model_name(cls, model: str) -> str:
        """Validate and sanitize model name"""
        if not model:
            raise ValidationError("Model name is required")
        
        model = cls._sanitize_string(model)
        
        if not cls.PATTERNS['model_name'].match(model):
            raise ValidationError(
                "Model name must be 1-100 characters, alphanumeric, slash, dot, underscore, or hyphen only"
            )
        
        return model
    
    @classmethod
    def validate_mode(cls, mode: str) -> str:
        """Validate task mode"""
        if not mode:
            raise ValidationError("Mode is required")
        
        mode = cls._sanitize_string(mode).lower()
        
        if not cls.PATTERNS['mode'].match(mode):
            raise ValidationError("Mode must be one of: build, chat, edit")
        
        return mode
    
    @classmethod
    def validate_file_paths(cls, files: List[str]) -> List[str]:
        """Validate and sanitize file paths"""
        if not files:
            raise ValidationError("File paths are required")
        
        if not isinstance(files, list):
            raise ValidationError("Files must be a list")
        
        if len(files) > 100:
            raise ValidationError("Too many files (max 100)")
        
        validated_files = []
        for file_path in files:
            if not isinstance(file_path, str):
                raise ValidationError("File path must be a string")
            
            file_path = cls._sanitize_string(file_path)
            
            if not cls.PATTERNS['file_path'].match(file_path):
                raise ValidationError(f"Invalid file path format: {file_path}")
            
            # Check for path traversal attempts
            if '..' in file_path or file_path.startswith('/'):
                raise ValidationError(f"Invalid file path (path traversal detected): {file_path}")
            
            validated_files.append(file_path)
        
        return validated_files
    
    @classmethod
    def validate_json_payload(cls, data: Dict[str, Any], required_fields: List[str] = None) -> Dict[str, Any]:
        """Validate JSON payload structure"""
        if not isinstance(data, dict):
            raise ValidationError("Request body must be valid JSON object")
        
        if required_fields:
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                raise ValidationError(f"Missing required fields: {missing_fields}")
        
        # Limit payload size
        if len(str(data)) > 100000:  # 100KB limit
            raise ValidationError("Request payload too large")
        
        return data
    
    @classmethod
    def validate_query_params(cls, params: Dict[str, str]) -> Dict[str, str]:
        """Validate query parameters"""
        validated_params = {}
        
        for key, value in params.items():
            if not isinstance(key, str) or not isinstance(value, str):
                continue
            
            # Sanitize key and value
            key = cls._sanitize_string(key)
            value = cls._sanitize_string(value)
            
            # Limit parameter length
            if len(key) > 100 or len(value) > 1000:
                logger.warning(f"Skipping oversized parameter: {key}")
                continue
            
            validated_params[key] = value
        
        return validated_params
    
    @classmethod
    def _sanitize_string(cls, value: str) -> str:
        """Basic string sanitization"""
        if not isinstance(value, str):
            raise ValidationError("Value must be a string")
        
        # Remove null bytes and control characters
        value = ''.join(char for char in value if ord(char) >= 32 or char in '\t\n\r')
        
        # HTML escape
        value = html.escape(value)
        
        # Strip whitespace
        value = value.strip()
        
        return value
    
    @classmethod
    def _check_dangerous_patterns(cls, value: str):
        """Check for dangerous patterns in input"""
        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern.search(value):
                raise ValidationError(f"Potentially dangerous input detected")
    
    @classmethod
    def sanitize_log_message(cls, message: str) -> str:
        """Sanitize message for safe logging"""
        if not isinstance(message, str):
            return str(message)
        
        # Remove potential log injection patterns
        message = message.replace('\n', ' ').replace('\r', ' ')
        message = message.replace('\t', ' ')
        
        # Limit length
        if len(message) > 1000:
            message = message[:997] + "..."
        
        return message

def validate_request_data(data: Dict[str, Any], validation_rules: Dict[str, str]) -> Dict[str, Any]:
    """
    Validate request data against validation rules.
    
    Args:
        data: Request data to validate
        validation_rules: Dict mapping field names to validation methods
    
    Returns:
        Validated and sanitized data
    
    Raises:
        ValidationError: If validation fails
    """
    validated_data = {}
    
    for field, rule in validation_rules.items():
        value = data.get(field)
        
        if hasattr(InputValidator, f'validate_{rule}'):
            validator = getattr(InputValidator, f'validate_{rule}')
            try:
                validated_data[field] = validator(value)
            except ValidationError as e:
                raise ValidationError(f"Validation failed for field '{field}': {str(e)}")
        else:
            # Fallback to basic sanitization
            if isinstance(value, str):
                validated_data[field] = InputValidator._sanitize_string(value)
            else:
                validated_data[field] = value
    
    return validated_data