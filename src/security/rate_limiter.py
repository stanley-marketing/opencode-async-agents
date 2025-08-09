"""
Rate limiting system for OpenCode-Slack API.
Implements per-endpoint and per-user rate limiting.
"""

from collections import defaultdict, deque
from flask import request, jsonify
from functools import wraps
from typing import Dict, Tuple, Optional
import logging
import threading
import time

logger = logging.getLogger(__name__)

class RateLimiter:
    """Thread-safe rate limiter with sliding window algorithm"""

    def __init__(self):
        self.requests = defaultdict(deque)  # {key: deque of timestamps}
        self.lock = threading.RLock()

        # Default rate limits (requests per minute)
        self.default_limits = {
            "global": 1000,      # Global limit per IP
            "auth": 10,          # Authentication endpoints
            "employees": 60,     # Employee management
            "tasks": 30,         # Task operations
            "files": 100,        # File operations
            "monitoring": 120,   # Monitoring endpoints
            "chat": 50,          # Chat operations
        }

        # Per-user limits (higher for authenticated users)
        self.user_limits = {
            "global": 2000,
            "auth": 20,
            "employees": 120,
            "tasks": 60,
            "files": 200,
            "monitoring": 240,
            "chat": 100,
        }

        logger.info("Rate limiter initialized")

    def _get_client_id(self) -> str:
        """Get client identifier (IP or authenticated user)"""
        # Try to get authenticated user first
        if hasattr(request, 'auth_info') and request.auth_info:
            if request.auth_info.get("type") == "jwt":
                return f"user:{request.auth_info['username']}"
            elif request.auth_info.get("type") == "api_key":
                return f"api_key:{request.auth_info['name']}"

        # Fall back to IP address
        return f"ip:{request.remote_addr}"

    def _get_endpoint_category(self, endpoint: str) -> str:
        """Categorize endpoint for rate limiting"""
        if "/auth/" in endpoint or endpoint.endswith("/login"):
            return "auth"
        elif "/employees" in endpoint:
            return "employees"
        elif "/tasks" in endpoint:
            return "tasks"
        elif "/files" in endpoint:
            return "files"
        elif "/monitoring" in endpoint:
            return "monitoring"
        elif "/chat" in endpoint:
            return "chat"
        else:
            return "global"

    def _cleanup_old_requests(self, request_times: deque, window_seconds: int = 60):
        """Remove requests older than the time window"""
        current_time = time.time()
        while request_times and request_times[0] < current_time - window_seconds:
            request_times.popleft()

    def is_allowed(self, client_id: str, endpoint: str, limit: int = None) -> Tuple[bool, Dict]:
        """Check if request is allowed under rate limit"""
        with self.lock:
            current_time = time.time()
            category = self._get_endpoint_category(endpoint)

            # Determine rate limit
            if limit is None:
                if client_id.startswith("user:") or client_id.startswith("api_key:"):
                    limit = self.user_limits.get(category, self.user_limits["global"])
                else:
                    limit = self.default_limits.get(category, self.default_limits["global"])

            # Create unique key for this client and category
            key = f"{client_id}:{category}"
            request_times = self.requests[key]

            # Clean up old requests
            self._cleanup_old_requests(request_times)

            # Check if under limit
            if len(request_times) < limit:
                request_times.append(current_time)
                remaining = limit - len(request_times)

                return True, {
                    "allowed": True,
                    "limit": limit,
                    "remaining": remaining,
                    "reset_time": int(current_time + 60),
                    "category": category
                }
            else:
                # Calculate when the limit will reset
                oldest_request = request_times[0] if request_times else current_time
                reset_time = int(oldest_request + 60)

                return False, {
                    "allowed": False,
                    "limit": limit,
                    "remaining": 0,
                    "reset_time": reset_time,
                    "category": category,
                    "retry_after": reset_time - int(current_time)
                }

    def get_stats(self) -> Dict:
        """Get rate limiting statistics"""
        with self.lock:
            current_time = time.time()
            stats = {
                "total_clients": len(self.requests),
                "active_clients": 0,
                "total_requests_last_minute": 0,
                "categories": defaultdict(int)
            }

            for key, request_times in self.requests.items():
                # Clean up old requests
                self._cleanup_old_requests(request_times)

                if request_times:
                    stats["active_clients"] += 1
                    stats["total_requests_last_minute"] += len(request_times)

                    # Count by category
                    category = key.split(":")[-1] if ":" in key else "unknown"
                    stats["categories"][category] += len(request_times)

            return dict(stats)

# Global rate limiter instance
rate_limiter = RateLimiter()

def rate_limit(limit: int = None, per_minute: bool = True):
    """Decorator to apply rate limiting to endpoints"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                client_id = rate_limiter._get_client_id()
                endpoint = request.endpoint or request.path

                allowed, info = rate_limiter.is_allowed(client_id, endpoint, limit)

                if not allowed:
                    logger.warning(f"Rate limit exceeded for {client_id} on {endpoint}")

                    response = jsonify({
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests. Limit: {info['limit']} per minute",
                        "limit": info["limit"],
                        "remaining": info["remaining"],
                        "reset_time": info["reset_time"],
                        "retry_after": info.get("retry_after", 60)
                    })

                    # Add rate limit headers
                    response.headers["X-RateLimit-Limit"] = str(info["limit"])
                    response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
                    response.headers["X-RateLimit-Reset"] = str(info["reset_time"])
                    response.headers["Retry-After"] = str(info.get("retry_after", 60))

                    return response, 429

                # Add rate limit headers to successful responses
                response = f(*args, **kwargs)

                # Handle both Response objects and tuples
                if isinstance(response, tuple):
                    response_obj, status_code = response[0], response[1]
                else:
                    response_obj, status_code = response, 200

                if hasattr(response_obj, 'headers'):
                    response_obj.headers["X-RateLimit-Limit"] = str(info["limit"])
                    response_obj.headers["X-RateLimit-Remaining"] = str(info["remaining"])
                    response_obj.headers["X-RateLimit-Reset"] = str(info["reset_time"])

                return response

            except Exception as e:
                logger.error(f"Rate limiting error: {e}")
                # Continue without rate limiting if there's an error
                return f(*args, **kwargs)

        return decorated_function
    return decorator

def get_rate_limit_status() -> Dict:
    """Get current rate limiting status"""
    return rate_limiter.get_stats()