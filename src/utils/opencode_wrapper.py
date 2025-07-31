#!/usr/bin/env python3
"""
Wrapper script to run opencode commands with our employee management system.
Handles real opencode session spawning, background execution, and progress tracking.
"""

import subprocess
import sys
import os
import threading
import time
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import Config
from managers.file_ownership import FileOwnershipManager
from trackers.task_progress import TaskProgressTracker

class OpencodeSession:
    """Manages a real opencode session for an employee"""
    
    def __init__(self, employee_name: str, task_description: str, 
                 file_manager: FileOwnershipManager, task_tracker: TaskProgressTracker,
                 model: Optional[str] = None, mode: str = "plan"):
        self.employee_name = employee_name
        self.task_description = task_description
        self.file_manager = file_manager
        self.task_tracker = task_tracker
        self.model = model
        self.mode = mode
        self.session_id = f"{employee_name}_{int(time.time())}"
        self.process = None
        self.thread = None
        self.is_running = False
        self.progress_callback = None
        self.files_locked = []
        self.session_dir = Path("sessions") / employee_name
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
    def start_session(self, progress_callback: Optional[Callable] = None):
        """Start the opencode session in background"""
        self.progress_callback = progress_callback
        self.is_running = True
        
        # Create session thread
        self.thread = threading.Thread(target=self._run_session, daemon=True)
        self.thread.start()
        
        print(f"🚀 Started opencode session for {self.employee_name}")
        print(f"   Session ID: {self.session_id}")
        print(f"   Task: {self.task_description}")
        
        return self.session_id
    
    def _run_session(self):
        """Run the actual opencode session"""
        try:
            # Step 1: Analyze task to determine files needed
            files_needed = self._analyze_task_for_files()
            print(f"   📁 {self.employee_name} identified files needed: {', '.join(files_needed)}")
            
            # Step 2: Lock files
            lock_result = self.file_manager.lock_files(
                self.employee_name, files_needed, self.task_description
            )
            
            successfully_locked = []
            for file_path, status in lock_result.items():
                if status == "locked":
                    successfully_locked.append(file_path)
                    self.files_locked.append(file_path)
            
            if not successfully_locked:
                print(f"   ❌ {self.employee_name} couldn't lock any files - task blocked")
                self.is_running = False
                return
            
            print(f"   🔒 {self.employee_name} locked files: {', '.join(successfully_locked)}")
            
            # Step 3: Create task tracking
            self.task_tracker.create_task_file(
                self.employee_name, self.task_description, successfully_locked
            )
            
            # Step 4: Run actual opencode command
            result = self._execute_opencode_command()
            
            if result["success"]:
                print(f"   ✅ {self.employee_name} completed opencode execution")
                self._process_opencode_output(result["stdout"], successfully_locked)
            else:
                print(f"   ❌ {self.employee_name} opencode execution failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"   💥 {self.employee_name} session crashed: {str(e)}")
        finally:
            self.is_running = False
            self._cleanup_session()
    
    def _analyze_task_for_files(self) -> List[str]:
        """Analyze task description to determine what files might be needed"""
        files = []
        task_lower = self.task_description.lower()
        
        # Authentication related
        if any(word in task_lower for word in ["auth", "authentication", "login", "jwt", "token"]):
            files.extend(["src/auth.py", "src/user.py", "src/jwt.py", "src/middleware/auth.py"])
        
        # API related
        if any(word in task_lower for word in ["api", "endpoint", "route", "rest"]):
            files.extend(["src/api.py", "src/routes.py", "src/controllers/", "src/handlers/"]) 
        
        # Database related
        if any(word in task_lower for word in ["database", "db", "model", "schema", "migration"]):
            files.extend(["src/database.py", "src/models.py", "src/migrations/", "src/schemas/"]) 
        
        # Testing related
        if any(word in task_lower for word in ["test", "testing", "spec", "unit test"]):
            files.extend(["tests/", "test_*.py", "*.test.js", "spec/"]) 
        
        # Configuration related
        if any(word in task_lower for word in ["config", "configuration", "settings", "env"]):
            files.extend(["config/", "src/config.py", ".env", "settings.py"]) 
        
        # Frontend related
        if any(word in task_lower for word in ["ui", "frontend", "component", "react", "vue"]):
            files.extend(["src/components/", "src/pages/", "src/views/", "public/"]) 
        
        # Default files if no specific patterns found
        if not files:
            files = ["src/main.py", "src/app.py", "src/utils.py", "README.md"]
        
        # Remove duplicates and return
        return list(set(files))
    
    def _execute_opencode_command(self) -> Dict:
        """Execute the actual opencode command"""
        cmd = ["opencode", "run", "--mode", self.mode]
        
        if self.model:
            cmd.extend(["--model", self.model])
        
        cmd.append(self.task_description)
        
        print(f"   🧠 {self.employee_name} executing: {' '.join(cmd)}")
        
        try:
            # Run opencode with real-time output capture
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            stdout_lines = []
            stderr_lines = []
            
            # Read output in real-time
            while self.process.poll() is None:
                if self.process.stdout:
                    line = self.process.stdout.readline()
                    if line:
                        stdout_lines.append(line.strip())
                        self._parse_progress_from_output(line.strip())
                
                time.sleep(0.1)  # Small delay to prevent busy waiting
            
            # Get any remaining output
            remaining_stdout, remaining_stderr = self.process.communicate()
            if remaining_stdout:
                stdout_lines.extend(remaining_stdout.strip().split('\n'))
            if remaining_stderr:
                stderr_lines.extend(remaining_stderr.strip().split('\n'))
            
            return {
                "success": self.process.returncode == 0,
                "stdout": '\n'.join(stdout_lines),
                "stderr": '\n'.join(stderr_lines),
                "returncode": self.process.returncode
            }
            
        except FileNotFoundError:
            return {
                "success": False,
                "error": "opencode command not found - please install opencode",
                "stdout": "",
                "stderr": "opencode command not found"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": str(e)
            }
    
    def _parse_progress_from_output(self, line: str):
        """Parse progress information from opencode output"""
        # Look for file operations in opencode output
        if "Writing to" in line or "Created" in line or "Modified" in line:
            # Extract file path
            file_match = re.search(r'(?:Writing to|Created|Modified)\s+([^\s]+)', line)
            if file_match:
                file_path = file_match.group(1)
                self.task_tracker.update_file_status(
                    self.employee_name, file_path, 50, f"Working on {file_path}"
                )
                print(f"      📝 {self.employee_name} working on {file_path}")
        
        # Look for completion indicators
        if "Task completed" in line or "Done" in line or "Finished" in line:
            for file_path in self.files_locked:
                self.task_tracker.update_file_status(
                    self.employee_name, file_path, 100, "READY TO RELEASE"
                )
            print(f"      ✅ {self.employee_name} completed work on all files")
    
    def _process_opencode_output(self, output: str, files_locked: List[str]):
        """Process the final opencode output and update progress"""
        # Parse output for actual files modified
        modified_files = []
        
        # Look for file operations in the output
        file_patterns = [
            r'(?:Writing to|Created|Modified|Updated)\s+([^\s\n]+)',
            r'File:\s+([^\s\n]+)',
            r'Path:\s+([^\s\n]+)'
        ]
        
        for pattern in file_patterns:
            matches = re.findall(pattern, output, re.IGNORECASE)
            modified_files.extend(matches)
        
        # Remove duplicates
        modified_files = list(set(modified_files))
        
        if modified_files:
            print(f"      📄 {self.employee_name} modified files: {', '.join(modified_files)}")
            
            # Update progress for actually modified files
            for file_path in modified_files:
                if file_path in files_locked:
                    self.task_tracker.update_file_status(
                        self.employee_name, file_path, 100, "READY TO RELEASE"
                    )
        else:
            # If no specific files found, mark all locked files as complete
            for file_path in files_locked:
                self.task_tracker.update_file_status(
                    self.employee_name, file_path, 100, "READY TO RELEASE"
                )
        
        # Save session output
        output_file = self.session_dir / f"session_{self.session_id}.log"
        with open(output_file, 'w') as f:
            f.write(f"Session: {self.session_id}\n")
            f.write(f"Employee: {self.employee_name}\n")
            f.write(f"Task: {self.task_description}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Files Locked: {', '.join(files_locked)}\n")
            f.write(f"Files Modified: {', '.join(modified_files)}\n")
            f.write("\n--- opencode Output ---\n")
            f.write(output)
    
    def _cleanup_session(self):
        """Clean up session resources"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
        
        # Note: We don't release file locks here - they should be released
        # manually when the work is approved and merged
        
        print(f"   🧹 {self.employee_name} session {self.session_id} cleaned up")
    
    def stop_session(self):
        """Stop the running session"""
        self.is_running = False
        if self.process and self.process.poll() is None:
            self.process.terminate()
        print(f"   🛑 Stopped session {self.session_id} for {self.employee_name}")


class OpencodeSessionManager:
    """Manages multiple opencode sessions for different employees"""
    
    def __init__(self, db_path: str = "employees.db", sessions_dir: str = "sessions"):
        self.file_manager = FileOwnershipManager(db_path)
        self.task_tracker = TaskProgressTracker(sessions_dir)
        self.active_sessions: Dict[str, OpencodeSession] = {}
        
    def start_employee_task(self, employee_name: str, task_description: str, 
                          model: Optional[str] = None, mode: str = "plan") -> str:
        """Start a new task for an employee"""
        
        # Check if employee exists
        employees = self.file_manager.list_employees()
        employee_names = [emp['name'] for emp in employees]
        
        if employee_name not in employee_names:
            print(f"❌ Employee {employee_name} not found")
            return None
        
        # Check if employee already has an active session
        if employee_name in self.active_sessions:
            if self.active_sessions[employee_name].is_running:
                print(f"⚠️  {employee_name} already has an active session")
                return None
            else:
                # Clean up old session
                del self.active_sessions[employee_name]
        
        # Create and start new session
        session = OpencodeSession(
            employee_name, task_description, 
            self.file_manager, self.task_tracker,
            model, mode
        )
        
        session_id = session.start_session()
        self.active_sessions[employee_name] = session
        
        return session_id
    
    def stop_employee_task(self, employee_name: str):
        """Stop an employee's active task"""
        if employee_name in self.active_sessions:
            self.active_sessions[employee_name].stop_session()
            del self.active_sessions[employee_name]
            print(f"✅ Stopped task for {employee_name}")
        else:
            print(f"❌ No active session found for {employee_name}")
    
    def get_active_sessions(self) -> Dict[str, Dict]:
        """Get information about all active sessions"""
        sessions_info = {}
        for employee_name, session in self.active_sessions.items():
            sessions_info[employee_name] = {
                "session_id": session.session_id,
                "task": session.task_description,
                "is_running": session.is_running,
                "files_locked": session.files_locked
            }
        return sessions_info
    
    def cleanup_all_sessions(self):
        """Stop all active sessions"""
        for employee_name in list(self.active_sessions.keys()):
            self.stop_employee_task(employee_name)


# Legacy function for backward compatibility
def run_opencode_command(employee_name, task_description, model=None, mode="plan"):
    """
    Legacy function - use OpencodeSessionManager for new code
    """
    manager = OpencodeSessionManager()
    return manager.start_employee_task(employee_name, task_description, model, mode)

def main():
    """Main function to demonstrate the opencode wrapper"""
    print("=== opencode Wrapper Demo ===")
    print("This demo shows how to run opencode commands with our system.\n")
    
    # Example usage
    print("Example usage:")
    print("  run_opencode_command('sarah', 'Analyze the user authentication requirements')")
    print("  run_opencode_command('dev-2', 'Implement the login API endpoint', model='claude-3.5')")
    print()
    
    # Show the command that would be run
    print("Example command that would be executed:")
    print("  opencode run --mode plan 'Analyze the user authentication requirements'")
    print()
    
    print("To use this in your system:")
    print("1. Import the run_opencode_command function")
    print("2. Call it with employee name and task description")
    print("3. Handle the result as needed")
    print()
    
    print("The function returns a dictionary with:")
    print("  - success: Boolean indicating if the command succeeded")
    print("  - stdout: Standard output from the command")
    print("  - stderr: Standard error from the command")
    print("  - returncode: Return code from the command")
    print("  - error: Error message if an exception occurred")

if __name__ == "__main__":
    main()