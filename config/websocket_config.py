"""
WebSocket configuration for OpenCode-Slack.
Provides configuration management for WebSocket transport.
"""

import os
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class WebSocketConfig:
    """WebSocket configuration settings"""
    
    # Server settings
    host: str = "localhost"
    port: int = 8765
    
    # Connection settings
    ping_interval: int = 30  # seconds
    ping_timeout: int = 10   # seconds
    max_connections: int = 100
    
    # Message settings
    max_message_size: int = 1024 * 1024  # 1MB
    message_queue_size: int = 1000
    
    # Authentication settings
    auth_timeout: int = 30  # seconds
    require_auth: bool = True
    
    # Rate limiting
    rate_limit_enabled: bool = True
    max_messages_per_minute: int = 60
    max_messages_per_hour: int = 1000
    
    # Reconnection settings
    auto_reconnect: bool = True
    reconnect_interval: int = 3  # seconds
    max_reconnect_attempts: int = 10
    
    # Logging
    log_level: str = "INFO"
    log_messages: bool = False  # Log all messages (for debugging)
    
    # CORS settings
    cors_origins: list = None
    
    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]


class WebSocketConfigManager:
    """Manages WebSocket configuration from environment and files"""
    
    def __init__(self):
        self._config = None
        
    def load_config(self) -> WebSocketConfig:
        """Load configuration from environment variables and defaults"""
        if self._config is None:
            self._config = self._create_config_from_env()
        return self._config
        
    def _create_config_from_env(self) -> WebSocketConfig:
        """Create configuration from environment variables"""
        return WebSocketConfig(
            # Server settings
            host=os.getenv('WEBSOCKET_HOST', 'localhost'),
            port=int(os.getenv('WEBSOCKET_PORT', '8765')),
            
            # Connection settings
            ping_interval=int(os.getenv('WEBSOCKET_PING_INTERVAL', '30')),
            ping_timeout=int(os.getenv('WEBSOCKET_PING_TIMEOUT', '10')),
            max_connections=int(os.getenv('WEBSOCKET_MAX_CONNECTIONS', '100')),
            
            # Message settings
            max_message_size=int(os.getenv('WEBSOCKET_MAX_MESSAGE_SIZE', str(1024 * 1024))),
            message_queue_size=int(os.getenv('WEBSOCKET_MESSAGE_QUEUE_SIZE', '1000')),
            
            # Authentication settings
            auth_timeout=int(os.getenv('WEBSOCKET_AUTH_TIMEOUT', '30')),
            require_auth=os.getenv('WEBSOCKET_REQUIRE_AUTH', 'true').lower() == 'true',
            
            # Rate limiting
            rate_limit_enabled=os.getenv('WEBSOCKET_RATE_LIMIT_ENABLED', 'true').lower() == 'true',
            max_messages_per_minute=int(os.getenv('WEBSOCKET_MAX_MESSAGES_PER_MINUTE', '60')),
            max_messages_per_hour=int(os.getenv('WEBSOCKET_MAX_MESSAGES_PER_HOUR', '1000')),
            
            # Reconnection settings
            auto_reconnect=os.getenv('WEBSOCKET_AUTO_RECONNECT', 'true').lower() == 'true',
            reconnect_interval=int(os.getenv('WEBSOCKET_RECONNECT_INTERVAL', '3')),
            max_reconnect_attempts=int(os.getenv('WEBSOCKET_MAX_RECONNECT_ATTEMPTS', '10')),
            
            # Logging
            log_level=os.getenv('WEBSOCKET_LOG_LEVEL', 'INFO'),
            log_messages=os.getenv('WEBSOCKET_LOG_MESSAGES', 'false').lower() == 'true',
            
            # CORS settings
            cors_origins=self._parse_cors_origins()
        )
        
    def _parse_cors_origins(self) -> list:
        """Parse CORS origins from environment variable"""
        cors_env = os.getenv('WEBSOCKET_CORS_ORIGINS', '')
        if cors_env:
            return [origin.strip() for origin in cors_env.split(',') if origin.strip()]
        else:
            return ["http://localhost:3000", "http://127.0.0.1:3000"]
            
    def get_server_config(self) -> Dict[str, Any]:
        """Get server configuration for websockets.serve()"""
        config = self.load_config()
        return {
            'host': config.host,
            'port': config.port,
            'ping_interval': config.ping_interval,
            'ping_timeout': config.ping_timeout,
            'max_size': config.max_message_size,
            'max_queue': config.message_queue_size
        }
        
    def get_client_config(self) -> Dict[str, Any]:
        """Get client configuration for frontend"""
        config = self.load_config()
        return {
            'url': f"ws://{config.host}:{config.port}",
            'auto_reconnect': config.auto_reconnect,
            'reconnect_interval': config.reconnect_interval * 1000,  # Convert to milliseconds
            'max_reconnect_attempts': config.max_reconnect_attempts,
            'ping_interval': config.ping_interval * 1000,  # Convert to milliseconds
            'auth_timeout': config.auth_timeout * 1000  # Convert to milliseconds
        }
        
    def validate_config(self) -> bool:
        """Validate configuration settings"""
        config = self.load_config()
        
        # Validate port range
        if not (1 <= config.port <= 65535):
            raise ValueError(f"Invalid port: {config.port}")
            
        # Validate timeouts
        if config.ping_timeout >= config.ping_interval:
            raise ValueError("ping_timeout must be less than ping_interval")
            
        if config.auth_timeout <= 0:
            raise ValueError("auth_timeout must be positive")
            
        # Validate rate limits
        if config.max_messages_per_minute <= 0:
            raise ValueError("max_messages_per_minute must be positive")
            
        if config.max_messages_per_hour <= 0:
            raise ValueError("max_messages_per_hour must be positive")
            
        # Validate reconnection settings
        if config.reconnect_interval <= 0:
            raise ValueError("reconnect_interval must be positive")
            
        if config.max_reconnect_attempts < 0:
            raise ValueError("max_reconnect_attempts must be non-negative")
            
        return True
        
    def update_config(self, **kwargs):
        """Update configuration with new values"""
        if self._config is None:
            self._config = self.load_config()
            
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
            else:
                raise ValueError(f"Unknown configuration key: {key}")
                
        # Validate updated configuration
        self.validate_config()
        
    def reset_config(self):
        """Reset configuration to defaults"""
        self._config = None


