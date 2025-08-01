"""
Tests for the OpenCode-Slack server.
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import tempfile
import os
from pathlib import Path

# Import the server module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.server import OpencodeSlackServer


class TestOpencodeSlackServer(unittest.TestCase):
    """Test cases for OpencodeSlackServer"""
    
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
                port=8081,  # Use different port for testing
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
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get('/health')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('chat_enabled', data)
        self.assertIn('active_sessions', data)
        self.assertIn('total_agents', data)
    
    def test_list_employees_empty(self):
        """Test listing employees when none exist"""
        response = self.client.get('/employees')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['employees'], [])
    
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
        self.assertEqual(data['session_id'], 'session_123')
    
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
    
    def test_stop_task(self):
        """Test stopping a task"""
        response = self.client.delete('/tasks/john')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('Stopped task for john', data['message'])
    
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
    
    def test_get_sessions(self):
        """Test getting active sessions"""
        response = self.client.get('/sessions')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('sessions', data)
        self.assertIsInstance(data['sessions'], dict)
    
    def test_get_files(self):
        """Test getting locked files"""
        response = self.client.get('/files')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('files', data)
        self.assertIsInstance(data['files'], list)
    
    def test_lock_files_success(self):
        """Test successful file locking"""
        # Hire employee first
        self.client.post('/employees', json={'name': 'john', 'role': 'developer'})
        
        response = self.client.post('/files/lock', json={
            'name': 'john',
            'files': ['src/main.py', 'src/utils.py'],
            'description': 'Working on main functionality'
        })
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('result', data)
    
    def test_lock_files_missing_data(self):
        """Test file locking with missing data"""
        response = self.client.post('/files/lock', json={'name': 'john'})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('Name and files are required', data['error'])
    
    def test_release_files(self):
        """Test file release"""
        response = self.client.post('/files/release', json={'name': 'john'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('released', data)
        self.assertIsInstance(data['released'], list)
    
    def test_release_files_missing_name(self):
        """Test file release with missing name"""
        response = self.client.post('/files/release', json={})
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('Name is required', data['error'])
    
    def test_get_progress_all(self):
        """Test getting progress for all employees"""
        response = self.client.get('/progress')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('progress', data)
        self.assertIsInstance(data['progress'], dict)
    
    def test_get_progress_specific(self):
        """Test getting progress for specific employee"""
        response = self.client.get('/progress?name=john')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('progress', data)
    
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
        
        with patch.object(self.server.telegram_manager, 'start_polling'):
            with patch.object(self.server.agent_bridge, 'start_monitoring'):
                response = self.client.post('/chat/start')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('Chat system started successfully', data['message'])
    
    def test_stop_chat_not_running(self):
        """Test stopping chat when not running"""
        response = self.client.post('/chat/stop')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('Chat system is not running', data['error'])
    
    def test_get_chat_status(self):
        """Test getting chat status"""
        response = self.client.get('/chat/status')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('configured', data)
        self.assertIn('connected', data)
        self.assertIn('polling', data)
        self.assertIn('statistics', data)
    
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
    
    def test_get_agents(self):
        """Test getting agents status"""
        response = self.client.get('/agents')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('agents', data)
        self.assertIsInstance(data['agents'], dict)
    
    def test_get_bridge_status(self):
        """Test getting bridge status"""
        response = self.client.get('/bridge')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('bridge', data)
        self.assertIsInstance(data['bridge'], dict)


if __name__ == '__main__':
    unittest.main()