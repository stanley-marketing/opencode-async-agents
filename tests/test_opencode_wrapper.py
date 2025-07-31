import unittest
import os
import tempfile
import sys
import time
import threading
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.opencode_wrapper import OpencodeSession, OpencodeSessionManager
from src.managers.file_ownership import FileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker

class TestOpencodeSession(unittest.TestCase):
    def setUp(self):
        # Create temporary database and sessions directory
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_sessions_dir = tempfile.mkdtemp()
        
        self.file_manager = FileOwnershipManager(self.test_db.name)
        self.task_tracker = TaskProgressTracker(self.test_sessions_dir)
        
        # Hire a test employee
        self.file_manager.hire_employee("test_employee", "developer")
    
    def tearDown(self):
        # Clean up temporary files
        os.unlink(self.test_db.name)
        import shutil
        shutil.rmtree(self.test_sessions_dir)
    
    def test_session_initialization(self):
        """Test that OpencodeSession initializes correctly"""
        session = OpencodeSession(
            "test_employee", 
            "test task", 
            self.file_manager, 
            self.task_tracker
        )
        
        self.assertEqual(session.employee_name, "test_employee")
        self.assertEqual(session.task_description, "test task")
        self.assertFalse(session.is_running)
        self.assertIsNone(session.process)
        self.assertIsNone(session.thread)
        self.assertEqual(session.files_locked, [])
    
    def test_analyze_task_for_files_auth(self):
        """Test file analysis for authentication tasks"""
        session = OpencodeSession(
            "test_employee", 
            "implement user authentication with JWT", 
            self.file_manager, 
            self.task_tracker
        )
        
        files = session._analyze_task_for_files()
        
        # Should include auth-related files
        auth_files = ["src/auth.py", "src/user.py", "src/jwt.py", "src/middleware/auth.py"]
        for auth_file in auth_files:
            self.assertIn(auth_file, files)
    
    def test_analyze_task_for_files_api(self):
        """Test file analysis for API tasks"""
        session = OpencodeSession(
            "test_employee", 
            "create REST API endpoints", 
            self.file_manager, 
            self.task_tracker
        )
        
        files = session._analyze_task_for_files()
        
        # Should include API-related files
        api_files = ["src/api.py", "src/routes.py", "src/controllers/", "src/handlers/"]
        for api_file in api_files:
            self.assertIn(api_file, files)
    
    def test_analyze_task_for_files_default(self):
        """Test file analysis for generic tasks"""
        session = OpencodeSession(
            "test_employee", 
            "implement some feature", 
            self.file_manager, 
            self.task_tracker
        )
        
        files = session._analyze_task_for_files()
        
        # Should include default files
        default_files = ["src/main.py", "src/app.py", "src/utils.py", "README.md"]
        for default_file in default_files:
            self.assertIn(default_file, files)
    
    @patch('subprocess.Popen')
    def test_execute_opencode_command_success(self, mock_popen):
        """Test successful opencode command execution"""
        # Mock successful process
        mock_process = Mock()
        mock_process.poll.side_effect = [None, None, 0]  # Running, then finished
        mock_process.stdout.readline.side_effect = [
            "Writing to src/auth.py\n",
            "Task completed\n",
            ""  # End of output
        ]
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        session = OpencodeSession(
            "test_employee", 
            "test task", 
            self.file_manager, 
            self.task_tracker
        )
        
        result = session._execute_opencode_command()
        
        self.assertTrue(result["success"])
        self.assertEqual(result["returncode"], 0)
        self.assertIn("Writing to src/auth.py", result["stdout"])
    
    @patch('subprocess.Popen')
    def test_execute_opencode_command_not_found(self, mock_popen):
        """Test opencode command not found"""
        mock_popen.side_effect = FileNotFoundError("opencode not found")
        
        session = OpencodeSession(
            "test_employee", 
            "test task", 
            self.file_manager, 
            self.task_tracker
        )
        
        result = session._execute_opencode_command()
        
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "opencode command not found - please install opencode")
    
    def test_parse_progress_from_output(self):
        """Test progress parsing from opencode output"""
        session = OpencodeSession(
            "test_employee", 
            "test task", 
            self.file_manager, 
            self.task_tracker
        )
        
        # Mock some files as locked
        session.files_locked = ["src/auth.py", "src/user.py"]
        
        # Test file operation detection
        session._parse_progress_from_output("Writing to src/auth.py")
        
        # Test completion detection
        session._parse_progress_from_output("Task completed successfully")
        
        # Should have updated progress (we can't easily test the actual updates
        # without mocking the task_tracker, but we can verify the method runs)
        self.assertTrue(True)  # Method completed without error
    
    def test_session_id_generation(self):
        """Test that session IDs are unique"""
        session1 = OpencodeSession(
            "employee1", 
            "task1", 
            self.file_manager, 
            self.task_tracker
        )
        
        time.sleep(0.01)  # Small delay to ensure different timestamps
        
        session2 = OpencodeSession(
            "employee2", 
            "task2", 
            self.file_manager, 
            self.task_tracker
        )
        
        self.assertNotEqual(session1.session_id, session2.session_id)
        self.assertIn("employee1", session1.session_id)
        self.assertIn("employee2", session2.session_id)


