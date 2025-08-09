#!/usr/bin/env python3
"""
Configuration Validation Script for OpenCode-Slack
Validates configuration files for syntax, completeness, and security
"""

import os
import sys
import json
import yaml
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
import logging
from dataclasses import dataclass

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of configuration validation"""
    passed: bool
    errors: List[str]
    warnings: List[str]
    recommendations: List[str]

class ConfigValidator:
    """Validates OpenCode-Slack configuration"""
    
    def __init__(self, config_dir: str = None):
        """Initialize validator"""
        self.config_dir = Path(config_dir or 'config')
        self.results = ValidationResult(True, [], [], [])
    
    def validate_all(self) -> ValidationResult:
        """Validate all configuration files"""
        logger.info("Starting comprehensive configuration validation...")
        
        # Validate directory structure
        self._validate_directory_structure()
        
        # Validate YAML files
        self._validate_yaml_files()
        
        # Validate JSON files
        self._validate_json_files()
        
        # Validate environment files
        self._validate_environment_files()
        
        # Validate deployment files
        self._validate_deployment_files()
        
        # Validate security configuration
        self._validate_security_config()
        
        # Validate file permissions
        self._validate_file_permissions()
        
        # Check for sensitive data exposure
        self._check_sensitive_data()
        
        # Validate configuration completeness
        self._validate_completeness()
        
        # Generate final result
        self.results.passed = len(self.results.errors) == 0
        
        return self.results
    
    def _validate_directory_structure(self):
        """Validate configuration directory structure"""
        logger.info("Validating directory structure...")
        
        required_dirs = [
            'environments',
            'deployment',
            'monitoring',
            'security'
        ]
        
        for dir_name in required_dirs:
            dir_path = self.config_dir / dir_name
            if not dir_path.exists():
                self.results.errors.append(f"Missing required directory: {dir_path}")
            elif not dir_path.is_dir():
                self.results.errors.append(f"Path exists but is not a directory: {dir_path}")
    
    def _validate_yaml_files(self):
        """Validate YAML configuration files"""
        logger.info("Validating YAML files...")
        
        yaml_files = list(self.config_dir.rglob('*.yaml')) + list(self.config_dir.rglob('*.yml'))
        
        for yaml_file in yaml_files:
            try:
                with open(yaml_file, 'r') as f:
                    yaml.safe_load(f)
                logger.info(f"✓ Valid YAML: {yaml_file}")
            except yaml.YAMLError as e:
                self.results.errors.append(f"Invalid YAML syntax in {yaml_file}: {e}")
            except Exception as e:
                self.results.errors.append(f"Error reading {yaml_file}: {e}")
    
    def _validate_json_files(self):
        """Validate JSON configuration files"""
        logger.info("Validating JSON files...")
        
        json_files = list(self.config_dir.rglob('*.json'))
        
        for json_file in json_files:
            try:
                with open(json_file, 'r') as f:
                    json.load(f)
                logger.info(f"✓ Valid JSON: {json_file}")
            except json.JSONDecodeError as e:
                self.results.errors.append(f"Invalid JSON syntax in {json_file}: {e}")
            except Exception as e:
                self.results.errors.append(f"Error reading {json_file}: {e}")
    
    def _validate_environment_files(self):
        """Validate environment configuration files"""
        logger.info("Validating environment files...")
        
        env_dir = self.config_dir / 'environments'
        if not env_dir.exists():
            return
        
        env_files = list(env_dir.glob('.env.*'))
        
        for env_file in env_files:
            self._validate_env_file(env_file)
    
    def _validate_env_file(self, env_file: Path):
        """Validate individual environment file"""
        try:
            with open(env_file, 'r') as f:
                lines = f.readlines()
            
            line_num = 0
            for line in lines:
                line_num += 1
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                # Check for valid key=value format
                if '=' not in line:
                    self.results.warnings.append(
                        f"Invalid format in {env_file}:{line_num}: {line}"
                    )
                    continue
                
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Validate key format
                if not re.match(r'^[A-Z][A-Z0-9_]*$', key):
                    self.results.warnings.append(
                        f"Non-standard environment variable name in {env_file}:{line_num}: {key}"
                    )
                
                # Check for placeholder values
                if value in ['your_', 'change_', 'replace_'] or 'your_' in value.lower():
                    self.results.warnings.append(
                        f"Placeholder value detected in {env_file}:{line_num}: {key}"
                    )
            
            logger.info(f"✓ Valid environment file: {env_file}")
            
        except Exception as e:
            self.results.errors.append(f"Error validating {env_file}: {e}")
    
    def _validate_deployment_files(self):
        """Validate deployment configuration files"""
        logger.info("Validating deployment files...")
        
        deployment_dir = self.config_dir / 'deployment'
        if not deployment_dir.exists():
            return
        
        # Check for required deployment files
        required_files = ['docker-compose.yml', 'Dockerfile', 'nginx.conf']
        
        for file_name in required_files:
            file_path = deployment_dir / file_name
            if not file_path.exists():
                self.results.warnings.append(f"Missing deployment file: {file_path}")
            else:
                logger.info(f"✓ Found deployment file: {file_path}")
        
        # Validate docker-compose.yml
        compose_file = deployment_dir / 'docker-compose.yml'
        if compose_file.exists():
            self._validate_docker_compose(compose_file)
    
    def _validate_docker_compose(self, compose_file: Path):
        """Validate docker-compose.yml file"""
        try:
            with open(compose_file, 'r') as f:
                compose_config = yaml.safe_load(f)
            
            # Check for required sections
            if 'services' not in compose_config:
                self.results.errors.append(f"Missing 'services' section in {compose_file}")
                return
            
            # Check for security best practices
            services = compose_config['services']
            for service_name, service_config in services.items():
                # Check for privileged mode
                if service_config.get('privileged'):
                    self.results.warnings.append(
                        f"Service '{service_name}' runs in privileged mode - security risk"
                    )
                
                # Check for host network mode
                if service_config.get('network_mode') == 'host':
                    self.results.warnings.append(
                        f"Service '{service_name}' uses host network mode - security risk"
                    )
                
                # Check for volume mounts
                volumes = service_config.get('volumes', [])
                for volume in volumes:
                    if isinstance(volume, str) and ':' in volume:
                        host_path, container_path = volume.split(':', 1)
                        if host_path.startswith('/'):
                            self.results.warnings.append(
                                f"Service '{service_name}' mounts host path '{host_path}' - review security"
                            )
            
            logger.info(f"✓ Valid docker-compose file: {compose_file}")
            
        except Exception as e:
            self.results.errors.append(f"Error validating docker-compose file: {e}")
    
    def _validate_security_config(self):
        """Validate security configuration"""
        logger.info("Validating security configuration...")
        
        security_file = self.config_dir / 'security' / 'security.yaml'
        if not security_file.exists():
            self.results.warnings.append("Missing security configuration file")
            return
        
        try:
            with open(security_file, 'r') as f:
                security_config = yaml.safe_load(f)
            
            # Check for required security sections
            required_sections = [
                'authentication',
                'api',
                'encryption',
                'network',
                'files'
            ]
            
            for section in required_sections:
                if section not in security_config:
                    self.results.warnings.append(f"Missing security section: {section}")
            
            # Validate specific security settings
            self._validate_security_settings(security_config)
            
            logger.info(f"✓ Valid security configuration: {security_file}")
            
        except Exception as e:
            self.results.errors.append(f"Error validating security configuration: {e}")
    
    def _validate_security_settings(self, security_config: Dict[str, Any]):
        """Validate specific security settings"""
        # Check TLS version
        tls_config = security_config.get('network', {}).get('tls', {})
        min_tls_version = tls_config.get('min_version')
        if min_tls_version and min_tls_version < "1.2":
            self.results.warnings.append("TLS version below 1.2 is not recommended")
        
        # Check password policy
        password_config = security_config.get('authentication', {}).get('password', {})
        min_length = password_config.get('min_length', 0)
        if min_length < 12:
            self.results.warnings.append("Password minimum length should be at least 12 characters")
        
        # Check session timeout
        session_config = security_config.get('authentication', {}).get('session', {})
        timeout = session_config.get('timeout', 0)
        if timeout > 86400:  # 24 hours
            self.results.warnings.append("Session timeout longer than 24 hours may be a security risk")
    
    def _validate_file_permissions(self):
        """Validate file permissions"""
        logger.info("Validating file permissions...")
        
        # Check permissions on sensitive files
        sensitive_patterns = [
            '*.env*',
            '*secret*',
            '*key*',
            '*password*'
        ]
        
        for pattern in sensitive_patterns:
            for file_path in self.config_dir.rglob(pattern):
                if file_path.is_file():
                    stat_info = file_path.stat()
                    mode = oct(stat_info.st_mode)[-3:]
                    
                    # Check if file is readable by others
                    if int(mode[2]) > 0:
                        self.results.warnings.append(
                            f"File {file_path} is readable by others (permissions: {mode})"
                        )
    
    def _check_sensitive_data(self):
        """Check for exposed sensitive data"""
        logger.info("Checking for sensitive data exposure...")
        
        # Patterns that might indicate sensitive data
        sensitive_patterns = [
            r'password\s*=\s*["\']?[^"\'\s]+',
            r'secret\s*=\s*["\']?[^"\'\s]+',
            r'key\s*=\s*["\']?[^"\'\s]+',
            r'token\s*=\s*["\']?[^"\'\s]+',
            r'api_key\s*=\s*["\']?[^"\'\s]+'
        ]
        
        # Files to check (exclude template files)
        config_files = []
        for ext in ['*.yaml', '*.yml', '*.json', '*.conf']:
            config_files.extend(self.config_dir.rglob(ext))
        
        for file_path in config_files:
            if 'template' in file_path.name.lower():
                continue
            
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                for pattern in sensitive_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        value = match.group().split('=')[1].strip().strip('"\'')
                        if not value.startswith('${') and 'your_' not in value.lower():
                            self.results.warnings.append(
                                f"Potential sensitive data in {file_path}: {match.group()}"
                            )
            
            except Exception as e:
                logger.warning(f"Could not check {file_path} for sensitive data: {e}")
    
    def _validate_completeness(self):
        """Validate configuration completeness"""
        logger.info("Validating configuration completeness...")
        
        # Check for required configuration files
        required_files = [
            'config.yaml',
            'models.json',
            'performance.json',
            'environments/.env.template',
            'environments/.env.development',
            'environments/.env.production'
        ]
        
        for file_path in required_files:
            full_path = self.config_dir / file_path
            if not full_path.exists():
                self.results.errors.append(f"Missing required configuration file: {full_path}")
        
        # Check for recommended files
        recommended_files = [
            'security/security.yaml',
            'deployment/docker-compose.yml',
            'deployment/Dockerfile',
            'monitoring/prometheus.yml'
        ]
        
        for file_path in recommended_files:
            full_path = self.config_dir / file_path
            if not full_path.exists():
                self.results.recommendations.append(f"Consider adding: {full_path}")
    
    def print_results(self):
        """Print validation results"""
        print("\n" + "="*60)
        print("CONFIGURATION VALIDATION RESULTS")
        print("="*60)
        
        if self.results.passed:
            print("✅ VALIDATION PASSED")
        else:
            print("❌ VALIDATION FAILED")
        
        if self.results.errors:
            print(f"\n🚨 ERRORS ({len(self.results.errors)}):")
            for error in self.results.errors:
                print(f"  • {error}")
        
        if self.results.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.results.warnings)}):")
            for warning in self.results.warnings:
                print(f"  • {warning}")
        
        if self.results.recommendations:
            print(f"\n💡 RECOMMENDATIONS ({len(self.results.recommendations)}):")
            for rec in self.results.recommendations:
                print(f"  • {rec}")
        
        print("\n" + "="*60)
        
        return self.results.passed

def main():
    """Main validation function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate OpenCode-Slack configuration')
    parser.add_argument('--config-dir', default='config', help='Configuration directory path')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')
    
    args = parser.parse_args()
    
    # Run validation
    validator = ConfigValidator(args.config_dir)
    results = validator.validate_all()
    
    if args.json:
        # Output JSON results
        json_results = {
            'passed': results.passed,
            'errors': results.errors,
            'warnings': results.warnings,
            'recommendations': results.recommendations
        }
        print(json.dumps(json_results, indent=2))
    else:
        # Print human-readable results
        success = validator.print_results()
        sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()