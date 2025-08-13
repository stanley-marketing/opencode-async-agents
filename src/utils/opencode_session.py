# SPDX-License-Identifier: MIT
#!/usr/bin/env python3
"""
opencode session management for the opencode-slack system.
"""

from pathlib import Path
from typing import Dict, List, Optional
import json
import os
import subprocess
import sys
import time

class OpencodeSession:
    def __init__(self, employee_name: str, session_dir: str = "sessions"):
        self.employee_name = employee_name
        self.session_dir = os.path.join(session_dir, employee_name)
        self.session_file = os.path.join(self.session_dir, "opencode_session.json")
        self.log_file = os.path.join(self.session_dir, "opencode_output.log")
        self.ensure_session_dir()

    def ensure_session_dir(self):
        """Ensure the session directory exists"""
        os.makedirs(self.session_dir, exist_ok=True)

    def run_task(self, task_description: str, model: str = "openrouter/google/gemini-2.5-pro") -> Dict:
        """
        Run an opencode task for this employee.

        Args:
            task_description: Description of the task to run
            model: AI model to use (optional)

        Returns:
            Dict with results of the opencode execution
        """
        print(f"🤖 {self.employee_name} starting opencode task: {task_description}")

        # Build the opencode command
        cmd = [
            "opencode", "run",
            "--model", model,
            "--mode", "plan",
            task_description
        ]

        print(f"   🧠 Running: {' '.join(cmd)}")

        try:
            # Run the command and capture output
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=self.session_dir
            )

            # Save output to log file
            with open(self.log_file, 'a') as f:
                f.write(f"\n=== Task: {task_description} ===\n")
                f.write(f"Command: {' '.join(cmd)}\n")
                f.write(f"Return code: {result.returncode}\n")
                f.write(f"STDOUT:\n{result.stdout}\n")
                f.write(f"STDERR:\n{result.stderr}\n")
                f.write("="*50 + "\n")

            # Parse the output to determine what files were affected
            files_affected = self._parse_affected_files(result.stdout, result.stderr)

            # Save session state
            self._save_session_state({
                'task': task_description,
                'command': ' '.join(cmd),
                'return_code': result.returncode,
                'files_affected': files_affected,
                'last_run': time.time()
            })

            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'files_affected': files_affected,
                'return_code': result.returncode
            }

        except subprocess.TimeoutExpired:
            error_msg = f"opencode command timed out after 5 minutes"
            with open(self.log_file, 'a') as f:
                f.write(f"\n=== Task: {task_description} ===\n")
                f.write(f"ERROR: {error_msg}\n")
                f.write("="*50 + "\n")

            return {
                'success': False,
                'error': error_msg,
                'stdout': '',
                'stderr': 'Command timed out',
                'files_affected': []
            }

        except Exception as e:
            error_msg = f"Error running opencode command: {str(e)}"
            with open(self.log_file, 'a') as f:
                f.write(f"\n=== Task: {task_description} ===\n")
                f.write(f"ERROR: {error_msg}\n")
                f.write("="*50 + "\n")

            return {
                'success': False,
                'error': error_msg,
                'stdout': '',
                'stderr': str(e),
                'files_affected': []
            }

    def _parse_affected_files(self, stdout: str, stderr: str) -> List[str]:
        """
        Parse opencode output to determine what files were affected.
        This is a simple implementation - in reality, you'd want to parse
        the actual file operations from the output.
        """
        files = []

        # Simple keyword-based file detection
        output = (stdout + stderr).lower()

        if 'src/' in output or 'source' in output:
            files.extend(['src/main.py', 'src/utils.py'])

        if 'auth' in output or 'authentication' in output:
            files.extend(['src/auth.py', 'src/user.py'])

        if 'api' in output or 'endpoint' in output:
            files.extend(['src/api.py', 'src/routes.py'])

        if 'database' in output or 'db' in output:
            files.extend(['src/database.py', 'src/models.py'])

        if 'test' in output:
            files.extend(['tests/test_main.py'])

        return list(set(files))  # Remove duplicates

    def _save_session_state(self, state: Dict):
        """Save session state to JSON file"""
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r') as f:
                    existing_state = json.load(f)
                existing_state.update(state)
            else:
                existing_state = state

            with open(self.session_file, 'w') as f:
                json.dump(existing_state, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save session state: {e}")

    def get_session_state(self) -> Optional[Dict]:
        """Get the current session state"""
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return None

    def get_recent_output(self) -> str:
        """Get recent opencode output"""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    return f.read()
            except:
                pass
        return ""

def demo_opencode_session():
    """Demo the opencode session functionality"""
    print("=== opencode Session Demo ===")

    # Create a session for sarah
    session = OpencodeSession("sarah")

    # Run a simple task
    result = session.run_task("Analyze the user authentication requirements")

    if result['success']:
        print(f"✅ Task completed successfully!")
        print(f"   Files affected: {result['files_affected']}")
    else:
        print(f"❌ Task failed: {result.get('error', 'Unknown error')}")

    # Show session state
    state = session.get_session_state()
    if state:
        print(f"Session state: {state}")

if __name__ == "__main__":
    demo_opencode_session()