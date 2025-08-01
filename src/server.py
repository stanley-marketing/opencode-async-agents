#!/usr/bin/env python3
"""
Standalone server for opencode-slack system.
Runs the employee management system with REST API and Telegram integration.
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
        
        # Initialize core components
        self.file_manager = FileOwnershipManager(db_path)
        self.task_tracker = TaskProgressTracker(sessions_dir)
        self.session_manager = OpencodeSessionManager(db_path, sessions_dir, quiet_mode=True)
        
        # Initialize chat system
        self.telegram_manager = TelegramManager()
        self.agent_manager = AgentManager(self.file_manager, self.telegram_manager)
        self.agent_bridge = AgentBridge(self.session_manager, self.agent_manager)
        
        # Initialize Flask app
        self.app = Flask(__name__)
        CORS(self.app)
        self._setup_routes()
        
        # Server state
        self.running = False
        self.chat_enabled = False
        
        self.logger.info(f"OpenCode-Slack server initialized on {host}:{port}")
    
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
    
    def start(self):
        """Start the server"""
        self.running = True
        
        # Auto-start chat system if configured
        self._auto_start_chat_if_configured()
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info(f"Starting OpenCode-Slack server on {self.host}:{self.port}")
        print(f"🚀 OpenCode-Slack server starting on http://{self.host}:{self.port}")
        print(f"👥 {len(self.agent_manager.agents)} communication agents ready")
        print("📊 Health check: GET /health")
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
        self.logger.info(f"Received signal {signum}, shutting down immediately...")
        import os
        os._exit(0)
    
    def stop(self):
        """Stop the server immediately"""
        self.logger.info("Shutting down OpenCode-Slack server immediately...")
        print("\n🛑 Shutting down server immediately...")
        
        # Stop chat system immediately
        self.chat_enabled = False
        
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