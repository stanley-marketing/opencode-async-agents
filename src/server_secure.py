# SPDX-License-Identifier: MIT
#!/usr/bin/env python3
"""
Secure standalone server for opencode-slack system with enhanced security features.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from functools import wraps
from pathlib import Path
import json
import logging
import os
import signal
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.managers.file_ownership import FileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker
from src.config.logging_config import setup_logging
from src.config.secure_config import init_config, get_config
from src.utils.opencode_wrapper import OpencodeSessionManager
from src.utils.input_validation import InputValidator, ValidationError, validate_request_data
from src.chat.telegram_manager import TelegramManager
from src.agents.agent_manager import AgentManager
from src.bridge.agent_bridge import AgentBridge

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

def validate_json_request(validation_rules=None):
    """Decorator to validate JSON request data"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Validate content type
                if not request.is_json:
                    return jsonify({'error': 'Content-Type must be application/json'}), 400

                # Get and validate JSON data
                data = request.get_json()
                if data is None:
                    return jsonify({'error': 'Invalid JSON payload'}), 400

                # Apply validation rules if provided
                if validation_rules:
                    data = validate_request_data(data, validation_rules)

                # Store validated data in request context
                request.validated_data = data

                return f(*args, **kwargs)

            except ValidationError as e:
                logger = logging.getLogger(__name__)
                logger.warning(f"Validation error: {str(e)}")
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"Request validation failed: {str(e)}")
                return jsonify({'error': 'Invalid request format'}), 400

        return decorated_function
    return decorator

