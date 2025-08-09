#!/usr/bin/env python3
"""
WebSocket-enabled OpenCode-Slack Server with real-time communication.
Enhanced version of the server with WebSocket support for modern UI.
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
from src.chat.communication_manager import CommunicationManager
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


class WebSocketOpencodeSlackServer:
    """WebSocket-enabled server with real-time communication capabilities"""

    def __init__(self, host="localhost", port=8080, websocket_port=8765, 
                 db_path="employees.db", sessions_dir="sessions", backup_dir=None,
                 transport_type=None):
        self.host = host
        self.port = port
        self.websocket_port = websocket_port
        self.db_path = db_path
        self.sessions_dir = sessions_dir
        self.backup_dir = backup_dir or str(Path(db_path).parent / "backups")
        self.transport_type = transport_type

        # Server state
        self.running = False
        self.chat_enabled = False
        self.degraded_mode = False
        self.initialization_errors = []

        # Load environment variables
        self._load_environment()

        # Configure logging
        self._setup_enhanced_logging()

        # Initialize core components
        self._initialize_components()

        # Initialize Flask app with WebSocket support
        self.app = Flask(__name__)
        CORS(self.app, origins=["http://localhost:3000", "http://127.0.0.1:3000"])  # Allow React dev server
        self._setup_enhanced_routes()

        self.logger.info(f"WebSocket OpenCode-Slack server initialized on {host}:{port}")
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
        self.communication_manager = None
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

        # Initialize communication system (WebSocket or Telegram)
        self._initialize_communication_system()

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

    def _initialize_communication_system(self):
        """Initialize communication system with WebSocket support"""
        try:
            # Create communication manager with WebSocket support
            self.communication_manager = CommunicationManager(
                transport_type=self.transport_type,
                host=self.host,
                port=self.websocket_port
            )

            if self.file_manager:
                self.agent_manager = AgentManager(self.file_manager, self.communication_manager)

                if self.session_manager:
                    self.agent_bridge = AgentBridge(self.session_manager, self.agent_manager)

            transport_type = self.communication_manager.get_transport_type()
            self.logger.info(f"Communication system initialized with {transport_type} transport")

        except Exception as e:
            error_msg = f"Communication system initialization failed: {e}"
            self.logger.error(error_msg)
            self.initialization_errors.append(error_msg)
            # Communication system is optional, continue without it

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
        """Set up Flask routes with enhanced error handling and WebSocket support"""

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
            """Enhanced health check endpoint with WebSocket info"""
            try:
                health_status = {
                    'status': 'degraded' if self.degraded_mode else 'healthy',
                    'degraded_mode': self.degraded_mode,
                    'initialization_errors': self.initialization_errors,
                    'components': {
                        'file_manager': self.file_manager is not None,
                        'task_tracker': self.task_tracker is not None,
                        'session_manager': self.session_manager is not None,
                        'communication_system': self.communication_manager is not None,
                        'monitoring_system': self.health_monitor is not None
                    },
                    'chat_enabled': self.chat_enabled,
                    'active_sessions': len(self.session_manager.get_active_sessions()) if self.session_manager else 0,
                    'total_agents': len(self.agent_manager.agents) if self.agent_manager else 0
                }

                # Add communication transport information
                if self.communication_manager:
                    health_status['communication'] = self.communication_manager.get_transport_info()

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

        @self.app.route('/communication/info', methods=['GET'])
        def get_communication_info():
            """Get information about the communication system"""
            try:
                if not self.communication_manager:
                    return jsonify({
                        'error': 'Communication system not available'
                    }), 503

                info = self.communication_manager.get_transport_info()
                return jsonify(info)

            except Exception as e:
                self.logger.error(f"Error getting communication info: {e}")
                return jsonify({
                    'error': 'Failed to get communication info',
                    'message': str(e)
                }), 500

        @self.app.route('/communication/switch', methods=['POST'])
        def switch_communication_transport():
            """Switch communication transport (Telegram <-> WebSocket)"""
            try:
                if not self.communication_manager:
                    return jsonify({
                        'error': 'Communication system not available'
                    }), 503

                data = request.get_json()
                if not data:
                    return jsonify({
                        'error': 'No JSON data provided'
                    }), 400

                new_transport = data.get('transport_type')
                if new_transport not in ['telegram', 'websocket']:
                    return jsonify({
                        'error': 'Invalid transport type. Must be "telegram" or "websocket"'
                    }), 400

                # Extract transport-specific config
                config = data.get('config', {})

                success = self.communication_manager.switch_transport(new_transport, **config)

                if success:
                    return jsonify({
                        'message': f'Successfully switched to {new_transport} transport',
                        'transport_info': self.communication_manager.get_transport_info()
                    })
                else:
                    return jsonify({
                        'error': f'Failed to switch to {new_transport} transport'
                    }), 500

            except Exception as e:
                self.logger.error(f"Error switching transport: {e}")
                return jsonify({
                    'error': 'Failed to switch transport',
                    'message': str(e)
                }), 500

        @self.app.route('/communication/stats', methods=['GET'])
        def get_communication_stats():
            """Get communication statistics"""
            try:
                if not self.communication_manager:
                    return jsonify({
                        'error': 'Communication system not available'
                    }), 503

                stats = self.communication_manager.get_statistics()
                return jsonify(stats)

            except Exception as e:
                self.logger.error(f"Error getting communication stats: {e}")
                return jsonify({
                    'error': 'Failed to get communication stats',
                    'message': str(e)
                }), 500

        # Include all the original routes from enhanced_server.py
        self._add_original_routes()

    def _add_original_routes(self):
        """Add all original routes from enhanced_server.py"""
        
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

                # Add communication info
                if self.communication_manager:
                    status['communication'] = self.communication_manager.get_transport_info()

                return jsonify(status)

            except Exception as e:
                self.logger.error(f"Error getting status: {e}")
                return jsonify({
                    'error': 'Failed to get status',
                    'message': str(e),
                    'degraded_mode': True
                }), 500

    def start(self):
        """Start the WebSocket-enabled server"""
        self.running = True

        # Auto-start communication system if configured and available
        self._auto_start_communication_if_configured()

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.logger.info(f"Starting WebSocket OpenCode-Slack server on {self.host}:{self.port}")
        print(f"🚀 WebSocket OpenCode-Slack server starting on http://{self.host}:{self.port}")

        if self.communication_manager:
            transport_type = self.communication_manager.get_transport_type()
            if transport_type == 'websocket':
                print(f"🔌 WebSocket server on ws://{self.host}:{self.websocket_port}")
            else:
                print(f"📱 Using {transport_type} transport")

        if self.degraded_mode:
            print(f"⚠️  Server running in DEGRADED MODE")
            print(f"   Errors: {len(self.initialization_errors)}")
            for error in self.initialization_errors:
                print(f"   - {error}")

        print(f"👥 {len(self.agent_manager.agents) if self.agent_manager else 0} communication agents ready")
        print("📊 Health check: GET /health")
        print("🔧 Communication info: GET /communication/info")
        print("🔄 Switch transport: POST /communication/switch")
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

    def _auto_start_communication_if_configured(self):
        """Auto-start communication system if properly configured"""
        if not self.communication_manager:
            print("💬 Communication system not available due to initialization errors")
            return

        try:
            # Check for safe mode environment variable
            safe_mode = os.environ.get('OPENCODE_SAFE_MODE', '').lower() in ['true', '1', 'yes']

            if safe_mode and self.communication_manager.get_transport_type() == 'telegram':
                print("🔒 Safe mode enabled - Telegram chat disabled")
                print("   Set OPENCODE_SAFE_MODE=false to enable Telegram")
                return

            try:
                self.communication_manager.start_polling()
                if self.agent_bridge:
                    self.agent_bridge.start_monitoring()
                self.chat_enabled = True
                
                transport_type = self.communication_manager.get_transport_type()
                print(f"💬 {transport_type.title()} communication system auto-started!")
                self.logger.info(f"{transport_type} communication system auto-started")
                
            except Exception as e:
                print(f"⚠️  Failed to auto-start communication system: {e}")
                self.logger.error(f"Failed to auto-start communication system: {e}")

        except Exception as e:
            self.logger.error(f"Error in auto-start communication: {e}")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()

    def stop(self):
        """Stop the server with comprehensive cleanup"""
        self.logger.info("Shutting down WebSocket OpenCode-Slack server...")
        print("\n🛑 Shutting down server...")

        # Stop communication system
        self.chat_enabled = False
        if self.communication_manager:
            try:
                self.communication_manager.stop_polling()
                print("💬 Communication system stopped")
            except Exception as e:
                self.logger.warning(f"Error stopping communication system: {e}")

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

    # Get default values from environment variables
    default_port = int(os.environ.get('PORT', 8080))
    default_host = os.environ.get('HOST', 'localhost')
    default_websocket_port = int(os.environ.get('WEBSOCKET_PORT', 8765))
    default_transport = os.environ.get('OPENCODE_TRANSPORT', 'websocket')

    parser = argparse.ArgumentParser(description='WebSocket OpenCode-Slack Server')
    parser.add_argument('--host', default=default_host,
                       help=f'Host to bind to (default: {default_host})')
    parser.add_argument('--port', type=int, default=default_port,
                       help=f'HTTP port to bind to (default: {default_port})')
    parser.add_argument('--websocket-port', type=int, default=default_websocket_port,
                       help=f'WebSocket port to bind to (default: {default_websocket_port})')
    parser.add_argument('--transport', choices=['telegram', 'websocket'], default=default_transport,
                       help=f'Communication transport (default: {default_transport})')
    parser.add_argument('--db-path', default='employees.db',
                       help='Database path (default: employees.db)')
    parser.add_argument('--sessions-dir', default='sessions',
                       help='Sessions directory (default: sessions)')
    parser.add_argument('--backup-dir',
                       help='Backup directory (default: <db-path-parent>/backups)')

    args = parser.parse_args()

    try:
        server = WebSocketOpencodeSlackServer(
            host=args.host,
            port=args.port,
            websocket_port=args.websocket_port,
            db_path=args.db_path,
            sessions_dir=args.sessions_dir,
            backup_dir=args.backup_dir,
            transport_type=args.transport
        )

        server.start()

    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()