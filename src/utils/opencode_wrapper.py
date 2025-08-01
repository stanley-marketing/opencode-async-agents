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
from config.models_config import models_config

class OpencodeSession:
    """Manages a real opencode session for an employee"""
    
    def __init__(self, employee_name: str, task_description: str, 
                 file_manager: FileOwnershipManager, task_tracker: TaskProgressTracker,
                 model: Optional[str] = None, mode: str = "build", quiet_mode: bool = False):
        self.employee_name = employee_name
        self.task_description = task_description
        self.file_manager = file_manager
        self.task_tracker = task_tracker
        self.mode = mode
        self.quiet_mode = quiet_mode  # Suppress console output in CLI mode
        self.session_id = f"{employee_name}_{int(time.time())}"
        self.process = None
        self.thread = None
        self.is_running = False
        self.progress_callback = None
        self.files_locked = []
        self.session_dir = Path("sessions") / employee_name
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.output_buffer = []  # Buffer output for quiet mode
        self.project_root = file_manager.get_project_root()
        
        # Determine model to use
        if model is None:
            # Get employee's smartness level from database
            employee_info = file_manager.get_employee_info(employee_name)
            if employee_info and 'smartness' in employee_info:
                smartness_level = employee_info['smartness']
                self.model = models_config.get_model_for_level(smartness_level)
            else:
                # Default to normal model
                self.model = models_config.get_model_for_level("normal")
        else:
            self.model = model
    
    def _print(self, message: str):
        """Print message respecting quiet mode"""
        if self.quiet_mode:
            self.output_buffer.append(message)
        else:
            print(message)
        
    def start_session(self, progress_callback: Optional[Callable] = None):
        """Start the opencode session in background"""
        self.progress_callback = progress_callback
        self.is_running = True
        
        # Create session thread
        self.thread = threading.Thread(target=self._run_session, daemon=True)
        self.thread.start()
        
        self._print(f"🚀 Started opencode session for {self.employee_name}")
        self._print(f"   Session ID: {self.session_id}")
        self._print(f"   Task: {self.task_description[:200]}{'...' if len(self.task_description) > 200 else ''}")
        
        return self.session_id
    
    def _run_session(self):
        """Run the actual opencode session"""
        try:
            # Step 1: Analyze task to determine files needed
            self.task_tracker.update_current_work(self.employee_name, "🔍 Analyzing task and identifying required files...")
            files_needed = self._analyze_task_for_files()
            self._print(f"   📁 {self.employee_name} identified files needed: {', '.join(files_needed)}")
            
            # Step 2: Lock files
            self.task_tracker.update_current_work(self.employee_name, f"🔒 Attempting to lock {len(files_needed)} files...")
            lock_result = self.file_manager.lock_files(
                self.employee_name, files_needed, self.task_description
            )
            
            successfully_locked = []
            for file_path, status in lock_result.items():
                if status == "locked":
                    successfully_locked.append(file_path)
                    self.files_locked.append(file_path)
            
            if not successfully_locked:
                self.task_tracker.update_current_work(self.employee_name, "❌ Could not lock any files - task blocked")
                self._print(f"   ❌ {self.employee_name} couldn't lock any files - task blocked")
                self.is_running = False
                return
            
            self._print(f"   🔒 {self.employee_name} locked files: {', '.join(successfully_locked)}")
            self.task_tracker.update_current_work(self.employee_name, f"✅ Successfully locked {len(successfully_locked)} files")
            
            # Step 3: Create task tracking
            self.task_tracker.create_task_file(
                self.employee_name, self.task_description, successfully_locked
            )
            
            # Step 4: Run actual opencode command
            self.task_tracker.update_current_work(self.employee_name, f"🧠 Executing opencode with {self.model or 'default model'}...")
            result = self._execute_opencode_command()
            
            # Check for API errors in the output even if returncode is 0
            output_text = result.get("stdout", "") + result.get("stderr", "")
            has_api_error = any(error in output_text for error in [
                "AI_APICallError", "Request body too large", "API error", "Authentication failed",
                "Rate limit exceeded", "Model not found", "Invalid API key"
            ])
            
            if result["success"] and not has_api_error:
                self._print(f"   ✅ {self.employee_name} completed opencode execution")
                self.task_tracker.update_current_work(self.employee_name, "✅ opencode execution completed successfully - processing results...")
                self._process_opencode_output(result["stdout"], successfully_locked)
            else:
                error_msg = result.get('error', 'Unknown error')
                if has_api_error:
                    # Extract the specific API error
                    for line in output_text.split('\n'):
                        if any(err in line for err in ["AI_APICallError", "Request body too large"]):
                            error_msg = line.strip()
                            break
                self.task_tracker.update_current_work(self.employee_name, f"❌ opencode execution failed: {error_msg}")
                self._print(f"   ❌ {self.employee_name} opencode execution failed: {error_msg}")
                self._print(f"   💡 Try using a different model with: assign {self.employee_name} '<task>' claude-3.5-sonnet")
                
        except Exception as e:
            self.task_tracker.update_current_work(self.employee_name, f"💥 Session crashed: {str(e)}")
            self._print(f"   💥 {self.employee_name} session crashed: {str(e)}")
        finally:
            self.is_running = False
            self.task_tracker.update_current_work(self.employee_name, "🧹 Cleaning up session and releasing files...")
            self._cleanup_session()
            # Mark task as complete in the task tracker
            self.task_tracker.mark_task_complete(self.employee_name)
    
    def _analyze_task_for_files(self) -> List[str]:
        """Analyze task description to determine what files might be needed"""
        import re
        import os
        files = []
        task_lower = self.task_description.lower()
        
        # Get project root from file manager
        project_root = self.file_manager.get_project_root()
        
        # First, look for explicit file paths in the task description
        # Match patterns like /path/to/file.ext or ./file.ext or file.ext
        file_patterns = [
            r'[/~][\w\-./]+\.\w+',  # Absolute paths like /home/user/file.html
            r'\.[\w\-./]+\.\w+',    # Relative paths like ./file.html
            r'\b[\w\-]+\.\w+\b'     # Simple filenames like file.html
        ]
        
        for pattern in file_patterns:
            matches = re.findall(pattern, self.task_description)
            for match in matches:
                # Check if the file actually exists
                if os.path.isabs(match):
                    # Absolute path - check directly
                    if os.path.exists(match):
                        files.append(match)
                        self._print(f"   📄 Found existing file in task: {match}")
                else:
                    # Relative path - check relative to project root
                    full_path = os.path.join(project_root, match)
                    if os.path.exists(full_path):
                        files.append(match)  # Keep relative path
                        self._print(f"   📄 Found existing file in task: {match} (resolved to {full_path})")
        
        # If we found explicit files, prioritize those
        if files:
            # Filter to only existing files
            existing_files = []
            for file_path in files:
                if os.path.isabs(file_path):
                    # Absolute path - check directly
                    if os.path.exists(file_path):
                        existing_files.append(file_path)
                else:
                    # Relative path - check relative to project root
                    full_path = os.path.join(project_root, file_path)
                    if os.path.exists(full_path):
                        existing_files.append(file_path)
            
            if existing_files:
                return list(set(existing_files))
            # If no existing files found, continue with keyword-based analysis
        
        # Otherwise, fall back to keyword-based analysis
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
        
        # Frontend/HTML related
        if any(word in task_lower for word in ["ui", "frontend", "component", "react", "vue", "html", "css", "background", "style"]):
            files.extend(["src/components/", "src/pages/", "src/views/", "public/", "*.html", "*.css"]) 
        
        # Default files if no specific patterns found
        if not files:
            # Use project root relative paths (only existing files)
            default_files = ["src/main.py", "README.md"]  # Only include files that exist
            # Add other common files if they exist
            for potential_file in ["src/client.py", "src/server.py", "src/config.py"]:
                full_path = os.path.join(project_root, potential_file)
                if os.path.exists(full_path):
                    default_files.append(potential_file)
            files = default_files
        
        # Remove duplicates and return
        return list(set(files))
    
    def _create_enhanced_prompt(self) -> str:
        """Create an enhanced prompt with progress tracking instructions"""
        task_file_path = self.session_dir / "current_task.md"
        
        enhanced_prompt = f"""
🚨 URGENT: YOU MUST UPDATE YOUR TASK FILE {task_file_path} THROUGHOUT THIS WORK! 🚨

EMPLOYEE: {self.employee_name}
ORIGINAL REQUEST: {self.task_description}

CRITICAL REQUIREMENTS - YOU MUST DO THESE:
1. You are an AI employee working on the above task
2. You MUST physically edit and update the file: {task_file_path}
3. Use the 'edit' tool to modify the "## Current Work:" section with what you're doing
4. Use the 'edit' tool to update the "## File Status:" section with percentage complete
5. When you complete work on a file, edit the status to "100% complete (READY TO RELEASE)"

EXAMPLE OF REQUIRED TASK FILE UPDATES:
- When starting: Edit "## Current Work:" to "🔍 Analyzing HTML file structure..."
- When working: Edit "## Current Work:" to "✏️ Adding HTML comment to demonstrate editing capability..."
- When done: Edit file status to "100% complete (READY TO RELEASE)"

FILE LOCKING SYSTEM:
- Files have been pre-locked for you based on the task analysis
- However, if you need additional files, be EXTREMELY SPECIFIC about which ones
- Use FULL ABSOLUTE PATHS when mentioning files (e.g., /home/user/project/src/component.js)
- Only work on files you will actually modify
- If you need to read a file to understand it, mention that clearly
- Example: "I need to modify /home/user/project/index.html to add CSS styles in the <style> section"
- Be specific about what changes you'll make to each file

TASK FILE LOCATION: {task_file_path}
⚠️  THIS FILE ALREADY EXISTS - YOU MUST EDIT IT TO UPDATE YOUR PROGRESS ⚠️

Your task file has these sections you MUST update using the 'edit' tool:
- ## Current Work: (update this frequently with your current activity)
- ## File Status: (update percentages as you work on files)
- ## Progress: (check off completed items)

MANDATORY WORKFLOW - FOLLOW EXACTLY:
1. FIRST: Use 'edit' tool to update {task_file_path} "## Current Work:" section with "🔍 Starting task analysis..."
2. Use 'edit' tool to check off "- [x] Task started" in the Progress section
3. Analyze the task and identify EXACTLY which files you need to modify
4. Use 'edit' tool to update "## Current Work:" with "📋 Planning implementation approach..."
5. Use 'edit' tool to check off "- [x] Files analyzed" in the Progress section
6. Use 'edit' tool to update "## Current Work:" with "✏️ Beginning implementation..."
7. Use 'edit' tool to check off "- [x] Implementation in progress" in the Progress section
8. Complete the actual work on the target files
9. DURING WORK: Use 'edit' tool to update file status percentages (e.g., "50% complete (in progress)")
10. Use 'edit' tool to update "## Current Work:" with "🧪 Testing changes..."
11. Use 'edit' tool to check off "- [x] Testing completed" in the Progress section
12. FINALLY: Use 'edit' tool to mark files as "100% complete (READY TO RELEASE)"
13. Use 'edit' tool to check off "- [x] Ready for review" in the Progress section

YOU MUST USE THE 'edit' TOOL TO UPDATE {task_file_path} AT EACH STEP!

Please complete the original request: {self.task_description}

REMEMBER: 
- Be specific about file paths
- YOU MUST USE THE 'edit' TOOL TO UPDATE {task_file_path} THROUGHOUT THE PROCESS
- Your manager is watching your progress in that file
- Update it frequently so they know you're working!
"""
        return enhanced_prompt.strip()
    
    def _execute_opencode_command(self) -> Dict:
        """Execute the actual opencode command"""
        cmd = ["opencode", "run", "--mode", self.mode]
        
        if self.model:
            cmd.extend(["--model", self.model])
        
        # Create enhanced prompt with progress tracking instructions
        enhanced_prompt = self._create_enhanced_prompt()
        cmd.append(enhanced_prompt)
        
        # Show simplified command for display (the actual prompt is much longer)
        display_cmd = ["opencode", "run", "--mode", self.mode]
        if self.model:
            display_cmd.extend(["--model", self.model])
        display_cmd.append(f"'{self.task_description[:50]}...'")
        self._print(f"   🧠 {self.employee_name} executing: {' '.join(display_cmd)}")
        self._print(f"   📝 Enhanced prompt includes progress tracking instructions")
        
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
                self._print(f"      📝 {self.employee_name} working on {file_path}")
        
        # Look for completion indicators
        if "Task completed" in line or "Done" in line or "Finished" in line:
            for file_path in self.files_locked:
                self.task_tracker.update_file_status(
                    self.employee_name, file_path, 100, "READY TO RELEASE"
                )
            self._print(f"      ✅ {self.employee_name} completed work on all files")
    
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
            self._print(f"      📄 {self.employee_name} modified files: {', '.join(modified_files)}")
            
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
            f.write(f"Task: {self.task_description}\n")  # Full task description in log file
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Files Locked: {', '.join(files_locked)}\n")
            f.write(f"Files Modified: {', '.join(modified_files)}\n")
            f.write("\n--- opencode Output ---\n")
            f.write(output)
    
    def _cleanup_session(self):
        """Clean up session resources"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
        
        # Release locked files when session is stopped/cleaned up
        if self.files_locked:
            released = self.file_manager.release_files(self.employee_name, self.files_locked)
            if released:
                self._print(f"   🔓 {self.employee_name} released files: {', '.join(released)}")
        
        self._print(f"   🧹 {self.employee_name} session {self.session_id} cleaned up")
    
    def stop_session(self):
        """Stop the running session"""
        self.is_running = False
        if self.process and self.process.poll() is None:
            self.process.terminate()
        
        # Release locked files when session is manually stopped
        if self.files_locked:
            released = self.file_manager.release_files(self.employee_name, self.files_locked)
            if released:
                self._print(f"   🔓 {self.employee_name} released files: {', '.join(released)}")
            self.files_locked.clear()
        
        self._print(f"   🛑 Stopped session {self.session_id} for {self.employee_name}")


class OpencodeSessionManager:
    """Manages multiple opencode sessions for different employees"""
    
    def __init__(self, file_manager: FileOwnershipManager, sessions_dir: str = "sessions", quiet_mode: bool = False):
        self.file_manager = file_manager
        self.task_tracker = TaskProgressTracker(sessions_dir)
        self.active_sessions: Dict[str, OpencodeSession] = {}
        self.quiet_mode = quiet_mode
        
    def start_employee_task(self, employee_name: str, task_description: str, 
                           model: Optional[str] = None, mode: str = "build") -> str:
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
            model, mode, self.quiet_mode
        )
        
        session_id = session.start_session()
        self.active_sessions[employee_name] = session
        
        return session_id
    
    def stop_employee_task(self, employee_name: str):
        """Stop an employee's active task"""
        if employee_name in self.active_sessions:
            session = self.active_sessions[employee_name]
            session.stop_session()
            # Ensure cleanup is called
            session._cleanup_session()
            del self.active_sessions[employee_name]
            print(f"✅ Stopped task for {employee_name}")
        else:
            print(f"❌ No active session found for {employee_name}")
    
    def get_active_sessions(self) -> Dict[str, Dict]:
        """Get information about all active sessions"""
        # First, clean up completed sessions
        completed_sessions = []
        for employee_name, session in self.active_sessions.items():
            if not session.is_running and session.thread and not session.thread.is_alive():
                completed_sessions.append(employee_name)
        
        # Remove completed sessions
        for employee_name in completed_sessions:
            print(f"🏁 {employee_name} task completed - removing from active sessions")
            del self.active_sessions[employee_name]
        
        # Return info for remaining active sessions
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
def run_opencode_command(employee_name, task_description, model=None, mode="build"):
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
    print("  opencode run --mode build 'Analyze the user authentication requirements'")
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