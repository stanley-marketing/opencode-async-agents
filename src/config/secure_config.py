# SPDX-License-Identifier: MIT
"""
Secure configuration management with validation and environment-specific loading.
"""
from dotenv import load_dotenv
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging
import os
import re
import secrets

logger = logging.getLogger(__name__)

class ConfigValidationError(Exception):
    """Raised when configuration validation fails"""
    pass

class SecureConfig:
    """Enhanced configuration management with security features"""

    # Required configuration keys for different environments
    REQUIRED_KEYS = {
        'development': [
            'OPENAI_API_KEY',
            'DATABASE_PATH',
            'SESSIONS_DIR'
        ],
        'production': [
            'OPENAI_API_KEY',
            'DATABASE_PATH',
            'SESSIONS_DIR',
            'SECRET_KEY',
            'LOG_FILE'
        ]
    }

    # Sensitive keys that should be masked in logs
    SENSITIVE_KEYS = {
        'OPENAI_API_KEY',
        'TELEGRAM_BOT_TOKEN',
        'SLACK_BOT_TOKEN',
        'SLACK_SIGNING_SECRET',
        'SECRET_KEY',
        'ENCRYPTION_KEY'
    }

    def __init__(self, environment: str = None):
        self.environment = environment or os.getenv('ENVIRONMENT', 'development')
        self._config = {}
        self._load_configuration()
        self._validate_configuration()

    def _load_configuration(self):
        """Load configuration from environment-specific files"""
        # Load base .env file first
        base_env_path = Path('.env')
        if base_env_path.exists():
            load_dotenv(base_env_path)
            logger.info("Loaded base .env configuration")

        # Load environment-specific configuration
        env_file_path = Path(f'.env.{self.environment}')
        if env_file_path.exists():
            load_dotenv(env_file_path, override=True)
            logger.info(f"Loaded {self.environment} environment configuration")
        else:
            logger.warning(f"Environment-specific config file not found: {env_file_path}")

        # Cache all environment variables
        self._config = dict(os.environ)

    def _validate_configuration(self):
        """Validate required configuration keys"""
        required_keys = self.REQUIRED_KEYS.get(self.environment, [])
        missing_keys = []

        for key in required_keys:
            if not self.get(key):
                missing_keys.append(key)

        if missing_keys:
            raise ConfigValidationError(
                f"Missing required configuration keys for {self.environment}: {missing_keys}"
            )

        # Validate API key formats
        self._validate_api_keys()

        logger.info(f"Configuration validation passed for {self.environment} environment")

    def _validate_api_keys(self):
        """Validate API key formats"""
        openai_key = self.get('OPENAI_API_KEY')
        if openai_key and not self._is_valid_openai_key(openai_key):
            logger.warning("OpenAI API key format appears invalid")

        telegram_token = self.get('TELEGRAM_BOT_TOKEN')
        if telegram_token and not self._is_valid_telegram_token(telegram_token):
            logger.warning("Telegram bot token format appears invalid")

    def _is_valid_openai_key(self, key: str) -> bool:
        """Validate OpenAI API key format"""
        return bool(re.match(r'^sk-[a-zA-Z0-9]{48,}$', key))

    def _is_valid_telegram_token(self, token: str) -> bool:
        """Validate Telegram bot token format"""
        return bool(re.match(r'^\d{8,10}:[a-zA-Z0-9_-]{35}$', token))

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with fallback"""
        value = self._config.get(key, default)

        # Convert string booleans
        if isinstance(value, str):
            if value.lower() in ('true', '1', 'yes', 'on'):
                return True
            elif value.lower() in ('false', '0', 'no', 'off'):
                return False

        return value

    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer configuration value"""
        try:
            return int(self.get(key, default))
        except (ValueError, TypeError):
            logger.warning(f"Invalid integer value for {key}, using default: {default}")
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get float configuration value"""
        try:
            return float(self.get(key, default))
        except (ValueError, TypeError):
            logger.warning(f"Invalid float value for {key}, using default: {default}")
            return default

    def get_list(self, key: str, separator: str = ',', default: List = None) -> List[str]:
        """Get list configuration value"""
        if default is None:
            default = []

        value = self.get(key)
        if not value:
            return default

        if isinstance(value, str):
            return [item.strip() for item in value.split(separator) if item.strip()]

        return default

    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment == 'production'

    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment == 'development'

    def get_masked_config(self) -> Dict[str, str]:
        """Get configuration with sensitive values masked"""
        masked_config = {}
        for key, value in self._config.items():
            if key in self.SENSITIVE_KEYS and value:
                masked_config[key] = f"{value[:8]}***{value[-4:]}" if len(value) > 12 else "***"
            else:
                masked_config[key] = value
        return masked_config

    def generate_secret_key(self) -> str:
        """Generate a secure secret key"""
        return secrets.token_urlsafe(32)

    def validate_paths(self):
        """Validate and create necessary directories"""
        paths_to_create = [
            self.get('SESSIONS_DIR', 'sessions'),
            Path(self.get('LOG_FILE', 'logs/app.log')).parent,
            Path(self.get('DATABASE_PATH', 'employees.db')).parent
        ]

        for path in paths_to_create:
            if path and path != '.':
                Path(path).mkdir(parents=True, exist_ok=True)
                logger.debug(f"Ensured directory exists: {path}")

# Global configuration instance
config = None

def get_config(environment: str = None) -> SecureConfig:
    """Get or create global configuration instance"""
    global config
    if config is None:
        config = SecureConfig(environment)
    return config

def init_config(environment: str = None) -> SecureConfig:
    """Initialize configuration for the application"""
    global config
    config = SecureConfig(environment)
    config.validate_paths()
    return config