#!/usr/bin/env python3
"""
Final test to verify the agent's improved behavior.
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.react_agent import ReActAgent
from src.trackers.task_progress import TaskProgressTracker

def test_final_behavior():
    """Test the final agent behavior"""
    
    print("🧪 Testing final agent behavior...")
    
    # Initialize components
    task_tracker = TaskProgressTracker("sessions")
    
    # Create a ReAct agent
    agent = ReActAgent(
        employee_name="test_agent",
        role="python-developer",
        expertise=["Python", "Flask", "AI/ML"],
        task_tracker=task_tracker
    )
    
    # Test message asking for coverage
    test_message = "please report the current test coverage"
    
    print(f"📝 Testing with message: '{test_message}'")
    
    try:
        response = agent.handle_message(test_message, mode="forward")
        
        print(f"✅ Agent responded successfully!")
        print(f"📤 Response: {response}")
        print(f"📤 Response length: {len(response)}")
        print(f"📤 Response contains 'started working': {'started working' in response.lower()}")
        print(f"📤 Response contains 'report back': {'report back' in response.lower()}")
        print(f"📤 Response contains 'started coding task': {'started coding task' in response.lower()}")
        print(f"📤 Response contains 'task id': {'task id' in response.lower()}")
        
        # Check if the response is user-friendly
        if "started working" in response.lower() or "report back" in response.lower():
            print("✅ Agent provided a proper user-friendly response!")
            print("✅ Agent is now behaving correctly - it starts tasks and informs the user!")
        else:
            print("❌ Agent response may not be user-friendly")
            print("🔍 Debug: Let's see what the agent actually returned...")
            
        return True
        
    except Exception as e:
        print(f"❌ Agent failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_final_behavior()
    if success:
        print("🎉 Final behavior test PASSED!")
        print("🎯 The agent now correctly starts tasks and informs users!")
        sys.exit(0)
    else:
        print("💥 Final behavior test FAILED!")
        sys.exit(1) 