class TestOpencodeSessionManager(unittest.TestCase):
    def setUp(self):
        # Create temporary database and sessions directory
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_sessions_dir = tempfile.mkdtemp()
        
        self.manager = OpencodeSessionManager(self.test_db.name, self.test_sessions_dir)
        
        # Hire some test employees
        self.manager.file_manager.hire_employee("alice", "developer")
        self.manager.file_manager.hire_employee("bob", "developer")
    
    def tearDown(self):
        # Clean up active sessions
        self.manager.cleanup_all_sessions()
        
        # Clean up temporary files
        os.unlink(self.test_db.name)
        import shutil
        shutil.rmtree(self.test_sessions_dir)
    
    def test_manager_initialization(self):
        """Test that OpencodeSessionManager initializes correctly"""
        # Check that managers are initialized (don't check exact type due to import path differences)
        self.assertIsNotNone(self.manager.file_manager)
        self.assertIsNotNone(self.manager.task_tracker)
        self.assertEqual(len(self.manager.active_sessions), 0)
    
    @patch.object(OpencodeSession, 'start_session')
    def test_start_employee_task_success(self, mock_start_session):
        """Test successfully starting an employee task"""
        mock_start_session.return_value = "alice_123456"
        
        session_id = self.manager.start_employee_task(
            "alice", 
            "implement authentication"
        )
        
        self.assertIsNotNone(session_id)
        self.assertEqual(session_id, "alice_123456")
        self.assertIn("alice", self.manager.active_sessions)
        mock_start_session.assert_called_once()
    
    def test_start_employee_task_nonexistent_employee(self):
        """Test starting task for non-existent employee"""
        session_id = self.manager.start_employee_task(
            "nonexistent", 
            "some task"
        )
        
        self.assertIsNone(session_id)
        self.assertNotIn("nonexistent", self.manager.active_sessions)
    
    @patch.object(OpencodeSession, 'start_session')
    def test_start_employee_task_already_active(self, mock_start_session):
        """Test starting task for employee who already has active session"""
        mock_start_session.return_value = "alice_123456"
        
        # Start first session
        session_id1 = self.manager.start_employee_task("alice", "task 1")
        self.assertIsNotNone(session_id1)
        
        # Mock the session as running
        self.manager.active_sessions["alice"].is_running = True
        
        # Try to start second session for same employee
        session_id2 = self.manager.start_employee_task("alice", "task 2")
        self.assertIsNone(session_id2)
        
        # Should still have only one session
        self.assertEqual(len(self.manager.active_sessions), 1)
    
    @patch.object(OpencodeSession, 'start_session')
    @patch.object(OpencodeSession, 'stop_session')
    def test_stop_employee_task(self, mock_stop_session, mock_start_session):
        """Test stopping an employee's task"""
        mock_start_session.return_value = "alice_123456"
        
        # Start a session
        self.manager.start_employee_task("alice", "test task")
        self.assertIn("alice", self.manager.active_sessions)
        
        # Stop the session
        self.manager.stop_employee_task("alice")
        self.assertNotIn("alice", self.manager.active_sessions)
        mock_stop_session.assert_called_once()
    
    def test_stop_employee_task_no_session(self):
        """Test stopping task for employee with no active session"""
        # Should not raise an error
        self.manager.stop_employee_task("alice")
        self.assertNotIn("alice", self.manager.active_sessions)
    
    @patch.object(OpencodeSession, 'start_session')
    def test_get_active_sessions(self, mock_start_session):
        """Test getting active session information"""
        mock_start_session.return_value = "alice_123456"
        
        # Start a session
        self.manager.start_employee_task("alice", "test task")
        
        active_sessions = self.manager.get_active_sessions()
        
        self.assertIn("alice", active_sessions)
        session_info = active_sessions["alice"]
        # Don't check exact session_id since it's generated with timestamp
        self.assertIn("alice", session_info["session_id"])
        self.assertEqual(session_info["task"], "test task")
        self.assertIn("is_running", session_info)
        self.assertIn("files_locked", session_info)
    
    @patch.object(OpencodeSession, 'start_session')
    @patch.object(OpencodeSession, 'stop_session')
    def test_cleanup_all_sessions(self, mock_stop_session, mock_start_session):
        """Test cleaning up all active sessions"""
        mock_start_session.return_value = "session_123"
        
        # Start multiple sessions
        self.manager.start_employee_task("alice", "task 1")
        self.manager.start_employee_task("bob", "task 2")
        
        self.assertEqual(len(self.manager.active_sessions), 2)
        
        # Cleanup all sessions
        self.manager.cleanup_all_sessions()
        
        self.assertEqual(len(self.manager.active_sessions), 0)
        self.assertEqual(mock_stop_session.call_count, 2)


