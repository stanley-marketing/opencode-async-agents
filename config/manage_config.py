#!/usr/bin/env python3
"""
Configuration Management Script for OpenCode-Slack
Provides utilities for managing configuration files and environments
"""

import os
import sys
import shutil
import secrets
import base64
from pathlib import Path
from typing import Dict, List, Optional
import argparse
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages OpenCode-Slack configuration"""
    
    def __init__(self, config_dir: str = 'config'):
        """Initialize configuration manager"""
        self.config_dir = Path(config_dir)
        self.env_dir = self.config_dir / 'environments'
    
    def create_environment(self, env_name: str, copy_from: str = None) -> bool:
        """Create a new environment configuration"""
        logger.info(f"Creating environment configuration: {env_name}")
        
        env_file = self.env_dir / f'.env.{env_name}'
        
        if env_file.exists():
            logger.error(f"Environment file already exists: {env_file}")
            return False
        
        # Determine source file
        if copy_from:
            source_file = self.env_dir / f'.env.{copy_from}'
            if not source_file.exists():
                logger.error(f"Source environment file not found: {source_file}")
                return False
        else:
            source_file = self.env_dir / '.env.template'
            if not source_file.exists():
                logger.error(f"Template file not found: {source_file}")
                return False
        
        try:
            # Copy source file
            shutil.copy2(source_file, env_file)
            
            # Update environment-specific values
            self._update_env_file(env_file, env_name)
            
            logger.info(f"✅ Created environment configuration: {env_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create environment configuration: {e}")
            return False
    
    def _update_env_file(self, env_file: Path, env_name: str):
        """Update environment-specific values in env file"""
        try:
            with open(env_file, 'r') as f:
                content = f.read()
            
            # Update environment name
            content = content.replace('ENVIRONMENT=development', f'ENVIRONMENT={env_name}')
            
            # Update paths for different environments
            if env_name == 'production':
                content = content.replace('DATABASE_PATH=employees.db', 
                                        'DATABASE_PATH=/var/lib/opencode-slack/employees.db')
                content = content.replace('SESSIONS_DIR=sessions', 
                                        'SESSIONS_DIR=/var/lib/opencode-slack/sessions')
                content = content.replace('LOG_FILE=logs/app.log', 
                                        'LOG_FILE=/var/log/opencode-slack/app.log')
                content = content.replace('SERVER_HOST=localhost', 
                                        'SERVER_HOST=0.0.0.0')
                content = content.replace('DEBUG_MODE=true', 
                                        'DEBUG_MODE=false')
                content = content.replace('LOG_LEVEL=DEBUG', 
                                        'LOG_LEVEL=INFO')
            elif env_name == 'staging':
                content = content.replace('DATABASE_PATH=employees.db', 
                                        f'DATABASE_PATH=data/employees_{env_name}.db')
                content = content.replace('SESSIONS_DIR=sessions', 
                                        f'SESSIONS_DIR=sessions_{env_name}')
                content = content.replace('LOG_FILE=logs/app.log', 
                                        f'LOG_FILE=logs/app_{env_name}.log')
                content = content.replace('LOG_LEVEL=DEBUG', 
                                        'LOG_LEVEL=INFO')
            
            with open(env_file, 'w') as f:
                f.write(content)
                
        except Exception as e:
            logger.error(f"Failed to update environment file: {e}")
    
    def generate_secrets(self, env_name: str) -> bool:
        """Generate secure secrets for an environment"""
        logger.info(f"Generating secrets for environment: {env_name}")
        
        env_file = self.env_dir / f'.env.{env_name}'
        if not env_file.exists():
            logger.error(f"Environment file not found: {env_file}")
            return False
        
        try:
            # Generate secrets
            secret_key = secrets.token_urlsafe(32)
            encryption_key = base64.b64encode(secrets.token_bytes(32)).decode('utf-8')
            admin_password = secrets.token_urlsafe(16)
            dashboard_secret = secrets.token_urlsafe(32)
            
            # Read current content
            with open(env_file, 'r') as f:
                lines = f.readlines()
            
            # Update secret values
            updated_lines = []
            for line in lines:
                if line.startswith('SECRET_KEY=') and 'your_' in line:
                    updated_lines.append(f'SECRET_KEY={secret_key}\n')
                elif line.startswith('ENCRYPTION_KEY=') and 'your_' in line:
                    updated_lines.append(f'ENCRYPTION_KEY={encryption_key}\n')
                elif line.startswith('ADMIN_PASSWORD=') and 'your_' in line:
                    updated_lines.append(f'ADMIN_PASSWORD={admin_password}\n')
                elif line.startswith('DASHBOARD_SECRET_KEY=') and 'your_' in line:
                    updated_lines.append(f'DASHBOARD_SECRET_KEY={dashboard_secret}\n')
                else:
                    updated_lines.append(line)
            
            # Write updated content
            with open(env_file, 'w') as f:
                f.writelines(updated_lines)
            
            logger.info(f"✅ Generated secrets for: {env_file}")
            logger.info("🔐 Generated secrets:")
            logger.info(f"  • SECRET_KEY: {secret_key[:10]}...")
            logger.info(f"  • ENCRYPTION_KEY: {encryption_key[:10]}...")
            logger.info(f"  • ADMIN_PASSWORD: {admin_password}")
            logger.info(f"  • DASHBOARD_SECRET_KEY: {dashboard_secret[:10]}...")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate secrets: {e}")
            return False
    
    def validate_environment(self, env_name: str) -> bool:
        """Validate environment configuration"""
        logger.info(f"Validating environment: {env_name}")
        
        env_file = self.env_dir / f'.env.{env_name}'
        if not env_file.exists():
            logger.error(f"Environment file not found: {env_file}")
            return False
        
        try:
            # Load environment variables
            env_vars = {}
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
            
            # Check required variables
            required_vars = [
                'ENVIRONMENT',
                'SECRET_KEY',
                'ENCRYPTION_KEY',
                'SERVER_HOST',
                'SERVER_PORT',
                'DATABASE_PATH',
                'SESSIONS_DIR',
                'LOG_LEVEL',
                'LOG_FILE'
            ]
            
            missing_vars = []
            placeholder_vars = []
            
            for var in required_vars:
                if var not in env_vars:
                    missing_vars.append(var)
                elif 'your_' in env_vars[var].lower() or env_vars[var] in ['', 'changeme']:
                    placeholder_vars.append(var)
            
            # Report results
            if missing_vars:
                logger.error(f"Missing required variables: {missing_vars}")
                return False
            
            if placeholder_vars:
                logger.warning(f"Variables with placeholder values: {placeholder_vars}")
            
            # Validate specific values
            if env_vars.get('ENVIRONMENT') != env_name:
                logger.warning(f"Environment mismatch: file says {env_vars.get('ENVIRONMENT')}, expected {env_name}")
            
            # Check secret strength
            secret_key = env_vars.get('SECRET_KEY', '')
            if len(secret_key) < 32:
                logger.warning("SECRET_KEY should be at least 32 characters long")
            
            logger.info(f"✅ Environment validation completed: {env_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate environment: {e}")
            return False
    
    def list_environments(self) -> List[str]:
        """List available environment configurations"""
        if not self.env_dir.exists():
            return []
        
        env_files = list(self.env_dir.glob('.env.*'))
        environments = []
        
        for env_file in env_files:
            env_name = env_file.name.replace('.env.', '')
            if env_name != 'template':
                environments.append(env_name)
        
        return sorted(environments)
    
    def backup_config(self, backup_dir: str = None) -> bool:
        """Create backup of configuration"""
        if backup_dir is None:
            backup_dir = f"config_backup_{os.getpid()}"
        
        backup_path = Path(backup_dir)
        
        try:
            if backup_path.exists():
                shutil.rmtree(backup_path)
            
            shutil.copytree(self.config_dir, backup_path)
            logger.info(f"✅ Configuration backed up to: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to backup configuration: {e}")
            return False
    
    def set_file_permissions(self) -> bool:
        """Set secure file permissions on configuration files"""
        logger.info("Setting secure file permissions...")
        
        try:
            # Set permissions on environment files (600 - owner read/write only)
            for env_file in self.env_dir.glob('.env.*'):
                if env_file.name != '.env.template':
                    env_file.chmod(0o600)
                    logger.info(f"Set permissions 600 on: {env_file}")
            
            # Set permissions on other config files (644 - owner read/write, group/other read)
            for config_file in self.config_dir.rglob('*.yaml'):
                config_file.chmod(0o644)
            
            for config_file in self.config_dir.rglob('*.yml'):
                config_file.chmod(0o644)
            
            for config_file in self.config_dir.rglob('*.json'):
                config_file.chmod(0o644)
            
            logger.info("✅ File permissions set successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set file permissions: {e}")
            return False
    
    def clean_test_files(self) -> bool:
        """Clean up test and temporary configuration files"""
        logger.info("Cleaning up test and temporary files...")
        
        try:
            # Patterns for files to clean
            cleanup_patterns = [
                '*test*',
                '*tmp*',
                '*temp*',
                '*.bak',
                '*.backup',
                '*~'
            ]
            
            cleaned_files = []
            for pattern in cleanup_patterns:
                for file_path in self.config_dir.rglob(pattern):
                    if file_path.is_file():
                        file_path.unlink()
                        cleaned_files.append(str(file_path))
            
            if cleaned_files:
                logger.info(f"✅ Cleaned {len(cleaned_files)} files:")
                for file_path in cleaned_files:
                    logger.info(f"  • {file_path}")
            else:
                logger.info("No temporary files found to clean")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to clean test files: {e}")
            return False

def main():
    """Main configuration management function"""
    parser = argparse.ArgumentParser(description='Manage OpenCode-Slack configuration')
    parser.add_argument('--config-dir', default='config', help='Configuration directory path')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create environment command
    create_parser = subparsers.add_parser('create-env', help='Create new environment')
    create_parser.add_argument('name', help='Environment name')
    create_parser.add_argument('--copy-from', help='Copy from existing environment')
    
    # Generate secrets command
    secrets_parser = subparsers.add_parser('generate-secrets', help='Generate secrets for environment')
    secrets_parser.add_argument('name', help='Environment name')
    
    # Validate environment command
    validate_parser = subparsers.add_parser('validate-env', help='Validate environment')
    validate_parser.add_argument('name', help='Environment name')
    
    # List environments command
    subparsers.add_parser('list-envs', help='List available environments')
    
    # Backup configuration command
    backup_parser = subparsers.add_parser('backup', help='Backup configuration')
    backup_parser.add_argument('--dir', help='Backup directory')
    
    # Set permissions command
    subparsers.add_parser('set-permissions', help='Set secure file permissions')
    
    # Clean test files command
    subparsers.add_parser('clean', help='Clean test and temporary files')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize manager
    manager = ConfigManager(args.config_dir)
    
    # Execute command
    success = True
    
    if args.command == 'create-env':
        success = manager.create_environment(args.name, args.copy_from)
    elif args.command == 'generate-secrets':
        success = manager.generate_secrets(args.name)
    elif args.command == 'validate-env':
        success = manager.validate_environment(args.name)
    elif args.command == 'list-envs':
        envs = manager.list_environments()
        print("Available environments:")
        for env in envs:
            print(f"  • {env}")
    elif args.command == 'backup':
        success = manager.backup_config(args.dir)
    elif args.command == 'set-permissions':
        success = manager.set_file_permissions()
    elif args.command == 'clean':
        success = manager.clean_test_files()
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()