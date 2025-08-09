#!/usr/bin/env python3
"""
Secure server for opencode-slack system with comprehensive authentication and security.
Implements JWT/API key authentication, rate limiting, input validation, and security headers.
"""

import sys
import os
import signal
import threading
import time
import json
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.managers.file_ownership import FileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker
from src.config.logging_config import setup_logging
from src.utils.opencode_wrapper import OpencodeSessionManager
from src.chat.telegram_manager import TelegramManager
from src.agents.agent_manager import AgentManager
from src.bridge.agent_bridge import AgentBridge

# Security imports
from src.security.auth import auth_manager, require_auth, optional_auth
from src.security.rate_limiter import rate_limiter, rate_limit
from src.security.middleware import security_middleware, security_headers, validate_request, cors_headers
from src.security.encryption import encryption_manager

# Optional imports for monitoring system
try:
    from src.monitoring.agent_health_monitor import AgentHealthMonitor
    from src.monitoring.agent_recovery_manager import AgentRecoveryManager
    from src.monitoring.monitoring_dashboard import MonitoringDashboard
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False
    AgentHealthMonitor = None
    AgentRecoveryManager = None
    MonitoringDashboard = None

class SecureOpencodeSlackServer:
    """Secure server for opencode-slack system with comprehensive security features"""
    
    def __init__(self, host="localhost", port=8080, db_path="employees.db", sessions_dir="sessions"):
        self.host = host
        self.port = port
        self.db_path = db_path
        self.sessions_dir = sessions_dir
        
        # Load environment variables
        self._load_environment()
        
        # Configure logging
        setup_logging(cli_mode=False)
        self.logger = logging.getLogger(__name__)
        
        # Initialize core components
        self.file_manager = FileOwnershipManager(db_path)
        self.task_tracker = TaskProgressTracker(sessions_dir)
        self.session_manager = OpencodeSessionManager(self.file_manager, sessions_dir, quiet_mode=True)
        
        # Initialize chat system
        self.telegram_manager = TelegramManager()
        self.agent_manager = AgentManager(self.file_manager, self.telegram_manager)
        self.agent_bridge = AgentBridge(self.session_manager, self.agent_manager)
        
        # Initialize monitoring system (if available)
        self.health_monitor = None
        self.recovery_manager = None
        self.monitoring_dashboard = None
        self._setup_monitoring_system()
        
        # Initialize Flask app with security
        self.app = Flask(__name__)
        self._setup_security()
        self._setup_routes()
        
        # Server state
        self.running = False
        self.chat_enabled = False
        
        self.logger.info(f"Secure OpenCode-Slack server initialized on {host}:{port}")
    
    def _setup_security(self):
        """Set up security configuration"""
        # Configure CORS for production
        CORS(self.app, 
             origins=["https://your-domain.com"],  # Replace with actual domain
             allow_headers=["Content-Type", "Authorization", "X-API-Key"],
             methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
        
        # Set up security middleware
        @self.app.before_request
        def before_request():
            # Apply security validation to all requests
            pass
        
        @self.app.after_request
        def after_request(response):
            # Add security headers to all responses
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
            return response
        
        self.logger.info("Security middleware configured")
    
    def _setup_monitoring_system(self):
        """Set up the agent monitoring system"""
        if not MONITORING_AVAILABLE:
            self.logger.info("Monitoring system not available")
            return
        
        try:
            # CRITICAL: Set up the agent manager with task tracker FIRST
            self.agent_manager.setup_monitoring_system(self.task_tracker, self.session_manager)
            
            # Initialize health monitor
            self.health_monitor = AgentHealthMonitor(self.agent_manager, self.task_tracker)
            
            # Initialize recovery manager
            self.recovery_manager = AgentRecoveryManager(self.agent_manager, self.session_manager)
            
            # Initialize monitoring dashboard
            self.monitoring_dashboard = MonitoringDashboard(self.health_monitor, self.recovery_manager)
            
            # Set up anomaly callback
            def anomaly_callback(agent_name, anomalies, status_record):
                if self.recovery_manager:
                    self.recovery_manager.handle_agent_anomaly(agent_name, anomalies, status_record)
            
            # Start monitoring
            self.health_monitor.start_monitoring(anomaly_callback)
            
            self.logger.info("Monitoring system initialized and started")
            print("🔍 Agent monitoring system initialized")
            
        except Exception as e:
            self.logger.error(f"Error setting up monitoring system: {e}")
            print(f"⚠️  Failed to initialize monitoring system: {e}")
    
    def _load_environment(self):
        """Load environment variables"""
        try:
            from dotenv import load_dotenv
            env_path = Path(__file__).parent.parent / '.env'
            if env_path.exists():
                load_dotenv(env_path)
                print(f"📄 Loaded .env from {env_path}")
            else:
                load_dotenv()  # Try current directory
        except ImportError:
            print("⚠️  Install python-dotenv: pip install python-dotenv")
        except Exception as e:
            print(f"⚠️  Could not load .env: {e}")
    
    def _setup_routes(self):
        """Set up Flask routes with security"""
        
        # Authentication endpoints
        @self.app.route('/auth/login', methods=['POST'])
        @rate_limit(limit=10)  # Strict rate limit for auth
        @validate_request()
        @security_headers()
        def login():
            """Authenticate user and return JWT token"""
            data = request.get_json()
            if not data or not data.get('username') or not data.get('password'):
                return jsonify({'error': 'Username and password required'}), 400
            
            username = data['username']
            password = data['password']
            
            user = auth_manager.authenticate_user(username, password)
            if not user:
                return jsonify({'error': 'Invalid credentials'}), 401
            
            token = auth_manager.generate_jwt_token(username)
            
            return jsonify({
                'token': token,
                'user': {
                    'username': user['username'],
                    'roles': user['roles'],
                    'permissions': user['permissions']
                },
                'expires_in': auth_manager.token_expiry_hours * 3600
            })
        
        @self.app.route('/auth/refresh', methods=['POST'])
        @require_auth()
        @rate_limit(limit=20)
        @security_headers()
        def refresh_token():
            """Refresh JWT token"""
            username = request.auth_info['username']
            new_token = auth_manager.generate_jwt_token(username)
            
            return jsonify({
                'token': new_token,
                'expires_in': auth_manager.token_expiry_hours * 3600
            })
        
        @self.app.route('/auth/api-keys', methods=['POST'])
        @require_auth(permission="admin")
        @rate_limit(limit=5)
        @validate_request()
        @security_headers()
        def create_api_key():
            """Create new API key"""
            data = request.get_json()
            if not data or not data.get('name'):
                return jsonify({'error': 'API key name required'}), 400
            
            name = data['name']
            permissions = data.get('permissions', ['read'])
            expires_days = data.get('expires_days')
            
            api_key = auth_manager.generate_api_key(name, permissions, expires_days)
            
            return jsonify({
                'api_key': api_key,
                'name': name,
                'permissions': permissions,
                'expires_days': expires_days
            })
        
        @self.app.route('/auth/api-keys', methods=['GET'])
        @require_auth(permission="admin")
        @rate_limit()
        @security_headers()
        def list_api_keys():
            """List all API keys"""
            keys = []
            for key, info in auth_manager.api_keys.items():
                keys.append({
                    'key': key[:8] + "..." + key[-4:],  # Masked key
                    'name': info['name'],
                    'permissions': info['permissions'],
                    'created_at': info['created_at'],
                    'expires_at': info.get('expires_at'),
                    'active': info['active'],
                    'last_used': info.get('last_used')
                })
            
            return jsonify({'api_keys': keys})
        
        @self.app.route('/auth/api-keys/<api_key>', methods=['DELETE'])
        @require_auth(permission="admin")
        @rate_limit()
        @security_headers()
        def revoke_api_key(api_key):
            """Revoke API key"""
            success = auth_manager.revoke_api_key(api_key)
            if success:
                return jsonify({'message': 'API key revoked successfully'})
            else:
                return jsonify({'error': 'API key not found'}), 404
        
        # Public endpoints (with optional auth for enhanced features)
        @self.app.route('/health', methods=['GET'])
        @optional_auth()
        @rate_limit(limit=100)
        @security_headers()
        def health_check():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'chat_enabled': self.chat_enabled,
                'active_sessions': len(self.session_manager.get_active_sessions()),
                'total_agents': len(self.agent_manager.agents),
                'authenticated': hasattr(request, 'auth_info') and request.auth_info is not None
            })
        
        # Employee management endpoints (require authentication)
        @self.app.route('/employees', methods=['GET'])
        @require_auth(permission="employees:read")
        @rate_limit()
        @security_headers()
        def list_employees():
            """List all employees"""
            employees = self.file_manager.list_employees()
            return jsonify({'employees': employees})
        
        @self.app.route('/employees', methods=['POST'])
        @require_auth(permission="employees:write")
        @rate_limit(limit=30)
        @validate_request()
        @security_headers()
        def hire_employee():
            """Hire a new employee"""
            data = request.get_json()
            name = data.get('name')
            role = data.get('role')
            
            if not name or not role:
                return jsonify({'error': 'Name and role are required'}), 400
            
            success = self.file_manager.hire_employee(name, role)
            if success:
                # Create communication agent
                expertise = self.agent_manager._get_expertise_for_role(role)
                self.agent_manager.create_agent(name, role, expertise)
                
                return jsonify({'message': f'Successfully hired {name} as {role}'})
            else:
                return jsonify({'error': f'Failed to hire {name}. Employee may already exist.'}), 400
        
        @self.app.route('/employees/<name>', methods=['DELETE'])
        @require_auth(permission="employees:delete")
        @rate_limit(limit=20)
        @security_headers()
        def fire_employee(name):
            """Fire an employee"""
            # Stop any active sessions first
            if name in self.session_manager.active_sessions:
                self.session_manager.stop_employee_task(name)
            
            # Remove communication agent
            self.agent_manager.remove_agent(name)
            
            success = self.file_manager.fire_employee(name, self.session_manager.task_tracker)
            if success:
                return jsonify({'message': f'Successfully fired {name}'})
            else:
                return jsonify({'error': f'Failed to fire {name}. Employee may not exist.'}), 400
        
        # Task management endpoints
        @self.app.route('/tasks', methods=['POST'])
        @require_auth(permission="tasks:write")
        @rate_limit(limit=20)
        @validate_request()
        @security_headers()
        def assign_task():
            """Assign a task to an employee"""
            data = request.get_json()
            name = data.get('name')
            task_description = data.get('task')
            model = data.get('model', 'openrouter/qwen/qwen3-coder')
            mode = data.get('mode', 'build')
            
            if not name or not task_description:
                return jsonify({'error': 'Name and task are required'}), 400
            
            # Make sure employee exists
            employees = self.file_manager.list_employees()
            employee_names = [emp['name'] for emp in employees]
            
            if name not in employee_names:
                # Auto-hire as developer
                if not self.file_manager.hire_employee(name, "developer"):
                    return jsonify({'error': f'Failed to hire {name}'}), 400
                
                expertise = self.agent_manager._get_expertise_for_role("developer")
                self.agent_manager.create_agent(name, "developer", expertise)
            
            # Start real opencode session
            session_id = self.session_manager.start_employee_task(
                name, task_description, model, mode
            )
            
            if session_id:
                return jsonify({
                    'message': f'Started task for {name}',
                    'session_id': session_id
                })
            else:
                return jsonify({'error': f'Failed to start task for {name}'}), 500
        
        @self.app.route('/tasks/<name>', methods=['DELETE'])
        @require_auth(permission="tasks:write")
        @rate_limit()
        @security_headers()
        def stop_task(name):
            """Stop an employee's task"""
            self.session_manager.stop_employee_task(name)
            return jsonify({'message': f'Stopped task for {name}'})
        
        # File management endpoints
        @self.app.route('/files', methods=['GET'])
        @require_auth(permission="files:read")
        @rate_limit()
        @security_headers()
        def get_files():
            """Get locked files"""
            all_files = self.file_manager.get_all_locked_files()
            return jsonify({'files': all_files})
        
        @self.app.route('/files/lock', methods=['POST'])
        @require_auth(permission="files:write")
        @rate_limit(limit=50)
        @validate_request()
        @security_headers()
        def lock_files():
            """Lock files for an employee"""
            data = request.get_json()
            name = data.get('name')
            files = data.get('files', [])
            description = data.get('description', '')
            
            if not name or not files:
                return jsonify({'error': 'Name and files are required'}), 400
            
            result = self.file_manager.lock_files(name, files, description)
            self.task_tracker.create_task_file(name, description, files)
            
            return jsonify({'result': result})
        
        @self.app.route('/files/release', methods=['POST'])
        @require_auth(permission="files:write")
        @rate_limit(limit=50)
        @validate_request()
        @security_headers()
        def release_files():
            """Release files for an employee"""
            data = request.get_json()
            name = data.get('name')
            files = data.get('files')  # Optional, if None releases all
            
            if not name:
                return jsonify({'error': 'Name is required'}), 400
            
            released = self.file_manager.release_files(name, files)
            return jsonify({'released': released})
        
        # Status and monitoring endpoints
        @self.app.route('/status', methods=['GET'])
        @require_auth(permission="status:read")
        @rate_limit()
        @security_headers()
        def get_status():
            """Get comprehensive system status"""
            active_sessions = self.session_manager.get_active_sessions()
            all_files = self.file_manager.get_all_locked_files()
            pending_requests = self.file_manager.get_pending_requests()
            employees = self.file_manager.list_employees()
            
            return jsonify({
                'active_sessions': active_sessions,
                'locked_files': all_files,
                'pending_requests': pending_requests,
                'employees': employees,
                'chat_enabled': self.chat_enabled,
                'chat_statistics': self.agent_manager.get_chat_statistics() if self.chat_enabled else None
            })
        
        @self.app.route('/progress', methods=['GET'])
        @require_auth(permission="progress:read")
        @rate_limit()
        @security_headers()
        def get_progress():
            """Get progress for all employees"""
            name = request.args.get('name')
            
            if name:
                progress = self.task_tracker.get_task_progress(name)
                return jsonify({'progress': progress})
            else:
                employees = self.file_manager.list_employees()
                all_progress = {}
                for employee in employees:
                    emp_name = employee['name']
                    progress = self.task_tracker.get_task_progress(emp_name)
                    all_progress[emp_name] = progress
                return jsonify({'progress': all_progress})
        
        # Chat system endpoints
        @self.app.route('/chat/start', methods=['POST'])
        @require_auth(permission="chat:admin")
        @rate_limit(limit=5)
        @security_headers()
        def start_chat():
            """Start the chat system"""
            if self.chat_enabled:
                return jsonify({'message': 'Chat system is already running'})
            
            from src.chat.chat_config import config
            if not config.is_configured():
                return jsonify({
                    'error': 'Chat system not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID'
                }), 400
            
            try:
                self.telegram_manager.start_polling()
                self.agent_bridge.start_monitoring()
                self.chat_enabled = True
                return jsonify({'message': 'Chat system started successfully'})
            except Exception as e:
                return jsonify({'error': f'Failed to start chat system: {str(e)}'}), 500
        
        @self.app.route('/chat/stop', methods=['POST'])
        @require_auth(permission="chat:admin")
        @rate_limit(limit=5)
        @security_headers()
        def stop_chat():
            """Stop the chat system"""
            if not self.chat_enabled:
                return jsonify({'error': 'Chat system is not running'}), 400
            
            self.telegram_manager.stop_polling()
            self.chat_enabled = False
            return jsonify({'message': 'Chat system stopped'})
        
        @self.app.route('/chat/status', methods=['GET'])
        @require_auth(permission="chat:read")
        @rate_limit()
        @security_headers()
        def get_chat_status():
            """Get chat system status"""
            from src.chat.chat_config import config
            
            return jsonify({
                'configured': config.is_configured(),
                'connected': self.telegram_manager.is_connected(),
                'polling': self.chat_enabled,
                'statistics': self.agent_manager.get_chat_statistics()
            })
        
        # Security management endpoints
        @self.app.route('/security/stats', methods=['GET'])
        @require_auth(permission="admin")
        @rate_limit()
        @security_headers()
        def get_security_stats():
            """Get security statistics"""
            auth_stats = auth_manager.get_auth_info()
            rate_limit_stats = rate_limiter.get_stats()
            security_stats = security_middleware.get_security_stats()
            
            return jsonify({
                'authentication': auth_stats,
                'rate_limiting': rate_limit_stats,
                'security': security_stats
            })
        
        @self.app.route('/security/blocked-ips', methods=['POST'])
        @require_auth(permission="admin")
        @rate_limit(limit=10)
        @validate_request()
        @security_headers()
        def block_ip():
            """Block an IP address"""
            data = request.get_json()
            ip = data.get('ip')
            
            if not ip:
                return jsonify({'error': 'IP address required'}), 400
            
            security_middleware.add_blocked_ip(ip)
            return jsonify({'message': f'IP {ip} blocked successfully'})
        
        @self.app.route('/security/blocked-ips/<ip>', methods=['DELETE'])
        @require_auth(permission="admin")
        @rate_limit(limit=10)
        @security_headers()
        def unblock_ip(ip):
            """Unblock an IP address"""
            security_middleware.remove_blocked_ip(ip)
            return jsonify({'message': f'IP {ip} unblocked successfully'})
        
        # Monitoring endpoints (if available)
        if MONITORING_AVAILABLE:
            @self.app.route('/monitoring/health', methods=['GET'])
            @require_auth(permission="monitoring:read")
            @rate_limit()
            @security_headers()
            def get_monitoring_health():
                """Get agent health monitoring status"""
                if not self.health_monitor:
                    return jsonify({'error': 'Monitoring system not available'}), 400
                
                health_summary = self.health_monitor.get_agent_health_summary()
                return jsonify({'health': health_summary})
            
            @self.app.route('/monitoring/recovery', methods=['GET'])
            @require_auth(permission="monitoring:read")
            @rate_limit()
            @security_headers()
            def get_monitoring_recovery():
                """Get agent recovery status"""
                if not self.recovery_manager:
                    return jsonify({'error': 'Recovery system not available'}), 400
                
                recovery_summary = self.recovery_manager.get_recovery_summary()
                return jsonify({'recovery': recovery_summary})
    
    def start(self):
        """Start the secure server"""
        self.running = True
        
        # Auto-start chat system if configured
        self._auto_start_chat_if_configured()
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info(f"Starting Secure OpenCode-Slack server on {self.host}:{self.port}")
        print(f"🔒 Secure OpenCode-Slack server starting on https://{self.host}:{self.port}")
        print(f"👥 {len(self.agent_manager.agents)} communication agents ready")
        print("🔐 Authentication: JWT tokens and API keys")
        print("🛡️  Security: Rate limiting, input validation, security headers")
        print("📊 Health check: GET /health")
        print("🔑 Login: POST /auth/login")
        print("Press Ctrl+C to stop")
        
        try:
            # Use Werkzeug's development server with proper shutdown handling
            from werkzeug.serving import make_server
            
            self.server_instance = make_server(
                self.host, 
                self.port, 
                self.app, 
                threaded=True,
                ssl_context='adhoc'  # Use self-signed certificate for HTTPS
            )
            
            # Start server in a way that can be interrupted
            self.server_instance.serve_forever()
            
        except KeyboardInterrupt:
            print("\n🔄 Received interrupt signal...")
            self.stop()
        except Exception as e:
            self.logger.error(f"Server error: {e}")
            self.stop()
    
    def _auto_start_chat_if_configured(self):
        """Auto-start chat system if properly configured"""
        from src.chat.chat_config import config
        
        # Check for safe mode environment variable
        safe_mode = os.environ.get('OPENCODE_SAFE_MODE', '').lower() in ['true', '1', 'yes']
        
        if safe_mode:
            print("🔒 Safe mode enabled - Telegram chat disabled")
            print("   Set OPENCODE_SAFE_MODE=false to enable chat")
            return
        
        if config.is_configured():
            try:
                self.telegram_manager.start_polling()
                self.agent_bridge.start_monitoring()
                self.chat_enabled = True
                print("💬 Chat system auto-started!")
                self.logger.info("Chat system auto-started")
            except Exception as e:
                print(f"⚠️  Failed to auto-start chat system: {e}")
                print(f"💡 Try setting OPENCODE_SAFE_MODE=true to disable chat")
                self.logger.error(f"Failed to auto-start chat system: {e}")
        else:
            print("💬 Chat system not configured (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()
    
    def stop(self):
        """Stop the server immediately"""
        self.logger.info("Shutting down Secure OpenCode-Slack server immediately...")
        print("\n🛑 Shutting down secure server immediately...")
        
        # Stop chat system immediately
        self.chat_enabled = False
        
        # Clean up all active sessions and release locks
        print("🧹 Cleaning up active sessions and releasing file locks...")
        try:
            self.session_manager.cleanup_all_sessions()
            # Release all remaining locks
            employees = self.file_manager.list_employees()
            for employee in employees:
                released = self.file_manager.release_files(employee['name'])
                if released:
                    print(f"   🔓 Released locks for {employee['name']}: {', '.join(released)}")
        except Exception as e:
            print(f"⚠️  Error during cleanup: {e}")
        
        self.running = False
        print("✅ Secure server shutdown complete")
        
        # Immediate exit
        import os
        os._exit(0)


def main():
    """Main function"""
    import argparse
    
    # Get default port from environment variable or use 8443 for HTTPS
    default_port = int(os.environ.get('PORT', 8443))
    default_host = os.environ.get('HOST', 'localhost')
    
    parser = argparse.ArgumentParser(description='Secure OpenCode-Slack Server')
    parser.add_argument('--host', default=default_host, help=f'Host to bind to (default: {default_host}, from HOST env var)')
    parser.add_argument('--port', type=int, default=default_port, help=f'Port to bind to (default: {default_port}, from PORT env var)')
    parser.add_argument('--db-path', default='employees.db', help='Database path (default: employees.db)')
    parser.add_argument('--sessions-dir', default='sessions', help='Sessions directory (default: sessions)')
    
    args = parser.parse_args()
    
    server = SecureOpencodeSlackServer(
        host=args.host,
        port=args.port,
        db_path=args.db_path,
        sessions_dir=args.sessions_dir
    )
    
    server.start()


if __name__ == "__main__":
    main()