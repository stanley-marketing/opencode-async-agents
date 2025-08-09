#!/usr/bin/env python3
"""
Comprehensive End-to-End Validation Test Suite for OpenCode-Slack Agent Orchestration System

This test suite validates:
1. Complete workflow testing from task assignment through completion reporting
2. Agent-to-agent communication validation
3. Task execution lifecycle verification
4. System state consistency across all components
5. Verification that agents can execute assigned tasks properly
6. Confirmation that completion reports are generated and delivered correctly

Test Methodology:
- Setup Phase: Initialize all system components
- Execution Phase: Run complete workflows with monitoring
- Verification Phase: Validate outcomes and state consistency
- Reporting Phase: Generate detailed findings report
"""

import os
import sys
import time
import json
import threading
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from unittest.mock import Mock, patch, MagicMock
import subprocess

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from src.managers.file_ownership import FileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker
from src.utils.opencode_wrapper import OpencodeSessionManager, OpencodeSession
from src.chat.telegram_manager import TelegramManager
from src.agents.agent_manager import AgentManager
from src.bridge.agent_bridge import AgentBridge
from src.chat.message_parser import MessageParser, ParsedMessage
from src.server import OpencodeSlackServer

@dataclass
class TestResult:
    """Test result data structure"""
    test_name: str
    status: str  # PASS, FAIL, SKIP
    duration: float
    details: str
    issues: List[str]
    recommendations: List[str]

@dataclass
class ValidationReport:
    """Comprehensive validation report"""
    test_results: List[TestResult]
    overall_status: str
    total_duration: float
    summary: str
    critical_issues: List[str]
    recommendations: List[str]

class MockTelegramManager:
    """Mock Telegram manager for testing"""
    
    def __init__(self):
        self.sent_messages = []
        self.message_handlers = []
        self.connected = True
        
    def add_message_handler(self, handler):
        self.message_handlers.append(handler)
        
    def send_message(self, text: str, sender_name: str = "system", reply_to: int = None) -> bool:
        message = {
            'text': text,
            'sender': sender_name,
            'reply_to': reply_to,
            'timestamp': datetime.now().isoformat()
        }
        self.sent_messages.append(message)
        return True
        
    def is_connected(self) -> bool:
        return self.connected
        
    def start_polling(self):
        self.connected = True
        
    def stop_polling(self):
        self.connected = False

class MockOpencodeSession:
    """Mock OpenCode session for testing"""
    
    def __init__(self, employee_name: str, task_description: str, 
                 file_manager: FileOwnershipManager, task_tracker: TaskProgressTracker,
                 model: Optional[str] = None, mode: str = "build", quiet_mode: bool = False):
        self.employee_name = employee_name
        self.task_description = task_description
        self.file_manager = file_manager
        self.task_tracker = task_tracker
        self.mode = mode
        self.quiet_mode = quiet_mode
        self.session_id = f"{employee_name}_{int(time.time())}"
        self.is_running = False
        self.files_locked = []
        self.session_dir = Path("sessions") / employee_name
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.model = model or "test-model"
        
    def start_session(self, progress_callback=None):
        """Start mock session"""
        self.is_running = True
        
        # Simulate task execution in background
        thread = threading.Thread(target=self._simulate_execution, daemon=True)
        thread.start()
        
        return self.session_id
        
    def _simulate_execution(self):
        """Simulate task execution"""
        try:
            # Step 1: Analyze task
            self.task_tracker.update_current_work(self.employee_name, "🔍 Analyzing task...")
            time.sleep(0.1)
            
            # Step 2: Lock files
            files_needed = ["src/test_file.py"]
            lock_result = self.file_manager.lock_files(
                self.employee_name, files_needed, self.task_description
            )
            
            successfully_locked = [f for f, status in lock_result.items() if status == "locked"]
            self.files_locked = successfully_locked
            
            if successfully_locked:
                self.task_tracker.update_current_work(self.employee_name, f"🔒 Locked {len(successfully_locked)} files")
                time.sleep(0.1)
                
                # Step 3: Create task file
                self.task_tracker.create_task_file(
                    self.employee_name, self.task_description, successfully_locked
                )
                
                # Step 4: Execute work
                self.task_tracker.update_current_work(self.employee_name, "🧠 Executing task...")
                time.sleep(0.2)
                
                # Step 5: Update progress
                for file_path in successfully_locked:
                    self.task_tracker.update_file_status(
                        self.employee_name, file_path, 100, "READY TO RELEASE"
                    )
                
                self.task_tracker.update_current_work(self.employee_name, "✅ Task completed successfully")
                
        except Exception as e:
            self.task_tracker.update_current_work(self.employee_name, f"❌ Error: {str(e)}")
        finally:
            self.is_running = False
            self._cleanup_session()
            self.task_tracker.mark_task_complete(self.employee_name)
            
    def _cleanup_session(self):
        """Clean up session"""
        if self.files_locked:
            self.file_manager.release_files(self.employee_name, self.files_locked)
            self.files_locked.clear()
            
    def stop_session(self):
        """Stop session"""
        self.is_running = False
        self._cleanup_session()

