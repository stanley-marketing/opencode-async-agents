#!/usr/bin/env python3
"""
Test script to verify that the CheckProgressTool fix is working correctly.
This script tests that the tool now returns real progress data instead of hardcoded values.
"""

import sys
import os
import logging

# Add src directory to Python path
sys.path.insert(0, 'src')

from src.trackers.task_progress import TaskProgressTracker
from src.agents.agent_tools import CheckProgressTool

def test_check_progress_tool():
    """Test the CheckProgressTool with a real TaskProgressTracker"""
    print("Testing CheckProgressTool with real TaskProgressTracker...")
    
    # Initialize task tracker
    task_tracker = TaskProgressTracker("sessions")
    
    # Create CheckProgressTool with real task tracker
    tool = CheckProgressTool(task_tracker=task_tracker)
    
    # Test getting overall progress (no task_id)
    print("\n1. Testing overall progress:")
    result = tool._run()
    print(f"Result: {result}")
    
    # Test getting specific task progress
    print("\n2. Testing specific task progress:")
    result = tool._run("check code coverage and report back")
    print(f"Result: {result}")
    
    # Test with non-existent task
    print("\n3. Testing non-existent task:")
    result = tool._run("non-existent task")
    print(f"Result: {result}")
    
    print("\n4. Testing fallback behavior (no task tracker):")
    # Test fallback behavior by creating a tool without task tracker
    CheckProgressTool.task_tracker = None
    fallback_tool = CheckProgressTool()
    result = fallback_tool._run()
    print(f"Fallback result: {result}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_check_progress_tool()