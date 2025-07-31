import unittest
import os
import tempfile
import sys
from pathlib import Path
from unittest.mock import Mock

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.managers.file_ownership import FileOwnershipManager

class TestFileOwnershipManager(unittest.TestCase):
    def setUp(self):
        # Create a temporary database for testing
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.test_db.close()
        self.manager = FileOwnershipManager(self.test_db.name)
    
    def tearDown(self):
        # Clean up the temporary database
        os.unlink(self.test_db.name)
    
    def test_hire_employee(self):
        # Test that we can hire an employee
        result = self.manager.hire_employee("sarah", "developer")
        self.assertTrue(result)
        
        # Check that the employee exists
        employees = self.manager.list_employees()
        self.assertEqual(len(employees), 1)
        self.assertEqual(employees[0]['name'], "sarah")
        self.assertEqual(employees[0]['role'], "developer")
    
    def test_hire_duplicate_employee(self):
        # Test that we can't hire the same employee twice
        self.manager.hire_employee("sarah", "developer")
        result = self.manager.hire_employee("sarah", "developer")
        self.assertFalse(result)
    
    def test_fire_employee(self):
        # Test that we can fire an employee
        self.manager.hire_employee("sarah", "developer")
        result = self.manager.fire_employee("sarah")
        self.assertTrue(result)
        
        # Check that the employee no longer exists
        employees = self.manager.list_employees()
        self.assertEqual(len(employees), 0)
    
    def test_fire_nonexistent_employee(self):
        # Test that we can't fire an employee that doesn't exist
        result = self.manager.fire_employee("nonexistent")
        self.assertFalse(result)
    
    def test_lock_files(self):
        # Test that an employee can lock files
        self.manager.hire_employee("sarah", "developer")
        result = self.manager.lock_files("sarah", ["src/auth.py", "src/user.py"], "implement auth feature")
        
        # Check that files are locked
        self.assertEqual(result["src/auth.py"], "locked")
        self.assertEqual(result["src/user.py"], "locked")
        
        # Check that sarah owns the files
        self.assertEqual(self.manager.get_file_owner("src/auth.py"), "sarah")
        self.assertEqual(self.manager.get_file_owner("src/user.py"), "sarah")
    
    def test_lock_already_locked_file(self):
        # Test that we can't lock a file that's already locked
        self.manager.hire_employee("sarah", "developer")
        self.manager.hire_employee("dev-1", "developer")
        
        # Sarah locks a file
        self.manager.lock_files("sarah", ["src/auth.py"], "implement auth feature")
        
        # dev-1 tries to lock the same file
        result = self.manager.lock_files("dev-1", ["src/auth.py"], "fix auth bug")
        self.assertEqual(result["src/auth.py"], "locked_by_sarah")
    
    def test_release_files(self):
        # Test that an employee can release their files
        self.manager.hire_employee("sarah", "developer")
        self.manager.lock_files("sarah", ["src/auth.py", "src/user.py"], "implement auth feature")
        
        # Release specific files
        released = self.manager.release_files("sarah", ["src/auth.py"])
        self.assertIn("src/auth.py", released)
        self.assertNotIn("src/user.py", released)
        
        # Check that the file is no longer locked
        self.assertIsNone(self.manager.get_file_owner("src/auth.py"))
        self.assertEqual(self.manager.get_file_owner("src/user.py"), "sarah")
    
    def test_release_all_files(self):
        # Test that an employee can release all their files
        self.manager.hire_employee("sarah", "developer")
        self.manager.lock_files("sarah", ["src/auth.py", "src/user.py"], "implement auth feature")
        
        # Release all files
        released = self.manager.release_files("sarah")
        self.assertIn("src/auth.py", released)
        self.assertIn("src/user.py", released)
        
        # Check that no files are locked
        self.assertIsNone(self.manager.get_file_owner("src/auth.py"))
        self.assertIsNone(self.manager.get_file_owner("src/user.py"))
    
    def test_auto_release_based_on_task_completion(self):
        # Test that files are automatically released when task is marked complete
        self.manager.hire_employee("sarah", "developer")
        self.manager.lock_files("sarah", ["src/auth.py", "src/user.py"], "implement auth feature")
        
        # Create a mock task progress tracker that says files are ready to release
        mock_tracker = Mock()
        mock_tracker.get_task_progress.return_value = {
            'ready_to_release': ['src/auth.py']
        }
        
        # Release ready files
        released = self.manager.release_ready_files("sarah", mock_tracker)
        self.assertIn("src/auth.py", released)
        self.assertNotIn("src/user.py", released)
        
        # Check that the released file is no longer locked
        self.assertIsNone(self.manager.get_file_owner("src/auth.py"))
        self.assertEqual(self.manager.get_file_owner("src/user.py"), "sarah")
    
    def test_request_file(self):
        # Test that an employee can request a file from another employee
        self.manager.hire_employee("sarah", "developer")
        self.manager.hire_employee("dev-1", "developer")
        
        # Sarah locks a file
        self.manager.lock_files("sarah", ["src/auth.py"], "implement auth feature")
        
        # dev-1 requests the file
        result = self.manager.request_file("dev-1", "src/auth.py", "need to add validation")
        self.assertEqual(result, "request_sent_to_sarah")
        
        # Check that the request was created
        requests = self.manager.get_pending_requests("sarah")
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]['requester'], "dev-1")
        self.assertEqual(requests[0]['file_path'], "src/auth.py")
        self.assertEqual(requests[0]['reason'], "need to add validation")
    
    def test_request_unowned_file(self):
        # Test that requesting an unowned file returns appropriate response
        self.manager.hire_employee("dev-1", "developer")
        
        # dev-1 requests a file that isn't locked
        result = self.manager.request_file("dev-1", "src/auth.py", "need to implement")
        self.assertEqual(result, "file_not_locked")
    
    def test_request_owned_file_by_self(self):
        # Test that requesting a file you already own returns appropriate response
        self.manager.hire_employee("sarah", "developer")
        
        # Sarah locks a file
        self.manager.lock_files("sarah", ["src/auth.py"], "implement auth feature")
        
        # Sarah requests the same file
        result = self.manager.request_file("sarah", "src/auth.py", "need to add validation")
        self.assertEqual(result, "already_owner")
    
    def test_approve_request(self):
        # Test that a file request can be approved
        self.manager.hire_employee("sarah", "developer")
        self.manager.hire_employee("dev-1", "developer")
        
        # Sarah locks a file
        self.manager.lock_files("sarah", ["src/auth.py"], "implement auth feature")
        
        # dev-1 requests the file
        self.manager.request_file("dev-1", "src/auth.py", "need to add validation")
        
        # Get the request ID
        requests = self.manager.get_pending_requests("sarah")
        request_id = requests[0]['id']
        
        # Sarah approves the request
        result = self.manager.approve_request(request_id)
        self.assertTrue(result)
        
        # Check that dev-1 now owns the file
        self.assertEqual(self.manager.get_file_owner("src/auth.py"), "dev-1")
    
    def test_deny_request(self):
        # Test that a file request can be denied
        self.manager.hire_employee("sarah", "developer")
        self.manager.hire_employee("dev-1", "developer")
        
        # Sarah locks a file
        self.manager.lock_files("sarah", ["src/auth.py"], "implement auth feature")
        
        # dev-1 requests the file
        self.manager.request_file("dev-1", "src/auth.py", "need to add validation")
        
        # Get the request ID
        requests = self.manager.get_pending_requests("sarah")
        request_id = requests[0]['id']
        
        # Sarah denies the request
        result = self.manager.deny_request(request_id)
        self.assertTrue(result)
        
        # Check that sarah still owns the file
        self.assertEqual(self.manager.get_file_owner("src/auth.py"), "sarah")

if __name__ == '__main__':
    unittest.main()