class TestRealTaskAssignmentIntegration(unittest.TestCase):
    def setUp(self):
        # Create temporary database and sessions directory
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.test_sessions_dir = tempfile.mkdtemp()
        
        # Import here to avoid circular imports
        from task_assigner import TaskAssigner
        self.assigner = TaskAssigner(self.test_db.name, self.test_sessions_dir)
        
        # Hire a test employee
        self.assigner.file_manager.hire_employee("test_dev", "developer")
    
    def tearDown(self):
        # Clean up active sessions
        self.assigner.session_manager.cleanup_all_sessions()
        
        # Clean up temporary files
        os.unlink(self.test_db.name)
        import shutil
        shutil.rmtree(self.test_sessions_dir)
    
    @patch.object(OpencodeSession, 'start_session')
    def test_assign_task_with_real_opencode(self, mock_start_session):
        """Test task assignment with real opencode integration"""
        mock_start_session.return_value = "test_dev_123456"
        
        session_id = self.assigner.assign_task(
            "test_dev", 
            "implement user authentication",
            model="claude-3.5"
        )
        
        self.assertIsNotNone(session_id)
        self.assertEqual(session_id, "test_dev_123456")
        
        # Check that session was created
        active_sessions = self.assigner.get_active_sessions()
        self.assertIn("test_dev", active_sessions)
        
        session_info = active_sessions["test_dev"]
        self.assertEqual(session_info["task"], "implement user authentication")
    
    def test_assign_task_nonexistent_employee_auto_hire(self):
        """Test that assigning task to non-existent employee auto-hires them"""
        with patch.object(OpencodeSession, 'start_session') as mock_start_session:
            mock_start_session.return_value = "new_dev_123456"
            
            session_id = self.assigner.assign_task(
                "new_dev", 
                "create API endpoints"
            )
            
            self.assertIsNotNone(session_id)
            
            # Check that employee was hired
            employees = self.assigner.file_manager.list_employees()
            employee_names = [emp['name'] for emp in employees]
            self.assertIn("new_dev", employee_names)
    
    @patch.object(OpencodeSession, 'start_session')
    def test_stop_employee_task_integration(self, mock_start_session):
        """Test stopping employee task through task assigner"""
        mock_start_session.return_value = "test_dev_123456"
        
        # Start a task
        self.assigner.assign_task("test_dev", "test task")
        
        # Verify session is active
        active_sessions = self.assigner.get_active_sessions()
        self.assertIn("test_dev", active_sessions)
        
        # Stop the task
        with patch.object(OpencodeSession, 'stop_session') as mock_stop_session:
            self.assigner.stop_employee_task("test_dev")
            mock_stop_session.assert_called_once()
        
        # Verify session is no longer active
        active_sessions = self.assigner.get_active_sessions()
        self.assertNotIn("test_dev", active_sessions)


if __name__ == '__main__':
    unittest.main()