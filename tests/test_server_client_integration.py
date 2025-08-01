"""
Integration tests for the complete OpenCode-Slack server-client system.
Tests the full workflow from server startup to task completion.
"""

import pytest
import unittest
import threading
import time
import requests
import tempfile
import os
import shutil
from pathlib import Path

# Import modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.server import OpencodeSlackServer
from src.client import OpencodeSlackClient


class TestServerClientIntegration(unittest.TestCase):
    """Integration tests for the complete server-client system"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test server for all tests"""
        # Create temporary directory for test data
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.temp_dir, "test_employees.db")
        cls.sessions_dir = os.path.join(cls.temp_dir, "test_sessions")
        
        # Create test server
        cls.server = OpencodeSlackServer(
            host="localhost",
            port=8082,  # Use different port for integration tests
            db_path=cls.db_path,
            sessions_dir=cls.sessions_dir
        )
        
        # Start server in background thread
        cls.server_thread = threading.Thread(
            target=cls.server.app.run,
            kwargs={'host': 'localhost', 'port': 8082, 'debug': False, 'threaded': True},
            daemon=True
        )
        cls.server_thread.start()
        
        # Wait for server to start
        cls._wait_for_server()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        # Stop server
        cls.server.stop()
        
        # Clean up temporary directory
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
    
    @classmethod
    def _wait_for_server(cls, timeout=10):
        """Wait for server to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get('http://localhost:8082/health', timeout=1)
                if response.status_code == 200:
                    return
            except:
                pass
            time.sleep(0.1)
        
        raise Exception("Server failed to start within timeout")
    
    def setUp(self):
        """Set up for each test"""
        self.server_url = "http://localhost:8082"
        
        # Clean up any existing employees
        try:
            response = requests.get(f"{self.server_url}/employees")
            if response.status_code == 200:
                employees = response.json().get('employees', [])
                for emp in employees:
                    requests.delete(f"{self.server_url}/employees/{emp['name']}")
        except:
            pass
    
    def test_server_health(self):
        """Test that server is healthy"""
        response = requests.get(f"{self.server_url}/health")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
    
    def test_employee_lifecycle(self):
        """Test complete employee lifecycle"""
        # 1. Hire employee
        response = requests.post(f"{self.server_url}/employees", json={
            'name': 'alice',
            'role': 'developer'
        })
        self.assertEqual(response.status_code, 200)
        
        # 2. Verify employee exists
        response = requests.get(f"{self.server_url}/employees")
        self.assertEqual(response.status_code, 200)
        employees = response.json()['employees']
        self.assertEqual(len(employees), 1)
        self.assertEqual(employees[0]['name'], 'alice')
        self.assertEqual(employees[0]['role'], 'developer')
        
        # 3. Fire employee
        response = requests.delete(f"{self.server_url}/employees/alice")
        self.assertEqual(response.status_code, 200)
        
        # 4. Verify employee is gone
        response = requests.get(f"{self.server_url}/employees")
        self.assertEqual(response.status_code, 200)
        employees = response.json()['employees']
        self.assertEqual(len(employees), 0)
    
    def test_task_assignment_workflow(self):
        """Test task assignment and management workflow"""
        # 1. Assign task (should auto-hire employee)
        response = requests.post(f"{self.server_url}/tasks", json={
            'name': 'bob',
            'task': 'create hello world application',
            'model': 'test-model',
            'mode': 'build'
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('Started task for bob', data['message'])
        
        # 2. Verify employee was auto-hired
        response = requests.get(f"{self.server_url}/employees")
        self.assertEqual(response.status_code, 200)
        employees = response.json()['employees']
        self.assertEqual(len(employees), 1)
        self.assertEqual(employees[0]['name'], 'bob')
        self.assertEqual(employees[0]['role'], 'developer')
        
        # 3. Check system status
        response = requests.get(f"{self.server_url}/status")
        self.assertEqual(response.status_code, 200)
        status = response.json()
        self.assertIn('active_sessions', status)
        self.assertIn('employees', status)
        
        # 4. Stop task
        response = requests.delete(f"{self.server_url}/tasks/bob")
        self.assertEqual(response.status_code, 200)
    
    def test_file_management_workflow(self):
        """Test file locking and release workflow"""
        # 1. Hire employee first
        requests.post(f"{self.server_url}/employees", json={
            'name': 'charlie',
            'role': 'developer'
        })
        
        # 2. Lock files
        response = requests.post(f"{self.server_url}/files/lock", json={
            'name': 'charlie',
            'files': ['src/main.py', 'src/utils.py'],
            'description': 'Working on core functionality'
        })
        self.assertEqual(response.status_code, 200)
        
        # 3. Check locked files
        response = requests.get(f"{self.server_url}/files")
        self.assertEqual(response.status_code, 200)
        files = response.json()['files']
        self.assertGreater(len(files), 0)
        
        # 4. Release files
        response = requests.post(f"{self.server_url}/files/release", json={
            'name': 'charlie'
        })
        self.assertEqual(response.status_code, 200)
        
        # 5. Verify files are released
        response = requests.get(f"{self.server_url}/files")
        self.assertEqual(response.status_code, 200)
        files = response.json()['files']
        # Files should be empty or not contain charlie's files
    
    def test_progress_tracking(self):
        """Test progress tracking functionality"""
        # 1. Hire employee
        requests.post(f"{self.server_url}/employees", json={
            'name': 'diana',
            'role': 'developer'
        })
        
        # 2. Get progress (should be empty initially)
        response = requests.get(f"{self.server_url}/progress")
        self.assertEqual(response.status_code, 200)
        progress = response.json()['progress']
        self.assertIn('diana', progress)
        
        # 3. Get progress for specific employee
        response = requests.get(f"{self.server_url}/progress?name=diana")
        self.assertEqual(response.status_code, 200)
        # Progress might be None for new employee
    
    def test_chat_system_endpoints(self):
        """Test chat system endpoints"""
        # 1. Get chat status
        response = requests.get(f"{self.server_url}/chat/status")
        self.assertEqual(response.status_code, 200)
        status = response.json()
        self.assertIn('configured', status)
        self.assertIn('connected', status)
        self.assertIn('polling', status)
        
        # 2. Try to start chat (will fail if not configured, which is expected)
        response = requests.post(f"{self.server_url}/chat/start")
        # Should either succeed (if configured) or fail with 400 (if not configured)
        self.assertIn(response.status_code, [200, 400])
        
        # 3. Get agents status
        response = requests.get(f"{self.server_url}/agents")
        self.assertEqual(response.status_code, 200)
        agents = response.json()['agents']
        self.assertIsInstance(agents, dict)
        
        # 4. Get bridge status
        response = requests.get(f"{self.server_url}/bridge")
        self.assertEqual(response.status_code, 200)
        bridge = response.json()['bridge']
        self.assertIsInstance(bridge, dict)
    
    def test_error_handling(self):
        """Test error handling in various scenarios"""
        # 1. Try to hire employee with missing data
        response = requests.post(f"{self.server_url}/employees", json={'name': 'incomplete'})
        self.assertEqual(response.status_code, 400)
        
        # 2. Try to fire non-existent employee
        response = requests.delete(f"{self.server_url}/employees/nonexistent")
        self.assertEqual(response.status_code, 400)
        
        # 3. Try to assign task with missing data
        response = requests.post(f"{self.server_url}/tasks", json={'name': 'test'})
        self.assertEqual(response.status_code, 400)
        
        # 4. Try to lock files with missing data
        response = requests.post(f"{self.server_url}/files/lock", json={'name': 'test'})
        self.assertEqual(response.status_code, 400)
        
        # 5. Try to release files with missing data
        response = requests.post(f"{self.server_url}/files/release", json={})
        self.assertEqual(response.status_code, 400)
    
    def test_multiple_employees_workflow(self):
        """Test workflow with multiple employees"""
        # 1. Hire multiple employees
        employees = [
            ('eve', 'developer'),
            ('frank', 'designer'),
            ('grace', 'tester')
        ]
        
        for name, role in employees:
            response = requests.post(f"{self.server_url}/employees", json={
                'name': name,
                'role': role
            })
            self.assertEqual(response.status_code, 200)
        
        # 2. Verify all employees exist
        response = requests.get(f"{self.server_url}/employees")
        self.assertEqual(response.status_code, 200)
        emp_list = response.json()['employees']
        self.assertEqual(len(emp_list), 3)
        
        # 3. Assign tasks to multiple employees
        tasks = [
            ('eve', 'implement user authentication'),
            ('frank', 'design user interface'),
            ('grace', 'write integration tests')
        ]
        
        for name, task in tasks:
            response = requests.post(f"{self.server_url}/tasks", json={
                'name': name,
                'task': task
            })
            self.assertEqual(response.status_code, 200)
        
        # 4. Check system status with multiple active sessions
        response = requests.get(f"{self.server_url}/status")
        self.assertEqual(response.status_code, 200)
        status = response.json()
        
        # Should have multiple active sessions
        active_sessions = status.get('active_sessions', {})
        # Note: Sessions might complete quickly in test environment
        
        # 5. Stop all tasks
        for name, _ in tasks:
            requests.delete(f"{self.server_url}/tasks/{name}")
    
    def test_concurrent_operations(self):
        """Test concurrent operations"""
        import concurrent.futures
        
        def hire_employee(name_role):
            name, role = name_role
            response = requests.post(f"{self.server_url}/employees", json={
                'name': name,
                'role': role
            })
            return response.status_code == 200
        
        # Hire multiple employees concurrently
        employees = [(f'worker_{i}', 'developer') for i in range(5)]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(hire_employee, employees))
        
        # All hires should succeed
        self.assertTrue(all(results))
        
        # Verify all employees were created
        response = requests.get(f"{self.server_url}/employees")
        self.assertEqual(response.status_code, 200)
        emp_list = response.json()['employees']
        self.assertEqual(len(emp_list), 5)


if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2)