# Global configuration manager instance
config_manager = WebSocketConfigManager()


def get_websocket_config() -> WebSocketConfig:
    """Get the current WebSocket configuration"""
    return config_manager.load_config()


def get_server_config() -> Dict[str, Any]:
    """Get server configuration for websockets.serve()"""
    return config_manager.get_server_config()


def get_client_config() -> Dict[str, Any]:
    """Get client configuration for frontend"""
    return config_manager.get_client_config()


def validate_websocket_config() -> bool:
    """Validate the current WebSocket configuration"""
    return config_manager.validate_config()


# Environment variable documentation
ENV_VARS_DOCUMENTATION = """
WebSocket Configuration Environment Variables:

Server Settings:
  WEBSOCKET_HOST                    - WebSocket server host (default: localhost)
  WEBSOCKET_PORT                    - WebSocket server port (default: 8765)

Connection Settings:
  WEBSOCKET_PING_INTERVAL           - Ping interval in seconds (default: 30)
  WEBSOCKET_PING_TIMEOUT            - Ping timeout in seconds (default: 10)
  WEBSOCKET_MAX_CONNECTIONS         - Maximum concurrent connections (default: 100)

Message Settings:
  WEBSOCKET_MAX_MESSAGE_SIZE        - Maximum message size in bytes (default: 1048576)
  WEBSOCKET_MESSAGE_QUEUE_SIZE      - Message queue size (default: 1000)

Authentication Settings:
  WEBSOCKET_AUTH_TIMEOUT            - Authentication timeout in seconds (default: 30)
  WEBSOCKET_REQUIRE_AUTH            - Require authentication (default: true)

Rate Limiting:
  WEBSOCKET_RATE_LIMIT_ENABLED      - Enable rate limiting (default: true)
  WEBSOCKET_MAX_MESSAGES_PER_MINUTE - Max messages per minute (default: 60)
  WEBSOCKET_MAX_MESSAGES_PER_HOUR   - Max messages per hour (default: 1000)

Reconnection Settings:
  WEBSOCKET_AUTO_RECONNECT          - Enable auto-reconnection (default: true)
  WEBSOCKET_RECONNECT_INTERVAL      - Reconnect interval in seconds (default: 3)
  WEBSOCKET_MAX_RECONNECT_ATTEMPTS  - Max reconnection attempts (default: 10)

Logging:
  WEBSOCKET_LOG_LEVEL               - Log level (default: INFO)
  WEBSOCKET_LOG_MESSAGES            - Log all messages (default: false)

CORS Settings:
  WEBSOCKET_CORS_ORIGINS            - Comma-separated list of allowed origins
                                      (default: http://localhost:3000,http://127.0.0.1:3000)

Example .env file:
  WEBSOCKET_HOST=localhost
  WEBSOCKET_PORT=8765
  WEBSOCKET_PING_INTERVAL=30
  WEBSOCKET_REQUIRE_AUTH=true
  WEBSOCKET_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
"""


def print_env_vars_help():
    """Print environment variables documentation"""
    print(ENV_VARS_DOCUMENTATION)


if __name__ == "__main__":
    # Print configuration help
    print_env_vars_help()
    
    # Validate current configuration
    try:
        config = get_websocket_config()
        validate_websocket_config()
        print("\n✅ Current WebSocket configuration is valid")
        print(f"Server will run on: ws://{config.host}:{config.port}")
        print(f"Max connections: {config.max_connections}")
        print(f"Rate limiting: {'enabled' if config.rate_limit_enabled else 'disabled'}")
    except Exception as e:
        print(f"\n❌ Configuration error: {e}")