#!/usr/bin/env python3
"""
Real task assignment system for opencode-slack.
Assign tasks and employees will spawn real opencode sessions to work on them.
"""

import sys
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from src.managers.file_ownership import FileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker
from src.utils.opencode_wrapper import OpencodeSessionManager

class TaskAssigner:
    def __init__(self, db_path="employees.db", sessions_dir="sessions"):
        self.file_manager = FileOwnershipManager(db_path)
        self.task_tracker = TaskProgressTracker(sessions_dir)
        self.session_manager = OpencodeSessionManager(db_path, sessions_dir)
        print("=== Real Task Assigner System ===")
        print("Ready to assign real opencode tasks to employees!\n")
    
    def assign_task(self, employee_name, task_description, model=None, mode="plan"):
        """
        Assign a real task to an employee. They will automatically:
        1. Spawn a real opencode session
        2. Analyze what files they need
        3. Lock those files
        4. Execute the task with real opencode
        5. Update progress in real-time
        """
        print(f"🤖 Assigning REAL task to {employee_name}:")
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
        
        # Start real opencode session for the employee
        session_id = self.session_manager.start_employee_task(
            employee_name, task_description, model, mode
        )
        
        if session_id:
            print(f"   🚀 {employee_name} is now working on the task with real opencode!")
            print(f"   📋 Session ID: {session_id}")
            return session_id
        else:
            print(f"   ❌ Failed to start opencode session for {employee_name}")
            return False
    
    def _analyze_task_for_files(self, task_description):
        """
        Simple analysis to determine what files are needed for a task.
        In a real implementation, this could be more sophisticated.
        """
        # Simple keyword-based file determination
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
    
    def list_employees_working(self):
        """Show which employees are currently working on what (including active opencode sessions)"""
        employees = self.file_manager.list_employees()
        if not employees:
            print("No employees currently hired.")
            return
        
        # Get active opencode sessions
        active_sessions = self.session_manager.get_active_sessions()
        
        print("📋 Currently hired employees:")
        for employee in employees:
            name = employee['name']
            files = self.file_manager.get_employee_files(name)
            
            # Check if employee has active opencode session
            if name in active_sessions:
                session_info = active_sessions[name]
                status = "🔥 ACTIVE OPENCODE SESSION" if session_info['is_running'] else "⏸️  PAUSED SESSION"
                print(f"  👤 {name} ({employee['role']}) - {status}")
                print(f"     🧠 Task: {session_info['task']}")
                print(f"     📋 Session: {session_info['session_id']}")
                if session_info['files_locked']:
                    print(f"     🔒 Files locked: {', '.join(session_info['files_locked'])}")
            elif files:
                print(f"  👤 {name} ({employee['role']}) - Working on files:")
                for file_info in files:
                    print(f"     🔧 {file_info['file_path']} ({file_info['task_description']})")
            else:
                print(f"  👤 {name} ({employee['role']}) - Available")
    
    def check_task_progress(self, employee_name=None):
        """Check progress of tasks"""
        if employee_name:
            progress = self.task_tracker.get_task_progress(employee_name)
            if progress:
                print(f"📊 Progress for {employee_name}:")
                print(f"   Task: {progress['task_description']}")
                print(f"   Overall: {progress['overall_progress']}% complete")
                print(f"   Ready to release: {', '.join(progress['ready_to_release']) if progress['ready_to_release'] else 'None'}")
            else:
                print(f"No progress found for {employee_name}")
        else:
            # Show progress for all employees
            employees = self.file_manager.list_employees()
            if not employees:
                print("No employees found.")
                return
            
            print("📊 Task Progress:")
            for employee in employees:
                name = employee['name']
                progress = self.task_tracker.get_task_progress(name)
                if progress:
                    print(f"  {name}: {progress['overall_progress']}% complete")
                else:
                    print(f"  {name}: No active tasks")
    
    def stop_employee_task(self, employee_name):
        """Stop an employee's active opencode session"""
        self.session_manager.stop_employee_task(employee_name)
    
    def complete_task(self, employee_name, file_path):
        """Mark a file as complete (100% progress)"""
        progress = self.task_tracker.get_task_progress(employee_name)
        if progress:
            self.task_tracker.update_file_status(employee_name, file_path, 100, "READY TO RELEASE")
            print(f"✅ Marked {file_path} as complete for {employee_name}")
            
            # Auto-release ready files
            released = self.file_manager.release_ready_files(employee_name, self.task_tracker)
            if released:
                print(f"📤 Auto-released files: {', '.join(released)}")
        else:
            print(f"No active task found for {employee_name}")
    
    def get_active_sessions(self):
        """Get information about all active opencode sessions"""
        return self.session_manager.get_active_sessions()

def main():
    """Main function with real opencode demo"""
    assigner = TaskAssigner()
    
    print("Demo: Assigning REAL opencode tasks to employees\n")
    
    # Assign some real tasks that will spawn opencode sessions
    print("🚀 Starting real opencode sessions...")
    assigner.assign_task("sarah", "Implement user authentication with JWT tokens")
    assigner.assign_task("dev-2", "Create REST API endpoints for user management") 
    assigner.assign_task("analyst-1", "Write technical documentation for the auth system")
    
    # Show current status with active sessions
    print("\n📊 Current employee status:")
    assigner.list_employees_working()
    
    print("\n" + "="*60)
    print("🔥 REAL OPENCODE SYSTEM IS NOW RUNNING!")
    print("Your employees are working with actual opencode sessions!")
    print("\nAvailable methods:")
    print("  assigner.assign_task('employee', 'task', model='claude-3.5')")
    print("  assigner.list_employees_working()  # Shows active sessions")
    print("  assigner.check_task_progress('employee_name')")
    print("  assigner.stop_employee_task('employee_name')")
    print("  assigner.get_active_sessions()  # Get session details")
    print("  assigner.complete_task('employee', 'file_path')")
    print("="*60 + "\n")
    
    # Keep the demo running to show real progress
    import time
    print("⏳ Letting employees work for a few seconds...")
    time.sleep(5)
    
    print("\n📈 Progress update:")
    assigner.check_task_progress()

if __name__ == "__main__":
    main()