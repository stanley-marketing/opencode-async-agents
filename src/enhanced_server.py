#!/usr/bin/env python3
"""
Enhanced OpenCode-Slack Server with comprehensive error handling and resilience.
Provides robust database initialization, graceful degradation, and recovery mechanisms.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
import json
import logging
import os
import signal
import sys
import threading
import time
import traceback

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.database_manager import DatabaseManager, DatabaseError
from src.managers.enhanced_file_ownership import EnhancedFileOwnershipManager, FileOwnershipError
from src.trackers.task_progress import TaskProgressTracker
from src.config.logging_config import setup_logging
from src.utils.opencode_wrapper import OpencodeSessionManager
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


class EnhancedOpencodeSlackServer:
    """Enhanced server with comprehensive error handling and resilience"""

    def __init__(self, host="localhost", port=8080, db_path="employees.db",
                 sessions_dir="sessions", backup_dir=None):
        self.host = host
        self.port = port
        self.db_path = db_path
        self.sessions_dir = sessions_dir
        self.backup_dir = backup_dir or str(Path(db_path).parent / "backups")

        # Server state
        self.running = False
        self.chat_enabled = False
        self.degraded_mode = False
        self.initialization_errors = []

        # Load environment variables
        self._load_environment()

        # Configure logging with enhanced error handling
        self._setup_enhanced_logging()

        # Initialize core components with error handling
        self._initialize_components()

        # Initialize Flask app
        self.app = Flask(__name__)
        CORS(self.app)
        self._setup_enhanced_routes()

        self.logger.info(f"Enhanced OpenCode-Slack server initialized on {host}:{port}")
        if self.degraded_mode:
            self.logger.warning("Server running in degraded mode due to initialization errors")

    def _load_environment(self):
        """Load environment variables with error handling"""
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

    def _setup_enhanced_logging(self):
        """Set up enhanced logging with error handling"""
        try:
            setup_logging(cli_mode=False)
            self.logger = logging.getLogger(__name__)

            # Add custom error handler
            error_handler = logging.StreamHandler()
            error_handler.setLevel(logging.ERROR)
            error_formatter = logging.Formatter(
                '%(asctime)s [ERROR] %(name)s: %(message)s'
            )
            error_handler.setFormatter(error_formatter)
            self.logger.addHandler(error_handler)

        except Exception as e:
            # Fallback to basic logging
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(__name__)
            self.logger.error(f"Enhanced logging setup failed: {e}")

    def _initialize_components(self):
        """Initialize core components with comprehensive error handling"""
        self.file_manager = None
        self.task_tracker = None
        self.session_manager = None
        self.telegram_manager = None
        self.agent_manager = None
        self.agent_bridge = None
        self.health_monitor = None
        self.recovery_manager = None
        self.monitoring_dashboard = None

        # Initialize database and file management
        self._initialize_database_components()

        # Initialize task tracking
        self._initialize_task_tracking()

        # Initialize session management
        self._initialize_session_management()

        # Initialize chat system
        self._initialize_chat_system()

        # Initialize monitoring system
        self._initialize_monitoring_system()

        # Check if we're in degraded mode
        if self.initialization_errors:
            self.degraded_mode = True
            self.logger.warning(f"Server in degraded mode. Errors: {self.initialization_errors}")

    def _initialize_database_components(self):
        """Initialize database and file management with error handling"""
        try:
            # Ensure database directory exists
            db_path = Path(self.db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            # Initialize enhanced file manager
            self.file_manager = EnhancedFileOwnershipManager(
                db_path=self.db_path,
                backup_dir=self.backup_dir
            )

            self.logger.info("Database and file management initialized successfully")

        except FileOwnershipError as e:
            error_msg = f"File ownership manager initialization failed: {e}"
            self.logger.error(error_msg)
            self.initialization_errors.append(error_msg)

            # Try fallback to basic file manager
            try:
                from src.managers.file_ownership import FileOwnershipManager
                self.file_manager = FileOwnershipManager(self.db_path)
                self.logger.warning("Using fallback file ownership manager")
            except Exception as fallback_error:
                self.logger.error(f"Fallback file manager also failed: {fallback_error}")
                self.file_manager = None

        except Exception as e:
            error_msg = f"Database initialization failed: {e}"
            self.logger.error(error_msg)
            self.initialization_errors.append(error_msg)
            self.file_manager = None

    def _initialize_task_tracking(self):
        """Initialize task tracking with error handling"""
        try:
            # Ensure sessions directory exists
            sessions_path = Path(self.sessions_dir)
            sessions_path.mkdir(parents=True, exist_ok=True)

            self.task_tracker = TaskProgressTracker(self.sessions_dir)
            self.logger.info("Task tracking initialized successfully")

        except Exception as e:
            error_msg = f"Task tracker initialization failed: {e}"
            self.logger.error(error_msg)
            self.initialization_errors.append(error_msg)
            self.task_tracker = None

    def _initialize_session_management(self):
        """Initialize session management with error handling"""
        try:
            if self.file_manager and self.task_tracker:
                self.session_manager = OpencodeSessionManager(
                    self.file_manager, self.sessions_dir, quiet_mode=True
                )
                self.logger.info("Session management initialized successfully")
            else:
                raise Exception("Dependencies not available")

        except Exception as e:
            error_msg = f"Session manager initialization failed: {e}"
            self.logger.error(error_msg)
            self.initialization_errors.append(error_msg)
            self.session_manager = None

    def _initialize_chat_system(self):
        """Initialize chat system with error handling"""
        try:
            self.telegram_manager = TelegramManager()

            if self.file_manager:
                self.agent_manager = AgentManager(self.file_manager, self.telegram_manager)

                if self.session_manager:
                    self.agent_bridge = AgentBridge(self.session_manager, self.agent_manager)

            self.logger.info("Chat system initialized successfully")

        except Exception as e:
            error_msg = f"Chat system initialization failed: {e}"
            self.logger.error(error_msg)
            self.initialization_errors.append(error_msg)
            # Chat system is optional, continue without it

    def _initialize_monitoring_system(self):
        """Initialize monitoring system with error handling"""
        if not MONITORING_AVAILABLE:
            self.logger.info("Monitoring system not available")
            return

        try:
            if self.agent_manager and self.task_tracker and self.session_manager:
                # Set up the agent manager with task tracker
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
            else:
                raise Exception("Required dependencies not available")

        except Exception as e:
            error_msg = f"Monitoring system initialization failed: {e}"
            self.logger.error(error_msg)
            self.initialization_errors.append(error_msg)
            # Monitoring is optional, continue without it

    def _setup_enhanced_routes(self):
        """Set up Flask routes with enhanced error handling"""

        # Error handler for all routes
        @self.app.errorhandler(Exception)
        def handle_exception(e):
            self.logger.error(f"Unhandled exception: {e}")
            self.logger.error(traceback.format_exc())

            return jsonify({
                'error': 'Internal server error',
                'message': str(e) if self.app.debug else 'An unexpected error occurred',
                'degraded_mode': self.degraded_mode
            }), 500

        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Enhanced health check endpoint"""
            try:
                health_status = {
                    'status': 'degraded' if self.degraded_mode else 'healthy',
                    'degraded_mode': self.degraded_mode,
                    'initialization_errors': self.initialization_errors,
                    'components': {
                        'file_manager': self.file_manager is not None,
                        'task_tracker': self.task_tracker is not None,
                        'session_manager': self.session_manager is not None,
                        'chat_system': self.agent_manager is not None,
                        'monitoring_system': self.health_monitor is not None
                    },
                    'chat_enabled': self.chat_enabled,
                    'active_sessions': len(self.session_manager.get_active_sessions()) if self.session_manager else 0,
                    'total_agents': len(self.agent_manager.agents) if self.agent_manager else 0
                }

                # Add detailed health information if available
                if self.file_manager and hasattr(self.file_manager, 'get_system_health'):
                    health_status['detailed_health'] = self.file_manager.get_system_health()

                return jsonify(health_status)

            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                return jsonify({
                    'status': 'failed',
                    'error': str(e),
                    'degraded_mode': True
                }), 500

        @self.app.route('/employees', methods=['GET'])
        def list_employees():
            """List all employees with error handling"""
            try:
                if not self.file_manager:
                    return jsonify({
                        'error': 'File manager not available',
                        'employees': []
                    }), 503

                employees = self.file_manager.list_employees()
                return jsonify({'employees': employees})

            except Exception as e:
                self.logger.error(f"Error listing employees: {e}")
                return jsonify({
                    'error': 'Failed to list employees',
                    'message': str(e),
                    'employees': []
                }), 500

        @self.app.route('/employees', methods=['POST'])
        def hire_employee():
            """Hire a new employee with enhanced error handling"""
            try:
                if not self.file_manager:
                    return jsonify({
                        'error': 'File manager not available'
                    }), 503

                data = request.get_json()
                if not data:
                    return jsonify({
                        'error': 'No JSON data provided'
                    }), 400

                name = data.get('name')
                role = data.get('role')
                smartness = data.get('smartness', 'normal')

                if not name or not role:
                    return jsonify({
                        'error': 'Name and role are required'
                    }), 400

                # Validate inputs
                if not isinstance(name, str) or not name.strip():
                    return jsonify({
                        'error': 'Name must be a non-empty string'
                    }), 400

                if not isinstance(role, str) or not role.strip():
                    return jsonify({
                        'error': 'Role must be a non-empty string'
                    }), 400

                success = self.file_manager.hire_employee(name, role, smartness)

                if success:
                    # Create communication agent if agent manager is available
                    if self.agent_manager:
                        try:
                            expertise = self.agent_manager._get_expertise_for_role(role)
                            self.agent_manager.create_agent(name, role, expertise)
                        except Exception as e:
                            self.logger.warning(f"Failed to create agent for {name}: {e}")

                    return jsonify({
                        'message': f'Successfully hired {name} as {role}',
                        'employee': {
                            'name': name,
                            'role': role,
                            'smartness': smartness
                        }
                    })
                else:
                    return jsonify({
                        'error': f'Failed to hire {name}. Employee may already exist.'
                    }), 400

            except Exception as e:
                self.logger.error(f"Error hiring employee: {e}")
                return jsonify({
                    'error': 'Failed to hire employee',
                    'message': str(e)
                }), 500

        @self.app.route('/employees/<name>', methods=['DELETE'])
        def fire_employee(name):
            """Fire an employee with enhanced error handling"""
            try:
                if not self.file_manager:
                    return jsonify({
                        'error': 'File manager not available'
                    }), 503

                if not name or not name.strip():
                    return jsonify({
                        'error': 'Employee name cannot be empty'
                    }), 400

                # Stop any active sessions first
                if self.session_manager and name in self.session_manager.active_sessions:
                    try:
                        self.session_manager.stop_employee_task(name)
                    except Exception as e:
                        self.logger.warning(f"Failed to stop session for {name}: {e}")

                # Remove communication agent
                if self.agent_manager:
                    try:
                        self.agent_manager.remove_agent(name)
                    except Exception as e:
                        self.logger.warning(f"Failed to remove agent for {name}: {e}")

                success = self.file_manager.fire_employee(name, self.task_tracker)

                if success:
                    return jsonify({
                        'message': f'Successfully fired {name}'
                    })
                else:
                    return jsonify({
                        'error': f'Failed to fire {name}. Employee may not exist.'
                    }), 400

            except Exception as e:
                self.logger.error(f"Error firing employee {name}: {e}")
                return jsonify({
                    'error': 'Failed to fire employee',
                    'message': str(e)
                }), 500

        @self.app.route('/tasks', methods=['POST'])
        def assign_task():
            """Assign a task to an employee with enhanced error handling"""
            try:
                if not self.file_manager:
                    return jsonify({
                        'error': 'File manager not available'
                    }), 503

                if not self.session_manager:
                    return jsonify({
                        'error': 'Session manager not available'
                    }), 503

                data = request.get_json()
                if not data:
                    return jsonify({
                        'error': 'No JSON data provided'
                    }), 400

                name = data.get('name')
                task_description = data.get('task')
                model = data.get('model', 'openrouter/qwen/qwen3-coder')
                mode = data.get('mode', 'build')

                if not name or not task_description:
                    return jsonify({
                        'error': 'Name and task are required'
                    }), 400

                # Validate inputs
                if not isinstance(name, str) or not name.strip():
                    return jsonify({
                        'error': 'Name must be a non-empty string'
                    }), 400

                if not isinstance(task_description, str) or not task_description.strip():
                    return jsonify({
                        'error': 'Task description must be a non-empty string'
                    }), 400

                # Make sure employee exists
                employees = self.file_manager.list_employees()
                employee_names = [emp['name'] for emp in employees]

                if name not in employee_names:
                    # Auto-hire as developer
                    if not self.file_manager.hire_employee(name, "developer"):
                        return jsonify({
                            'error': f'Failed to hire {name}'
                        }), 400

                    if self.agent_manager:
                        try:
                            expertise = self.agent_manager._get_expertise_for_role("developer")
                            self.agent_manager.create_agent(name, "developer", expertise)
                        except Exception as e:
                            self.logger.warning(f"Failed to create agent for {name}: {e}")

                # Start real opencode session
                session_id = self.session_manager.start_employee_task(
                    name, task_description, model, mode
                )

                if session_id:
                    return jsonify({
                        'message': f'Started task for {name}',
                        'session_id': session_id,
                        'task': task_description,
                        'model': model,
                        'mode': mode
                    })
                else:
                    return jsonify({
                        'error': f'Failed to start task for {name}'
                    }), 500

            except Exception as e:
                self.logger.error(f"Error assigning task: {e}")
                return jsonify({
                    'error': 'Failed to assign task',
                    'message': str(e)
                }), 500

        @self.app.route('/system/backup', methods=['POST'])
        def create_backup():
            """Create system backup"""
            try:
                if not self.file_manager or not hasattr(self.file_manager, 'create_backup'):
                    return jsonify({
                        'error': 'Backup functionality not available'
                    }), 503

                success = self.file_manager.create_backup()

                if success:
                    return jsonify({
                        'message': 'Backup created successfully'
                    })
                else:
                    return jsonify({
                        'error': 'Backup creation failed'
                    }), 500

            except Exception as e:
                self.logger.error(f"Error creating backup: {e}")
                return jsonify({
                    'error': 'Backup creation failed',
                    'message': str(e)
                }), 500

        @self.app.route('/system/vacuum', methods=['POST'])
        def vacuum_database():
            """Vacuum database for optimization"""
            try:
                if not self.file_manager or not hasattr(self.file_manager, 'vacuum_database'):
                    return jsonify({
                        'error': 'Database vacuum functionality not available'
                    }), 503

                success = self.file_manager.vacuum_database()

                if success:
                    return jsonify({
                        'message': 'Database vacuum completed successfully'
                    })
                else:
                    return jsonify({
                        'error': 'Database vacuum failed'
                    }), 500

            except Exception as e:
                self.logger.error(f"Error vacuuming database: {e}")
                return jsonify({
                    'error': 'Database vacuum failed',
                    'message': str(e)
                }), 500

        @self.app.route('/system/health/detailed', methods=['GET'])
        def get_detailed_health():
            """Get detailed system health information"""
            try:
                health_info = {
                    'server_status': 'degraded' if self.degraded_mode else 'healthy',
                    'initialization_errors': self.initialization_errors,
                    'components': {}
                }

                # Add component health information
                if self.file_manager and hasattr(self.file_manager, 'get_system_health'):
                    health_info['components']['file_system'] = self.file_manager.get_system_health()

                if self.health_monitor:
                    health_info['components']['monitoring'] = self.health_monitor.get_agent_health_summary()

                if self.recovery_manager:
                    health_info['components']['recovery'] = self.recovery_manager.get_recovery_summary()

                return jsonify(health_info)

            except Exception as e:
                self.logger.error(f"Error getting detailed health: {e}")
                return jsonify({
                    'error': 'Failed to get detailed health information',
                    'message': str(e)
                }), 500

        # Add all other routes from the original server with error handling
        self._add_remaining_routes()

    def _add_remaining_routes(self):
        """Add remaining routes from original server with error handling"""

        @self.app.route('/tasks/<name>', methods=['DELETE'])
        def stop_task(name):
            """Stop an employee's task"""
            try:
                if not self.session_manager:
                    return jsonify({'error': 'Session manager not available'}), 503

                self.session_manager.stop_employee_task(name)
                return jsonify({'message': f'Stopped task for {name}'})

            except Exception as e:
                self.logger.error(f"Error stopping task for {name}: {e}")
                return jsonify({
                    'error': 'Failed to stop task',
                    'message': str(e)
                }), 500

        @self.app.route('/status', methods=['GET'])
        def get_status():
            """Get comprehensive system status"""
            try:
                status = {
                    'degraded_mode': self.degraded_mode,
                    'initialization_errors': self.initialization_errors
                }

                if self.session_manager:
                    status['active_sessions'] = self.session_manager.get_active_sessions()
                else:
                    status['active_sessions'] = []

                if self.file_manager:
                    status['locked_files'] = self.file_manager.get_all_locked_files()
                    status['employees'] = self.file_manager.list_employees()
                else:
                    status['locked_files'] = []
                    status['employees'] = []

                status['chat_enabled'] = self.chat_enabled

                if self.agent_manager:
                    status['chat_statistics'] = self.agent_manager.get_chat_statistics()
                else:
                    status['chat_statistics'] = None

                return jsonify(status)

            except Exception as e:
                self.logger.error(f"Error getting status: {e}")
                return jsonify({
                    'error': 'Failed to get status',
                    'message': str(e),
                    'degraded_mode': True
                }), 500

    def start(self):
        """Start the enhanced server with comprehensive error handling"""
        self.running = True

        # Auto-start chat system if configured and available
        self._auto_start_chat_if_configured()

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.logger.info(f"Starting Enhanced OpenCode-Slack server on {self.host}:{self.port}")
        print(f"🚀 Enhanced OpenCode-Slack server starting on http://{self.host}:{self.port}")

        if self.degraded_mode:
            print(f"⚠️  Server running in DEGRADED MODE")
            print(f"   Errors: {len(self.initialization_errors)}")
            for error in self.initialization_errors:
                print(f"   - {error}")

        print(f"👥 {len(self.agent_manager.agents) if self.agent_manager else 0} communication agents ready")
        print("📊 Health check: GET /health")
        print("🔧 Detailed health: GET /system/health/detailed")
        print("💾 Create backup: POST /system/backup")
        print("Press Ctrl+C to stop")

        try:
            # Use Werkzeug's development server with proper shutdown handling
            from werkzeug.serving import make_server

            self.server_instance = make_server(
                self.host,
                self.port,
                self.app,
                threaded=True
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
        if not self.telegram_manager or not self.agent_bridge:
            print("💬 Chat system not available due to initialization errors")
            return

        try:
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

        except Exception as e:
            self.logger.error(f"Error in auto-start chat: {e}")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()

    def stop(self):
        """Stop the server with comprehensive cleanup"""
        self.logger.info("Shutting down Enhanced OpenCode-Slack server...")
        print("\n🛑 Shutting down server...")

        # Stop chat system
        self.chat_enabled = False

        # Clean up all active sessions and release locks
        print("🧹 Cleaning up active sessions and releasing file locks...")
        try:
            if self.session_manager:
                self.session_manager.cleanup_all_sessions()

            # Release all remaining locks
            if self.file_manager:
                employees = self.file_manager.list_employees()
                for employee in employees:
                    try:
                        released = self.file_manager.release_files(employee['name'])
                        if released:
                            print(f"   🔓 Released locks for {employee['name']}: {', '.join(released)}")
                    except Exception as e:
                        self.logger.warning(f"Error releasing locks for {employee['name']}: {e}")
        except Exception as e:
            print(f"⚠️  Error during cleanup: {e}")

        # Close database connections
        try:
            if self.file_manager and hasattr(self.file_manager, 'close'):
                self.file_manager.close()
                print("💾 Database connections closed")
        except Exception as e:
            self.logger.warning(f"Error closing database: {e}")

        self.running = False
        print("✅ Server shutdown complete")

        # Immediate exit
        import os
        os._exit(0)


def main():
    """Main function with enhanced error handling"""
    import argparse

    # Get default port from environment variable or use 8080
    default_port = int(os.environ.get('PORT', 8080))
    default_host = os.environ.get('HOST', 'localhost')

    parser = argparse.ArgumentParser(description='Enhanced OpenCode-Slack Server')
    parser.add_argument('--host', default=default_host,
                       help=f'Host to bind to (default: {default_host}, from HOST env var)')
    parser.add_argument('--port', type=int, default=default_port,
                       help=f'Port to bind to (default: {default_port}, from PORT env var)')
    parser.add_argument('--db-path', default='employees.db',
                       help='Database path (default: employees.db)')
    parser.add_argument('--sessions-dir', default='sessions',
                       help='Sessions directory (default: sessions)')
    parser.add_argument('--backup-dir',
                       help='Backup directory (default: <db-path-parent>/backups)')

    args = parser.parse_args()

    try:
        server = EnhancedOpencodeSlackServer(
            host=args.host,
            port=args.port,
            db_path=args.db_path,
            sessions_dir=args.sessions_dir,
            backup_dir=args.backup_dir
        )

        server.start()

    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()