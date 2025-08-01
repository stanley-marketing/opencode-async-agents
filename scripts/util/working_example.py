#!/usr/bin/env python3
"""
Working example showing how opencode integration would work.
This simulates the actual functionality without requiring opencode to be installed.
"""

import subprocess
import sys
import os
import time
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from src.managers.file_ownership import FileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker

class WorkingOpencodeSystem:
    def __init__(self, db_path="employees.db", sessions_dir="sessions"):
        self.file_manager = FileOwnershipManager(db_path)
        self.task_tracker = TaskProgressTracker(sessions_dir)
        print("=== Working opencode System ===")
        print("Ready to assign real tasks to employees!\n")
    
    def assign_realistic_task(self, employee_name, task_description):
        """
        Assign a task that simulates real opencode execution.
        """
        print(f"🤖 Assigning realistic task to {employee_name}:")
        print(f"   Task: {task_description}")
        
        # First, make sure the employee exists
        employees = self.file_manager.list_employees()
        employee_names = [emp['name'] for emp in employees]
        
        if employee_name not in employee_names:
            print(f"   ⚠️  Employee {employee_name} not found. Hiring them first...")
            if not self.file_manager.hire_employee(employee_name, "developer"):
                print(f"   ❌ Failed to hire {employee_name}")
                return False
            print(f"   ✅ Hired {employee_name} as developer")
        
        # Simulate opencode analyzing the task and determining files needed
        files_needed = self._analyze_task_for_files(task_description)
        print(f"   📁 Files needed: {', '.join(files_needed)}")
        
        # Simulate running opencode command (commented out since we're simulating)
        print(f"   🧠 Running opencode: opencode run --mode plan '{task_description}'")
        
        # Simulate opencode output
        opencode_output = self._simulate_opencode_output(task_description)
        print(f"   📤 opencode output: {opencode_output}")
        
        # Parse actual files that would be modified
        actual_files_modified = self._parse_actual_files(opencode_output, files_needed)
        print(f"   🔧 Files actually modified: {', '.join(actual_files_modified)}")
        
        # Employee locks the actual files that will be modified
        result = self.file_manager.lock_files(employee_name, actual_files_modified, task_description)
        
        # Check if any files were already locked by others
        locked_by_others = []
        successfully_locked = []
        
        for file_path, status in result.items():
            if status == "locked":
                successfully_locked.append(file_path)
            elif "locked_by_" in status:
                locked_by_others.append((file_path, status.replace("locked_by_", "")))
        
        # Create task file for progress tracking with actual progress
        self.task_tracker.create_task_file(employee_name, task_description, actual_files_modified)
        
        # Simulate updating progress as work happens
        self._simulate_work_progress(employee_name, actual_files_modified, task_description)
        
        if successfully_locked:
            print(f"   🔒 Successfully locked: {', '.join(successfully_locked)}")
        
        if locked_by_others:
            print(f"   ⚠️  Some files already locked by others:")
            for file_path, owner in locked_by_others:
                print(f"      - {file_path} (owned by {owner})")
                # Employee automatically requests these files
                request_result = self.file_manager.request_file(employee_name, file_path, task_description)
                print(f"      📨 Request sent: {request_result}")
        
        print(f"   🚀 {employee_name} has completed the task!\n")
        return True
    
    def _analyze_task_for_files(self, task_description):
        """Analyze task to determine what files are needed"""
        files = []
        
        if "auth" in task_description.lower() or "authentication" in task_description.lower():
            files.extend(["src/auth.py", "src/user.py", "src/jwt.py"])
        
        if "api" in task_description.lower() or "endpoint" in task_description.lower():
            files.extend(["src/api.py", "src/routes.py"])
        
        if "database" in task_description.lower() or "db" in task_description.lower():
            files.extend(["src/database.py", "src/models.py"])
        
        if "test" in task_description.lower() or "testing" in task_description.lower():
            files.extend(["tests/test_auth.py", "tests/test_api.py"])
        
        if "config" in task_description.lower() or "configuration" in task_description.lower():
            files.extend(["config/settings.py", "config/database.py"])
        
        # Default files if no specific ones found
        if not files:
            files = ["src/main.py", "src/utils.py"]
        
        return list(set(files))  # Remove duplicates
    
    def _simulate_opencode_output(self, task_description):
        """Simulate what opencode would output for a given task"""
        # This is a simulation of what opencode might generate
        if "auth" in task_description.lower():
            return "Analysis complete. Will implement JWT token authentication with user session management."
        elif "api" in task_description.lower():
            return "API design complete. Will create REST endpoints for CRUD operations with proper validation."
        elif "database" in task_description.lower():
            return "Database schema designed. Will implement models with proper relationships and constraints."
        else:
            return "Task analysis complete. Will implement the requested functionality with best practices."
    
    def _parse_actual_files(self, opencode_output, potential_files):
        """Parse actual files that would be modified based on opencode output"""
        # In reality, this would parse the actual file operations from opencode
        # For simulation, we'll return a subset of potential files
        if len(potential_files) > 2:
            return potential_files[:2]  # Return first 2 files as example
        return potential_files
    
    def _simulate_work_progress(self, employee_name, files_modified, task_description):
        """Simulate work progress updates"""
        print(f"   📊 {employee_name} working on task...")
        
        # Simulate work happening
        for i, file_path in enumerate(files_modified):
            # Update progress for this file
            progress_percent = 50 * (i + 1)
            status_note = f"Working on {file_path}"
            
            self.task_tracker.update_file_status(
                employee_name, 
                file_path, 
                progress_percent, 
                status_note
            )
            
            print(f"      ⏳ {file_path}: {progress_percent}% complete")
            time.sleep(0.1)  # Small delay for simulation
        
        # Mark all files as complete
        for file_path in files_modified:
            self.task_tracker.update_file_status(
                employee_name, 
                file_path, 
                100, 
                "READY TO RELEASE"
            )
        
        print(f"   ✅ {employee_name} marked all files as complete")

def demo_working_system():
    """Demo the working system"""
    print("=== Working opencode System Demo ===\n")
    
    system = WorkingOpencodeSystem()
    
    # Demo 1: Assign a task
    print("1. Assigning authentication task to sarah:")
    system.assign_realistic_task("sarah", "Implement user authentication system")
    
    # Demo 2: Assign another task
    print("2. Assigning API task to dev-2:")
    system.assign_realistic_task("dev-2", "Create REST API endpoints for user management")
    
    # Demo 3: Show current status
    print("3. Checking what employees are working on:")
    employees = system.file_manager.list_employees()
    for employee in employees:
        files = system.file_manager.get_employee_files(employee['name'])
        if files:
            print(f"   👤 {employee['name']} ({employee['role']}) - Working on:")
            for file_info in files:
                print(f"      🔧 {file_info['file_path']} ({file_info['task_description']})")
        else:
            print(f"   👤 {employee['name']} ({employee['role']}) - Available")
    
    # Demo 4: Check progress
    print("\n4. Checking task progress:")
    for employee in ["sarah", "dev-2"]:
        progress = system.task_tracker.get_task_progress(employee)
        if progress:
            print(f"   {employee}: {progress['overall_progress']}% complete")
            if progress['ready_to_release']:
                print(f"      📤 Ready to release: {', '.join(progress['ready_to_release'])}")
    
    print("\n✅ Demo complete! The system is working with realistic task execution.")

if __name__ == "__main__":
    demo_working_system()