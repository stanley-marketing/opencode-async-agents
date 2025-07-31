#!/usr/bin/env python3
"""
CLI Server for opencode-slack system with readline support.
Allows local testing without Slack integration.
"""

import sys
import os
try:
    import readline
    readline_available = True
except ImportError:
    readline_available = False

from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.managers.file_ownership import FileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker
from src.config.logging_config import setup_logging
from src.utils.opencode_wrapper import OpencodeSessionManager

class CLIServer:
    def __init__(self, db_path="employees.db", sessions_dir="sessions"):
        # Configure logging for CLI mode (no console output)
        setup_logging(cli_mode=True)
        
        self.file_manager = FileOwnershipManager(db_path)
        self.task_tracker = TaskProgressTracker(sessions_dir)
        self.session_manager = OpencodeSessionManager(db_path, sessions_dir, quiet_mode=True)
        self.running = True
        self.command_history_file = os.path.expanduser("~/.opencode_slack_history")
        self.load_history()
        print("=== opencode-slack CLI Server ===")
        print("Type 'help' for available commands")
        print("Use ↑/↓ arrows for command history")
        print("Type 'quit' to exit")
        print()

    def load_history(self):
        """Load command history from file"""
        if not readline_available:
            return
            
        try:
            if os.path.exists(self.command_history_file):
                readline.read_history_file(self.command_history_file)
        except:
            pass

    def save_history(self):
        """Save command history to file"""
        if not readline_available:
            return
            
        try:
            readline.write_history_file(self.command_history_file)
        except:
            pass

    def run(self):
        """Main server loop"""
        try:
            while self.running:
                try:
                    command = input("opencode-slack> ").strip()
                    if command:
                        self.handle_command(command)
                except KeyboardInterrupt:
                    print("\nExiting...")
                    self.running = False
                except EOFError:
                    print("\nExiting...")
                    self.running = False
        finally:
            self.save_history()

    def handle_command(self, command_line):
        """Handle a command from the user"""
        import shlex
        try:
            parts = shlex.split(command_line)
        except ValueError as e:
            print(f"Error parsing command: {e}")
            return
        
        if not parts:
            return
            
        command = parts[0].lower()
        
        if command == "help":
            self.show_help()
        elif command == "quit" or command == "exit":
            self.running = False
            print("Goodbye!")
        elif command == "hire":
            self.handle_hire(parts[1:])
        elif command == "fire":
            self.handle_fire(parts[1:])
        elif command == "assign":
            self.handle_assign(parts[1:])
        elif command == "start":
            self.handle_assign(parts[1:])  # start is alias for assign
        elif command == "stop":
            self.handle_stop(parts[1:])
        elif command == "status":
            self.handle_status(parts[1:])
        elif command == "sessions":
            self.handle_sessions(parts[1:])
        elif command == "lock":
            self.handle_lock(parts[1:])
        elif command == "release":
            self.handle_release(parts[1:])
        elif command == "request":
            self.handle_request(parts[1:])
        elif command == "approve":
            self.handle_approve(parts[1:])
        elif command == "deny":
            self.handle_deny(parts[1:])
        elif command == "progress":
            self.handle_progress(parts[1:])
        elif command == "task":
            self.handle_task(parts[1:])
        elif command == "cleanup":
            self.handle_cleanup(parts[1:])
        elif command == "employees":
            self.handle_employees(parts[1:])
        elif command == "files":
            self.handle_files(parts[1:])
        elif command == "clear":
            self.handle_clear(parts[1:])
        elif command == "history":
            self.handle_history(parts[1:])
        else:
            print(f"Unknown command: {command}")
            print("Type 'help' for available commands")

    def show_help(self):
        """Show available commands"""
        print("🔥 REAL OPENCODE EMPLOYEE SYSTEM - Available commands:")
        print("  hire <name> <role>              - Hire a new employee")
        print("  fire <name>                     - Fire an employee")
        print("  assign <name> '<task>' [model]  - Assign REAL opencode task to employee")
        print("  start <name> '<task>' [model]  - Start employee working on task")
        print("  stop <name>                     - Stop employee's opencode session")
        print("  status                          - Show comprehensive system status")
        print("  sessions                        - Show active opencode sessions")
        print("  lock <name> <files> <desc>      - Lock files for work")
        print("  release <name> [files]          - Release files (all if none specified)")
        print("  request <name> <file> <desc>    - Request a file from another employee")
        print("  approve <request_id>            - Approve a file request")
        print("  deny <request_id>               - Deny a file request")
        print("  progress [name]                 - Show progress for employee (or all)")
        print("  task <name>                     - Show current task file for employee")
        print("  cleanup                         - Clean up completed sessions")
        print("  employees                       - List all employees and their status")
        print("  files [name]                    - Show locked files (for employee or all)")
        print("  history                         - Show command history")
        print("  clear                           - Clear the screen")
        print("  help                            - Show this help")
        print("  quit                            - Exit the server")
        print()
        print("🚀 Examples:")
        print("  assign sarah 'implement user authentication'")
        print("  assign dev-2 'create API endpoints' claude-3.5")
        print("  status  # See complete system overview")

    def handle_assign(self, args):
        """Handle assign command - now with REAL opencode sessions"""
        if len(args) < 2:
            print("Usage: assign <name> <task_description> [model] [mode]")
            print("Example: assign sarah 'implement user auth' openrouter/qwen/qwen3-coder build")
            return
        
        name = args[0]
        task_description = args[1]
        model = args[2] if len(args) > 2 else "openrouter/qwen/qwen3-coder"
        mode = args[3] if len(args) > 3 else "build"
        
        # Make sure employee exists
        employees = self.file_manager.list_employees()
        employee_names = [emp['name'] for emp in employees]
        
        if name not in employee_names:
            print(f"Employee {name} not found. Hiring as developer...")
            if not self.file_manager.hire_employee(name, "developer"):
                print(f"Failed to hire {name}")
                return
            print(f"✅ Hired {name} as developer")
        
        # Start real opencode session with callback to reprint prompt
        session_id = self.session_manager.start_employee_task(
            name, task_description, model, mode
        )
        
        if session_id:
            print(f"🚀 Started REAL opencode session for {name}")
            print(f"📋 Session ID: {session_id}")
            print("   (Task running in background - use 'status' to check progress)")
        else:
            print(f"❌ Failed to start opencode session for {name}")
    
    def handle_stop(self, args):
        """Handle stop command - stop an employee's opencode session"""
        if len(args) < 1:
            print("Usage: stop <name>")
            return
        
        name = args[0]
        self.session_manager.stop_employee_task(name)
    
    def handle_status(self, args):
        """Handle status command - show comprehensive system status"""
        print("📊 SYSTEM STATUS OVERVIEW")
        print("=" * 50)
        
        # Show active sessions
        active_sessions = self.session_manager.get_active_sessions()
        if active_sessions:
            print("\n🔥 ACTIVE SESSIONS:")
            for employee_name, session_info in active_sessions.items():
                status = "🔥 RUNNING" if session_info['is_running'] else "⏸️  PAUSED"
                print(f"  👤 {employee_name} - {status}")
                print(f"     🧠 Task: {session_info['task'][:60]}{'...' if len(session_info['task']) > 60 else ''}")
                if session_info['files_locked']:
                    locked_files = session_info['files_locked'][:3]
                    more_files = len(session_info['files_locked']) - 3
                    files_display = ', '.join(locked_files)
                    if more_files > 0:
                        files_display += f" (+{more_files} more)"
                    print(f"     🔒 Files: {files_display}")
        else:
            print("\n✅ No active sessions")
        
        # Show file locks
        all_files = self.file_manager.get_all_locked_files()
        if all_files:
            print("\n📁 LOCKED FILES:")
            for file_info in all_files:
                print(f"  🔒 {file_info['file_path']} - locked by {file_info['employee_name']}")
                if file_info['task_description']:
                    print(f"     📝 Task: {file_info['task_description'][:60]}{'...' if len(file_info['task_description']) > 60 else ''}")
        else:
            print("\n🔓 No files currently locked")
        
        # Show pending requests
        pending_requests = self.file_manager.get_pending_requests()
        if pending_requests:
            print("\n📬 PENDING REQUESTS:")
            for req in pending_requests:
                print(f"  📨 Request #{req['id']}: {req['requesting_employee']} wants {req['file_path']}")
                print(f"     👤 From: {req['requesting_employee']} | To: {req['locked_by_employee']}")
                print(f"     📝 Reason: {req['task_description']}")
        else:
            print("\n📭 No pending requests")
        
        # Show all employees
        employees = self.file_manager.list_employees()
        if employees:
            print(f"\n👥 ALL EMPLOYEES ({len(employees)} total):")
            for emp in employees:
                files = self.file_manager.get_employee_files(emp['name'])
                if files:
                    file_count = len(files)
                    print(f"  👤 {emp['name']} ({emp['role']}) - {file_count} files locked")
                else:
                    print(f"  👤 {emp['name']} ({emp['role']}) - Available")
        else:
            print("\n👥 No employees hired")
        
        print("\n" + "=" * 50)
    
    def handle_sessions(self, args):
        """Handle sessions command - show active opencode sessions"""
        active_sessions = self.session_manager.get_active_sessions()
        
        if not active_sessions:
            print("No active opencode sessions")
            return
        
        print("🔥 Active opencode sessions:")
        for employee_name, session_info in active_sessions.items():
            status = "🔥 RUNNING" if session_info['is_running'] else "⏸️  PAUSED"
            print(f"  👤 {employee_name} - {status}")
            print(f"     🧠 Task: {session_info['task']}")
            print(f"     📋 Session: {session_info['session_id']}")
            if session_info['files_locked']:
                print(f"     🔒 Files: {', '.join(session_info['files_locked'])}")

    def _analyze_task_for_files(self, task_description):
        """
        Simple analysis to determine what files are needed for a task.
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

    def handle_history(self, args):
        """Handle history command"""
        if not readline_available:
            print("History not available (readline not installed)")
            return
            
        try:
            history_len = readline.get_current_history_length()
            start_index = max(1, history_len - 10)  # Show last 10 commands
            print("Recent commands:")
            for i in range(start_index, history_len + 1):
                cmd = readline.get_history_item(i)
                if cmd:
                    print(f"  {i:2d}. {cmd}")
        except:
            print("History not available")

    def handle_hire(self, args):
        """Handle hire command"""
        if len(args) < 2:
            print("Usage: hire <name> <role>")
            return
        
        name = args[0]
        role = " ".join(args[1:])
        
        if self.file_manager.hire_employee(name, role):
            print(f"✅ Successfully hired {name} as a {role}!")
            # Show updated employee count
            employees = self.file_manager.list_employees()
            print(f"📊 Total employees: {len(employees)}")
        else:
            print(f"❌ Failed to hire {name}. Employee may already exist.")

    def handle_fire(self, args):
        """Handle fire command"""
        if len(args) < 1:
            print("Usage: fire <name>")
            return
        
        name = args[0]
        
        # Stop any active sessions first
        if name in self.session_manager.active_sessions:
            self.session_manager.stop_employee_task(name)
        
        if self.file_manager.fire_employee(name, self.session_manager.task_tracker):
            print(f"✅ Successfully fired {name} and cleaned up their session data.")
        else:
            print(f"❌ Failed to fire {name}. Employee may not exist.")

    def handle_lock(self, args):
        """Handle lock command"""
        if len(args) < 3:
            print("Usage: lock <name> <file1,file2,...> <description>")
            return
        
        name = args[0]
        files_str = args[1]
        description = " ".join(args[2:])
        
        files = [f.strip() for f in files_str.split(",")]
        
        result = self.file_manager.lock_files(name, files, description)
        
        # Create task file
        self.task_tracker.create_task_file(name, description, files)
        
        print(f"Files locked for {name}:")
        for file_path, status in result.items():
            print(f"  - {file_path}: {status}")
        
        if any("locked" in status for status in result.values()):
            print("✅ Files locked successfully!")

    def handle_release(self, args):
        """Handle release command"""
        if len(args) < 1:
            print("Usage: release <name> [files]")
            return
        
        name = args[0]
        
        if len(args) == 1:
            # Release all files
            released = self.file_manager.release_files(name)
            if released:
                print(f"✅ Released all files for {name}: {', '.join(released)}")
            else:
                print(f"❌ No files to release for {name}")
        else:
            # Release specific files
            files = args[1:]
            released = self.file_manager.release_files(name, files)
            if released:
                print(f"✅ Released files for {name}: {', '.join(released)}")
            else:
                print(f"❌ No files released for {name}")

    def handle_request(self, args):
        """Handle request command"""
        if len(args) < 3:
            print("Usage: request <name> <file> <reason>")
            return
        
        requester = args[0]
        file_path = args[1]
        reason = " ".join(args[2:])
        
        result = self.file_manager.request_file(requester, file_path, reason)
        
        if result == "file_not_locked":
            print(f"❌ File {file_path} is not currently locked by anyone.")
        elif result == "already_owner":
            print(f"✅ You already own {file_path}.")
        elif result.startswith("request_sent_to_"):
            owner = result.replace("request_sent_to_", "")
            print(f"✅ File request sent to {owner} for {file_path}. Reason: {reason}")
        else:
            print(f"❌ Unexpected error requesting {file_path}.")

    def handle_approve(self, args):
        """Handle approve command"""
        if len(args) < 1:
            print("Usage: approve <request_id>")
            return
        
        try:
            request_id = int(args[0])
        except ValueError:
            print("❌ Request ID must be a number")
            return
        
        if self.file_manager.approve_request(request_id):
            print(f"✅ Request {request_id} approved successfully!")
        else:
            print(f"❌ Failed to approve request {request_id}. It may not exist or already be processed.")

    def handle_deny(self, args):
        """Handle deny command"""
        if len(args) < 1:
            print("Usage: deny <request_id>")
            return
        
        try:
            request_id = int(args[0])
        except ValueError:
            print("❌ Request ID must be a number")
            return
        
        if self.file_manager.deny_request(request_id):
            print(f"✅ Request {request_id} denied successfully!")
        else:
            print(f"❌ Failed to deny request {request_id}. It may not exist or already be processed.")

    def handle_progress(self, args):
        """Handle progress command"""
        if len(args) == 0:
            # Show progress for all employees
            employees = self.file_manager.list_employees()
            if not employees:
                print("❌ No employees found.")
                return
            
            print("Employee Progress:")
            for employee in employees:
                name = employee['name']
                progress = self.task_tracker.get_task_progress(name)
                if progress:
                    print(f"  {name}: {progress['overall_progress']}% complete")
                else:
                    print(f"  {name}: No progress data")
        else:
            # Show progress for specific employee
            name = args[0]
            progress = self.task_tracker.get_task_progress(name)
            if progress:
                print(f"Progress for {name}:")
                print(f"  Task: {progress['task_description']}")
                print(f"  Overall Progress: {progress['overall_progress']}%")
                print(f"  Files ready to release: {', '.join(progress['ready_to_release']) if progress['ready_to_release'] else 'None'}")
                print(f"  Still working on: {', '.join(progress['still_working_on']) if progress['still_working_on'] else 'None'}")
            else:
                print(f"❌ No progress found for {name}")

    def handle_task(self, args):
        """Handle task command - show current task file content"""
        if len(args) < 1:
            print("Usage: task <employee_name>")
            return
        
        name = args[0]
        task_file = f"sessions/{name}/current_task.md"
        
        try:
            with open(task_file, 'r') as f:
                content = f.read()
            print(f"📋 Current task file for {name}:")
            print("=" * 50)
            print(content)
            print("=" * 50)
        except FileNotFoundError:
            print(f"❌ No task file found for {name}")
        except Exception as e:
            print(f"❌ Error reading task file: {e}")

    def handle_cleanup(self, args):
        """Handle cleanup command - clean up completed sessions"""
        print("🧹 Cleaning up completed sessions...")
        # This will trigger the cleanup in get_active_sessions
        active = self.session_manager.get_active_sessions()
        print(f"✅ Active sessions remaining: {len(active)}")

    def handle_employees(self, args):
        """Handle employees command"""
        employees = self.file_manager.list_employees()
        if not employees:
            print("❌ No employees found.")
            return
        
        print("Employees:")
        for employee in employees:
            print(f"  - {employee['name']} ({employee['role']})")

    def handle_files(self, args):
        """Handle files command"""
        if len(args) == 0:
            # Show all locked files
            employees = self.file_manager.list_employees()
            if not employees:
                print("❌ No employees found.")
                return
            
            print("Locked Files:")
            for employee in employees:
                files = self.file_manager.get_employee_files(employee['name'])
                if files:
                    print(f"  {employee['name']}:")
                    for file_info in files:
                        print(f"    - {file_info['file_path']} ({file_info['task_description']})")
                else:
                    print(f"❌ No files locked by {employee['name']}")

    def handle_clear(self, args):
        """Handle clear command - clear the screen"""
        import os
        os.system("clear" if os.name == "posix" else "cls")
        print("=== opencode-slack CLI Server ===")
        print("Type 'help' for available commands")
        print("Use ↑/↓ arrows for command history")
        print("Type 'quit' to exit")
        print()

def main():
    """Main function"""
    server = CLIServer()
    server.run()

if __name__ == "__main__":
    main()
