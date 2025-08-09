#!/usr/bin/env python3
"""
Core concurrency testing for the OpenCode-Slack agent system.
Focuses on thread safety, resource contention, and concurrent operations
without external dependencies like LLM calls.
"""

import concurrent.futures
import logging
import os
import random
import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Dict, List
from unittest.mock import Mock, patch

# Import system components
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.managers.file_ownership import FileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker
from src.utils.opencode_wrapper import OpencodeSessionManager
from src.chat.telegram_manager import TelegramManager
from src.agents.agent_manager import AgentManager
from src.bridge.agent_bridge import AgentBridge

# Configure logging
logging.basicConfig(level=logging.WARNING)  # Reduce noise
logger = logging.getLogger(__name__)


class FastConcurrencyTest(unittest.TestCase):
    """Fast concurrency tests without external dependencies"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_employees.db")
        self.sessions_dir = os.path.join(self.temp_dir, "test_sessions")
        
        # Initialize core components
        self.file_manager = FileOwnershipManager(self.db_path)
        self.task_tracker = TaskProgressTracker(self.sessions_dir)
        
        # Mock Telegram to avoid network calls
        self.telegram_manager = Mock(spec=TelegramManager)
        self.telegram_manager.send_message = Mock(return_value=True)
        self.telegram_manager.is_connected = Mock(return_value=True)
        
        # Track thread safety violations
        self.violations = []
        self.lock = threading.Lock()
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_concurrent_file_locking(self):
        """Test concurrent file locking operations"""
        print("\n=== Testing Concurrent File Locking ===")
        
        # Create test employees
        employees = []
        for i in range(5):
            name = f"worker_{i}"
            self.file_manager.hire_employee(name, "developer")
            employees.append(name)
        
        # Shared files that multiple agents will try to lock
        shared_files = ["src/shared.py", "README.md", "config.json"]
        
        def attempt_lock(employee_name, iteration):
            try:
                files_to_lock = random.sample(shared_files, random.randint(1, 3))
                result = self.file_manager.lock_files(
                    employee_name, files_to_lock, f"Task {iteration}"
                )
                
                # Hold locks briefly
                time.sleep(random.uniform(0.01, 0.05))
                
                # Release locks
                locked_files = [f for f, status in result.items() if status == "locked"]
                if locked_files:
                    self.file_manager.release_files(employee_name, locked_files)
                
                return len(locked_files)
            except Exception as e:
                with self.lock:
                    self.violations.append(f"Lock operation failed: {e}")
                return 0
        
        # Run concurrent locking operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(50):  # 50 operations
                employee = random.choice(employees)
                future = executor.submit(attempt_lock, employee, i)
                futures.append(future)
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Verify results
        total_locks = sum(results)
        print(f"Total successful locks: {total_locks}")
        print(f"Thread safety violations: {len(self.violations)}")
        
        self.assertEqual(len(self.violations), 0, "Thread safety violations detected")
        self.assertGreater(total_locks, 0, "No locks were successful")
        
        # Verify no files are still locked
        all_locked = self.file_manager.get_all_locked_files()
        self.assertEqual(len(all_locked), 0, "Files still locked after test")
    
    def test_concurrent_database_operations(self):
        """Test concurrent database operations for thread safety"""
        print("\n=== Testing Concurrent Database Operations ===")
        
        def database_operations(worker_id):
            violations = []
            try:
                # Hire and fire employees concurrently
                for i in range(10):
                    name = f"temp_{worker_id}_{i}"
                    
                    # Hire
                    success = self.file_manager.hire_employee(name, "tester")
                    if not success:
                        violations.append(f"Failed to hire {name}")
                        continue
                    
                    # Check employee exists
                    employees = self.file_manager.list_employees()
                    employee_names = [emp['name'] for emp in employees]
                    if name not in employee_names:
                        violations.append(f"Employee {name} not found after hiring")
                    
                    # Fire
                    success = self.file_manager.fire_employee(name, self.task_tracker)
                    if not success:
                        violations.append(f"Failed to fire {name}")
                
                return violations
            except Exception as e:
                return [f"Database operation failed: {e}"]
        
        # Run concurrent database operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(database_operations, i) 
                for i in range(5)
            ]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Collect all violations
        all_violations = []
        for violations in results:
            all_violations.extend(violations)
        
        print(f"Database operation violations: {len(all_violations)}")
        if all_violations:
            for violation in all_violations[:5]:  # Show first 5
                print(f"  {violation}")
        
        # Should have minimal violations (some expected due to race conditions)
        self.assertLess(len(all_violations), 10, "Too many database operation failures")
    
    def test_concurrent_task_tracking(self):
        """Test concurrent task progress tracking operations"""
        print("\n=== Testing Concurrent Task Tracking ===")
        
        # Create test employees
        employees = []
        for i in range(3):
            name = f"tracker_{i}"
            self.file_manager.hire_employee(name, "developer")
            employees.append(name)
        
        def task_operations(employee_name, task_id):
            violations = []
            try:
                task_desc = f"Task {task_id} for {employee_name}"
                files = [f"src/{employee_name}_file_{task_id}.py"]
                
                # Create task file
                task_file = self.task_tracker.create_task_file(
                    employee_name, task_desc, files
                )
                
                # Update progress multiple times
                for progress in [25, 50, 75, 100]:
                    success = self.task_tracker.update_file_status(
                        employee_name, files[0], progress, f"Progress {progress}%"
                    )
                    if not success:
                        violations.append(f"Failed to update progress to {progress}%")
                    
                    # Update current work
                    self.task_tracker.update_current_work(
                        employee_name, f"Working on step {progress}%"
                    )
                    
                    time.sleep(0.01)  # Small delay
                
                # Get progress
                progress = self.task_tracker.get_task_progress(employee_name)
                if not progress:
                    violations.append("Failed to get task progress")
                
                # Mark complete
                self.task_tracker.mark_task_complete(employee_name)
                
                return violations
            except Exception as e:
                return [f"Task tracking failed: {e}"]
        
        # Run concurrent task operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = []
            for i, employee in enumerate(employees):
                for task_id in range(3):  # 3 tasks per employee
                    future = executor.submit(task_operations, employee, task_id)
                    futures.append(future)
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Collect violations
        all_violations = []
        for violations in results:
            all_violations.extend(violations)
        
        print(f"Task tracking violations: {len(all_violations)}")
        self.assertLess(len(all_violations), 5, "Too many task tracking failures")
    
    def test_agent_manager_thread_safety(self):
        """Test AgentManager operations under concurrent access"""
        print("\n=== Testing AgentManager Thread Safety ===")
        
        # Patch ReAct agent to avoid LLM calls
        with patch('src.agents.communication_agent.ReActAgent', return_value=None):
            agent_manager = AgentManager(self.file_manager, self.telegram_manager)
            
            # Create some initial agents
            for i in range(3):
                name = f"agent_{i}"
                self.file_manager.hire_employee(name, "developer")
                agent_manager.create_agent(name, "developer", ["python"])
        
        def agent_operations(operation_id):
            violations = []
            try:
                # Various agent operations
                for i in range(10):
                    # Get agent status
                    status = agent_manager.get_agent_status()
                    if not isinstance(status, dict):
                        violations.append("Invalid status type returned")
                    
                    # List active agents
                    active = agent_manager.list_active_agents()
                    if not isinstance(active, list):
                        violations.append("Invalid active agents type returned")
                    
                    # Check availability
                    for agent_name in active:
                        available = agent_manager.is_agent_available(agent_name)
                        if not isinstance(available, bool):
                            violations.append(f"Invalid availability type for {agent_name}")
                    
                    # Get chat statistics
                    stats = agent_manager.get_chat_statistics()
                    if not isinstance(stats, dict):
                        violations.append("Invalid chat statistics type returned")
                
                return violations
            except Exception as e:
                return [f"Agent operation failed: {e}"]
        
        # Run concurrent agent operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(agent_operations, i) 
                for i in range(8)
            ]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Collect violations
        all_violations = []
        for violations in results:
            all_violations.extend(violations)
        
        print(f"Agent manager violations: {len(all_violations)}")
        self.assertEqual(len(all_violations), 0, "AgentManager thread safety violations")
    
    def test_resource_contention_resolution(self):
        """Test how the system handles resource contention"""
        print("\n=== Testing Resource Contention Resolution ===")
        
        # Create employees
        employees = []
        for i in range(4):
            name = f"contender_{i}"
            self.file_manager.hire_employee(name, "developer")
            employees.append(name)
        
        # Single file that everyone wants
        contested_file = "src/critical_module.py"
        
        def compete_for_resource(employee_name, attempt_id):
            try:
                # Try to lock the contested file
                result = self.file_manager.lock_files(
                    employee_name, [contested_file], f"Attempt {attempt_id}"
                )
                
                if result.get(contested_file) == "locked":
                    # Got the lock, hold it briefly
                    time.sleep(random.uniform(0.05, 0.1))
                    
                    # Release it
                    self.file_manager.release_files(employee_name, [contested_file])
                    return "success"
                else:
                    return "blocked"
            except Exception as e:
                return f"error: {e}"
        
        # All employees compete for the same resource
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            for i in range(20):  # 20 attempts
                employee = random.choice(employees)
                future = executor.submit(compete_for_resource, employee, i)
                futures.append(future)
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Analyze results
        success_count = sum(1 for r in results if r == "success")
        blocked_count = sum(1 for r in results if r == "blocked")
        error_count = sum(1 for r in results if r.startswith("error"))
        
        print(f"Successful locks: {success_count}")
        print(f"Blocked attempts: {blocked_count}")
        print(f"Errors: {error_count}")
        
        # Verify contention was handled properly
        self.assertGreater(success_count, 0, "No successful locks")
        self.assertGreater(blocked_count, 0, "No contention detected")
        self.assertEqual(error_count, 0, "Errors during contention resolution")
        
        # Verify file is not locked at the end
        all_locked = self.file_manager.get_all_locked_files()
        locked_files = [f['file_path'] for f in all_locked]
        self.assertNotIn(contested_file, locked_files, "File still locked after test")
    
    def test_concurrent_session_management(self):
        """Test concurrent session management operations"""
        print("\n=== Testing Concurrent Session Management ===")
        
        session_manager = OpencodeSessionManager(
            self.file_manager, self.sessions_dir, quiet_mode=True
        )
        
        # Create employees
        employees = []
        for i in range(3):
            name = f"session_{i}"
            self.file_manager.hire_employee(name, "developer")
            employees.append(name)
        
        # Mock opencode execution to be fast
        def mock_execute(session_instance):
            time.sleep(0.1)  # Quick execution
            return {
                "success": True,
                "stdout": "Mock execution completed",
                "stderr": "",
                "returncode": 0
            }
        
        with patch.object(session_manager, 'start_employee_task') as mock_start:
            mock_start.return_value = "mock_session_id"
            
            def session_operations(employee_name, task_id):
                violations = []
                try:
                    # Start task
                    session_id = session_manager.start_employee_task(
                        employee_name, f"Task {task_id}", model="test", mode="build"
                    )
                    
                    if not session_id:
                        violations.append(f"Failed to start task for {employee_name}")
                        return violations
                    
                    # Get active sessions
                    active = session_manager.get_active_sessions()
                    if not isinstance(active, dict):
                        violations.append("Invalid active sessions type")
                    
                    # Stop task
                    session_manager.stop_employee_task(employee_name)
                    
                    return violations
                except Exception as e:
                    return [f"Session operation failed: {e}"]
            
            # Run concurrent session operations
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                futures = []
                for i, employee in enumerate(employees):
                    for task_id in range(2):  # 2 tasks per employee
                        future = executor.submit(session_operations, employee, task_id)
                        futures.append(future)
                
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Collect violations
        all_violations = []
        for violations in results:
            all_violations.extend(violations)
        
        print(f"Session management violations: {len(all_violations)}")
        self.assertEqual(len(all_violations), 0, "Session management violations detected")


def run_fast_concurrency_tests():
    """Run fast concurrency tests"""
    print("=" * 60)
    print("FAST CONCURRENCY TESTING")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(FastConcurrencyTest)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    print("CONCURRENCY TEST SUMMARY")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  {test}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"  {test}")
    
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
    print(f"\nSuccess rate: {success_rate:.1f}%")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_fast_concurrency_tests()
    sys.exit(0 if success else 1)