def validate_query_params():
    """Decorator to validate query parameters"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Validate query parameters
                validated_params = InputValidator.validate_query_params(request.args.to_dict())
                request.validated_params = validated_params
                return f(*args, **kwargs)
            except ValidationError as e:
                logger = logging.getLogger(__name__)
                logger.warning(f"Query parameter validation error: {str(e)}")
                return jsonify({'error': str(e)}), 400
        return decorated_function
    return decorator

class SecureOpencodeSlackServer:
    """Secure standalone server for opencode-slack system"""

    def __init__(self, host="localhost", port=8080, environment=None):
        # Initialize secure configuration
        self.config = init_config(environment)

        self.host = self.config.get('SERVER_HOST', host)
        self.port = self.config.get_int('SERVER_PORT', port)

        # Configure logging
        setup_logging(cli_mode=False)
        self.logger = logging.getLogger(__name__)

        # Log configuration (masked)
        masked_config = self.config.get_masked_config()
        self.logger.info(f"Starting server with configuration: {json.dumps(masked_config, indent=2)}")

        # Initialize core components with secure config
        db_path = self.config.get('DATABASE_PATH', 'employees.db')
        sessions_dir = self.config.get('SESSIONS_DIR', 'sessions')

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

        # Initialize Flask app with security headers
        self.app = Flask(__name__)
        self._configure_flask_security()
        self._setup_routes()

        # Server state
        self.running = False
        self.chat_enabled = False

        self.logger.info(f"Secure OpenCode-Slack server initialized on {self.host}:{self.port}")

    def _configure_flask_security(self):
        """Configure Flask with security headers and settings"""
        # Enable CORS with secure settings
        CORS(self.app,
             origins=self.config.get_list('ALLOWED_ORIGINS', default=['http://localhost:3000']),
             methods=['GET', 'POST', 'DELETE'],
             allow_headers=['Content-Type', 'Authorization'])

        # Set security headers
        @self.app.after_request
        def add_security_headers(response):
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response.headers['Content-Security-Policy'] = "default-src 'self'"
            return response

        # Configure Flask settings
        self.app.config['SECRET_KEY'] = self.config.get('SECRET_KEY', self.config.generate_secret_key())
        self.app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max request size

        # Disable debug mode in production
        if self.config.is_production():
            self.app.config['DEBUG'] = False
            self.app.config['TESTING'] = False

    def _setup_monitoring_system(self):
        """Set up the agent monitoring system"""
        if not MONITORING_AVAILABLE:
            self.logger.info("Monitoring system not available")
            return

        if not self.config.get('MONITORING_ENABLED', True):
            self.logger.info("Monitoring system disabled by configuration")
            return

        try:
            # Set up the agent manager with task tracker
            self.agent_manager.setup_monitoring_system(self.task_tracker, self.session_manager)

            # Initialize health monitor
            self.health_monitor = AgentHealthMonitor(self.agent_manager, self.task_tracker)

            # Initialize recovery manager
            if self.config.get('RECOVERY_ENABLED', True):
                self.recovery_manager = AgentRecoveryManager(self.agent_manager, self.session_manager)

            # Initialize monitoring dashboard
            self.monitoring_dashboard = MonitoringDashboard(
                self.health_monitor,
                self.recovery_manager,
                self.agent_manager
            )

            self.logger.info("Monitoring system initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize monitoring system: {str(e)}")

    def _setup_routes(self):
        """Set up secure API routes with validation"""

        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'timestamp': time.time(),
                'version': '1.0.0'
            })

        @self.app.route('/employees', methods=['GET'])
        @validate_query_params()
        def list_employees():
            """List all employees"""
            try:
                employees = self.file_manager.list_employees()
                return jsonify({'employees': employees})
            except Exception as e:
                self.logger.error(f"Failed to list employees: {str(e)}")
                return jsonify({'error': 'Internal server error'}), 500

        @self.app.route('/employees', methods=['POST'])
        @validate_json_request({
            'name': 'employee_name',
            'role': 'role'
        })
        def hire_employee():
            """Hire a new employee"""
            try:
                data = request.validated_data
                name = data['name']
                role = data['role']

                success = self.file_manager.hire_employee(name, role)
                if success:
                    # Create communication agent
                    expertise = self.agent_manager._get_expertise_for_role(role)
                    self.agent_manager.create_agent(name, role, expertise)

                    self.logger.info(f"Successfully hired {name} as {role}")
                    return jsonify({'message': f'Successfully hired {name} as {role}'})
                else:
                    return jsonify({'error': f'Failed to hire {name}. Employee may already exist.'}), 400

            except Exception as e:
                self.logger.error(f"Failed to hire employee: {str(e)}")
                return jsonify({'error': 'Internal server error'}), 500

        @self.app.route('/employees/<name>', methods=['DELETE'])
        def fire_employee(name):
            """Fire an employee"""
            try:
                # Validate employee name
                name = InputValidator.validate_employee_name(name)

                # Stop any active sessions first
                if name in self.session_manager.active_sessions:
                    self.session_manager.stop_employee_task(name)

                # Remove communication agent
                self.agent_manager.remove_agent(name)

                success = self.file_manager.fire_employee(name, self.session_manager.task_tracker)
                if success:
                    self.logger.info(f"Successfully fired {name}")
                    return jsonify({'message': f'Successfully fired {name}'})
                else:
                    return jsonify({'error': f'Failed to fire {name}. Employee may not exist.'}), 400

            except ValidationError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                self.logger.error(f"Failed to fire employee: {str(e)}")
                return jsonify({'error': 'Internal server error'}), 500

        @self.app.route('/tasks', methods=['POST'])
        @validate_json_request({
            'name': 'employee_name',
            'task': 'task_description',
            'model': 'model_name',
            'mode': 'mode'
        })
        def assign_task():
            """Assign a task to an employee"""
            try:
                data = request.validated_data
                name = data['name']
                task_description = data['task']
                model = data.get('model', self.config.get('DEFAULT_MODEL', 'openrouter/qwen/qwen3-coder'))
                mode = data.get('mode', 'build')

                # Validate model and mode
                model = InputValidator.validate_model_name(model)
                mode = InputValidator.validate_mode(mode)

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
                    self.logger.info(f"Started task for {name}: {session_id}")
                    return jsonify({
                        'message': f'Started task for {name}',
                        'session_id': session_id
                    })
                else:
                    return jsonify({'error': f'Failed to start task for {name}'}), 500

            except ValidationError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                self.logger.error(f"Failed to assign task: {str(e)}")
                return jsonify({'error': 'Internal server error'}), 500

        @self.app.route('/tasks/<name>', methods=['DELETE'])
        def stop_task(name):
            """Stop an employee's task"""
            try:
                # Validate employee name
                name = InputValidator.validate_employee_name(name)

                self.session_manager.stop_employee_task(name)
                self.logger.info(f"Stopped task for {name}")
                return jsonify({'message': f'Stopped task for {name}'})

            except ValidationError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                self.logger.error(f"Failed to stop task: {str(e)}")
                return jsonify({'error': 'Internal server error'}), 500

        @self.app.route('/status', methods=['GET'])
        @validate_query_params()
        def get_status():
            """Get comprehensive system status"""
            try:
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
                    'chat_statistics': self.agent_manager.get_chat_statistics() if self.chat_enabled else None,
                    'monitoring_enabled': MONITORING_AVAILABLE and self.config.get('MONITORING_ENABLED', True)
                })
            except Exception as e:
                self.logger.error(f"Failed to get status: {str(e)}")
                return jsonify({'error': 'Internal server error'}), 500

        @self.app.route('/files/lock', methods=['POST'])
        @validate_json_request({
            'name': 'employee_name',
            'files': 'file_paths'
        })
        def lock_files():
            """Lock files for an employee"""
            try:
                data = request.validated_data
                name = data['name']
                files = data['files']
                description = data.get('description', '')

                # Validate files
                files = InputValidator.validate_file_paths(files)

                result = self.file_manager.lock_files(name, files, description)
                self.task_tracker.create_task_file(name, description, files)

                self.logger.info(f"Locked files for {name}: {files}")
                return jsonify({'result': result})

            except ValidationError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                self.logger.error(f"Failed to lock files: {str(e)}")
                return jsonify({'error': 'Internal server error'}), 500

        @self.app.route('/files/release', methods=['POST'])
        @validate_json_request({
            'name': 'employee_name'
        })
        def release_files():
            """Release files for an employee"""
            try:
                data = request.validated_data
                name = data['name']
                files = data.get('files')  # Optional

                # Validate files if provided
                if files:
                    files = InputValidator.validate_file_paths(files)

                released = self.file_manager.release_files(name, files)
                self.logger.info(f"Released files for {name}: {released}")
                return jsonify({'released': released})

            except ValidationError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                self.logger.error(f"Failed to release files: {str(e)}")
                return jsonify({'error': 'Internal server error'}), 500

    def start(self):
        """Start the secure server"""
        if self.running:
            self.logger.warning("Server is already running")
            return

        self.running = True

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        try:
            self.logger.info(f"Starting secure server on {self.host}:{self.port}")

            # Start monitoring system if available
            if self.health_monitor:
                self.health_monitor.start()

            # Run Flask app
            self.app.run(
                host=self.host,
                port=self.port,
                debug=self.config.get('DEBUG_MODE', False),
                threaded=True
            )

        except Exception as e:
            self.logger.error(f"Failed to start server: {str(e)}")
            self.running = False
            raise

    def stop(self):
        """Stop the server gracefully"""
        if not self.running:
            return

        self.logger.info("Stopping server...")
        self.running = False

        # Stop monitoring system
        if self.health_monitor:
            self.health_monitor.stop()

        # Stop chat system
        if self.chat_enabled:
            self.telegram_manager.stop_polling()
            self.chat_enabled = False

        # Stop all active sessions
        for session_id in list(self.session_manager.active_sessions.keys()):
            self.session_manager.stop_session(session_id)

        self.logger.info("Server stopped")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Secure OpenCode-Slack Server')
    parser.add_argument('--host', default='localhost', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    parser.add_argument('--environment', choices=['development', 'production'],
                       help='Environment to run in')

    args = parser.parse_args()

    try:
        server = SecureOpencodeSlackServer(
            host=args.host,
            port=args.port,
            environment=args.environment
        )
        server.start()
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Server failed to start: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()