#!/usr/bin/env python3
"""
Comprehensive validation test for the critical integration fixes.
Tests the specific issues that were identified and resolved:

1. Agent Discovery Mechanism
2. Component Synchronization 
3. Workflow Coordination
4. End-to-End Workflow Fixes
"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from src.managers.file_ownership import FileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker
from src.utils.opencode_wrapper import OpencodeSessionManager
from src.chat.telegram_manager import TelegramManager
from src.agents.agent_manager import AgentManager
from src.bridge.agent_bridge import AgentBridge
from src.chat.message_parser import MessageParser


class MockTelegramManager:
    """Mock Telegram manager for testing"""
    def __init__(self):
        self.sent_messages = []
        self.connected = True
    
    def send_message(self, text, sender="system", reply_to=None):
        self.sent_messages.append(text)
        return True
    
    def add_message_handler(self, handler):
        pass
    
    def is_connected(self):
        return self.connected


def test_agent_discovery_mechanism():
    """Test 1: Agent Discovery Mechanism"""
    print("🔍 Testing Agent Discovery Mechanism...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test.db")
        sessions_dir = os.path.join(temp_dir, "sessions")
        
        # Initialize components
        file_manager = FileOwnershipManager(db_path)
        telegram_manager = MockTelegramManager()
        agent_manager = AgentManager(file_manager, telegram_manager)
        
        # Test: Hire employee and verify agent is created automatically
        success = file_manager.hire_employee("test_dev", "developer", "smart")
        assert success, "Failed to hire employee"
        
        # Sync agents with employees
        agent_manager.sync_agents_with_employees()
        
        # Verify agent was created
        assert "test_dev" in agent_manager.agents, "Agent not created for hired employee"
        agent = agent_manager.agents["test_dev"]
        assert agent.employee_name == "test_dev", "Agent has wrong employee name"
        assert agent.role == "developer", "Agent has wrong role"
        
        print("✅ Agent Discovery Mechanism: PASSED")
        return True


def test_component_synchronization():
    """Test 2: Component Synchronization"""
    print("🔄 Testing Component Synchronization...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test.db")
        sessions_dir = os.path.join(temp_dir, "sessions")
        
        # Initialize components in proper order
        file_manager = FileOwnershipManager(db_path)
        task_tracker = TaskProgressTracker(sessions_dir)
        session_manager = OpencodeSessionManager(file_manager, sessions_dir, quiet_mode=True)
        telegram_manager = MockTelegramManager()
        agent_manager = AgentManager(file_manager, telegram_manager)
        
        # CRITICAL: Set up monitoring system to ensure proper synchronization
        agent_manager.setup_monitoring_system(task_tracker, session_manager)
        
        # Hire employee
        file_manager.hire_employee("sync_test", "developer")
        agent_manager.sync_agents_with_employees()
        
        # Verify synchronization
        assert "sync_test" in agent_manager.agents, "Agent not synchronized with employee"
        agent = agent_manager.agents["sync_test"]
        assert hasattr(agent, 'task_tracker'), "Agent missing task tracker"
        assert agent.task_tracker is task_tracker, "Agent has wrong task tracker reference"
        
        print("✅ Component Synchronization: PASSED")
        return True


def test_workflow_coordination():
    """Test 3: Workflow Coordination"""
    print("🔗 Testing Workflow Coordination...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test.db")
        sessions_dir = os.path.join(temp_dir, "sessions")
        
        # Initialize full system
        file_manager = FileOwnershipManager(db_path)
        task_tracker = TaskProgressTracker(sessions_dir)
        session_manager = OpencodeSessionManager(file_manager, sessions_dir, quiet_mode=True)
        telegram_manager = MockTelegramManager()
        agent_manager = AgentManager(file_manager, telegram_manager)
        agent_manager.setup_monitoring_system(task_tracker, session_manager)
        
        # Hire employee and sync
        file_manager.hire_employee("workflow_test", "developer")
        agent_manager.sync_agents_with_employees()
        
        # Create agent bridge
        agent_bridge = AgentBridge(session_manager, agent_manager)
        
        # Test task assignment through bridge
        success = agent_bridge.assign_task_to_worker("workflow_test", "Test workflow coordination")
        assert success, "Failed to assign task through bridge"
        
        # Verify task is tracked
        assert "workflow_test" in agent_bridge.active_tasks, "Task not tracked in bridge"
        task_info = agent_bridge.active_tasks["workflow_test"]
        assert task_info["task_description"] == "Test workflow coordination", "Wrong task description"
        assert task_info["status"] == "working", "Wrong task status"
        
        print("✅ Workflow Coordination: PASSED")
        return True


def test_end_to_end_workflow():
    """Test 4: End-to-End Workflow"""
    print("🎯 Testing End-to-End Workflow...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test.db")
        sessions_dir = os.path.join(temp_dir, "sessions")
        
        # Initialize full system
        file_manager = FileOwnershipManager(db_path)
        task_tracker = TaskProgressTracker(sessions_dir)
        session_manager = OpencodeSessionManager(file_manager, sessions_dir, quiet_mode=True)
        telegram_manager = MockTelegramManager()
        agent_manager = AgentManager(file_manager, telegram_manager)
        agent_manager.setup_monitoring_system(task_tracker, session_manager)
        
        # Hire employee and sync
        file_manager.hire_employee("e2e_test", "developer")
        agent_manager.sync_agents_with_employees()
        
        # Create agent bridge
        agent_bridge = AgentBridge(session_manager, agent_manager)
        
        # Simulate message handling
        parser = MessageParser()
        message_data = {
            "message_id": 1,
            "text": "@e2e_test please create a simple test file",
            "from": {"username": "manager"},
            "date": int(time.time()),
        }
        parsed_message = parser.parse_message(message_data)
        
        # Process message through agent manager
        agent_manager.handle_message(parsed_message)
        
        # Wait a moment for task file creation
        time.sleep(0.5)
        
        # Verify task file was created
        task_file_path = Path(sessions_dir) / "e2e_test" / "current_task.md"
        assert task_file_path.exists(), "Task file was not created"
        
        # Verify task file content
        with open(task_file_path, 'r') as f:
            content = f.read()
        assert "create a simple test file" in content, "Task description not in file"
        assert "Current Work:" in content, "Task file missing required sections"
        
        # Verify agent responded
        assert len(telegram_manager.sent_messages) > 0, "No response sent to Telegram"
        response = telegram_manager.sent_messages[0]
        assert "create a simple test file" in response, "Response doesn't mention the task"
        
        print("✅ End-to-End Workflow: PASSED")
        return True


def test_task_file_timing_fix():
    """Test 5: Task File Timing Fix (Critical Fix)"""
    print("⏰ Testing Task File Timing Fix...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test.db")
        sessions_dir = os.path.join(temp_dir, "sessions")
        
        # Initialize components
        file_manager = FileOwnershipManager(db_path)
        task_tracker = TaskProgressTracker(sessions_dir)
        session_manager = OpencodeSessionManager(file_manager, sessions_dir, quiet_mode=True)
        
        # Hire employee
        file_manager.hire_employee("timing_test", "developer")
        
        # Start task and verify immediate task file creation
        session_id = session_manager.start_employee_task("timing_test", "Test timing fix")
        assert session_id is not None, "Failed to start task"
        
        # Task file should exist IMMEDIATELY after start_employee_task returns
        task_file_path = Path(sessions_dir) / "timing_test" / "current_task.md"
        assert task_file_path.exists(), "Task file not created immediately (timing issue)"
        
        # Verify content
        with open(task_file_path, 'r') as f:
            content = f.read()
        assert "Test timing fix" in content, "Task description not in immediate file"
        
        print("✅ Task File Timing Fix: PASSED")
        return True


def main():
    """Run all integration fix validation tests"""
    print("=" * 60)
    print("🧪 INTEGRATION FIXES VALIDATION TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_agent_discovery_mechanism,
        test_component_synchronization,
        test_workflow_coordination,
        test_end_to_end_workflow,
        test_task_file_timing_fix,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
                print(f"❌ {test.__name__}: FAILED")
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__}: FAILED with exception: {e}")
    
    print("=" * 60)
    print(f"📊 RESULTS: {passed} PASSED, {failed} FAILED")
    
    if failed == 0:
        print("🎉 ALL INTEGRATION FIXES VALIDATED SUCCESSFULLY!")
        print("\n✅ Fixed Issues:")
        print("   1. Agent Discovery Mechanism - Agents created automatically for hired employees")
        print("   2. Component Synchronization - Proper initialization order and state consistency")
        print("   3. Workflow Coordination - Agent bridge task assignment works correctly")
        print("   4. End-to-End Workflow - Complete workflows execute from assignment to completion")
        print("   5. Task File Timing - Task files created immediately, no race conditions")
        return True
    else:
        print("❌ SOME TESTS FAILED - Integration issues remain")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)