#!/usr/bin/env python3
"""
Configuration Loader for OpenCode-Slack
Loads configuration from YAML files and environment variables
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ConfigPaths:
    """Configuration file paths"""
    config_dir: Path
    main_config: Path
    env_dir: Path
    models_config: Path
    performance_config: Path
    
    @classmethod
    def from_project_root(cls, project_root: Optional[str] = None) -> 'ConfigPaths':
        """Create ConfigPaths from project root"""
        if project_root is None:
            project_root = os.environ.get('PROJECT_ROOT', os.getcwd())
        
        root = Path(project_root)
        config_dir = root / 'config'
        
        return cls(
            config_dir=config_dir,
            main_config=config_dir / 'config.yaml',
            env_dir=config_dir / 'environments',
            models_config=config_dir / 'models.json',
            performance_config=config_dir / 'performance.json'
        )

class ConfigLoader:
    """Loads and manages configuration for OpenCode-Slack"""
    
    def __init__(self, environment: str = None, project_root: str = None):
        """
        Initialize configuration loader
        
        Args:
            environment: Environment name (development, production, etc.)
            project_root: Project root directory path
        """
        self.environment = environment or os.environ.get('ENVIRONMENT', 'development')
        self.paths = ConfigPaths.from_project_root(project_root)
        self._config = {}
        self._env_vars = {}
        
    def load_config(self) -> Dict[str, Any]:
        """Load complete configuration"""
        try:
            # Load environment variables first
            self._load_environment_file()
            
            # Load main configuration
            self._load_main_config()
            
            # Load additional configs
            self._load_models_config()
            self._load_performance_config()
            
            # Substitute environment variables
            self._substitute_env_vars()
            
            logger.info(f"Configuration loaded successfully for environment: {self.environment}")
            return self._config
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _load_environment_file(self):
        """Load environment-specific .env file"""
        env_file = self.paths.env_dir / f'.env.{self.environment}'
        
        if not env_file.exists():
            logger.warning(f"Environment file not found: {env_file}")
            return
        
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        
                        # Set in environment if not already set
                        if key not in os.environ:
                            os.environ[key] = value
                        
                        self._env_vars[key] = value
            
            logger.info(f"Loaded environment file: {env_file}")
            
        except Exception as e:
            logger.error(f"Failed to load environment file {env_file}: {e}")
            raise
    
    def _load_main_config(self):
        """Load main YAML configuration"""
        if not self.paths.main_config.exists():
            logger.error(f"Main configuration file not found: {self.paths.main_config}")
            raise FileNotFoundError(f"Configuration file not found: {self.paths.main_config}")
        
        try:
            with open(self.paths.main_config, 'r') as f:
                self._config = yaml.safe_load(f)
            
            logger.info(f"Loaded main configuration: {self.paths.main_config}")
            
        except Exception as e:
            logger.error(f"Failed to load main configuration: {e}")
            raise
    
    def _load_models_config(self):
        """Load models configuration"""
        if self.paths.models_config.exists():
            try:
                with open(self.paths.models_config, 'r') as f:
                    models_config = json.load(f)
                
                self._config['models'] = models_config
                logger.info(f"Loaded models configuration: {self.paths.models_config}")
                
            except Exception as e:
                logger.warning(f"Failed to load models configuration: {e}")
    
    def _load_performance_config(self):
        """Load performance configuration"""
        if self.paths.performance_config.exists():
            try:
                with open(self.paths.performance_config, 'r') as f:
                    perf_config = json.load(f)
                
                # Merge with existing performance config
                if 'performance' not in self._config:
                    self._config['performance'] = {}
                
                self._config['performance'].update(perf_config)
                logger.info(f"Loaded performance configuration: {self.paths.performance_config}")
                
            except Exception as e:
                logger.warning(f"Failed to load performance configuration: {e}")
    
    def _substitute_env_vars(self):
        """Substitute environment variables in configuration"""
        self._config = self._substitute_recursive(self._config)
    
    def _substitute_recursive(self, obj):
        """Recursively substitute environment variables"""
        if isinstance(obj, dict):
            return {k: self._substitute_recursive(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_recursive(item) for item in obj]
        elif isinstance(obj, str):
            return self._substitute_env_var(obj)
        else:
            return obj
    
    def _substitute_env_var(self, value: str) -> str:
        """Substitute environment variable in string"""
        if not value.startswith('${') or not value.endswith('}'):
            return value
        
        # Extract variable name and default value
        var_expr = value[2:-1]  # Remove ${ and }
        
        if ':-' in var_expr:
            var_name, default_value = var_expr.split(':-', 1)
        else:
            var_name = var_expr
            default_value = ''
        
        # Get value from environment
        env_value = os.environ.get(var_name, default_value)
        
        # Convert boolean strings
        if env_value.lower() in ('true', 'false'):
            return env_value.lower() == 'true'
        
        # Convert numeric strings
        if env_value.isdigit():
            return int(env_value)
        
        try:
            return float(env_value)
        except ValueError:
            pass
        
        return env_value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def validate_required_config(self) -> bool:
        """Validate that all required configuration is present"""
        required_vars = [
            'TELEGRAM_BOT_TOKEN',
            'TELEGRAM_CHAT_ID',
            'OPENAI_API_KEY',
            'SECRET_KEY',
            'ENCRYPTION_KEY'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            return False
        
        logger.info("All required configuration variables are present")
        return True
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return self.get('database', {})
    
    def get_server_config(self) -> Dict[str, Any]:
        """Get server configuration"""
        return self.get('server', {})
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration"""
        return self.get('monitoring', {})
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration"""
        return self.get('security', {})

# Global configuration instance
_config_loader = None

def get_config_loader(environment: str = None, project_root: str = None) -> ConfigLoader:
    """Get global configuration loader instance"""
    global _config_loader
    
    if _config_loader is None:
        _config_loader = ConfigLoader(environment, project_root)
        _config_loader.load_config()
    
    return _config_loader

def get_config(key: str = None, default: Any = None) -> Any:
    """Get configuration value"""
    loader = get_config_loader()
    
    if key is None:
        return loader._config
    
    return loader.get(key, default)

# Convenience functions
def get_database_config() -> Dict[str, Any]:
    """Get database configuration"""
    return get_config_loader().get_database_config()

def get_server_config() -> Dict[str, Any]:
    """Get server configuration"""
    return get_config_loader().get_server_config()

def get_monitoring_config() -> Dict[str, Any]:
    """Get monitoring configuration"""
    return get_config_loader().get_monitoring_config()

def get_security_config() -> Dict[str, Any]:
    """Get security configuration"""
    return get_config_loader().get_security_config()

if __name__ == '__main__':
    # Test configuration loading
    import sys
    
    env = sys.argv[1] if len(sys.argv) > 1 else 'development'
    
    try:
        loader = ConfigLoader(env)
        config = loader.load_config()
        
        print(f"Configuration loaded for environment: {env}")
        print(f"Server config: {loader.get_server_config()}")
        print(f"Database config: {loader.get_database_config()}")
        print(f"Validation passed: {loader.validate_required_config()}")
        
    except Exception as e:
        print(f"Configuration loading failed: {e}")
        sys.exit(1)