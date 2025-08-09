#!/usr/bin/env python3
"""
Integration test to verify that the agent now reports real progress instead of fictional 45%.
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, 'src')

from src.trackers.task_progress import TaskProgressTracker
from src.agents.agent_tools import get_agent_tools, CheckProgressTool

def test_integration():
    """Test that the integration works correctly"""
    print("Testing full integration...")
    
    # Initialize task tracker
    task_tracker = TaskProgressTracker("sessions")
    
    # Get tools with task tracker
    tools = get_agent_tools(task_tracker=task_tracker)
    
    # Find the check progress tool
    check_progress_tool = None
    for tool in tools:
        if isinstance(tool, CheckProgressTool):
            check_progress_tool = tool
            break
    
    if check_progress_tool is None:
        print("ERROR: CheckProgressTool not found in tools list")
        return
    
    print(f"CheckProgressTool found: {check_progress_tool}")
    print(f"Task tracker set: {check_progress_tool.task_tracker is not None}")
    
    # Test the tool
    print("\nTesting tool with real task tracker:")
    result = check_progress_tool._run()
    print(f"Result: {result}")
    
    # Check if result contains real data instead of fictional 45%
    if "45%" in result and "fictional" not in result.lower():
        print("\n✅ SUCCESS: Tool is returning real progress data (45% for elad)")
    elif "User authentication system" in result:
        print("\n❌ FAILURE: Tool is still returning fictional hardcoded data")
    else:
        print(f"\n✅ SUCCESS: Tool is returning real progress data: {result}")

if __name__ == "__main__":
    test_integration()