"""
Comprehensive tests for the OpenCode-Slack server.
This file provides full coverage for all server endpoints and functionality.
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock, call
import json
import tempfile
import os
from pathlib import Path

# Import the server module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.server import OpencodeSlackServer


class TestOpencodeSlackServerComprehensive(unittest.TestCase):
    """Comprehensive test cases for OpencodeSlackServer"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary database and sessions directory
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_employees.db")
        self.sessions_dir = os.path.join(self.temp_dir, "test_sessions")
        
        # Mock environment loading - patch the _load_environment method instead
        with patch.object(OpencodeSlackServer, '_load_environment'):
            self.server = OpencodeSlackServer(
                host="localhost",
                port=8082,  # Use different port for testing
                db_path=self.db_path,
                sessions_dir=self.sessions_dir
            )
        
        # Create test client
        self.client = self.server.app.test_client()
        self.client.testing = True
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    # Health check endpoint tests
    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get('/health')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('chat_enabled', data)
        self.assertIn('active_sessions', data)
        self.assertIn('total_agents', data)
    
    # Employee management endpoint tests
    def test_list_employees_empty(self):
        """Test listing employees when none exist"""
        response = self.client.get('/employees')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['employees'], [])
    
    def test_list_employees_with_data(self):
        """Test listing employees when some exist"""
        # Hire some employees
        self.client.post('/employees', json={'name': 'john', 'role': 'developer'})
        self.client.post('/employees', json={'name': 'jane', 'role': 'tester'})
        
        response = self.client.get('/employees')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data['employees']), 2)
        employee_names = [emp['name'] for emp in data['employees']]
        self.assertIn('john', employee_names)
        self.assertIn('jane', employee_names)
    
    def test_hire_employee_success(self):
        """Test successful employee hiring"""
        response = self.client.post('/employees', 
                                  json={'name': 'john', 'role': 'developer'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('Successfully hired john', data['message'])
        
        # Verify employee was created
        response = self.client.get('/employees')
        data = json.loads(response.data)
        self.assertEqual(len(data['employees']), 1)
        self.assertEqual(data['employees'][0]['name'], 'john')
        self.assertEqual(data['employees'][0]['role'], 'developer')
    
    def test_hire_employee_missing_data(self):
        """Test hiring employee with missing data"""
        response = self.client.post('/employees', json={'name': 'john'})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('Name and role are required', data['error'])
    
    def test_hire_employee_duplicate(self):
        """Test hiring duplicate employee"""
        # Hire first time
        self.client.post('/employees', json={'name': 'john', 'role': 'developer'})
        
        # Try to hire again
        response = self.client.post('/employees', json={'name': 'john', 'role': 'tester'})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('Failed to hire john', data['error'])
    
    def test_fire_employee_success(self):
        """Test successful employee firing"""
        # Hire employee first
        self.client.post('/employees', json={'name': 'john', 'role': 'developer'})
        
        # Fire employee
        response = self.client.delete('/employees/john')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('Successfully fired john', data['message'])
        
        # Verify employee was removed
        response = self.client.get('/employees')
        data = json.loads(response.data)
        self.assertEqual(len(data['employees']), 0)
    
    def test_fire_nonexistent_employee(self):
        """Test firing non-existent employee"""
        response = self.client.delete('/employees/nonexistent')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('Failed to fire nonexistent', data['error'])
    
    def test_fire_employee_with_active_session(self):
        """Test firing employee with active session"""
        # Hire employee
        self.client.post('/employees', json={'name': 'john', 'role': 'developer'})
        
        # Mock session manager to simulate active session
        with patch.object(self.server.session_manager, 'active_sessions', {'john': 'session_123'}):
            with patch.object(self.server.session_manager, 'stop_employee_task') as mock_stop:
                # Fire employee
                response = self.client.delete('/employees/john')
                
                # Verify stop_employee_task was called
                mock_stop.assert_called_once_with('john')
                
                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertIn('Successfully fired john', data['message'])
    
    # Task assignment endpoint tests
    @patch('src.server.OpencodeSessionManager')
    def test_assign_task_success(self, mock_session_manager):
        """Test successful task assignment"""
        # Mock session manager
        mock_instance = mock_session_manager.return_value
        mock_instance.start_employee_task.return_value = "session_123"
        
        # Hire employee first
        self.client.post('/employees', json={'name': 'john', 'role': 'developer'})
        
        # Assign task
        response = self.client.post('/tasks', json={
            'name': 'john',
            'task': 'implement authentication',
            'model': 'gpt-4',
            'mode': 'build'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('Started task for john', data['message'])
        # Note: session_id will be dynamically generated, so we just check it exists
        self.assertIn('session_id', data)
    
    def test_assign_task_missing_data(self):
        """Test task assignment with missing data"""
        response = self.client.post('/tasks', json={'name': 'john'})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('Name and task are required', data['error'])
    
    @patch('src.server.OpencodeSessionManager')
    def test_assign_task_auto_hire(self, mock_session_manager):
        """Test task assignment with auto-hiring"""
        # Mock session manager
        mock_instance = mock_session_manager.return_value
        mock_instance.start_employee_task.return_value = "session_123"
        
        # Assign task to non-existent employee (should auto-hire)
        response = self.client.post('/tasks', json={
            'name': 'jane',
            'task': 'create API',
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('Started task for jane', data['message'])
        
        # Verify employee was auto-hired
        response = self.client.get('/employees')
        data = json.loads(response.data)
        self.assertEqual(len(data['employees']), 1)
        self.assertEqual(data['employees'][0]['name'], 'jane')
        self.assertEqual(data['employees'][0]['role'], 'developer')
    
    @patch('src.server.OpencodeSessionManager')
    def test_assign_task_auto_hire_failure(self, mock_session_manager):
        """Test task assignment when auto-hire fails"""
        # Mock file manager to fail hiring
        with patch.object(self.server.file_manager, 'hire_employee', return_value=False):
            # Assign task to non-existent employee
            response = self.client.post('/tasks', json={
                'name': 'jane',
                'task': 'create API',
            })
            
            self.assertEqual(response.status_code, 400)
            data = json.loads(response.data)
            self.assertIn('Failed to hire jane', data['error'])
    
    def test_stop_task(self):
        """Test stopping a task"""
        with patch.object(self.server.session_manager, 'stop_employee_task') as mock_stop:
            response = self.client.delete('/tasks/john')
            
            # Verify stop_employee_task was called
            mock_stop.assert_called_once_with('john')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertIn('Stopped task for john', data['message'])
    
    # System status endpoint tests
    def test_get_status(self):
        """Test getting system status"""
        response = self.client.get('/status')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('active_sessions', data)
        self.assertIn('locked_files', data)
        self.assertIn('pending_requests', data)
        self.assertIn('employees', data)
        self.assertIn('chat_enabled', data)
        self.assertIn('chat_statistics', data)
    
    def test_get_sessions(self):
        """Test getting active sessions"""
        with patch.object(self.server.session_manager, 'get_active_sessions', return_value={'john': 'session_123'}):
            response = self.client.get('/sessions')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertIn('sessions', data)
            self.assertEqual(data['sessions'], {'john': 'session_123'})
    
    # File management endpoint tests
    def test_get_files(self):
        """Test getting locked files"""
        with patch.object(self.server.file_manager, 'get_all_locked_files', return_value=[{'file': 'test.py'}]):
            response = self.client.get('/files')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertIn('files', data)
            self.assertEqual(data['files'], [{'file': 'test.py'}])
    
    def test_lock_files_success(self):
        """Test successful file locking"""
        # Hire employee first
        self.client.post('/employees', json={'name': 'john', 'role': 'developer'})
        
        with patch.object(self.server.file_manager, 'lock_files', return_value=True):
            with patch.object(self.server.task_tracker, 'create_task_file') as mock_create:
                response = self.client.post('/files/lock', json={
                    'name': 'john',
                    'files': ['src/main.py', 'src/utils.py'],
                    'description': 'Working on main functionality'
                })
                
                # Verify task file was created
                mock_create.assert_called_once_with('john', 'Working on main functionality', ['src/main.py', 'src/utils.py'])
                
                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertTrue(data['result'])
    
    def test_lock_files_missing_data(self):
        """Test file locking with missing data"""
        response = self.client.post('/files/lock', json={'name': 'john'})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('Name and files are required', data['error'])
    
    def test_release_files(self):
        """Test file release"""
        with patch.object(self.server.file_manager, 'release_files', return_value=['src/main.py']):
            response = self.client.post('/files/release', json={'name': 'john'})
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertIn('released', data)
            self.assertEqual(data['released'], ['src/main.py'])
    
    def test_release_files_missing_name(self):
        """Test file release with missing name"""
        response = self.client.post('/files/release', json={})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('Name is required', data['error'])
    
    def test_release_files_specific_files(self):
        """Test releasing specific files"""
        with patch.object(self.server.file_manager, 'release_files', return_value=['src/main.py']):
            response = self.client.post('/files/release', json={
                'name': 'john',
                'files': ['src/main.py']
            })
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertIn('released', data)
            self.assertEqual(data['released'], ['src/main.py'])
    
    # Progress tracking endpoint tests
    def test_get_progress_all(self):
        """Test getting progress for all employees"""
        # Hire some employees
        self.client.post('/employees', json={'name': 'john', 'role': 'developer'})
        self.client.post('/employees', json={'name': 'jane', 'role': 'tester'})
        
        with patch.object(self.server.task_tracker, 'get_task_progress', side_effect=[0.5, 0.8]):
            response = self.client.get('/progress')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertIn('progress', data)
            self.assertIsInstance(data['progress'], dict)
            self.assertIn('john', data['progress'])
            self.assertIn('jane', data['progress'])
    
    def test_get_progress_specific(self):
        """Test getting progress for specific employee"""
        with patch.object(self.server.task_tracker, 'get_task_progress', return_value=0.75):
            response = self.client.get('/progress?name=john')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertIn('progress', data)
            self.assertEqual(data['progress'], 0.75)
    
    # Chat integration endpoint tests
    @patch('src.chat.chat_config.config')
    def test_start_chat_not_configured(self, mock_config):
        """Test starting chat when not configured"""
        mock_config.is_configured.return_value = False
        
        response = self.client.post('/chat/start')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('Chat system not configured', data['error'])
    
    @patch('src.chat.chat_config.config')
    def test_start_chat_success(self, mock_config):
        """Test successful chat start"""
        mock_config.is_configured.return_value = True
        
        with patch.object(self.server.telegram_manager, 'start_polling') as mock_start_polling:
            with patch.object(self.server.agent_bridge, 'start_monitoring') as mock_start_monitoring:
                response = self.client.post('/chat/start')
                
                # Verify methods were called
                mock_start_polling.assert_called_once()
                mock_start_monitoring.assert_called_once()
                
                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertIn('Chat system started successfully', data['message'])
                self.assertTrue(self.server.chat_enabled)
    
    @patch('src.chat.chat_config.config')
    def test_start_chat_already_running(self, mock_config):
        """Test starting chat when already running"""
        mock_config.is_configured.return_value = True
        self.server.chat_enabled = True
        
        response = self.client.post('/chat/start')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('Chat system is already running', data['message'])
    
    @patch('src.chat.chat_config.config')
    def test_start_chat_failure(self, mock_config):
        """Test chat start failure"""
        mock_config.is_configured.return_value = True
        
        with patch.object(self.server.telegram_manager, 'start_polling', side_effect=Exception("Test error")):
            response = self.client.post('/chat/start')
            
            self.assertEqual(response.status_code, 500)
            data = json.loads(response.data)
            self.assertIn('Failed to start chat system', data['error'])
    
    def test_stop_chat_not_running(self):
        """Test stopping chat when not running"""
        response = self.client.post('/chat/stop')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('Chat system is not running', data['error'])
    
    def test_stop_chat_success(self):
        """Test successful chat stop"""
        self.server.chat_enabled = True
        
        with patch.object(self.server.telegram_manager, 'stop_polling') as mock_stop_polling:
            response = self.client.post('/chat/stop')
            
            # Verify method was called
            mock_stop_polling.assert_called_once()
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertIn('Chat system stopped', data['message'])
            self.assertFalse(self.server.chat_enabled)
    
    def test_get_chat_status(self):
        """Test getting chat status"""
        with patch('src.chat.chat_config.config') as mock_config:
            mock_config.is_configured.return_value = True
            with patch.object(self.server.telegram_manager, 'is_connected', return_value=True):
                with patch.object(self.server.agent_manager, 'get_chat_statistics', return_value={'messages': 5}):
                    response = self.client.get('/chat/status')
                    
                    self.assertEqual(response.status_code, 200)
                    data = json.loads(response.data)
                    self.assertTrue(data['configured'])
                    self.assertTrue(data['connected'])
                    self.assertFalse(data['polling'])  # Not running in test
                    self.assertIn('statistics', data)
    
    def test_get_chat_debug(self):
        """Test getting chat debug information"""
        with patch('src.chat.chat_config.config') as mock_config:
            mock_config.is_configured.return_value = True
            with patch.object(self.server.telegram_manager, 'is_connected', return_value=True):
                with patch.object(self.server.agent_manager, 'get_chat_statistics', return_value={'messages': 5}):
                    with patch.object(self.server.telegram_manager, 'get_webhook_info', return_value={'url': 'test'}):
                        response = self.client.get('/chat/debug')
                        
                        self.assertEqual(response.status_code, 200)
                        data = json.loads(response.data)
                        self.assertTrue(data['configured'])
                        self.assertTrue(data['connected'])
                        self.assertFalse(data['polling'])
                        self.assertIn('statistics', data)
                        self.assertIn('webhook_info', data)
    
    def test_send_chat_message_missing_message(self):
        """Test sending chat message without message"""
        response = self.client.post('/chat/send', json={})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('Message is required', data['error'])
    
    def test_send_chat_message_not_connected(self):
        """Test sending chat message when not connected"""
        with patch.object(self.server.telegram_manager, 'is_connected', return_value=False):
            response = self.client.post('/chat/send', json={'message': 'test'})
            
            self.assertEqual(response.status_code, 400)
            data = json.loads(response.data)
            self.assertIn('Chat system not connected', data['error'])
    
    def test_send_chat_message_success(self):
        """Test successful chat message sending"""
        with patch.object(self.server.telegram_manager, 'is_connected', return_value=True):
            with patch.object(self.server.telegram_manager, 'send_message', return_value=True):
                response = self.client.post('/chat/send', json={'message': 'test message'})
                
                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertIn('Message sent successfully', data['message'])
    
    def test_send_chat_message_failure(self):
        """Test chat message sending failure"""
        with patch.object(self.server.telegram_manager, 'is_connected', return_value=True):
            with patch.object(self.server.telegram_manager, 'send_message', return_value=False):
                response = self.client.post('/chat/send', json={'message': 'test message'})
                
                self.assertEqual(response.status_code, 500)
                data = json.loads(response.data)
                self.assertIn('Failed to send message', data['error'])
    
    # Agent management endpoint tests
    def test_get_agents(self):
        """Test getting agents status"""
        with patch.object(self.server.agent_manager, 'get_agent_status', return_value={'agent1': 'active'}):
            response = self.client.get('/agents')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertIn('agents', data)
            self.assertEqual(data['agents'], {'agent1': 'active'})
    
    def test_get_bridge_status(self):
        """Test getting bridge status"""
        with patch.object(self.server.agent_bridge, 'get_bridge_status', return_value={'status': 'running'}):
            response = self.client.get('/bridge')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertIn('bridge', data)
            self.assertEqual(data['bridge'], {'status': 'running'})
    
    # Project root endpoint tests
    def test_get_project_root(self):
        """Test getting project root"""
        with patch.object(self.server.file_manager, 'get_project_root', return_value='/test/project'):
            response = self.client.get('/project-root')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertIn('project_root', data)
            self.assertEqual(data['project_root'], '/test/project')
    
    def test_set_project_root_success(self):
        """Test setting project root successfully"""
        with patch.object(self.server.file_manager, 'set_project_root', return_value=True):
            response = self.client.post('/project-root', json={'project_root': '/new/project'})
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertIn('Project root set to /new/project', data['message'])
    
    def test_set_project_root_missing_data(self):
        """Test setting project root with missing data"""
        response = self.client.post('/project-root', json={})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('project_root is required', data['error'])
    
    def test_set_project_root_failure(self):
        """Test setting project root failure"""
        with patch.object(self.server.file_manager, 'set_project_root', return_value=False):
            response = self.client.post('/project-root', json={'project_root': '/new/project'})
            
            self.assertEqual(response.status_code, 500)
            data = json.loads(response.data)
            self.assertIn('Failed to set project root', data['error'])
    
    # Monitoring endpoint tests
    def test_get_monitoring_health_not_available(self):
        """Test getting monitoring health when not available"""
        self.server.health_monitor = None
        
        response = self.client.get('/monitoring/health')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('Monitoring system not available', data['error'])
    
    def test_get_monitoring_health_success(self):
        """Test getting monitoring health successfully"""
        # Mock health monitor
        mock_health_monitor = MagicMock()
        mock_health_monitor.get_agent_health_summary.return_value = {'status': 'healthy'}
        self.server.health_monitor = mock_health_monitor
        
        response = self.client.get('/monitoring/health')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('health', data)
        self.assertEqual(data['health'], {'status': 'healthy'})
    
    def test_get_monitoring_recovery_not_available(self):
        """Test getting monitoring recovery when not available"""
        self.server.recovery_manager = None
        
        response = self.client.get('/monitoring/recovery')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('Recovery system not available', data['error'])
    
    def test_get_monitoring_recovery_success(self):
        """Test getting monitoring recovery successfully"""
        # Mock recovery manager
        mock_recovery_manager = MagicMock()
        mock_recovery_manager.get_recovery_summary.return_value = {'status': 'stable'}
        self.server.recovery_manager = mock_recovery_manager
        
        response = self.client.get('/monitoring/recovery')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('recovery', data)
        self.assertEqual(data['recovery'], {'status': 'stable'})
    
    def test_get_agent_monitoring_details_not_available(self):
        """Test getting agent monitoring details when not available"""
        self.server.health_monitor = None
        self.server.recovery_manager = None
        
        response = self.client.get('/monitoring/agents/test_agent')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('Monitoring system not available', data['error'])
    
    def test_get_agent_monitoring_details_success(self):
        """Test getting agent monitoring details successfully"""
        # Mock health monitor and recovery manager
        mock_health_monitor = MagicMock()
        mock_health_monitor.get_agent_health_summary.return_value = {
            'agent_details': {
                'test_agent': {'status': 'healthy', 'last_check': '2023-01-01'}
            }
        }
        self.server.health_monitor = mock_health_monitor
        
        mock_recovery_manager = MagicMock()
        mock_recovery_manager.get_recovery_history.return_value = {
            'test_agent': [{'timestamp': '2023-01-01', 'action': 'recovered'}]
        }
        self.server.recovery_manager = mock_recovery_manager
        
        response = self.client.get('/monitoring/agents/test_agent')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['agent'], 'test_agent')
        self.assertIn('health', data)
        self.assertIn('recovery_history', data)
        self.assertEqual(data['health'], {'status': 'healthy', 'last_check': '2023-01-01'})
        self.assertEqual(data['recovery_history'], [{'timestamp': '2023-01-01', 'action': 'recovered'}])
    
    # Server initialization tests
    def test_server_initialization(self):
        """Test server initialization"""
        self.assertIsNotNone(self.server.host)
        self.assertIsNotNone(self.server.port)
        self.assertIsNotNone(self.server.db_path)
        self.assertIsNotNone(self.server.sessions_dir)
        self.assertIsNotNone(self.server.app)
        self.assertFalse(self.server.running)
        self.assertFalse(self.server.chat_enabled)
    
    @patch('src.server.MONITORING_AVAILABLE', True)
    def test_monitoring_system_setup_success(self):
        """Test successful monitoring system setup"""
        # Create a new server instance with monitoring available
        with patch.object(OpencodeSlackServer, '_load_environment'):
            with patch('src.server.AgentHealthMonitor') as mock_health_monitor_class:
                with patch('src.server.AgentRecoveryManager') as mock_recovery_manager_class:
                    with patch('src.server.MonitoringDashboard') as mock_dashboard_class:
                        # Mock the monitoring classes
                        mock_health_monitor = MagicMock()
                        mock_health_monitor_class.return_value = mock_health_monitor
                        
                        mock_recovery_manager = MagicMock()
                        mock_recovery_manager_class.return_value = mock_recovery_manager
                        
                        mock_dashboard = MagicMock()
                        mock_dashboard_class.return_value = mock_dashboard
                        
                        # Create server with monitoring
                        server = OpencodeSlackServer(
                            host="localhost",
                            port=8083,
                            db_path=self.db_path,
                            sessions_dir=self.sessions_dir
                        )
                        
                        # Verify monitoring components were initialized
                        self.assertIsNotNone(server.health_monitor)
                        self.assertIsNotNone(server.recovery_manager)
                        self.assertIsNotNone(server.monitoring_dashboard)
                        
                        # Verify agent manager setup was called
                        server.agent_manager.setup_monitoring_system.assert_called_once_with(
                            server.task_tracker, server.session_manager
                        )
                        
                        # Verify health monitor start was called
                        mock_health_monitor.start_monitoring.assert_called_once()
    
    @patch('src.server.MONITORING_AVAILABLE', True)
    def test_monitoring_system_setup_failure(self):
        """Test monitoring system setup failure"""
        # Create a new server instance with monitoring that fails
        with patch.object(OpencodeSlackServer, '_load_environment'):
            with patch('src.server.AgentHealthMonitor', side_effect=Exception("Test error")):
                # Mock logging to prevent output during test
                with patch('src.server.logging'):
                    server = OpencodeSlackServer(
                        host="localhost",
                        port=8084,
                        db_path=self.db_path,
                        sessions_dir=self.sessions_dir
                    )
                    
                    # Monitoring should not be available due to exception
                    self.assertIsNone(server.health_monitor)
    
    def test_auto_start_chat_if_configured_safe_mode(self):
        """Test auto-start chat with safe mode enabled"""
        with patch.dict(os.environ, {'OPENCODE_SAFE_MODE': 'true'}):
            with patch('src.server.print') as mock_print:
                self.server._auto_start_chat_if_configured()
                
                # Verify safe mode messages were printed
                mock_print.assert_any_call("🔒 Safe mode enabled - Telegram chat disabled")
    
    def test_auto_start_chat_if_configured_not_configured(self):
        """Test auto-start chat when not configured"""
        with patch.dict(os.environ, {}, clear=True):  # Clear safe mode
            with patch('src.chat.chat_config.config') as mock_config:
                mock_config.is_configured.return_value = False
                with patch('src.server.print') as mock_print:
                    self.server._auto_start_chat_if_configured()
                    
                    # Verify not configured message was printed
                    mock_print.assert_called_with("💬 Chat system not configured (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)")
    
    @patch('src.chat.chat_config.config')
    def test_auto_start_chat_if_configured_success(self, mock_config):
        """Test successful auto-start chat"""
        mock_config.is_configured.return_value = True
        
        with patch.dict(os.environ, {}, clear=True):  # Clear safe mode
            with patch.object(self.server.telegram_manager, 'start_polling') as mock_start_polling:
                with patch.object(self.server.agent_bridge, 'start_monitoring') as mock_start_monitoring:
                    with patch('src.server.print') as mock_print:
                        self.server._auto_start_chat_if_configured()
                        
                        # Verify methods were called
                        mock_start_polling.assert_called_once()
                        mock_start_monitoring.assert_called_once()
                        
                        # Verify success message was printed
                        mock_print.assert_called_with("💬 Chat system auto-started!")
                        self.assertTrue(self.server.chat_enabled)
    
    @patch('src.chat.chat_config.config')
    def test_auto_start_chat_if_configured_failure(self, mock_config):
        """Test auto-start chat failure"""
        mock_config.is_configured.return_value = True
        
        with patch.dict(os.environ, {}, clear=True):  # Clear safe mode
            with patch.object(self.server.telegram_manager, 'start_polling', side_effect=Exception("Test error")):
                with patch('src.server.print') as mock_print:
                    self.server._auto_start_chat_if_configured()
                    
                    # Verify error messages were printed
                    mock_print.assert_any_call("⚠️  Failed to auto-start chat system: Test error")
                    self.assertFalse(self.server.chat_enabled)
    
    # Signal handling tests
    def test_signal_handler(self):
        """Test signal handler"""
        with patch('os._exit') as mock_exit:
            self.server._signal_handler(2, None)  # SIGINT
            
            # Verify exit was called
            mock_exit.assert_called_once_with(0)
    
    # Server stop tests
    def test_stop_server(self):
        """Test stopping server"""
        with patch('src.server.print') as mock_print:
            with patch('os._exit') as mock_exit:
                self.server.stop()
                
                # Verify messages were printed
                calls = [call("\n🛑 Shutting down server immediately..."), call("✅ Server shutdown complete")]
                mock_print.assert_has_calls(calls)
                
                # Verify exit was called
                mock_exit.assert_called_once_with(0)
                
                # Verify server state
                self.assertFalse(self.server.chat_enabled)
                self.assertFalse(self.server.running)


if __name__ == '__main__':
    unittest.main()