class ComprehensiveE2EValidator:
    """Comprehensive end-to-end validation system"""
    
    def __init__(self):
        self.test_results = []
        self.start_time = None
        self.temp_dir = None
        self.file_manager = None
        self.task_tracker = None
        self.session_manager = None
        self.telegram_manager = None
        self.agent_manager = None
        self.agent_bridge = None
        
    def setup_test_environment(self) -> bool:
        """Set up isolated test environment"""
        try:
            self.start_time = time.time()
            
            # Create temporary directory
            self.temp_dir = Path(tempfile.mkdtemp(prefix="opencode_e2e_test_"))
            
            # Initialize core components
            db_path = self.temp_dir / "test_employees.db"
            sessions_dir = self.temp_dir / "sessions"
            sessions_dir.mkdir(exist_ok=True)
            
            self.file_manager = FileOwnershipManager(str(db_path))
            self.task_tracker = TaskProgressTracker(str(sessions_dir))
            
            # Mock telegram manager
            self.telegram_manager = MockTelegramManager()
            
            # Initialize agent manager
            self.agent_manager = AgentManager(self.file_manager, self.telegram_manager)
            
            # Mock session manager with our mock sessions
            self.session_manager = OpencodeSessionManager(self.file_manager, str(sessions_dir), quiet_mode=True)
            
            # Patch OpencodeSession to use our mock
            original_session_class = OpencodeSession
            def mock_session_factory(*args, **kwargs):
                return MockOpencodeSession(*args, **kwargs)
            
            # Replace the session creation in session manager
            self.session_manager._create_session = mock_session_factory
            
            # Initialize agent bridge
            self.agent_bridge = AgentBridge(self.session_manager, self.agent_manager)
            
            # Set up monitoring system
            self.agent_manager.setup_monitoring_system(self.task_tracker, self.session_manager)
            
            return True
            
        except Exception as e:
            self._record_test_result("Environment Setup", "FAIL", 0, f"Failed to setup test environment: {str(e)}", [str(e)], ["Check system dependencies"])
            return False
    
    def cleanup_test_environment(self):
        """Clean up test environment"""
        try:
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Warning: Failed to cleanup test environment: {e}")
    
    def _record_test_result(self, test_name: str, status: str, duration: float, details: str, issues: List[str] = None, recommendations: List[str] = None):
        """Record a test result"""
        result = TestResult(
            test_name=test_name,
            status=status,
            duration=duration,
            details=details,
            issues=issues or [],
            recommendations=recommendations or []
        )
        self.test_results.append(result)
        
    def test_employee_lifecycle_management(self) -> bool:
        """Test 1: Employee Lifecycle Management"""
        start_time = time.time()
        issues = []
        recommendations = []
        
        try:
            # Test hiring employees
            success = self.file_manager.hire_employee("alice", "developer")
            if not success:
                issues.append("Failed to hire employee 'alice'")
                
            success = self.file_manager.hire_employee("bob", "designer")
            if not success:
                issues.append("Failed to hire employee 'bob'")
            
            # Test listing employees
            employees = self.file_manager.list_employees()
            if len(employees) != 2:
                issues.append(f"Expected 2 employees, found {len(employees)}")
                
            # Test communication agent creation
            if "alice" not in self.agent_manager.agents:
                issues.append("Communication agent not created for alice")
                
            if "bob" not in self.agent_manager.agents:
                issues.append("Communication agent not created for bob")
            
            # Test firing employees
            success = self.file_manager.fire_employee("bob", self.task_tracker)
            if not success:
                issues.append("Failed to fire employee 'bob'")
                
            employees = self.file_manager.list_employees()
            if len(employees) != 1:
                issues.append(f"Expected 1 employee after firing, found {len(employees)}")
            
            duration = time.time() - start_time
            status = "PASS" if not issues else "FAIL"
            details = f"Tested employee hiring, listing, agent creation, and firing. {len(employees)} employees remain."
            
            if issues:
                recommendations.extend([
                    "Check database connectivity and schema",
                    "Verify agent manager initialization",
                    "Review employee lifecycle callbacks"
                ])
            
            self._record_test_result("Employee Lifecycle Management", status, duration, details, issues, recommendations)
            return status == "PASS"
            
        except Exception as e:
            duration = time.time() - start_time
            self._record_test_result("Employee Lifecycle Management", "FAIL", duration, f"Exception: {str(e)}", [str(e)], ["Check system initialization"])
            return False
    
    def test_task_assignment_workflow(self) -> bool:
        """Test 2: Task Assignment Workflow"""
        start_time = time.time()
        issues = []
        recommendations = []
        
        try:
            # Ensure we have an employee
            if not self.file_manager.list_employees():
                self.file_manager.hire_employee("alice", "developer")
            
            # Create a test file to work with
            test_file = self.temp_dir / "src" / "test_file.py"
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text("# Test file for validation\nprint('Hello, World!')\n")
            
            # Test task assignment through agent bridge
            task_description = "Add documentation to test file"
            success = self.agent_bridge.assign_task_to_worker("alice", task_description)
            
            if not success:
                issues.append("Failed to assign task to worker")
            
            # Check if task is tracked
            if "alice" not in self.agent_bridge.active_tasks:
                issues.append("Task not tracked in agent bridge")
            
            # Wait for task file creation
            task_file = self.temp_dir / "sessions" / "alice" / "current_task.md"
            timeout = 5
            while timeout > 0 and not task_file.exists():
                time.sleep(0.1)
                timeout -= 0.1
                
            if not task_file.exists():
                issues.append("Task file not created")
            else:
                # Verify task file content
                content = task_file.read_text()
                if task_description not in content:
                    issues.append("Task description not found in task file")
            
            # Check session manager
            active_sessions = self.session_manager.get_active_sessions()
            if "alice" not in active_sessions:
                issues.append("Active session not found in session manager")
            
            duration = time.time() - start_time
            status = "PASS" if not issues else "FAIL"
            details = f"Tested task assignment workflow. Task file exists: {task_file.exists()}"
            
            if issues:
                recommendations.extend([
                    "Check file system permissions",
                    "Verify task tracker initialization",
                    "Review agent bridge callbacks"
                ])
            
            self._record_test_result("Task Assignment Workflow", status, duration, details, issues, recommendations)
            return status == "PASS"
            
        except Exception as e:
            duration = time.time() - start_time
            self._record_test_result("Task Assignment Workflow", "FAIL", duration, f"Exception: {str(e)}", [str(e)], ["Check task assignment logic"])
            return False
    
    def test_agent_communication_flow(self) -> bool:
        """Test 3: Agent-to-Agent Communication Flow"""
        start_time = time.time()
        issues = []
        recommendations = []
        
        try:
            # Ensure we have employees
            if not self.file_manager.list_employees():
                self.file_manager.hire_employee("alice", "developer")
                self.file_manager.hire_employee("bob", "designer")
            
            # Test message parsing
            parser = MessageParser()
            message_data = {
                "message_id": 1,
                "text": "@alice please implement authentication system",
                "from": {"username": "manager"},
                "date": int(time.time())
            }
            
            parsed_message = parser.parse_message(message_data)
            
            if not parsed_message.mentions:
                issues.append("Message parsing failed to extract mentions")
            elif "alice" not in parsed_message.mentions:
                issues.append("Alice not found in parsed mentions")
            
            # Test message handling
            initial_message_count = len(self.telegram_manager.sent_messages)
            self.agent_manager.handle_message(parsed_message)
            
            # Check if response was generated
            if len(self.telegram_manager.sent_messages) <= initial_message_count:
                issues.append("No response generated to message")
            
            # Test help request flow
            if "alice" in self.agent_manager.agents:
                help_success = self.agent_manager.request_help_for_agent(
                    "alice", "authentication system", "50% complete", "stuck on JWT implementation"
                )
                
                if not help_success:
                    issues.append("Failed to request help for agent")
                
                # Check if help message was sent
                help_messages = [msg for msg in self.telegram_manager.sent_messages if "help" in msg['text'].lower()]
                if not help_messages:
                    issues.append("Help request message not sent")
            
            duration = time.time() - start_time
            status = "PASS" if not issues else "FAIL"
            details = f"Tested message parsing, handling, and help requests. {len(self.telegram_manager.sent_messages)} messages sent."
            
            if issues:
                recommendations.extend([
                    "Check message parser regex patterns",
                    "Verify agent response generation",
                    "Review telegram manager integration"
                ])
            
            self._record_test_result("Agent Communication Flow", status, duration, details, issues, recommendations)
            return status == "PASS"
            
        except Exception as e:
            duration = time.time() - start_time
            self._record_test_result("Agent Communication Flow", "FAIL", duration, f"Exception: {str(e)}", [str(e)], ["Check communication system"])
            return False
    
    def test_file_locking_system(self) -> bool:
        """Test 4: File Locking and Conflict Prevention"""
        start_time = time.time()
        issues = []
        recommendations = []
        
        try:
            # Ensure we have employees
            if not self.file_manager.list_employees():
                self.file_manager.hire_employee("alice", "developer")
                self.file_manager.hire_employee("bob", "designer")
            
            # Create test files
            test_files = []
            for i in range(3):
                test_file = self.temp_dir / f"test_file_{i}.py"
                test_file.write_text(f"# Test file {i}\n")
                test_files.append(str(test_file))
            
            # Test file locking
            lock_result = self.file_manager.lock_files("alice", test_files, "Testing file locks")
            
            locked_count = sum(1 for status in lock_result.values() if status == "locked")
            if locked_count != len(test_files):
                issues.append(f"Expected {len(test_files)} files locked, got {locked_count}")
            
            # Test conflict prevention
            conflict_result = self.file_manager.lock_files("bob", test_files, "Attempting to lock same files")
            
            conflicted_count = sum(1 for status in conflict_result.values() if status == "locked_by_other")
            if conflicted_count != len(test_files):
                issues.append(f"Expected {len(test_files)} conflicts, got {conflicted_count}")
            
            # Test file release
            released = self.file_manager.release_files("alice", test_files)
            if len(released) != len(test_files):
                issues.append(f"Expected {len(test_files)} files released, got {len(released)}")
            
            # Test locking after release
            relock_result = self.file_manager.lock_files("bob", test_files, "Locking after release")
            relocked_count = sum(1 for status in relock_result.values() if status == "locked")
            if relocked_count != len(test_files):
                issues.append(f"Expected {len(test_files)} files relocked, got {relocked_count}")
            
            duration = time.time() - start_time
            status = "PASS" if not issues else "FAIL"
            details = f"Tested file locking, conflict prevention, and release. {len(test_files)} files tested."
            
            if issues:
                recommendations.extend([
                    "Check database file locking implementation",
                    "Verify file path resolution",
                    "Review conflict detection logic"
                ])
            
            self._record_test_result("File Locking System", status, duration, details, issues, recommendations)
            return status == "PASS"
            
        except Exception as e:
            duration = time.time() - start_time
            self._record_test_result("File Locking System", "FAIL", duration, f"Exception: {str(e)}", [str(e)], ["Check file system access"])
            return False
    
    def test_task_progress_tracking(self) -> bool:
        """Test 5: Task Progress Tracking and Reporting"""
        start_time = time.time()
        issues = []
        recommendations = []
        
        try:
            # Ensure we have an employee
            if not self.file_manager.list_employees():
                self.file_manager.hire_employee("alice", "developer")
            
            # Test task file creation
            task_description = "Implement user authentication"
            files = ["src/auth.py", "src/user.py"]
            
            self.task_tracker.create_task_file("alice", task_description, files)
            
            task_file = self.temp_dir / "sessions" / "alice" / "current_task.md"
            if not task_file.exists():
                issues.append("Task file not created")
            
            # Test progress updates
            self.task_tracker.update_current_work("alice", "Implementing JWT token generation")
            self.task_tracker.update_file_status("alice", "src/auth.py", 50, "In progress")
            
            # Test progress retrieval
            progress = self.task_tracker.get_task_progress("alice")
            if not progress:
                issues.append("Failed to retrieve task progress")
            elif progress.get('overall_progress', 0) == 0:
                issues.append("Progress not updated correctly")
            
            # Test task completion
            self.task_tracker.mark_task_complete("alice")
            
            # Check if task was archived
            completed_dir = self.temp_dir / "sessions" / "alice" / "completed_tasks"
            if not completed_dir.exists():
                issues.append("Completed tasks directory not created")
            else:
                completed_files = list(completed_dir.glob("*.md"))
                if not completed_files:
                    issues.append("Task not archived to completed tasks")
            
            # Test completed task retrieval
            completed_output = self.task_tracker.get_last_completed_task_output("alice")
            if not completed_output:
                issues.append("Failed to retrieve completed task output")
            
            duration = time.time() - start_time
            status = "PASS" if not issues else "FAIL"
            details = f"Tested task creation, progress tracking, and completion. Progress: {progress.get('overall_progress', 0) if progress else 0}%"
            
            if issues:
                recommendations.extend([
                    "Check task tracker file operations",
                    "Verify progress calculation logic",
                    "Review task archival process"
                ])
            
            self._record_test_result("Task Progress Tracking", status, duration, details, issues, recommendations)
            return status == "PASS"
            
        except Exception as e:
            duration = time.time() - start_time
            self._record_test_result("Task Progress Tracking", "FAIL", duration, f"Exception: {str(e)}", [str(e)], ["Check task tracking system"])
            return False
    
    def test_complete_workflow_integration(self) -> bool:
        """Test 6: Complete End-to-End Workflow Integration"""
        start_time = time.time()
        issues = []
        recommendations = []
        
        try:
            # Ensure clean state
            if not self.file_manager.list_employees():
                self.file_manager.hire_employee("alice", "developer")
            
            # Create test file
            test_file = self.temp_dir / "src" / "integration_test.py"
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text("# Integration test file\ndef hello():\n    pass\n")
            
            # Step 1: Simulate incoming message
            parser = MessageParser()
            message_data = {
                "message_id": 1,
                "text": "@alice please add documentation to integration_test.py",
                "from": {"username": "manager"},
                "date": int(time.time())
            }
            
            parsed_message = parser.parse_message(message_data)
            
            # Step 2: Handle message through agent manager
            initial_messages = len(self.telegram_manager.sent_messages)
            self.agent_manager.handle_message(parsed_message)
            
            # Step 3: Wait for task to start
            timeout = 5
            while timeout > 0 and "alice" not in self.agent_bridge.active_tasks:
                time.sleep(0.1)
                timeout -= 0.1
            
            if "alice" not in self.agent_bridge.active_tasks:
                issues.append("Task not started in agent bridge")
            
            # Step 4: Wait for task file creation
            task_file = self.temp_dir / "sessions" / "alice" / "current_task.md"
            timeout = 5
            while timeout > 0 and not task_file.exists():
                time.sleep(0.1)
                timeout -= 0.1
                
            if not task_file.exists():
                issues.append("Task file not created during workflow")
            
            # Step 5: Wait for task completion
            timeout = 10
            while timeout > 0 and "alice" in self.agent_bridge.active_tasks:
                self.agent_bridge.check_task_completion()
                time.sleep(0.2)
                timeout -= 0.2
            
            # Step 6: Verify completion
            if "alice" in self.agent_bridge.active_tasks:
                issues.append("Task did not complete within timeout")
            
            # Step 7: Check for completion message
            completion_messages = [msg for msg in self.telegram_manager.sent_messages[initial_messages:] 
                                 if "completed" in msg['text'].lower() or "✅" in msg['text']]
            
            if not completion_messages:
                issues.append("No completion message sent")
            
            # Step 8: Verify task was archived
            completed_dir = self.temp_dir / "sessions" / "alice" / "completed_tasks"
            if completed_dir.exists():
                completed_files = list(completed_dir.glob("*.md"))
                if not completed_files:
                    issues.append("Task not archived after completion")
            else:
                issues.append("Completed tasks directory not created")
            
            # Step 9: Check system state consistency
            active_sessions = self.session_manager.get_active_sessions()
            if "alice" in active_sessions:
                session_info = active_sessions["alice"]
                if session_info.get("is_running", False):
                    issues.append("Session still running after completion")
            
            # Step 10: Verify file locks released
            locked_files = self.file_manager.get_all_locked_files()
            alice_locks = [f for f in locked_files if f.get('employee') == 'alice']
            if alice_locks:
                issues.append("File locks not released after task completion")
            
            duration = time.time() - start_time
            status = "PASS" if not issues else "FAIL"
            details = f"Complete workflow test: {len(self.telegram_manager.sent_messages)} messages, {len(completion_messages)} completion messages"
            
            if issues:
                recommendations.extend([
                    "Check workflow coordination between components",
                    "Verify task completion detection",
                    "Review state cleanup processes",
                    "Ensure proper message flow"
                ])
            
            self._record_test_result("Complete Workflow Integration", status, duration, details, issues, recommendations)
            return status == "PASS"
            
        except Exception as e:
            duration = time.time() - start_time
            self._record_test_result("Complete Workflow Integration", "FAIL", duration, f"Exception: {str(e)}", [str(e)], ["Check end-to-end integration"])
            return False
    
    def test_error_handling_and_recovery(self) -> bool:
        """Test 7: Error Handling and Recovery Mechanisms"""
        start_time = time.time()
        issues = []
        recommendations = []
        
        try:
            # Ensure we have an employee
            if not self.file_manager.list_employees():
                self.file_manager.hire_employee("alice", "developer")
            
            # Test 1: Invalid task assignment
            invalid_success = self.agent_bridge.assign_task_to_worker("nonexistent", "test task")
            if invalid_success:
                issues.append("Task assignment succeeded for nonexistent employee")
            
            # Test 2: File locking with invalid paths
            invalid_files = ["/nonexistent/path/file.py", ""]
            lock_result = self.file_manager.lock_files("alice", invalid_files, "Testing invalid files")
            
            # Should handle gracefully without crashing
            if not isinstance(lock_result, dict):
                issues.append("File locking did not return proper result for invalid files")
            
            # Test 3: Progress tracking with invalid employee
            try:
                self.task_tracker.update_current_work("nonexistent", "test work")
                # Should not crash, but may log warnings
            except Exception as e:
                issues.append(f"Progress tracking crashed with invalid employee: {str(e)}")
            
            # Test 4: Message handling with malformed data
            try:
                malformed_message = ParsedMessage(
                    message_id=999,
                    text="",
                    sender="",
                    mentions=[],
                    timestamp=datetime.now()
                )
                self.agent_manager.handle_message(malformed_message)
                # Should handle gracefully
            except Exception as e:
                issues.append(f"Message handling crashed with malformed data: {str(e)}")
            
            # Test 5: Session cleanup on error
            # Create a session and simulate error
            session_id = self.session_manager.start_employee_task("alice", "test task")
            if session_id:
                # Force stop the session
                self.session_manager.stop_employee_task("alice")
                
                # Check if cleanup occurred
                active_sessions = self.session_manager.get_active_sessions()
                if "alice" in active_sessions:
                    issues.append("Session not cleaned up after forced stop")
            
            duration = time.time() - start_time
            status = "PASS" if not issues else "FAIL"
            details = f"Tested error handling for invalid inputs and edge cases. {len(issues)} issues found."
            
            if issues:
                recommendations.extend([
                    "Improve input validation",
                    "Add more robust error handling",
                    "Implement better cleanup mechanisms",
                    "Add error logging and monitoring"
                ])
            
            self._record_test_result("Error Handling and Recovery", status, duration, details, issues, recommendations)
            return status == "PASS"
            
        except Exception as e:
            duration = time.time() - start_time
            self._record_test_result("Error Handling and Recovery", "FAIL", duration, f"Exception: {str(e)}", [str(e)], ["Improve system robustness"])
            return False
    
    def test_system_state_consistency(self) -> bool:
        """Test 8: System State Consistency Across Components"""
        start_time = time.time()
        issues = []
        recommendations = []
        
        try:
            # Ensure we have employees
            if not self.file_manager.list_employees():
                self.file_manager.hire_employee("alice", "developer")
                self.file_manager.hire_employee("bob", "designer")
            
            # Test 1: Employee consistency across components
            employees = self.file_manager.list_employees()
            agent_names = list(self.agent_manager.agents.keys())
            
            for employee in employees:
                if employee['name'] not in agent_names:
                    issues.append(f"Employee {employee['name']} has no corresponding agent")
            
            for agent_name in agent_names:
                employee_names = [emp['name'] for emp in employees]
                if agent_name not in employee_names:
                    issues.append(f"Agent {agent_name} has no corresponding employee")
            
            # Test 2: File lock consistency
            # Lock some files
            test_files = ["src/test1.py", "src/test2.py"]
            self.file_manager.lock_files("alice", test_files, "Consistency test")
            
            # Check consistency between file manager and task tracker
            locked_files = self.file_manager.get_all_locked_files()
            alice_locks = [f for f in locked_files if f.get('employee') == 'alice']
            
            if len(alice_locks) != len(test_files):
                issues.append(f"File lock count mismatch: expected {len(test_files)}, got {len(alice_locks)}")
            
            # Test 3: Session state consistency
            session_id = self.session_manager.start_employee_task("alice", "consistency test")
            if session_id:
                # Check if session appears in all relevant places
                active_sessions = self.session_manager.get_active_sessions()
                bridge_tasks = self.agent_bridge.active_tasks
                
                if "alice" not in active_sessions:
                    issues.append("Session not found in session manager")
                
                # Wait a moment for bridge to register the task
                time.sleep(0.5)
                if "alice" not in bridge_tasks:
                    issues.append("Task not found in agent bridge")
            
            # Test 4: Message state consistency
            initial_count = len(self.telegram_manager.sent_messages)
            
            # Send a message through agent manager
            parser = MessageParser()
            message_data = {
                "message_id": 1,
                "text": "@bob please design a logo",
                "from": {"username": "manager"},
                "date": int(time.time())
            }
            parsed_message = parser.parse_message(message_data)
            self.agent_manager.handle_message(parsed_message)
            
            # Check if message was recorded
            final_count = len(self.telegram_manager.sent_messages)
            if final_count <= initial_count:
                issues.append("Message not recorded in telegram manager")
            
            duration = time.time() - start_time
            status = "PASS" if not issues else "FAIL"
            details = f"Tested state consistency across {len(employees)} employees and multiple components"
            
            if issues:
                recommendations.extend([
                    "Implement state synchronization mechanisms",
                    "Add consistency validation checks",
                    "Review component initialization order",
                    "Add state monitoring and alerts"
                ])
            
            self._record_test_result("System State Consistency", status, duration, details, issues, recommendations)
            return status == "PASS"
            
        except Exception as e:
            duration = time.time() - start_time
            self._record_test_result("System State Consistency", "FAIL", duration, f"Exception: {str(e)}", [str(e)], ["Check state management"])
            return False
    
    def run_all_tests(self) -> ValidationReport:
        """Run all validation tests and generate comprehensive report"""
        print("🚀 Starting Comprehensive End-to-End Validation of OpenCode-Slack Agent Orchestration System")
        print("=" * 100)
        
        # Setup test environment
        if not self.setup_test_environment():
            return self._generate_report()
        
        print("✅ Test environment setup complete")
        print()
        
        # Define test suite
        tests = [
            ("Employee Lifecycle Management", self.test_employee_lifecycle_management),
            ("Task Assignment Workflow", self.test_task_assignment_workflow),
            ("Agent Communication Flow", self.test_agent_communication_flow),
            ("File Locking System", self.test_file_locking_system),
            ("Task Progress Tracking", self.test_task_progress_tracking),
            ("Complete Workflow Integration", self.test_complete_workflow_integration),
            ("Error Handling and Recovery", self.test_error_handling_and_recovery),
            ("System State Consistency", self.test_system_state_consistency)
        ]
        
        # Run tests
        for test_name, test_func in tests:
            print(f"🧪 Running: {test_name}")
            try:
                success = test_func()
                status = "✅ PASS" if success else "❌ FAIL"
                print(f"   {status}")
            except Exception as e:
                print(f"   💥 CRASH: {str(e)}")
                self._record_test_result(test_name, "FAIL", 0, f"Test crashed: {str(e)}", [str(e)], ["Fix test implementation"])
            print()
        
        # Generate and return report
        report = self._generate_report()
        
        # Cleanup
        self.cleanup_test_environment()
        
        return report
    
    def _generate_report(self) -> ValidationReport:
        """Generate comprehensive validation report"""
        total_duration = time.time() - (self.start_time or time.time())
        
        # Calculate overall status
        passed_tests = [r for r in self.test_results if r.status == "PASS"]
        failed_tests = [r for r in self.test_results if r.status == "FAIL"]
        
        if not self.test_results:
            overall_status = "NO_TESTS"
        elif len(failed_tests) == 0:
            overall_status = "PASS"
        elif len(passed_tests) == 0:
            overall_status = "FAIL"
        else:
            overall_status = "PARTIAL"
        
        # Collect critical issues
        critical_issues = []
        all_recommendations = []
        
        for result in self.test_results:
            if result.status == "FAIL":
                critical_issues.extend(result.issues)
            all_recommendations.extend(result.recommendations)
        
        # Remove duplicates
        critical_issues = list(set(critical_issues))
        all_recommendations = list(set(all_recommendations))
        
        # Generate summary
        summary = f"""
Validation completed with {len(passed_tests)} passed, {len(failed_tests)} failed out of {len(self.test_results)} total tests.
Overall system status: {overall_status}
Total execution time: {total_duration:.2f} seconds
        """.strip()
        
        return ValidationReport(
            test_results=self.test_results,
            overall_status=overall_status,
            total_duration=total_duration,
            summary=summary,
            critical_issues=critical_issues,
            recommendations=all_recommendations
        )

