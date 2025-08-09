#!/usr/bin/env python3
"""
Comprehensive security audit script for OpenCode-Slack Agent Orchestration System.
"""

import os
import sys
import json
import stat
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SecurityAuditor:
    """Comprehensive security auditor for the OpenCode-Slack system"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.findings = []
        self.passed_checks = []
        
    def add_finding(self, severity: str, category: str, description: str, file_path: str = None, recommendation: str = None):
        """Add a security finding"""
        finding = {
            'severity': severity,
            'category': category,
            'description': description,
            'file_path': file_path,
            'recommendation': recommendation
        }
        self.findings.append(finding)
        
    def add_passed_check(self, category: str, description: str):
        """Add a passed security check"""
        self.passed_checks.append({
            'category': category,
            'description': description
        })
    
    def audit_file_permissions(self) -> None:
        """Audit file permissions for security issues"""
        logger.info("Auditing file permissions...")
        
        # Check .env files
        env_files = list(self.project_root.glob('.env*'))
        for env_file in env_files:
            if env_file.is_file():
                file_stat = env_file.stat()
                file_mode = stat.filemode(file_stat.st_mode)
                
                # Check if file is readable by others
                if file_stat.st_mode & stat.S_IROTH:
                    self.add_finding(
                        'CRITICAL',
                        'File Permissions',
                        f'Environment file {env_file.name} is readable by others',
                        str(env_file),
                        'Run: chmod 600 ' + str(env_file)
                    )
                elif file_stat.st_mode & stat.S_IRGRP:
                    self.add_finding(
                        'HIGH',
                        'File Permissions',
                        f'Environment file {env_file.name} is readable by group',
                        str(env_file),
                        'Run: chmod 600 ' + str(env_file)
                    )
                else:
                    self.add_passed_check(
                        'File Permissions',
                        f'Environment file {env_file.name} has secure permissions'
                    )
        
        # Check log files
        log_files = list(self.project_root.glob('**/*.log'))
        for log_file in log_files:
            if log_file.is_file():
                file_stat = log_file.stat()
                
                if file_stat.st_mode & stat.S_IROTH:
                    self.add_finding(
                        'MEDIUM',
                        'File Permissions',
                        f'Log file {log_file.name} is readable by others',
                        str(log_file),
                        'Run: chmod 640 ' + str(log_file)
                    )
                else:
                    self.add_passed_check(
                        'File Permissions',
                        f'Log file {log_file.name} has appropriate permissions'
                    )
        
        # Check for executable scripts
        script_files = list(self.project_root.glob('**/*.sh')) + list(self.project_root.glob('**/*.py'))
        for script_file in script_files:
            if script_file.is_file():
                file_stat = script_file.stat()
                
                if file_stat.st_mode & stat.S_IXOTH:
                    self.add_finding(
                        'LOW',
                        'File Permissions',
                        f'Script {script_file.name} is executable by others',
                        str(script_file),
                        'Consider restricting execute permissions'
                    )
    
    def audit_secrets_exposure(self) -> None:
        """Audit for exposed secrets and API keys"""
        logger.info("Auditing for exposed secrets...")
        
        # Patterns for common secrets (excluding legitimate code patterns)
        secret_patterns = {
            'OpenAI API Key': re.compile(r'sk-[a-zA-Z0-9]{48,}'),
            'Telegram Bot Token': re.compile(r'\d{8,10}:[a-zA-Z0-9_-]{35}'),
            'AWS Access Key': re.compile(r'AKIA[0-9A-Z]{16}'),
            'Generic API Key': re.compile(r'api[_-]?key["\']?\s*[:=]\s*["\'][a-zA-Z0-9]{20,}["\']', re.IGNORECASE),
            'Hardcoded Password': re.compile(r'password["\']?\s*[:=]\s*["\'][^"\'$\{][^"\']{7,}["\']', re.IGNORECASE),
            'Secret Token': re.compile(r'secret[_-]?token["\']?\s*[:=]\s*["\'][a-zA-Z0-9]{16,}["\']', re.IGNORECASE),
        }
        
        # Files to check
        code_files = (
            list(self.project_root.glob('**/*.py')) +
            list(self.project_root.glob('**/*.js')) +
            list(self.project_root.glob('**/*.ts')) +
            list(self.project_root.glob('**/*.json')) +
            list(self.project_root.glob('**/*.yml')) +
            list(self.project_root.glob('**/*.yaml'))
        )
        
        # Exclude certain directories
        exclude_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}
        
        for file_path in code_files:
            # Skip files in excluded directories
            if any(excluded in file_path.parts for excluded in exclude_dirs):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                for secret_type, pattern in secret_patterns.items():
                    matches = pattern.findall(content)
                    if matches:
                        # Skip if it's in a template, example, or test file
                        if any(keyword in str(file_path).lower() for keyword in [
                            'template', 'example', 'sample', 'test', 'spec', 'mock', 
                            'security_audit.py', 'docker-compose'
                        ]):
                            continue
                        
                        # Skip if it's a function parameter or variable assignment in legitimate auth code
                        if secret_type == 'Hardcoded Password' and any(keyword in content for keyword in [
                            'def _hash_password', 'def _verify_password', 'def authenticate_user',
                            'password = password or', 'self.password =', 'admin_password = os.getenv'
                        ]):
                            continue
                            
                        self.add_finding(
                            'CRITICAL',
                            'Secret Exposure',
                            f'Potential {secret_type} found in {file_path.name}',
                            str(file_path),
                            'Remove hardcoded secrets and use environment variables'
                        )
            except Exception as e:
                logger.warning(f"Could not read file {file_path}: {e}")
    
    def audit_dependencies(self) -> None:
        """Audit Python dependencies for known vulnerabilities"""
        logger.info("Auditing dependencies...")
        
        requirements_file = self.project_root / 'requirements.txt'
        if not requirements_file.exists():
            self.add_finding(
                'MEDIUM',
                'Dependencies',
                'requirements.txt file not found',
                None,
                'Create requirements.txt with pinned versions'
            )
            return
        
        try:
            # Check for pip-audit tool
            result = subprocess.run(['pip-audit', '--version'], capture_output=True, text=True)
            if result.returncode != 0:
                self.add_finding(
                    'LOW',
                    'Dependencies',
                    'pip-audit tool not available for vulnerability scanning',
                    None,
                    'Install pip-audit: pip install pip-audit'
                )
            else:
                # Run pip-audit
                result = subprocess.run(
                    ['pip-audit', '--requirement', str(requirements_file), '--format', 'json'],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    try:
                        audit_data = json.loads(result.stdout)
                        if audit_data:
                            for vuln in audit_data:
                                self.add_finding(
                                    'HIGH',
                                    'Dependencies',
                                    f"Vulnerability in {vuln.get('package', 'unknown')}: {vuln.get('vulnerability_id', 'unknown')}",
                                    str(requirements_file),
                                    f"Update to version {vuln.get('fixed_versions', ['latest'])[0] if vuln.get('fixed_versions') else 'latest'}"
                                )
                        else:
                            self.add_passed_check(
                                'Dependencies',
                                'No known vulnerabilities found in dependencies'
                            )
                    except json.JSONDecodeError:
                        logger.warning("Could not parse pip-audit output")
        except FileNotFoundError:
            self.add_finding(
                'LOW',
                'Dependencies',
                'pip-audit tool not available',
                None,
                'Install pip-audit for vulnerability scanning'
            )
    
    def audit_configuration(self) -> None:
        """Audit configuration files for security issues"""
        logger.info("Auditing configuration...")
        
        # Check for secure configuration implementation
        secure_config_file = self.project_root / 'src' / 'config' / 'secure_config.py'
        if secure_config_file.exists():
            self.add_passed_check(
                'Configuration',
                'Secure configuration module implemented'
            )
        else:
            self.add_finding(
                'MEDIUM',
                'Configuration',
                'Secure configuration module not found',
                None,
                'Implement secure configuration management'
            )
        
        # Check for input validation
        validation_file = self.project_root / 'src' / 'utils' / 'input_validation.py'
        if validation_file.exists():
            self.add_passed_check(
                'Configuration',
                'Input validation module implemented'
            )
        else:
            self.add_finding(
                'HIGH',
                'Configuration',
                'Input validation module not found',
                None,
                'Implement input validation for API endpoints'
            )
        
        # Check Docker configuration
        dockerfile = self.project_root / 'Dockerfile'
        if dockerfile.exists():
            self.add_passed_check(
                'Configuration',
                'Dockerfile found for containerized deployment'
            )
            
            # Check Dockerfile security
            try:
                with open(dockerfile, 'r') as f:
                    content = f.read()
                    
                if 'USER' not in content:
                    self.add_finding(
                        'MEDIUM',
                        'Configuration',
                        'Dockerfile does not specify non-root user',
                        str(dockerfile),
                        'Add USER directive to run as non-root'
                    )
                else:
                    self.add_passed_check(
                        'Configuration',
                        'Dockerfile uses non-root user'
                    )
                    
                if 'COPY . .' in content:
                    self.add_finding(
                        'LOW',
                        'Configuration',
                        'Dockerfile copies entire context',
                        str(dockerfile),
                        'Use .dockerignore and specific COPY commands'
                    )
            except Exception as e:
                logger.warning(f"Could not read Dockerfile: {e}")
        else:
            self.add_finding(
                'LOW',
                'Configuration',
                'Dockerfile not found',
                None,
                'Create Dockerfile for consistent deployment'
            )
    
    def audit_network_security(self) -> None:
        """Audit network security configurations"""
        logger.info("Auditing network security...")
        
        # Check for CORS configuration
        server_files = list(self.project_root.glob('**/server*.py'))
        cors_configured = False
        
        for server_file in server_files:
            try:
                with open(server_file, 'r') as f:
                    content = f.read()
                    if 'CORS' in content:
                        cors_configured = True
                        
                        # Check for overly permissive CORS
                        if 'origins=["*"]' in content or "origins=['*']" in content:
                            self.add_finding(
                                'HIGH',
                                'Network Security',
                                'CORS configured with wildcard origin',
                                str(server_file),
                                'Restrict CORS origins to specific domains'
                            )
                        else:
                            self.add_passed_check(
                                'Network Security',
                                'CORS configured with restricted origins'
                            )
                        break
            except Exception as e:
                logger.warning(f"Could not read server file {server_file}: {e}")
        
        if not cors_configured:
            self.add_finding(
                'MEDIUM',
                'Network Security',
                'CORS not configured',
                None,
                'Configure CORS with appropriate restrictions'
            )
        
        # Check for HTTPS configuration
        nginx_config = self.project_root / 'nginx.conf'
        if nginx_config.exists():
            try:
                with open(nginx_config, 'r') as f:
                    content = f.read()
                    
                if 'ssl_certificate' in content:
                    self.add_passed_check(
                        'Network Security',
                        'HTTPS/SSL configured in nginx'
                    )
                else:
                    self.add_finding(
                        'HIGH',
                        'Network Security',
                        'HTTPS/SSL not configured',
                        str(nginx_config),
                        'Configure SSL certificates for HTTPS'
                    )
            except Exception as e:
                logger.warning(f"Could not read nginx config: {e}")
    
    def run_audit(self) -> Dict[str, Any]:
        """Run complete security audit"""
        logger.info(f"Starting security audit of {self.project_root}")
        
        # Run all audit checks
        self.audit_file_permissions()
        self.audit_secrets_exposure()
        self.audit_dependencies()
        self.audit_configuration()
        self.audit_network_security()
        
        # Categorize findings by severity
        critical_findings = [f for f in self.findings if f['severity'] == 'CRITICAL']
        high_findings = [f for f in self.findings if f['severity'] == 'HIGH']
        medium_findings = [f for f in self.findings if f['severity'] == 'MEDIUM']
        low_findings = [f for f in self.findings if f['severity'] == 'LOW']
        
        # Generate report
        report = {
            'summary': {
                'total_findings': len(self.findings),
                'critical': len(critical_findings),
                'high': len(high_findings),
                'medium': len(medium_findings),
                'low': len(low_findings),
                'passed_checks': len(self.passed_checks)
            },
            'findings': {
                'critical': critical_findings,
                'high': high_findings,
                'medium': medium_findings,
                'low': low_findings
            },
            'passed_checks': self.passed_checks,
            'recommendations': self._generate_recommendations()
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate prioritized recommendations"""
        recommendations = []
        
        # Critical recommendations
        critical_count = len([f for f in self.findings if f['severity'] == 'CRITICAL'])
        if critical_count > 0:
            recommendations.append(f"🚨 URGENT: Address {critical_count} critical security issues immediately")
        
        # High priority recommendations
        high_count = len([f for f in self.findings if f['severity'] == 'HIGH'])
        if high_count > 0:
            recommendations.append(f"⚠️  HIGH: Fix {high_count} high-priority security issues")
        
        # General recommendations
        recommendations.extend([
            "🔒 Implement regular security audits",
            "📝 Keep dependencies updated",
            "🔑 Use environment variables for all secrets",
            "🛡️  Enable monitoring and alerting",
            "📋 Document security procedures"
        ])
        
        return recommendations

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Security audit for OpenCode-Slack')
    parser.add_argument('--project-root', default='.', help='Project root directory')
    parser.add_argument('--output', help='Output file for report (JSON format)')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run audit
    auditor = SecurityAuditor(args.project_root)
    report = auditor.run_audit()
    
    # Print summary
    print("\n" + "="*60)
    print("🔍 SECURITY AUDIT REPORT")
    print("="*60)
    print(f"Total Findings: {report['summary']['total_findings']}")
    print(f"  🚨 Critical: {report['summary']['critical']}")
    print(f"  ⚠️  High: {report['summary']['high']}")
    print(f"  📋 Medium: {report['summary']['medium']}")
    print(f"  ℹ️  Low: {report['summary']['low']}")
    print(f"✅ Passed Checks: {report['summary']['passed_checks']}")
    
    # Print critical and high findings
    if report['findings']['critical']:
        print("\n🚨 CRITICAL FINDINGS:")
        for finding in report['findings']['critical']:
            print(f"  • {finding['description']}")
            if finding['recommendation']:
                print(f"    → {finding['recommendation']}")
    
    if report['findings']['high']:
        print("\n⚠️  HIGH PRIORITY FINDINGS:")
        for finding in report['findings']['high']:
            print(f"  • {finding['description']}")
            if finding['recommendation']:
                print(f"    → {finding['recommendation']}")
    
    # Print recommendations
    print("\n📋 RECOMMENDATIONS:")
    for rec in report['recommendations']:
        print(f"  {rec}")
    
    # Save report if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Full report saved to: {args.output}")
    
    # Exit with appropriate code
    if report['summary']['critical'] > 0:
        print("\n❌ AUDIT FAILED: Critical security issues found")
        sys.exit(1)
    elif report['summary']['high'] > 0:
        print("\n⚠️  AUDIT WARNING: High priority issues found")
        sys.exit(2)
    else:
        print("\n✅ AUDIT PASSED: No critical or high priority issues found")
        sys.exit(0)

if __name__ == '__main__':
    main()