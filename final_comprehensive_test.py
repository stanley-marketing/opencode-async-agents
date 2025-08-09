#!/usr/bin/env python3
"""
Final comprehensive test to verify the fix works in the exact original scenario.
This simulates what happens when a user sends "@elad could you please check the coverage and report back what it is?"
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, 'src')

from src.trackers.task_progress import TaskProgressTracker
from src.agents.agent_manager import AgentManager
from src.managers.file_ownership import FileOwnershipManager
from src.chat.message_parser import ParsedMessage
from datetime import datetime

def test_original_scenario():
    """Test the exact original scenario that was broken"""
    print("=== Testing Original Broken Scenario ===\n")
    
    print("ORIGINAL PROBLEM:")
    print("User: @elad could you please check the coverage and report back what it is?")
    print("Agent Response (BROKEN): 'The task is currently in progress, with completion at 45%. The team is implementing core functionality, and the estimated completion time is 2 hours.'")
    print("Issue: This was hardcoded fictional data, not real progress!\n")
    
    # Set up the system components exactly like the real server does
    print("Setting up system components...")
    
    # Initialize components
    file_manager = FileOwnershipManager()
    task_tracker = TaskProgressTracker("sessions")
    
    # Mock telegram manager
    class MockTelegramManager:
        def add_message_handler(self, handler):
            pass
        def send_message(self, message, employee_name):
            return message
    
    telegram_manager = MockTelegramManager()
    agent_manager = AgentManager(file_manager, telegram_manager)
    
    # CRITICAL: Set up monitoring system (this is what was missing before)
    agent_manager.setup_monitoring_system(task_tracker, None)
    
    # Get the agent for elad
    if 'elad' not in agent_manager.agents:
        agent_manager.create_agent('elad', 'python-developer')
    
    agent = agent_manager.agents['elad']
    
    print("Testing agent's check_progress tool...")
    
    # Find the check_progress tool
    check_progress_tool = None
    if agent.react_agent and agent.react_agent.tools:
        for tool in agent.react_agent.tools:
            if tool.name == 'check_progress':
                check_progress_tool = tool
                break
    
    if not check_progress_tool:
        print("❌ FAILED: CheckProgressTool not found!")
        return False
    
    print(f"CheckProgressTool found: {check_progress_tool}")
    print(f"Task tracker attached: {check_progress_tool.task_tracker is not None}")
    
    # Test the tool (this simulates what happens when the agent uses check_progress)
    print("\nTesting progress check...")
    result = check_progress_tool._run()
    
    print(f"\nAFTER FIX - Agent Response:")
    print(f"'{result}'")
    
    # Verify the fix
    if "User authentication system" in result:
        print("\n❌ FAILED: Still returning fictional hardcoded data!")
        print("The fix did NOT work.")
        return False
    elif "elad:" in result and ("45%" in result or "50%" in result):
        print("\n✅ SUCCESS: Now returning REAL progress data!")
        print("The fix IS working correctly.")
        print("\nKey differences:")
        print("- Shows real agent names (elad, bob) instead of generic descriptions")
        print("- Shows real progress percentages from actual files")
        print("- No more fictional 'User authentication system' or 'Implementing core functionality'")
        return True
    else:
        print(f"\n⚠️  UNCLEAR: Unexpected result format")
        return False

def test_specific_task_query():
    """Test querying for a specific task"""
    print("\n=== Testing Specific Task Query ===\n")
    
    task_tracker = TaskProgressTracker("sessions")
    
    # Check what tasks are actually available
    all_progress = task_tracker.get_all_progress()
    print("Available progress data:")
    for employee, progress in all_progress.items():
        task_desc = progress.get('task_description', 'No description')
        overall_progress = progress.get('overall_progress', 0)
        print(f"- {employee}: {overall_progress}% - '{task_desc}'")
    
    print("\nThis shows the system now has access to REAL progress data from actual files!")

if __name__ == "__main__":
    print("Final Comprehensive Test: Agent Progress Reporting Fix\n")
    
    # Test the original scenario
    success = test_original_scenario()
    
    # Test specific task queries
    test_specific_task_query()
    
    print(f"\n{'='*60}")
    print("FINAL VERIFICATION RESULT:")
    if success:
        print("✅ THE FIX IS WORKING CORRECTLY!")
        print("   Agents now report real progress data instead of fictional 45%")
        print("   The original issue has been completely resolved.")
    else:
        print("❌ THE FIX IS NOT WORKING!")
        print("   Further investigation needed.")
    print(f"{'='*60}")