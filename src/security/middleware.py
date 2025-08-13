# SPDX-License-Identifier: MIT
"""
Security middleware for OpenCode-Slack API.
Provides request validation, security headers, and audit logging.
"""

from flask import request, jsonify, g
from functools import wraps
from typing import Dict, List, Any, Optional, Tuple
import ipaddress
import json
import logging
import re
import time

logger = logging.getLogger(__name__)

class SecurityMiddleware:
    """Security middleware for request processing"""

    def __init__(self):
        self.blocked_ips = set()
        self.allowed_ips = set()  # If set, only these IPs are allowed
        self.request_logs = []
        self.max_log_entries = 10000

        # Security patterns to detect potential attacks
        self.security_patterns = [
            r'<script[^>]*>.*?</script>',  # XSS
            r'javascript:',                # JavaScript injection
            r'on\w+\s*=',                 # Event handlers
            r'union\s+select',            # SQL injection
            r'drop\s+table',              # SQL injection
            r'insert\s+into',             # SQL injection
            r'delete\s+from',             # SQL injection
            r'\.\./.*\.\.',               # Path traversal
            r'etc/passwd',                # File access
            r'cmd\.exe',                  # Command injection
            r'/bin/sh',                   # Command injection
        ]

        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.security_patterns]

        logger.info("Security middleware initialized")

    def add_blocked_ip(self, ip: str):
        """Add IP to blocked list"""
        try:
            ipaddress.ip_address(ip)
            self.blocked_ips.add(ip)
            logger.info(f"IP blocked: {ip}")
        except ValueError:
            logger.error(f"Invalid IP address: {ip}")

    def remove_blocked_ip(self, ip: str):
        """Remove IP from blocked list"""
        self.blocked_ips.discard(ip)
        logger.info(f"IP unblocked: {ip}")

    def set_allowed_ips(self, ips: List[str]):
        """Set list of allowed IPs (whitelist mode)"""
        self.allowed_ips = set()
        for ip in ips:
            try:
                ipaddress.ip_address(ip)
                self.allowed_ips.add(ip)
            except ValueError:
                logger.error(f"Invalid IP address: {ip}")

        if self.allowed_ips:
            logger.info(f"IP whitelist enabled with {len(self.allowed_ips)} addresses")

    def is_ip_allowed(self, ip: str) -> bool:
        """Check if IP is allowed"""
        # Check if IP is blocked
        if ip in self.blocked_ips:
            return False

        # Check whitelist if enabled
        if self.allowed_ips and ip not in self.allowed_ips:
            return False

        return True

    def validate_input(self, data: Any) -> Tuple[bool, List[str]]:
        """Validate input data for security threats"""
        threats = []

        def check_string(s: str, context: str = ""):
            for pattern in self.compiled_patterns:
                if pattern.search(s):
                    threats.append(f"Potential security threat detected in {context}: {pattern.pattern}")

        def recursive_check(obj, path=""):
            if isinstance(obj, str):
                check_string(obj, path)
            elif isinstance(obj, dict):
                for key, value in obj.items():
                    check_string(str(key), f"{path}.{key}")
                    recursive_check(value, f"{path}.{key}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    recursive_check(item, f"{path}[{i}]")

        try:
            if isinstance(data, str):
                check_string(data, "string input")
            else:
                recursive_check(data, "input")
        except Exception as e:
            logger.error(f"Error during input validation: {e}")
            threats.append("Input validation error")

        return len(threats) == 0, threats

    def log_request(self, request_data: Dict):
        """Log request for security auditing"""
        log_entry = {
            "timestamp": time.time(),
            "ip": request_data.get("ip"),
            "method": request_data.get("method"),
            "path": request_data.get("path"),
            "user_agent": request_data.get("user_agent"),
            "auth_info": request_data.get("auth_info"),
            "status_code": request_data.get("status_code"),
            "response_time": request_data.get("response_time"),
            "threats": request_data.get("threats", [])
        }

        self.request_logs.append(log_entry)

        # Keep only recent logs
        if len(self.request_logs) > self.max_log_entries:
            self.request_logs = self.request_logs[-self.max_log_entries:]

        # Log security threats
        if log_entry["threats"]:
            logger.warning(f"Security threats detected from {log_entry['ip']}: {log_entry['threats']}")

    def get_security_stats(self) -> Dict:
        """Get security statistics"""
        recent_logs = [log for log in self.request_logs if time.time() - log["timestamp"] < 3600]  # Last hour

        threat_count = sum(1 for log in recent_logs if log["threats"])
        unique_ips = len(set(log["ip"] for log in recent_logs))

        return {
            "total_requests_last_hour": len(recent_logs),
            "threats_detected_last_hour": threat_count,
            "unique_ips_last_hour": unique_ips,
            "blocked_ips": len(self.blocked_ips),
            "whitelist_enabled": len(self.allowed_ips) > 0,
            "allowed_ips": len(self.allowed_ips)
        }

# Global security middleware instance
security_middleware = SecurityMiddleware()

def security_headers():
    """Decorator to add security headers to responses"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            response = f(*args, **kwargs)

            # Handle both Response objects and tuples
            if isinstance(response, tuple):
                response_obj = response[0]
            else:
                response_obj = response

            if hasattr(response_obj, 'headers'):
                # Security headers
                response_obj.headers["X-Content-Type-Options"] = "nosniff"
                response_obj.headers["X-Frame-Options"] = "DENY"
                response_obj.headers["X-XSS-Protection"] = "1; mode=block"
                response_obj.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
                response_obj.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
                response_obj.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                response_obj.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

            return response

        return decorated_function
    return decorator

def validate_request():
    """Decorator to validate requests for security threats"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()

            # Check IP restrictions
            client_ip = request.remote_addr
            if not security_middleware.is_ip_allowed(client_ip):
                logger.warning(f"Blocked request from IP: {client_ip}")
                return jsonify({"error": "Access denied"}), 403

            # Validate request data
            threats = []

            # Check URL parameters
            for key, value in request.args.items():
                is_safe, param_threats = security_middleware.validate_input(f"{key}={value}")
                if not is_safe:
                    threats.extend(param_threats)

            # Check JSON data
            if request.is_json:
                try:
                    json_data = request.get_json()
                    if json_data:
                        is_safe, json_threats = security_middleware.validate_input(json_data)
                        if not is_safe:
                            threats.extend(json_threats)
                except Exception as e:
                    logger.error(f"Error parsing JSON: {e}")
                    return jsonify({"error": "Invalid JSON data"}), 400

            # Check form data
            if request.form:
                for key, value in request.form.items():
                    is_safe, form_threats = security_middleware.validate_input(f"{key}={value}")
                    if not is_safe:
                        threats.extend(form_threats)

            # Block request if threats detected
            if threats:
                logger.warning(f"Security threats detected from {client_ip}: {threats}")

                # Log the threat
                security_middleware.log_request({
                    "ip": client_ip,
                    "method": request.method,
                    "path": request.path,
                    "user_agent": request.headers.get("User-Agent"),
                    "auth_info": getattr(request, "auth_info", None),
                    "status_code": 400,
                    "response_time": time.time() - start_time,
                    "threats": threats
                })

                return jsonify({
                    "error": "Request blocked due to security policy",
                    "message": "Potentially malicious content detected"
                }), 400

            # Execute the original function
            try:
                response = f(*args, **kwargs)
                status_code = 200

                if isinstance(response, tuple):
                    status_code = response[1] if len(response) > 1 else 200

                # Log successful request
                security_middleware.log_request({
                    "ip": client_ip,
                    "method": request.method,
                    "path": request.path,
                    "user_agent": request.headers.get("User-Agent"),
                    "auth_info": getattr(request, "auth_info", None),
                    "status_code": status_code,
                    "response_time": time.time() - start_time,
                    "threats": []
                })

                return response

            except Exception as e:
                logger.error(f"Request processing error: {e}")

                # Log error
                security_middleware.log_request({
                    "ip": client_ip,
                    "method": request.method,
                    "path": request.path,
                    "user_agent": request.headers.get("User-Agent"),
                    "auth_info": getattr(request, "auth_info", None),
                    "status_code": 500,
                    "response_time": time.time() - start_time,
                    "threats": []
                })

                return jsonify({"error": "Internal server error"}), 500

        return decorated_function
    return decorator

def cors_headers():
    """Decorator to add CORS headers for production"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            response = f(*args, **kwargs)

            # Handle both Response objects and tuples
            if isinstance(response, tuple):
                response_obj = response[0]
            else:
                response_obj = response

            if hasattr(response_obj, 'headers'):
                # Restrictive CORS headers for production
                response_obj.headers["Access-Control-Allow-Origin"] = "https://your-domain.com"  # Replace with actual domain
                response_obj.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                response_obj.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Key"
                response_obj.headers["Access-Control-Allow-Credentials"] = "true"
                response_obj.headers["Access-Control-Max-Age"] = "3600"

            return response

        return decorated_function
    return decorator