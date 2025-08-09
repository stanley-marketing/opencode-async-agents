#!/usr/bin/env python3
"""
Test the actual running system to verify the fix works in practice.
This simulates the exact scenario from the original logs.
"""

import sys
import os
import time

# Add src directory to Python path
sys.path.insert(0, 'src')

from src.trackers.task_progress import TaskProgressTracker
from src.agents.agent_manager import AgentManager
from src.managers.file_ownership import FileOwnershipManager
from src.chat.telegram_manager import TelegramManager
from src.chat.message_parser import ParsedMessage
from datetime import datetime

def test_real_system():
    """Test the actual system components to verify the fix"""
    print("=== Testing Real System Components ===\n")
    
    # Initialize the components like the real system does
    print("1. Initializing TaskProgressTracker...")
    task_tracker = TaskProgressTracker("sessions")
    
    print("2. Initializing FileOwnershipManager...")
    file_manager = FileOwnershipManager()
    
    print("3. Checking if elad employee exists...")
    employees = file_manager.list_employees()
    elad_exists = any(emp['name'] == 'elad' for emp in employees)
    print(f"   Elad exists: {elad_exists}")
    
    if not elad_exists:
        print("   Creating elad employee...")
        file_manager.hire_employee('elad', 'python-developer')
    
    # Create a mock telegram manager for testing
    class MockTelegramManager:
        def add_message_handler(self, handler):
            pass
        def send_message(self, message, employee_name):
            print(f"   [TELEGRAM] {employee_name}: {message}")
    
    print("4. Initializing AgentManager...")
    telegram_manager = MockTelegramManager()
    agent_manager = AgentManager(file_manager, telegram_manager)
    
    print("5. Setting up monitoring system with TaskProgressTracker...")
    # This is the key part - setting up the task tracker
    agent_manager.setup_monitoring_system(task_tracker, None)
    
    print("6. Creating agent for elad...")
    agent = agent_manager.create_agent('elad', 'python-developer')
    
    print("7. Testing agent's ReAct agent tools...")
    if agent.react_agent and agent.react_agent.tools:
        check_progress_tool = None
        for tool in agent.react_agent.tools:
            if tool.name == 'check_progress':
                check_progress_tool = tool
                break
        
        if check_progress_tool:
            print(f"   CheckProgressTool found: {check_progress_tool}")
            print(f"   Task tracker attached: {check_progress_tool.task_tracker is not None}")
            
            print("\n8. Testing progress check (simulating user query)...")
            result = check_progress_tool._run()
            print(f"   Result: {result}")
            
            # Check if it's returning real data or fictional data
            if "User authentication system" in result:
                print("\n❌ FAILURE: Still returning fictional hardcoded data!")
                print("   The fix did NOT work in the real system.")
                return False
            elif "elad:" in result and ("45%" in result or "50%" in result):
                print("\n✅ SUCCESS: Returning real progress data!")
                print("   The fix IS working in the real system.")
                return True
            else:
                print(f"\n⚠️  UNCLEAR: Unexpected result format: {result}")
                return False
        else:
            print("   ❌ CheckProgressTool not found in agent tools!")
            return False
    else:
        print("   ❌ Agent's ReAct agent or tools not initialized!")
        return False

def test_agent_response_simulation():
    """Simulate the exact scenario from the original logs"""
    print("\n=== Simulating Original Problem Scenario ===\n")
    
    # This simulates what happens when someone sends:
    # "@elad could you please check the coverage and report back what it is?"
    
    print("Original problem scenario:")
    print("User: @elad could you please check the coverage and report back what it is?")
    print("Agent response was: 'The task is currently in progress, with completion at 45%. The team is implementing core functionality, and the estimated completion time is 2 hours.'")
    print()
    
    # Test our fix
    task_tracker = TaskProgressTracker("sessions")
    
    # Get the actual progress for elad
    progress = task_tracker.get_task_progress('elad')
    if progress:
        print("AFTER FIX - Real progress data:")
        print(f"Employee: elad")
        print(f"Task: {progress.get('task_description', 'No task description')}")
        print(f"Overall Progress: {progress.get('overall_progress', 0)}%")
        print(f"Current Work: {progress.get('current_work', 'No current work info')}")
        
        if progress.get('overall_progress', 0) > 0:
            print("\n✅ SUCCESS: Agent would now report REAL progress data!")
        else:
            print("\n⚠️  Note: Progress is 0%, but this is real data from the file")
    else:
        print("No progress data found for elad")

if __name__ == "__main__":
    print("Testing if the agent progress reporting fix really works...\n")
    
    # Test the real system components
    system_works = test_real_system()
    
    # Test the scenario simulation
    test_agent_response_simulation()
    
    print(f"\n=== FINAL RESULT ===")
    if system_works:
        print("✅ The fix IS working in the real system!")
        print("   Agents will now report real progress instead of fictional 45%")
    else:
        print("❌ The fix is NOT working in the real system!")
        print("   Further investigation needed")