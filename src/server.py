#!/usr/bin/env python3
"""
Standalone server for opencode-slack system.
Runs the employee management system with REST API and Telegram integration.
"""

from datetime import datetime
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

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.managers.file_ownership import FileOwnershipManager
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


def serialize_for_json(obj):
    """Convert objects to JSON-serializable format"""
    from enum import Enum
    from datetime import datetime

    if isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, '__dict__'):
        result = {}
        for key, value in obj.__dict__.items():
            result[key] = serialize_for_json(value)
        return result
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    else:
        return obj


class OpencodeSlackServer:
    """Standalone server for opencode-slack system"""

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

        # Initialize core components in proper order
        self.file_manager = FileOwnershipManager(db_path)
        self.task_tracker = TaskProgressTracker(sessions_dir)
        self.session_manager = OpencodeSessionManager(self.file_manager, sessions_dir, quiet_mode=True)

        # Initialize chat system
        self.telegram_manager = TelegramManager()
        self.agent_manager = AgentManager(self.file_manager, self.telegram_manager)

        # CRITICAL FIX: Set up monitoring system BEFORE creating bridge
        # This ensures agents have proper task tracker references
        self.agent_manager.setup_monitoring_system(self.task_tracker, self.session_manager)

        # Ensure all existing employees have agents
        self.agent_manager.sync_agents_with_employees()

        self.agent_bridge = AgentBridge(self.session_manager, self.agent_manager)

        # Set up advanced monitoring system after all components are initialized
        self._setup_advanced_monitoring_system()

        # Initialize Flask app
        self.app = Flask(__name__)
        CORS(self.app)
        self._setup_routes()

        # Server state
        self.running = False
        self.chat_enabled = False

        self.logger.info(f"OpenCode-Slack server initialized on {host}:{port}")

    def _setup_advanced_monitoring_system(self):
        """Set up the production-grade monitoring system"""
        if not MONITORING_AVAILABLE:
            self.logger.info("Advanced monitoring system not available")
            return

        try:
            # Import production monitoring components
            from src.monitoring.production_monitoring_system import ProductionMonitoringSystem, MonitoringConfiguration

            # Configure production monitoring
            monitoring_config = MonitoringConfiguration(
                metrics_collection_interval=int(os.environ.get('MONITORING_METRICS_INTERVAL', 30)),
                health_check_interval=int(os.environ.get('MONITORING_HEALTH_INTERVAL', 30)),
                alert_processing_interval=int(os.environ.get('MONITORING_ALERT_INTERVAL', 15)),
                dashboard_port=int(os.environ.get('MONITORING_DASHBOARD_PORT', 8083)),
                dashboard_host=os.environ.get('MONITORING_DASHBOARD_HOST', '0.0.0.0'),
                auto_recovery_enabled=os.environ.get('MONITORING_AUTO_RECOVERY', 'true').lower() == 'true',
                data_retention_days=int(os.environ.get('MONITORING_RETENTION_DAYS', 30)),
                enable_dashboard=os.environ.get('MONITORING_ENABLE_DASHBOARD', 'true').lower() == 'true',
                enable_mobile_dashboard=os.environ.get('MONITORING_ENABLE_MOBILE', 'true').lower() == 'true',
                service_name="opencode-slack"
            )

            # Initialize production monitoring system
            self.production_monitoring = ProductionMonitoringSystem(
                agent_manager=self.agent_manager,
                task_tracker=self.task_tracker,
                session_manager=self.session_manager,
                config=monitoring_config
            )

            # Keep backward compatibility with existing monitoring
            self.health_monitor = self.production_monitoring.health_checker
            self.recovery_manager = self.production_monitoring.health_checker
            self.monitoring_dashboard = self.production_monitoring.dashboard

            self.logger.info("Production monitoring system initialized")
            print("🔍 Production monitoring system initialized")

        except ImportError as e:
            self.logger.warning(f"Production monitoring not available, falling back to basic monitoring: {e}")
            self._setup_basic_monitoring_fallback()
        except Exception as e:
            self.logger.error(f"Error setting up production monitoring system: {e}")
            print(f"⚠️  Failed to initialize production monitoring system: {e}")
            self._setup_basic_monitoring_fallback()

    def _setup_basic_monitoring_fallback(self):
        """Set up basic monitoring system as fallback"""
        try:
            # Initialize basic health monitor
            self.health_monitor = AgentHealthMonitor(self.agent_manager, self.task_tracker)

            # Initialize basic recovery manager
            self.recovery_manager = AgentRecoveryManager(self.agent_manager, self.session_manager)

            # Initialize basic monitoring dashboard
            self.monitoring_dashboard = MonitoringDashboard(self.health_monitor, self.recovery_manager)

            # Set up anomaly callback
            def anomaly_callback(agent_name, anomalies, status_record):
                if self.recovery_manager:
                    self.recovery_manager.handle_agent_anomaly(agent_name, anomalies, status_record)

            # Start monitoring
            self.health_monitor.start_monitoring(anomaly_callback)

            self.logger.info("Basic monitoring system initialized and started")
            print("🔍 Basic agent monitoring system initialized")

        except Exception as e:
            self.logger.error(f"Error setting up basic monitoring system: {e}")
            print(f"⚠️  Failed to initialize basic monitoring system: {e}")
            self.health_monitor = None
            self.recovery_manager = None
            self.monitoring_dashboard = None

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
        """Set up Flask routes"""

        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'chat_enabled': self.chat_enabled,
                'active_sessions': len(self.session_manager.get_active_sessions()),
                'total_agents': len(self.agent_manager.agents)
            })

        @self.app.route('/employees', methods=['GET'])
        def list_employees():
            """List all employees"""
            employees = self.file_manager.list_employees()
            return jsonify({'employees': employees})

        @self.app.route('/employees', methods=['POST'])
        def hire_employee():
            """Hire a new employee"""
            data = request.get_json()
            name = data.get('name')
            role = data.get('role')
            smartness = data.get('smartness', 'normal')

            if not name or not role:
                return jsonify({'error': 'Name and role are required'}), 400

            success = self.file_manager.hire_employee(name, role, smartness)
            if success:
                # CRITICAL FIX: Create communication agent immediately after hiring
                expertise = self.agent_manager._get_expertise_for_role(role)
                agent = self.agent_manager.create_agent(name, role, expertise)

                # Ensure agent has proper task tracker reference
                if hasattr(self.agent_manager, 'task_tracker') and self.agent_manager.task_tracker:
                    agent.task_tracker = self.agent_manager.task_tracker

                # Sync agents to ensure consistency
                self.agent_manager.sync_agents_with_employees()

                return jsonify({'message': f'Successfully hired {name} as {role} with {smartness} smartness'})
            else:
                return jsonify({'error': f'Failed to hire {name}. Employee may already exist.'}), 400

        @self.app.route('/employees/<name>', methods=['DELETE'])
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

        @self.app.route('/tasks', methods=['POST'])
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
        def stop_task(name):
            """Stop an employee's task"""
            self.session_manager.stop_employee_task(name)
            return jsonify({'message': f'Stopped task for {name}'})

        @self.app.route('/status', methods=['GET'])
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

        @self.app.route('/sessions', methods=['GET'])
        def get_sessions():
            """Get active sessions"""
            active_sessions = self.session_manager.get_active_sessions()
            return jsonify({'sessions': active_sessions})

        @self.app.route('/files', methods=['GET'])
        def get_files():
            """Get locked files"""
            all_files = self.file_manager.get_all_locked_files()
            return jsonify({'files': all_files})

        @self.app.route('/files/lock', methods=['POST'])
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
        def release_files():
            """Release files for an employee"""
            data = request.get_json()
            name = data.get('name')
            files = data.get('files')  # Optional, if None releases all

            if not name:
                return jsonify({'error': 'Name is required'}), 400

            released = self.file_manager.release_files(name, files)
            return jsonify({'released': released})

        @self.app.route('/progress', methods=['GET'])
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

        @self.app.route('/chat/start', methods=['POST'])
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
        def stop_chat():
            """Stop the chat system"""
            if not self.chat_enabled:
                return jsonify({'error': 'Chat system is not running'}), 400

            self.telegram_manager.stop_polling()
            self.chat_enabled = False
            return jsonify({'message': 'Chat system stopped'})

        @self.app.route('/chat/status', methods=['GET'])
        def get_chat_status():
            """Get chat system status"""
            from src.chat.chat_config import config

            return jsonify({
                'configured': config.is_configured(),
                'connected': self.telegram_manager.is_connected(),
                'polling': self.chat_enabled,
                'statistics': self.agent_manager.get_chat_statistics()
            })

        @self.app.route('/chat/debug', methods=['GET'])
        def get_chat_debug():
            """Get detailed chat debug information"""
            from src.chat.chat_config import config

            debug_info = {
                'configured': config.is_configured(),
                'connected': self.telegram_manager.is_connected(),
                'polling': self.chat_enabled,
                'statistics': self.agent_manager.get_chat_statistics()
            }

            # Add webhook information
            try:
                webhook_info = self.telegram_manager.get_webhook_info()
                debug_info['webhook_info'] = webhook_info
            except Exception as e:
                debug_info['webhook_error'] = str(e)

            # Add bot information
            try:
                import requests
                url = f"{self.telegram_manager.base_url}/getMe"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('ok'):
                        debug_info['bot_info'] = data.get('result', {})
            except Exception as e:
                debug_info['bot_info_error'] = str(e)

            return jsonify(debug_info)

        @self.app.route('/chat/send', methods=['POST'])
        def send_chat_message():
            """Send a message to the chat"""
            data = request.get_json()
            message = data.get('message')
            sender = data.get('sender', 'system')

            if not message:
                return jsonify({'error': 'Message is required'}), 400

            if not self.telegram_manager.is_connected():
                return jsonify({'error': 'Chat system not connected'}), 400

            success = self.telegram_manager.send_message(message, sender)
            if success:
                return jsonify({'message': 'Message sent successfully'})
            else:
                return jsonify({'error': 'Failed to send message'}), 500

        @self.app.route('/agents', methods=['GET'])
        def get_agents():
            """Get communication agents status"""
            agents_status = self.agent_manager.get_agent_status()
            return jsonify({'agents': agents_status})

        @self.app.route('/bridge', methods=['GET'])
        def get_bridge_status():
            """Get agent bridge status"""
            bridge_status = self.agent_bridge.get_bridge_status()
            return jsonify({'bridge': bridge_status})

        @self.app.route('/project-root', methods=['GET'])
        def get_project_root():
            """Get the current project root directory"""
            project_root = self.file_manager.get_project_root()
            return jsonify({'project_root': project_root})

        @self.app.route('/project-root', methods=['POST'])
        def set_project_root():
            """Set the project root directory"""
            data = request.get_json()
            project_root = data.get('project_root')

            if not project_root:
                return jsonify({'error': 'project_root is required'}), 400

            success = self.file_manager.set_project_root(project_root)
            if success:
                return jsonify({'message': f'Project root set to {project_root}'})
            else:
                return jsonify({'error': 'Failed to set project root'}), 500

        # Monitoring endpoints
        @self.app.route('/monitoring/health', methods=['GET'])
        def get_monitoring_health():
            """Get agent health monitoring status"""
            if hasattr(self, 'production_monitoring') and self.production_monitoring:
                # Use production monitoring system
                try:
                    system_status = self.production_monitoring.get_system_status()
                    health_data = system_status.get('health', {})

                    # Ensure all data is JSON serializable
                    if 'error' in system_status:
                        return jsonify({'error': system_status['error'], 'status': 'error'}), 500

                    return jsonify({
                        'status': 'success',
                        'health': health_data,
                        'timestamp': datetime.now().isoformat()
                    })
                except Exception as e:
                    self.logger.error(f"Error getting production health status: {e}")
                    return jsonify({
                        'error': 'Production monitoring error',
                        'details': str(e),
                        'status': 'error'
                    }), 500
            elif self.health_monitor:
                # Fallback to basic monitoring
                try:
                    health_summary = self.health_monitor.get_agent_health_summary()
                    return jsonify({
                        'status': 'success',
                        'health': health_summary,
                        'timestamp': datetime.now().isoformat()
                    })
                except Exception as e:
                    self.logger.error(f"Error getting basic health status: {e}")
                    return jsonify({
                        'error': 'Basic monitoring error',
                        'details': str(e),
                        'status': 'error'
                    }), 500
            else:
                return jsonify({
                    'error': 'Monitoring system not available',
                    'status': 'unavailable'
                }), 503

        @self.app.route('/monitoring/recovery', methods=['GET'])
        def get_monitoring_recovery():
            """Get agent recovery status"""
            if hasattr(self, 'production_monitoring') and self.production_monitoring:
                # Use production monitoring system
                try:
                    recovery_history = self.production_monitoring.health_checker.get_recovery_history(24)
                    recovery_summary = self.production_monitoring.health_checker.get_overall_health()

                    return jsonify({
                        'status': 'success',
                        'recovery_history': recovery_history,
                        'recovery_summary': recovery_summary,
                        'timestamp': datetime.now().isoformat()
                    })
                except Exception as e:
                    self.logger.error(f"Error getting production recovery status: {e}")
                    return jsonify({
                        'error': 'Production monitoring error',
                        'details': str(e),
                        'status': 'error'
                    }), 500
            elif self.recovery_manager:
                # Fallback to basic monitoring
                try:
                    recovery_summary = self.recovery_manager.get_recovery_summary()
                    return jsonify({
                        'status': 'success',
                        'recovery': recovery_summary,
                        'timestamp': datetime.now().isoformat()
                    })
                except Exception as e:
                    self.logger.error(f"Error getting basic recovery status: {e}")
                    return jsonify({
                        'error': 'Basic recovery error',
                        'details': str(e),
                        'status': 'error'
                    }), 500
            else:
                return jsonify({
                    'error': 'Recovery system not available',
                    'status': 'unavailable'
                }), 503

        @self.app.route('/monitoring/agents/<agent_name>', methods=['GET'])
        def get_agent_monitoring_details(agent_name):
            """Get detailed monitoring information for a specific agent"""
            if hasattr(self, 'production_monitoring') and self.production_monitoring:
                # Use production monitoring system
                try:
                    system_status = self.production_monitoring.get_system_status()
                    health_data = system_status.get('health', {})
                    agent_details = health_data.get('components', {}).get('agent_manager', {})

                    # Get observability data for the agent
                    observability_data = self.production_monitoring.get_observability_data(hours=24)

                    return jsonify({
                        'agent': agent_name,
                        'health': agent_details,
                        'observability': observability_data,
                        'metrics': system_status.get('metrics', {})
                    })
                except Exception as e:
                    self.logger.error(f"Error getting production agent details: {e}")
                    return jsonify({'error': 'Production monitoring error'}), 500
            elif self.health_monitor and self.recovery_manager:
                # Fallback to basic monitoring
                health_summary = self.health_monitor.get_agent_health_summary()
                agent_details = health_summary.get('agent_details', {}).get(agent_name, {})

                recovery_history = self.recovery_manager.get_recovery_history(agent_name)

                return jsonify({
                    'agent': agent_name,
                    'health': agent_details,
                    'recovery_history': recovery_history.get(agent_name, [])
                })
            else:
                return jsonify({'error': 'Monitoring system not available'}), 400

        # Production monitoring endpoints
        @self.app.route('/monitoring/production/status', methods=['GET'])
        def get_production_monitoring_status():
            """Get comprehensive production monitoring status"""
            if hasattr(self, 'production_monitoring') and self.production_monitoring:
                try:
                    system_status = self.production_monitoring.get_system_status()

                    # Ensure all data is JSON serializable
                    if 'error' in system_status:
                        return jsonify({
                            'error': system_status['error'],
                            'status': 'error',
                            'timestamp': datetime.now().isoformat()
                        }), 500

                    # Add success status and timestamp
                    system_status['status'] = 'success'
                    system_status['timestamp'] = datetime.now().isoformat()

                    return jsonify(system_status)
                except Exception as e:
                    self.logger.error(f"Error getting production monitoring status: {e}")
                    return jsonify({
                        'error': 'Production monitoring error',
                        'details': str(e),
                        'status': 'error',
                        'timestamp': datetime.now().isoformat()
                    }), 500
            else:
                return jsonify({
                    'error': 'Production monitoring not available',
                    'status': 'unavailable',
                    'timestamp': datetime.now().isoformat()
                }), 503

        @self.app.route('/monitoring/production/performance', methods=['GET'])
        def get_production_performance():
            """Get production performance summary"""
            if hasattr(self, 'production_monitoring') and self.production_monitoring:
                try:
                    hours = int(request.args.get('hours', 24))
                    return jsonify(self.production_monitoring.get_performance_summary(hours))
                except Exception as e:
                    self.logger.error(f"Error getting production performance: {e}")
                    return jsonify({'error': str(e)}), 500
            else:
                return jsonify({'error': 'Production monitoring not available'}), 404

        @self.app.route('/monitoring/production/alerts', methods=['GET'])
        def get_production_alerts():
            """Get production alerts"""
            if hasattr(self, 'production_monitoring') and self.production_monitoring:
                try:
                    active_alerts = self.production_monitoring.alerting_system.get_active_alerts()
                    alert_history = self.production_monitoring.alerting_system.get_alert_history(24)
                    alert_stats = self.production_monitoring.alerting_system.get_alerting_statistics()

                    return jsonify(serialize_for_json({
                        'active_alerts': active_alerts,
                        'alert_history': alert_history,
                        'statistics': alert_stats
                    }))
                except Exception as e:
                    self.logger.error(f"Error getting production alerts: {e}")
                    return jsonify({'error': str(e)}), 500
            else:
                return jsonify({'error': 'Production monitoring not available'}), 404

        @self.app.route('/monitoring/production/alerts/<alert_id>/acknowledge', methods=['POST'])
        def acknowledge_production_alert(alert_id):
            """Acknowledge a production alert"""
            if hasattr(self, 'production_monitoring') and self.production_monitoring:
                try:
                    data = request.get_json() or {}
                    acknowledged_by = data.get('acknowledged_by', 'unknown')

                    success = self.production_monitoring.acknowledge_alert(alert_id, acknowledged_by)

                    if success:
                        return jsonify({'message': f'Alert {alert_id} acknowledged by {acknowledged_by}'})
                    else:
                        return jsonify({'error': 'Failed to acknowledge alert'}), 400
                except Exception as e:
                    self.logger.error(f"Error acknowledging alert: {e}")
                    return jsonify({'error': str(e)}), 500
            else:
                return jsonify({'error': 'Production monitoring not available'}), 404

        @self.app.route('/monitoring/production/recovery/<action_name>', methods=['POST'])
        def trigger_production_recovery(action_name):
            """Trigger a production recovery action"""
            if hasattr(self, 'production_monitoring') and self.production_monitoring:
                try:
                    success = self.production_monitoring.trigger_recovery_action(action_name)

                    if success:
                        return jsonify({'message': f'Recovery action {action_name} triggered successfully'})
                    else:
                        return jsonify({'error': f'Failed to trigger recovery action {action_name}'}), 400
                except Exception as e:
                    self.logger.error(f"Error triggering recovery action: {e}")
                    return jsonify({'error': str(e)}), 500
            else:
                return jsonify({'error': 'Production monitoring not available'}), 404

        @self.app.route('/monitoring/production/export', methods=['GET'])
        def export_production_monitoring_data():
            """Export production monitoring data"""
            if hasattr(self, 'production_monitoring') and self.production_monitoring:
                try:
                    format_type = request.args.get('format', 'json')
                    hours = int(request.args.get('hours', 24))

                    exported_data = self.production_monitoring.export_monitoring_data(format_type, hours)

                    if format_type.lower() == 'json':
                        return jsonify({'data': exported_data})
                    else:
                        return exported_data, 200, {'Content-Type': 'text/plain'}
                except Exception as e:
                    self.logger.error(f"Error exporting monitoring data: {e}")
                    return jsonify({'error': str(e)}), 500
            else:
                return jsonify({'error': 'Production monitoring not available'}), 404

    def start(self):
        """Start the server"""
        self.running = True

        # Start production monitoring system if available
        if hasattr(self, 'production_monitoring') and self.production_monitoring:
            try:
                self.production_monitoring.start()
                self.logger.info("Production monitoring system started")
            except Exception as e:
                self.logger.error(f"Failed to start production monitoring: {e}")

        # Auto-start chat system if configured
        self._auto_start_chat_if_configured()

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.logger.info(f"Starting OpenCode-Slack server on {self.host}:{self.port}")
        print(f"🚀 OpenCode-Slack server starting on http://{self.host}:{self.port}")
        print(f"👥 {len(self.agent_manager.agents)} communication agents ready")
        print("📊 Health check: GET /health")

        # Show monitoring information
        if hasattr(self, 'production_monitoring') and self.production_monitoring:
            if self.production_monitoring.dashboard:
                dashboard_port = self.production_monitoring.config.dashboard_port
                dashboard_host = self.production_monitoring.config.dashboard_host
                print(f"🎛️  Production Dashboard: http://{dashboard_host}:{dashboard_port}")
                print(f"📱 Mobile Dashboard: http://{dashboard_host}:{dashboard_port}/mobile")
            print("📈 Production Monitoring: GET /monitoring/production/status")
            print("🚨 Alerts: GET /monitoring/production/alerts")
            print("⚡ Performance: GET /monitoring/production/performance")
        else:
            print("🔍 Basic Monitoring: GET /monitoring/health")

        print("🔗 API documentation available at /docs (if implemented)")
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
        self.logger.info("Shutting down OpenCode-Slack server immediately...")
        print("\n🛑 Shutting down server immediately...")

        # Stop production monitoring system if available
        if hasattr(self, 'production_monitoring') and self.production_monitoring:
            try:
                print("🔍 Stopping production monitoring system...")
                self.production_monitoring.stop()
                self.logger.info("Production monitoring system stopped")
            except Exception as e:
                self.logger.error(f"Error stopping production monitoring: {e}")
                print(f"⚠️  Error stopping production monitoring: {e}")

        # Stop basic monitoring if available
        if hasattr(self, 'health_monitor') and self.health_monitor:
            try:
                self.health_monitor.stop_monitoring()
            except Exception as e:
                self.logger.error(f"Error stopping health monitor: {e}")

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
        print("✅ Server shutdown complete")

        # Immediate exit
        import os
        os._exit(0)


def main():
    """Main function"""
    import argparse

    # Get default port from environment variable or use 8080
    default_port = int(os.environ.get('PORT', 8080))
    default_host = os.environ.get('HOST', 'localhost')

    parser = argparse.ArgumentParser(description='OpenCode-Slack Server')
    parser.add_argument('--host', default=default_host, help=f'Host to bind to (default: {default_host}, from HOST env var)')
    parser.add_argument('--port', type=int, default=default_port, help=f'Port to bind to (default: {default_port}, from PORT env var)')
    parser.add_argument('--db-path', default='employees.db', help='Database path (default: employees.db)')
    parser.add_argument('--sessions-dir', default='sessions', help='Sessions directory (default: sessions)')

    args = parser.parse_args()

    server = OpencodeSlackServer(
        host=args.host,
        port=args.port,
        db_path=args.db_path,
        sessions_dir=args.sessions_dir
    )

    server.start()


if __name__ == "__main__":
    main()