def print_validation_report(report: ValidationReport):
    """Print comprehensive validation report"""
    print("\n" + "=" * 100)
    print("📊 COMPREHENSIVE END-TO-END VALIDATION REPORT")
    print("=" * 100)
    
    # Overall status
    status_emoji = {
        "PASS": "✅",
        "FAIL": "❌", 
        "PARTIAL": "⚠️",
        "NO_TESTS": "❓"
    }
    
    print(f"\n🎯 OVERALL STATUS: {status_emoji.get(report.overall_status, '❓')} {report.overall_status}")
    print(f"⏱️  TOTAL DURATION: {report.total_duration:.2f} seconds")
    print(f"📈 SUMMARY: {report.summary}")
    
    # Test results breakdown
    print(f"\n📋 TEST RESULTS BREAKDOWN:")
    print("-" * 50)
    
    for result in report.test_results:
        status_symbol = "✅" if result.status == "PASS" else "❌" if result.status == "FAIL" else "⏭️"
        print(f"{status_symbol} {result.test_name}")
        print(f"   Duration: {result.duration:.2f}s")
        print(f"   Details: {result.details}")
        
        if result.issues:
            print(f"   Issues ({len(result.issues)}):")
            for issue in result.issues:
                print(f"     • {issue}")
        
        if result.recommendations:
            print(f"   Recommendations ({len(result.recommendations)}):")
            for rec in result.recommendations:
                print(f"     → {rec}")
        print()
    
    # Critical issues summary
    if report.critical_issues:
        print(f"🚨 CRITICAL ISSUES FOUND ({len(report.critical_issues)}):")
        print("-" * 50)
        for i, issue in enumerate(report.critical_issues, 1):
            print(f"{i}. {issue}")
        print()
    
    # Recommendations summary
    if report.recommendations:
        print(f"💡 RECOMMENDATIONS FOR IMPROVEMENT ({len(report.recommendations)}):")
        print("-" * 50)
        for i, rec in enumerate(report.recommendations, 1):
            print(f"{i}. {rec}")
        print()
    
    # Final assessment
    print("🏁 FINAL ASSESSMENT:")
    print("-" * 50)
    
    if report.overall_status == "PASS":
        print("✅ The OpenCode-Slack agent orchestration system is functioning correctly.")
        print("   All core workflows operate seamlessly from initiation to completion.")
        print("   Agent-to-agent communication is working properly.")
        print("   System state consistency is maintained across all components.")
        
    elif report.overall_status == "PARTIAL":
        print("⚠️  The system has some issues but core functionality is working.")
        print("   Some workflows may experience problems.")
        print("   Review the critical issues and implement recommended fixes.")
        
    elif report.overall_status == "FAIL":
        print("❌ The system has significant issues that prevent proper operation.")
        print("   Core workflows are not functioning correctly.")
        print("   Immediate attention required to fix critical issues.")
        
    else:
        print("❓ Unable to determine system status due to test failures.")
        print("   Check test environment and system dependencies.")
    
    print("\n" + "=" * 100)

def main():
    """Main function to run comprehensive validation"""
    validator = ComprehensiveE2EValidator()
    
    try:
        report = validator.run_all_tests()
        print_validation_report(report)
        
        # Return appropriate exit code
        if report.overall_status == "PASS":
            return 0
        elif report.overall_status == "PARTIAL":
            return 1
        else:
            return 2
            
    except KeyboardInterrupt:
        print("\n🛑 Validation interrupted by user")
        return 130
    except Exception as e:
        print(f"\n💥 Validation failed with exception: {str(e)}")
        return 1
    finally:
        # Ensure cleanup
        try:
            validator.cleanup_test_environment()
        except:
            pass

if __name__ == "__main__":
    exit(main())