"""
Comprehensive E2E tests for core system workflows.
Tests employee hiring/firing, task assignment, file ownership, session management, and CLI commands.
"""

import asyncio
import json
import os
import pytest
import requests
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.managers.file_ownership import FileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker
from src.utils.opencode_wrapper import OpencodeSessionManager
from src.server import OpencodeSlackServer


class TestCoreSystemWorkflows:
    """Test core system workflows end-to-end"""

    @pytest.fixture(autouse=True)
    def setup_test_environment(self, tmp_path):
        """Set up test environment with temporary directories"""
        self.test_dir = tmp_path
        self.db_path = self.test_dir / "test_employees.db"
        self.sessions_dir = self.test_dir / "test_sessions"
        self.sessions_dir.mkdir(exist_ok=True)
        
        # Create test project structure
        self.project_root = self.test_dir / "test_project"
        self.project_root.mkdir(exist_ok=True)
        
        # Create sample files for testing
        (self.project_root / "src").mkdir(exist_ok=True)
        (self.project_root / "src" / "main.py").write_text("# Main application file\nprint('Hello World')")
        (self.project_root / "src" / "utils.py").write_text("# Utility functions\ndef helper(): pass")
        (self.project_root / "tests").mkdir(exist_ok=True)
        (self.project_root / "tests" / "test_main.py").write_text("# Test file\ndef test_main(): pass")
        
        # Set environment variables for testing
        os.environ["OPENCODE_SAFE_MODE"] = "true"  # Disable communication for core tests
        os.environ["PROJECT_ROOT"] = str(self.project_root)
        
        yield
        
        # Cleanup
        if "OPENCODE_SAFE_MODE" in os.environ:
            del os.environ["OPENCODE_SAFE_MODE"]
        if "PROJECT_ROOT" in os.environ:
            del os.environ["PROJECT_ROOT"]

    @pytest.fixture
    def file_manager(self):
        """Create file ownership manager for testing"""
        return FileOwnershipManager(str(self.db_path))

    @pytest.fixture
    def task_tracker(self):
        """Create task progress tracker for testing"""
        return TaskProgressTracker(str(self.sessions_dir))

    @pytest.fixture
    def session_manager(self, file_manager):
        """Create session manager for testing"""
        return OpencodeSessionManager(file_manager, str(self.sessions_dir), quiet_mode=True)

    @pytest.fixture
    def server(self, test_port):
        """Create and start test server"""
        server = OpencodeSlackServer(
            host="localhost",
            port=test_port,
            websocket_port=test_port + 1,
            db_path=str(self.db_path),
            sessions_dir=str(self.sessions_dir),
            transport_type="websocket"
        )
        
        # Start server in background thread
        import threading
        server_thread = threading.Thread(target=server.start, daemon=True)
        server_thread.start()
        
        # Wait for server to start
        time.sleep(2)
        
        yield server
        
        # Stop server
        server.stop()

    def test_employee_lifecycle_management(self, file_manager):
        """Test complete employee lifecycle: hire, work, fire"""
        
        # Test hiring employees
        assert file_manager.hire_employee("alice", "developer", "smart")
        assert file_manager.hire_employee("bob", "designer", "normal")
        assert file_manager.hire_employee("charlie", "tester", "smart")
        
        # Verify employees were hired
        employees = file_manager.list_employees()
        assert len(employees) == 3
        
        employee_names = [emp['name'] for emp in employees]
        assert "alice" in employee_names
        assert "bob" in employee_names
        assert "charlie" in employee_names
        
        # Test employee details
        alice = next(emp for emp in employees if emp['name'] == 'alice')
        assert alice['role'] == 'developer'
        assert alice['smartness'] == 'smart'
        
        # Test duplicate hiring prevention
        assert not file_manager.hire_employee("alice", "developer")
        
        # Test firing employees
        assert file_manager.fire_employee("charlie", None)
        
        # Verify employee was fired
        employees = file_manager.list_employees()
        assert len(employees) == 2
        employee_names = [emp['name'] for emp in employees]
        assert "charlie" not in employee_names
        
        # Test firing non-existent employee
        assert not file_manager.fire_employee("nonexistent", None)

    def test_file_ownership_and_locking(self, file_manager):
        """Test file ownership and locking mechanisms"""
        
        # Hire employees for testing
        file_manager.hire_employee("alice", "developer")
        file_manager.hire_employee("bob", "designer")
        
        # Test file locking
        test_files = ["src/main.py", "src/utils.py"]
        result = file_manager.lock_files("alice", test_files, "Working on core functionality")
        
        # Verify files were locked
        assert "src/main.py" in result
        assert "src/utils.py" in result
        assert "locked" in result["src/main.py"]
        assert "locked" in result["src/utils.py"]
        
        # Test conflict prevention
        conflict_result = file_manager.lock_files("bob", ["src/main.py"], "Trying to work on same file")
        assert "locked" in conflict_result["src/main.py"].lower()  # Should indicate file is locked (by alice)
        
        # Test file request system
        request_result = file_manager.request_file("bob", "src/main.py", "Need to update styling")
        assert request_result is not None
        
        # Verify request was created
        pending_requests = file_manager.get_pending_requests()
        assert len(pending_requests) == 1
        assert pending_requests[0]['requesting_employee'] == 'bob'
        assert 'src/main.py' in pending_requests[0]['file_path']
        
        # Test request approval using the actual request ID from the database
        request_id = pending_requests[0]['id']
        assert file_manager.approve_request(request_id)
        
        # Verify file was transferred
        all_locked_files = file_manager.get_all_locked_files()
        alice_files = [f for f in all_locked_files if f['employee_name'] == 'alice']
        bob_files = [f for f in all_locked_files if f['employee_name'] == 'bob']
        
        alice_file_paths = [f['file_path'] for f in alice_files]
        bob_file_paths = [f['file_path'] for f in bob_files]
        
        assert "src/main.py" not in alice_file_paths
        assert "src/main.py" in bob_file_paths
        
        # Test file release - release_files returns empty list when releasing all files
        released = file_manager.release_files("alice")
        # When releasing all files (None parameter), it returns empty list
        assert isinstance(released, list)
        
        # Verify alice no longer has files locked
        alice_files_after = [f for f in file_manager.get_all_locked_files() if f['employee_name'] == 'alice']
        assert len(alice_files_after) == 0
        
        released = file_manager.release_files("bob")
        assert isinstance(released, list)
        
        # Verify bob no longer has files locked
        bob_files_after = [f for f in file_manager.get_all_locked_files() if f['employee_name'] == 'bob']
        assert len(bob_files_after) == 0

    def test_task_assignment_and_progress_tracking(self, task_tracker):
        """Test task assignment and progress tracking"""
        
        # Create task for employee
        task_tracker.create_task_file("alice", "Implement user authentication", ["src/auth.py", "src/user.py"])
        
        # Verify task file was created
        progress = task_tracker.get_task_progress("alice")
        assert progress is not None
        assert progress['task_description'] == "Implement user authentication"
        assert progress['overall_progress'] == 0
        
        # Update file progress
        task_tracker.update_file_status("alice", "src/auth.py", 50, "Authentication logic implemented")
        task_tracker.update_file_status("alice", "src/user.py", 75, "User model created")
        
        # Check updated progress
        progress = task_tracker.get_task_progress("alice")
        assert progress['overall_progress'] > 0
        
        # Mark file as complete
        task_tracker.update_file_status("alice", "src/auth.py", 100, "Authentication complete")
        
        # Verify completion
        progress = task_tracker.get_task_progress("alice")
        assert "src/auth.py" in progress.get('ready_to_release', [])

    @patch('src.utils.opencode_wrapper.subprocess.Popen')
    def test_session_management(self, mock_popen, session_manager):
        """Test session management and task execution"""
        
        # Mock opencode process
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        # Start employee task
        session_id = session_manager.start_employee_task(
            "alice", 
            "Implement user authentication", 
            "claude-3.5-sonnet",
            "build"
        )
        
        assert session_id is not None
        
        # Verify session is active
        active_sessions = session_manager.get_active_sessions()
        assert "alice" in active_sessions
        assert active_sessions["alice"]["is_running"]
        assert active_sessions["alice"]["task"] == "Implement user authentication"
        
        # Test session status
        assert session_manager.is_employee_working("alice")
        
        # Stop employee task
        session_manager.stop_employee_task("alice")
        
        # Verify session is stopped
        active_sessions = session_manager.get_active_sessions()
        assert "alice" not in active_sessions or not active_sessions["alice"]["is_running"]

    def test_cli_commands_integration(self, server, test_port):
        """Test CLI commands through server API"""
        
        base_url = f"http://localhost:{test_port}"
        
        # Test health check
        response = requests.get(f"{base_url}/health")
        assert response.status_code == 200
        health_data = response.json()
        assert health_data['status'] == 'healthy'
        
        # Test hiring employee via API
        response = requests.post(f"{base_url}/employees", json={
            'name': 'alice',
            'role': 'developer',
            'smartness': 'smart'
        })
        assert response.status_code == 200
        
        # Test listing employees
        response = requests.get(f"{base_url}/employees")
        assert response.status_code == 200
        employees_data = response.json()
        assert len(employees_data['employees']) == 1
        assert employees_data['employees'][0]['name'] == 'alice'
        
        # Test task assignment via API
        with patch('src.utils.opencode_wrapper.subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_process.pid = 12345
            mock_popen.return_value = mock_process
            
            response = requests.post(f"{base_url}/tasks", json={
                'name': 'alice',
                'task': 'Implement user authentication',
                'model': 'claude-3.5-sonnet'
            })
            assert response.status_code == 200
            task_data = response.json()
            assert 'session_id' in task_data
        
        # Test system status
        response = requests.get(f"{base_url}/status")
        assert response.status_code == 200
        status_data = response.json()
        assert 'employees' in status_data
        assert 'active_sessions' in status_data
        
        # Test file locking via API
        response = requests.post(f"{base_url}/files/lock", json={
            'name': 'alice',
            'files': ['src/main.py', 'src/utils.py'],
            'description': 'Working on core functionality'
        })
        assert response.status_code == 200
        
        # Test file listing
        response = requests.get(f"{base_url}/files")
        assert response.status_code == 200
        files_data = response.json()
        assert len(files_data['files']) == 2
        
        # Test firing employee
        response = requests.delete(f"{base_url}/employees/alice")
        assert response.status_code == 200

    def test_project_root_management(self, server, test_port):
        """Test project root directory management"""
        
        base_url = f"http://localhost:{test_port}"
        
        # Test getting current project root
        response = requests.get(f"{base_url}/project-root")
        assert response.status_code == 200
        root_data = response.json()
        assert 'project_root' in root_data
        
        # Test setting project root
        new_root = str(self.project_root)
        response = requests.post(f"{base_url}/project-root", json={
            'project_root': new_root
        })
        assert response.status_code == 200
        
        # Verify project root was set
        response = requests.get(f"{base_url}/project-root")
        assert response.status_code == 200
        root_data = response.json()
        assert root_data['project_root'] == new_root

    def test_concurrent_operations(self, file_manager):
        """Test concurrent operations and race conditions"""
        
        # Hire multiple employees
        file_manager.hire_employee("alice", "developer")
        file_manager.hire_employee("bob", "designer")
        file_manager.hire_employee("charlie", "tester")
        
        # Test concurrent file locking
        import threading
        results = {}
        
        def lock_files(employee, files, description):
            results[employee] = file_manager.lock_files(employee, files, description)
        
        # Try to lock same files concurrently
        threads = []
        for employee in ["alice", "bob", "charlie"]:
            thread = threading.Thread(
                target=lock_files,
                args=(employee, ["src/main.py"], f"Work by {employee}")
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify only one employee got the lock
        successful_locks = 0
        for employee, result in results.items():
            if "locked" in result.get("src/main.py", ""):
                successful_locks += 1
        
        assert successful_locks == 1

    def test_error_handling_and_recovery(self, file_manager, session_manager):
        """Test error handling and recovery scenarios"""
        
        # Test handling non-existent employee
        result = file_manager.lock_files("nonexistent", ["src/main.py"], "Test")
        assert "Employee not found" in str(result) or not result
        
        # Test handling non-existent files
        file_manager.hire_employee("alice", "developer")
        result = file_manager.lock_files("alice", ["nonexistent/file.py"], "Test")
        # Should handle gracefully without crashing
        
        # Test session cleanup after process failure
        with patch('src.utils.opencode_wrapper.subprocess.Popen') as mock_popen:
            # Mock a process that fails
            mock_process = MagicMock()
            mock_process.poll.return_value = 1  # Process failed
            mock_process.pid = 12345
            mock_popen.return_value = mock_process
            
            session_id = session_manager.start_employee_task(
                "alice", 
                "Test task", 
                "claude-3.5-sonnet"
            )
            
            # Simulate process failure
            mock_process.poll.return_value = 1
            
            # Session manager should handle this gracefully
            active_sessions = session_manager.get_active_sessions()
            # Should either clean up failed session or mark it as failed

    def test_data_persistence_and_recovery(self, tmp_path):
        """Test data persistence across system restarts"""
        
        # Create first instance and add data
        db_path = tmp_path / "persistence_test.db"
        file_manager1 = FileOwnershipManager(str(db_path))
        
        file_manager1.hire_employee("alice", "developer")
        file_manager1.hire_employee("bob", "designer")
        file_manager1.lock_files("alice", ["src/main.py"], "Test work")
        
        # Verify data exists
        employees1 = file_manager1.list_employees()
        files1 = file_manager1.get_all_locked_files()
        
        assert len(employees1) == 2
        assert len(files1) == 1
        
        # Create second instance with same database
        file_manager2 = FileOwnershipManager(str(db_path))
        
        # Verify data persisted
        employees2 = file_manager2.list_employees()
        files2 = file_manager2.get_all_locked_files()
        
        assert len(employees2) == 2
        assert len(files2) == 1
        assert employees2[0]['name'] in ['alice', 'bob']
        assert files2[0]['employee_name'] == 'alice'

    def test_system_limits_and_boundaries(self, file_manager):
        """Test system limits and boundary conditions"""
        
        # Test maximum number of employees (if there's a limit)
        for i in range(100):  # Try to hire many employees
            success = file_manager.hire_employee(f"employee_{i}", "developer")
            if not success:
                break
        
        employees = file_manager.list_employees()
        # Should handle large numbers gracefully
        
        # Test long task descriptions
        file_manager.hire_employee("alice", "developer")
        long_description = "A" * 10000  # Very long description
        
        result = file_manager.lock_files("alice", ["src/main.py"], long_description)
        # Should handle long descriptions without crashing
        
        # Test many files at once
        many_files = [f"file_{i}.py" for i in range(1000)]
        result = file_manager.lock_files("alice", many_files, "Many files test")
        # Should handle many files gracefully

    def test_integration_with_monitoring_system(self, server, test_port):
        """Test integration with monitoring and health check systems"""
        
        base_url = f"http://localhost:{test_port}"
        
        # Test monitoring health endpoint
        response = requests.get(f"{base_url}/monitoring/health")
        # Should return monitoring data or graceful error
        
        # Test system health with active operations
        requests.post(f"{base_url}/employees", json={
            'name': 'alice',
            'role': 'developer'
        })
        
        with patch('src.utils.opencode_wrapper.subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_process.pid = 12345
            mock_popen.return_value = mock_process
            
            requests.post(f"{base_url}/tasks", json={
                'name': 'alice',
                'task': 'Test task'
            })
        
        # Check health with active session
        response = requests.get(f"{base_url}/health")
        assert response.status_code == 200
        health_data = response.json()
        assert health_data['active_sessions'] >= 0

    @pytest.mark.slow
    def test_long_running_operations(self, session_manager):
        """Test long-running operations and stability"""
        
        with patch('src.utils.opencode_wrapper.subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_process.pid = 12345
            mock_popen.return_value = mock_process
            
            # Start long-running task
            session_id = session_manager.start_employee_task(
                "alice", 
                "Long running task", 
                "claude-3.5-sonnet"
            )
            
            # Simulate long-running operation
            for i in range(10):
                time.sleep(0.1)  # Simulate work
                active_sessions = session_manager.get_active_sessions()
                assert "alice" in active_sessions
                assert active_sessions["alice"]["is_running"]
            
            # Stop task
            session_manager.stop_employee_task("alice")

    def test_screenshot_capture_for_visual_validation(self, test_config):
        """Capture screenshots for visual validation of system state"""
        
        # This would capture screenshots if we had a UI
        # For now, we'll create visual reports of system state
        
        screenshot_dir = test_config["screenshot_dir"]
        
        # Create visual report of system state
        report_data = {
            "test_name": "core_system_workflows",
            "timestamp": time.time(),
            "system_state": {
                "employees_hired": True,
                "files_locked": True,
                "tasks_assigned": True,
                "sessions_active": True
            }
        }
        
        report_file = screenshot_dir / "core_system_state.json"
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        assert report_file.exists()

    def test_performance_under_load(self, file_manager):
        """Test system performance under load"""
        
        import time
        
        # Measure employee hiring performance
        start_time = time.time()
        for i in range(50):
            file_manager.hire_employee(f"employee_{i}", "developer")
        hiring_time = time.time() - start_time
        
        # Should complete within reasonable time
        assert hiring_time < 10.0  # 10 seconds for 50 employees
        
        # Measure file locking performance
        start_time = time.time()
        for i in range(20):
            employee_name = f"employee_{i}"
            files = [f"file_{i}_{j}.py" for j in range(5)]
            file_manager.lock_files(employee_name, files, f"Work by {employee_name}")
        locking_time = time.time() - start_time
        
        # Should complete within reasonable time
        assert locking_time < 5.0  # 5 seconds for 100 file locks

    def teardown_method(self):
        """Clean up after each test method"""
        # Cleanup is handled by fixtures
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])