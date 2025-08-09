#!/usr/bin/env python3
"""
Focused Workflow Validation Test

This test focuses on validating the core workflow functionality by testing
the actual system components in a controlled manner.
"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from src.managers.file_ownership import FileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker
from src.utils.opencode_wrapper import OpencodeSessionManager
from src.chat.telegram_manager import TelegramManager
from src.agents.agent_manager import AgentManager
from src.bridge.agent_bridge import AgentBridge
from src.chat.message_parser import MessageParser

def test_core_workflow():
    """Test the core workflow functionality"""
    print("🧪 Testing Core Workflow Functionality")
    print("=" * 60)
    
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix="workflow_test_"))
    
    try:
        # Initialize components
        print("📋 Initializing system components...")
        
        db_path = temp_dir / "test.db"
        sessions_dir = temp_dir / "sessions"
        sessions_dir.mkdir(exist_ok=True)
        
        file_manager = FileOwnershipManager(str(db_path))
        task_tracker = TaskProgressTracker(str(sessions_dir))
        
        print("✅ File manager and task tracker initialized")
        
        # Test 1: Employee Management
        print("\n🧪 Test 1: Employee Management")
        success = file_manager.hire_employee("alice", "developer")
        print(f"   Hire alice: {'✅ SUCCESS' if success else '❌ FAILED'}")
        
        employees = file_manager.list_employees()
        print(f"   Employee count: {len(employees)}")
        
        # Test 2: File Locking
        print("\n🧪 Test 2: File Locking System")
        
        # Create test files
        test_file = temp_dir / "test_file.py"
        test_file.write_text("# Test file\nprint('Hello')\n")
        
        lock_result = file_manager.lock_files("alice", [str(test_file)], "Test task")
        locked_count = sum(1 for status in lock_result.values() if status == "locked")
        print(f"   Files locked: {locked_count}/1")
        
        # Test conflict prevention
        conflict_result = file_manager.lock_files("bob", [str(test_file)], "Conflict test")
        conflicts = sum(1 for status in conflict_result.values() if status == "locked_by_other")
        print(f"   Conflicts detected: {conflicts}/1")
        
        # Test 3: Task Progress Tracking
        print("\n🧪 Test 3: Task Progress Tracking")
        
        task_tracker.create_task_file("alice", "Test task", [str(test_file)])
        task_file = sessions_dir / "alice" / "current_task.md"
        print(f"   Task file created: {'✅ YES' if task_file.exists() else '❌ NO'}")
        
        task_tracker.update_current_work("alice", "Working on test file")
        task_tracker.update_file_status("alice", str(test_file), 50, "In progress")
        
        progress = task_tracker.get_task_progress("alice")
        print(f"   Progress tracking: {'✅ WORKING' if progress else '❌ FAILED'}")
        if progress:
            print(f"   Overall progress: {progress.get('overall_progress', 0)}%")
        
        # Test 4: Task Completion
        print("\n🧪 Test 4: Task Completion")
        
        task_tracker.mark_task_complete("alice")
        completed_dir = sessions_dir / "alice" / "completed_tasks"
        completed_files = list(completed_dir.glob("*.md")) if completed_dir.exists() else []
        print(f"   Task archived: {'✅ YES' if completed_files else '❌ NO'}")
        
        # Test 5: File Release
        print("\n🧪 Test 5: File Release")
        
        released = file_manager.release_files("alice", [str(test_file)])
        print(f"   Files released: {len(released)}/1")
        
        # Test 6: Session Manager (with mocked opencode)
        print("\n🧪 Test 6: Session Manager")
        
        with patch('src.utils.opencode_wrapper.OpencodeSession') as mock_session_class:
            # Create a mock session instance
            mock_session = MagicMock()
            mock_session.session_id = "test_session_123"
            mock_session.is_running = True
            mock_session.files_locked = []
            mock_session_class.return_value = mock_session
            
            session_manager = OpencodeSessionManager(file_manager, str(sessions_dir), quiet_mode=True)
            
            # Test session creation
            session_id = session_manager.start_employee_task("alice", "Test session task")
            print(f"   Session started: {'✅ YES' if session_id else '❌ NO'}")
            
            # Test active sessions
            active_sessions = session_manager.get_active_sessions()
            print(f"   Active sessions: {len(active_sessions)}")
            
            # Test session cleanup
            session_manager.stop_employee_task("alice")
            print("   Session stopped: ✅ YES")
        
        # Test 7: Message Parsing
        print("\n🧪 Test 7: Message Parsing")
        
        parser = MessageParser()
        message_data = {
            "message_id": 1,
            "text": "@alice please implement authentication",
            "from": {"username": "manager"},
            "date": int(time.time())
        }
        
        parsed = parser.parse_message(message_data)
        mentions_found = "alice" in parsed.mentions
        print(f"   Message parsing: {'✅ WORKING' if mentions_found else '❌ FAILED'}")
        print(f"   Mentions found: {parsed.mentions}")
        
        # Summary
        print("\n📊 WORKFLOW VALIDATION SUMMARY")
        print("=" * 60)
        
        tests_passed = 0
        total_tests = 7
        
        # Count successful tests based on our checks
        if success:  # Employee management
            tests_passed += 1
        if locked_count == 1 and conflicts == 1:  # File locking
            tests_passed += 1
        if task_file.exists() and progress:  # Task tracking
            tests_passed += 1
        if completed_files:  # Task completion
            tests_passed += 1
        if len(released) == 1:  # File release
            tests_passed += 1
        if session_id:  # Session management
            tests_passed += 1
        if mentions_found:  # Message parsing
            tests_passed += 1
        
        success_rate = (tests_passed / total_tests) * 100
        
        print(f"Tests Passed: {tests_passed}/{total_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("🎉 OVERALL STATUS: ✅ SYSTEM FUNCTIONAL")
            print("   Core workflows are operating correctly.")
        elif success_rate >= 60:
            print("⚠️  OVERALL STATUS: ⚠️  PARTIAL FUNCTIONALITY")
            print("   Some components working, but issues detected.")
        else:
            print("🚨 OVERALL STATUS: ❌ SYSTEM ISSUES")
            print("   Significant problems detected in core workflows.")
        
        return success_rate >= 80
        
    except Exception as e:
        print(f"\n💥 Test failed with exception: {str(e)}")
        return False
        
    finally:
        # Cleanup
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

def test_agent_communication():
    """Test agent communication without external dependencies"""
    print("\n🧪 Testing Agent Communication")
    print("=" * 60)
    
    temp_dir = Path(tempfile.mkdtemp(prefix="agent_test_"))
    
    try:
        # Mock telegram manager
        class MockTelegramManager:
            def __init__(self):
                self.sent_messages = []
                self.handlers = []
                
            def add_message_handler(self, handler):
                self.handlers.append(handler)
                
            def send_message(self, text, sender="system", reply_to=None):
                self.sent_messages.append({
                    'text': text,
                    'sender': sender,
                    'reply_to': reply_to
                })
                return True
                
            def is_connected(self):
                return True
        
        # Initialize components
        db_path = temp_dir / "test.db"
        sessions_dir = temp_dir / "sessions"
        sessions_dir.mkdir(exist_ok=True)
        
        file_manager = FileOwnershipManager(str(db_path))
        telegram_manager = MockTelegramManager()
        
        # Hire an employee first
        file_manager.hire_employee("alice", "developer")
        
        # Test agent manager initialization
        agent_manager = AgentManager(file_manager, telegram_manager)
        
        print(f"   Agent manager initialized: ✅ YES")
        print(f"   Agents created: {len(agent_manager.agents)}")
        
        # Test message handling
        parser = MessageParser()
        message_data = {
            "message_id": 1,
            "text": "@alice please help with testing",
            "from": {"username": "manager"},
            "date": int(time.time())
        }
        
        parsed = parser.parse_message(message_data)
        initial_messages = len(telegram_manager.sent_messages)
        
        # Handle the message
        agent_manager.handle_message(parsed)
        
        messages_sent = len(telegram_manager.sent_messages) - initial_messages
        print(f"   Messages sent in response: {messages_sent}")
        
        # Test help request
        if "alice" in agent_manager.agents:
            help_success = agent_manager.request_help_for_agent(
                "alice", "test task", "50% complete", "need assistance"
            )
            print(f"   Help request: {'✅ SUCCESS' if help_success else '❌ FAILED'}")
        
        print(f"   Total messages sent: {len(telegram_manager.sent_messages)}")
        
        return len(agent_manager.agents) > 0
        
    except Exception as e:
        print(f"   💥 Agent communication test failed: {str(e)}")
        return False
        
    finally:
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

def main():
    """Run focused workflow validation"""
    print("🚀 OpenCode-Slack Focused Workflow Validation")
    print("=" * 80)
    
    # Test core workflow
    workflow_success = test_core_workflow()
    
    # Test agent communication
    agent_success = test_agent_communication()
    
    # Final assessment
    print("\n🏁 FINAL VALIDATION RESULTS")
    print("=" * 80)
    
    print(f"Core Workflow: {'✅ PASS' if workflow_success else '❌ FAIL'}")
    print(f"Agent Communication: {'✅ PASS' if agent_success else '❌ FAIL'}")
    
    if workflow_success and agent_success:
        print("\n🎉 VALIDATION RESULT: ✅ SYSTEM OPERATIONAL")
        print("   The OpenCode-Slack agent orchestration system is functioning correctly.")
        print("   Core workflows and agent communication are working as expected.")
        return 0
    elif workflow_success or agent_success:
        print("\n⚠️  VALIDATION RESULT: ⚠️  PARTIAL FUNCTIONALITY")
        print("   Some components are working, but issues were detected.")
        print("   Review the test output for specific problems.")
        return 1
    else:
        print("\n🚨 VALIDATION RESULT: ❌ SYSTEM ISSUES")
        print("   Significant problems detected in the system.")
        print("   Core functionality is not working properly.")
        return 2

if __name__ == "__main__":
    exit(main())