"""
Tests for the OpenCode-Slack CLI client.
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import requests
from pathlib import Path

# Import the client module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.client import OpencodeSlackClient


class TestOpencodeSlackClient(unittest.TestCase):
    """Test cases for OpencodeSlackClient"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock the connection test to avoid actual network calls
        with patch.object(OpencodeSlackClient, '_test_connection', return_value=True):
            with patch('builtins.print'):  # Suppress print statements during testing
                self.client = OpencodeSlackClient("http://test-server:8080")
    
    def test_initialization(self):
        """Test client initialization"""
        self.assertEqual(self.client.server_url, "http://test-server:8080")
        self.assertTrue(self.client.running)
    
    def test_initialization_connection_failure(self):
        """Test client initialization with connection failure"""
        with patch.object(OpencodeSlackClient, '_test_connection', return_value=False):
            with patch('sys.exit') as mock_exit:
                with patch('builtins.print'):
                    OpencodeSlackClient("http://nonexistent:8080")
                mock_exit.assert_called_once_with(1)
    
    def test_test_connection_success(self):
        """Test successful connection test"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            result = self.client._test_connection()
            self.assertTrue(result)
    
    def test_test_connection_failure(self):
        """Test failed connection test"""
        with patch('requests.get', side_effect=requests.exceptions.RequestException):
            result = self.client._test_connection()
            self.assertFalse(result)
    
    def test_make_request_get(self):
        """Test making GET request"""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            response = self.client._make_request('GET', '/test')
            
            self.assertEqual(response, mock_response)
            mock_get.assert_called_once()
    
    def test_make_request_post(self):
        """Test making POST request"""
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response
            
            response = self.client._make_request('POST', '/test', {'data': 'value'})
            
            self.assertEqual(response, mock_response)
            mock_post.assert_called_once()
    
    def test_make_request_delete(self):
        """Test making DELETE request"""
        with patch('requests.delete') as mock_delete:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_delete.return_value = mock_response
            
            response = self.client._make_request('DELETE', '/test')
            
            self.assertEqual(response, mock_response)
            mock_delete.assert_called_once()
    
    def test_make_request_exception(self):
        """Test request with exception"""
        with patch('requests.get', side_effect=requests.exceptions.RequestException):
            with patch('builtins.print'):
                response = self.client._make_request('GET', '/test')
            
            self.assertIsNone(response)
    
    def test_handle_hire_success(self):
        """Test successful hire command"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'message': 'Successfully hired john as developer'}
        
        with patch.object(self.client, '_make_request', return_value=mock_response):
            with patch('builtins.print') as mock_print:
                self.client.handle_hire(['john', 'developer'])
            
            mock_print.assert_called_with('✅ Successfully hired john as developer')
    
    def test_handle_hire_missing_args(self):
        """Test hire command with missing arguments"""
        with patch('builtins.print') as mock_print:
            self.client.handle_hire(['john'])
        
        mock_print.assert_called_with('Usage: hire <name> <role>')
    
    def test_handle_hire_error(self):
        """Test hire command with server error"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {'error': 'Employee already exists'}
        
        with patch.object(self.client, '_make_request', return_value=mock_response):
            with patch('builtins.print') as mock_print:
                self.client.handle_hire(['john', 'developer'])
            
            mock_print.assert_called_with('❌ Employee already exists')
    
    def test_handle_fire_success(self):
        """Test successful fire command"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'message': 'Successfully fired john'}
        
        with patch.object(self.client, '_make_request', return_value=mock_response):
            with patch('builtins.print') as mock_print:
                self.client.handle_fire(['john'])
            
            mock_print.assert_called_with('✅ Successfully fired john')
    
    def test_handle_fire_missing_args(self):
        """Test fire command with missing arguments"""
        with patch('builtins.print') as mock_print:
            self.client.handle_fire([])
        
        mock_print.assert_called_with('Usage: fire <name>')
    
    def test_handle_assign_success(self):
        """Test successful assign command"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'message': 'Started task for john',
            'session_id': 'session_123'
        }
        
        with patch.object(self.client, '_make_request', return_value=mock_response):
            with patch('builtins.print') as mock_print:
                self.client.handle_assign(['john', 'implement auth'])
            
            # Check that both messages were printed
            calls = mock_print.call_args_list
            self.assertTrue(any('🚀 Started task for john' in str(call) for call in calls))
            self.assertTrue(any('📋 Session ID: session_123' in str(call) for call in calls))
    
    def test_handle_assign_missing_args(self):
        """Test assign command with missing arguments"""
        with patch('builtins.print') as mock_print:
            self.client.handle_assign(['john'])
        
        # Check that usage information was printed
        calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any('Usage: assign <name> <task_description> [model] [mode]' in call for call in calls))
    
    def test_handle_stop_success(self):
        """Test successful stop command"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'message': 'Stopped task for john'}
        
        with patch.object(self.client, '_make_request', return_value=mock_response):
            with patch('builtins.print') as mock_print:
                self.client.handle_stop(['john'])
            
            mock_print.assert_called_with('✅ Stopped task for john')
    
    def test_handle_stop_missing_args(self):
        """Test stop command with missing arguments"""
        with patch('builtins.print') as mock_print:
            self.client.handle_stop([])
        
        mock_print.assert_called_with('Usage: stop <name>')
    
    def test_handle_status_success(self):
        """Test successful status command"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'active_sessions': {
                'john': {
                    'is_running': True,
                    'task': 'implement authentication system',
                    'files_locked': ['src/auth.py', 'src/user.py']
                }
            },
            'locked_files': [
                {
                    'file_path': 'src/auth.py',
                    'employee_name': 'john',
                    'task_description': 'implement auth'
                }
            ],
            'employees': [
                {'name': 'john', 'role': 'developer'}
            ],
            'chat_enabled': True,
            'chat_statistics': {
                'total_agents': 1,
                'working_agents': 1,
                'idle_agents': 0
            }
        }
        
        with patch.object(self.client, '_make_request', return_value=mock_response):
            with patch('builtins.print') as mock_print:
                self.client.handle_status([])
            
            # Check that status overview was printed
            calls = [str(call) for call in mock_print.call_args_list]
            self.assertTrue(any('📊 SYSTEM STATUS OVERVIEW' in call for call in calls))
            self.assertTrue(any('🔥 ACTIVE SESSIONS:' in call for call in calls))
            self.assertTrue(any('👤 john - 🔥 RUNNING' in call for call in calls))
    
    def test_handle_status_failure(self):
        """Test status command with server failure"""
        with patch.object(self.client, '_make_request', return_value=None):
            with patch('builtins.print') as mock_print:
                self.client.handle_status([])
            
            mock_print.assert_called_with('❌ Failed to get status')
    
    def test_handle_employees_success(self):
        """Test successful employees command"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'employees': [
                {'name': 'john', 'role': 'developer'},
                {'name': 'jane', 'role': 'designer'}
            ]
        }
        
        with patch.object(self.client, '_make_request', return_value=mock_response):
            with patch('builtins.print') as mock_print:
                self.client.handle_employees([])
            
            calls = [str(call) for call in mock_print.call_args_list]
            self.assertTrue(any('👥 EMPLOYEES:' in call for call in calls))
            self.assertTrue(any('👤 john (developer)' in call for call in calls))
            self.assertTrue(any('👤 jane (designer)' in call for call in calls))
    
    def test_handle_employees_empty(self):
        """Test employees command with no employees"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'employees': []}
        
        with patch.object(self.client, '_make_request', return_value=mock_response):
            with patch('builtins.print') as mock_print:
                self.client.handle_employees([])
            
            mock_print.assert_called_with('❌ No employees found')
    
    def test_handle_chat_success(self):
        """Test successful chat command"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'message': 'Message sent successfully'}
        
        with patch.object(self.client, '_make_request', return_value=mock_response):
            with patch('builtins.print') as mock_print:
                self.client.handle_chat(['hello', 'team'])
            
            mock_print.assert_called_with('✅ Message sent successfully')
    
    def test_handle_chat_missing_args(self):
        """Test chat command with missing arguments"""
        with patch('builtins.print') as mock_print:
            self.client.handle_chat([])
        
        mock_print.assert_called_with('Usage: chat <message>')
    
    def test_handle_chat_start_success(self):
        """Test successful chat-start command"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'message': 'Chat system started successfully'}
        
        with patch.object(self.client, '_make_request', return_value=mock_response):
            with patch('builtins.print') as mock_print:
                self.client.handle_chat_start([])
            
            mock_print.assert_called_with('🚀 Chat system started successfully')
    
    def test_handle_chat_stop_success(self):
        """Test successful chat-stop command"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'message': 'Chat system stopped'}
        
        with patch.object(self.client, '_make_request', return_value=mock_response):
            with patch('builtins.print') as mock_print:
                self.client.handle_chat_stop([])
            
            mock_print.assert_called_with('🛑 Chat system stopped')
    
    def test_handle_health_success(self):
        """Test successful health command"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'healthy',
            'chat_enabled': True,
            'active_sessions': 2,
            'total_agents': 3
        }
        
        with patch.object(self.client, '_make_request', return_value=mock_response):
            with patch('builtins.print') as mock_print:
                self.client.handle_health([])
            
            calls = [str(call) for call in mock_print.call_args_list]
            self.assertTrue(any('🏥 SERVER HEALTH' in call for call in calls))
            self.assertTrue(any('Status: ✅ healthy' in call for call in calls))
            self.assertTrue(any('Chat Enabled: ✅ Yes' in call for call in calls))
    
    def test_handle_health_failure(self):
        """Test health command with server failure"""
        with patch.object(self.client, '_make_request', return_value=None):
            with patch('builtins.print') as mock_print:
                self.client.handle_health([])
            
            mock_print.assert_called_with('❌ Server is not healthy')
    
    def test_handle_command_quit(self):
        """Test quit command"""
        with patch('builtins.print') as mock_print:
            self.client.handle_command('quit')
        
        self.assertFalse(self.client.running)
        mock_print.assert_called_with('Goodbye!')
    
    def test_handle_command_exit(self):
        """Test exit command"""
        with patch('builtins.print') as mock_print:
            self.client.handle_command('exit')
        
        self.assertFalse(self.client.running)
        mock_print.assert_called_with('Goodbye!')
    
    def test_handle_command_help(self):
        """Test help command"""
        with patch('builtins.print') as mock_print:
            self.client.handle_command('help')
        
        calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any('🔥 OPENCODE-SLACK CLIENT' in call for call in calls))
    
    def test_handle_command_unknown(self):
        """Test unknown command"""
        with patch('builtins.print') as mock_print:
            self.client.handle_command('unknown_command')
        
        calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any('Unknown command: unknown_command' in call for call in calls))
    
    def test_handle_command_parsing_error(self):
        """Test command with parsing error"""
        with patch('builtins.print') as mock_print:
            self.client.handle_command('command "unclosed quote')
        
        calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any('Error parsing command:' in call for call in calls))
    
    @patch('os.system')
    def test_handle_clear(self, mock_system):
        """Test clear command"""
        with patch('builtins.print'):
            self.client.handle_clear([])
        
        mock_system.assert_called_once()


if __name__ == '__main__':
    unittest.main()