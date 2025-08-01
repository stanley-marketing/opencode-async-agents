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
from src.chat.telegram_manager import TelegramManager
from src.agents.agent_manager import AgentManager
from src.bridge.agent_bridge import AgentBridge
from src.config.models_config import models_config

class CLIServer:
    def __init__(self, db_path="employees.db", sessions_dir="sessions"):
        # Load environment variables first
        try:
            from dotenv import load_dotenv
            from pathlib import Path
            env_path = Path(__file__).parent.parent / '.env'
            if env_path.exists():
                load_dotenv(env_path)
                print(f"📄 Loaded .env from {env_path}")
            else:
                load_dotenv()  # Try current directory
        except ImportError:
            print("⚠️  Install python-dotenv: pip install python-dotenv")
        except Exception as e:
            print(f"⚠️  Could not load .env: {e}")
        
        # Configure logging for CLI mode (no console output)
        setup_logging(cli_mode=True)
        
        self.file_manager = FileOwnershipManager(db_path)
        self.task_tracker = TaskProgressTracker(sessions_dir)
        self.session_manager = OpencodeSessionManager(db_path, sessions_dir, quiet_mode=True)
        
        # Initialize chat system
        self.telegram_manager = TelegramManager()
        self.agent_manager = AgentManager(self.file_manager, self.telegram_manager)
        self.agent_bridge = AgentBridge(self.session_manager, self.agent_manager)
        self.chat_enabled = False
        self.running = True
        
        self.command_history_file = os.path.expanduser("~/.opencode_slack_history")
        self.load_history()
        self._setup_autocomplete()
        print("=== opencode-slack CLI Server ===")
        print("Type 'help' for available commands")
        print("Use ↑/↓ arrows for command history")
        print("Use TAB for command completion")
        print("Type 'quit' to exit")
        print()
        
        # Auto-start chat system if configured (after initial setup)
        self._auto_start_chat_if_configured()
    
    def _auto_start_chat_if_configured(self):
        """Auto-start chat system if properly configured"""
        from src.chat.chat_config import config
        
        if config.is_configured():
            try:
                self.telegram_manager.start_polling()
                self.agent_bridge.start_monitoring()
                self.chat_enabled = True
                print("🚀 Chat system auto-started!")
                print(f"👥 {len(self.agent_manager.agents)} communication agents ready")
                print("💬 Employees can now be mentioned in the Telegram group")
            except Exception as e:
                print(f"⚠️  Failed to auto-start chat system: {e}")
                print("   Use 'chat-start' to start manually")
        else:
            print("💬 Chat system not configured (set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)")
            print("   See TELEGRAM_SETUP.md for setup instructions")

    def load_history(self):
        """Load command history from file"""
        if not readline_available:
            return
            
        try:
            if os.path.exists(self.command_history_file):
                readline.read_history_file(self.command_history_file)
        except:
            pass

    def _setup_autocomplete(self):
        """Set up command autocompletion using readline"""
        if not readline_available:
            return
            
        # List of available commands for autocompletion
        self.commands = [
            'help', 'quit', 'exit', 'hire', 'fire', 'assign', 'start', 'stop',
            'status', 'sessions', 'lock', 'release', 'request', 'approve',
            'deny', 'progress', 'task', 'cleanup', 'chat', 'chat-start',
            'chat-stop', 'chat-status', 'agents', 'bridge', 'employees',
            'files', 'clear', 'history', 'models', 'model-set', 'hire-specialist',
            'monitor', 'monitor-dashboard'
        ]
        
        # Set up readline completion
        readline.set_completer(self._autocomplete)
        readline.parse_and_bind("tab: complete")

    def _autocomplete(self, text, state):
        """Autocomplete function for readline"""
        if state == 0:
            # This is the first time calling autocomplete for this text
            line = readline.get_line_buffer()
            words = line.split()
            
            # Check if we're at the end of the line with a space
            ends_with_space = line.endswith(' ')
            
            # If we're at the beginning of the line
            if not words:
                self.matches = self.commands[:]
            elif len(words) == 1 and not ends_with_space:
                # Autocomplete command names
                self.matches = [cmd for cmd in self.commands if cmd.startswith(text)]
            else:
                # Autocomplete command arguments based on the command
                command = words[0].lower()
                self.matches = self._get_command_args_autocomplete(command, words, text, ends_with_space)
        
        # Return the match for the current state, or None if no more matches
        try:
            return self.matches[state]
        except IndexError:
            return None

    def _get_command_args_autocomplete(self, command, words, text, ends_with_space=False):
        """Get autocomplete suggestions for command arguments"""
        try:
            if command in ['hire']:
                # hire <name> <role> [smartness]
                if len(words) == 1 and ends_with_space:
                    # After "hire " - need name
                    return [text] if text else ['']
                elif len(words) == 2 and not ends_with_space:
                    # Typing name
                    return [text] if text else ['']
                elif (len(words) == 2 and ends_with_space) or (len(words) == 3 and not ends_with_space):
                    # After "hire name " - need role
                    roles = ['developer', 'analyst', 'pm', 'qa', 'devops', 'designer']
                    if not text:
                        return roles[:]
                    else:
                        return [role for role in roles if role.startswith(text)]
                elif (len(words) == 3 and ends_with_space) or (len(words) == 4 and not ends_with_space):
                    # After "hire name role " - need smartness
                    smartness_levels = ['smart', 'normal']
                    if not text:
                        return smartness_levels[:]
                    else:
                        return [level for level in smartness_levels if level.startswith(text)]
            elif command in ['fire', 'assign', 'start', 'stop', 'progress', 'task']:
                # These commands need employee names
                if len(words) == 1 and ends_with_space:
                    # After "fire " - need employee name
                    employees = self.file_manager.list_employees()
                    employee_names = [emp['name'] for emp in employees]
                    if not text:
                        return employee_names[:]
                    else:
                        return [name for name in employee_names if name.startswith(text)]
                elif len(words) == 2 and not ends_with_space:
                    # Typing employee name
                    employees = self.file_manager.list_employees()
                    employee_names = [emp['name'] for emp in employees]
                    if not text:
                        return employee_names[:]
                    else:
                        return [name for name in employee_names if name.startswith(text)]
            elif command in ['lock']:
                # lock <name> <files> <desc>
                if len(words) == 1 and ends_with_space:
                    # After "lock " - need employee name
                    employees = self.file_manager.list_employees()
                    employee_names = [emp['name'] for emp in employees]
                    if not text:
                        return employee_names[:]
                    else:
                        return [name for name in employee_names if name.startswith(text)]
                elif len(words) == 2 and not ends_with_space:
                    # Typing employee name
                    employees = self.file_manager.list_employees()
                    employee_names = [emp['name'] for emp in employees]
                    if not text:
                        return employee_names[:]
                    else:
                        return [name for name in employee_names if name.startswith(text)]
                elif len(words) == 2 and ends_with_space:
                    # After "lock name " - need files
                    common_files = [
                        'src/main.py', 'src/utils.py', 'src/auth.py', 'src/user.py',
                        'src/api.py', 'src/database.py', 'src/models.py', 'tests/test_main.py',
                        'config/settings.py', 'docs/README.md'
                    ]
                    if not text:
                        return common_files[:]
                    else:
                        return [f for f in common_files if f.startswith(text)]
            elif command in ['release']:
                # release <name> [files]
                if len(words) == 1 and ends_with_space:
                    # After "release " - need employee name
                    employees = self.file_manager.list_employees()
                    employee_names = [emp['name'] for emp in employees]
                    if not text:
                        return employee_names[:]
                    else:
                        return [name for name in employee_names if name.startswith(text)]
                elif len(words) == 2 and not ends_with_space:
                    # Typing employee name
                    employees = self.file_manager.list_employees()
                    employee_names = [emp['name'] for emp in employees]
                    if not text:
                        return employee_names[:]
                    else:
                        return [name for name in employee_names if name.startswith(text)]
                elif len(words) == 2 and ends_with_space:
                    # After "release name " - need files
                    if len(words) > 1:
                        employee_name = words[1]
                        locked_files = self.file_manager.get_employee_files(employee_name)
                        file_paths = [f['file_path'] for f in locked_files]
                        if not text:
                            return file_paths[:]
                        else:
                            return [f for f in file_paths if f.startswith(text)]
            elif command in ['request']:
                # request <name> <file> <desc>
                if len(words) == 1 and ends_with_space:
                    # After "request " - need requester name
                    employees = self.file_manager.list_employees()
                    employee_names = [emp['name'] for emp in employees]
                    if not text:
                        return employee_names[:]
                    else:
                        return [name for name in employee_names if name.startswith(text)]
                elif len(words) == 2 and not ends_with_space:
                    # Typing requester name
                    employees = self.file_manager.list_employees()
                    employee_names = [emp['name'] for emp in employees]
                    if not text:
                        return employee_names[:]
                    else:
                        return [name for name in employee_names if name.startswith(text)]
                elif len(words) == 2 and ends_with_space:
                    # After "request name " - need file
                    common_files = [
                        'src/main.py', 'src/utils.py', 'src/auth.py', 'src/user.py',
                        'src/api.py', 'src/database.py', 'src/models.py'
                    ]
                    if not text:
                        return common_files[:]
                    else:
                        return [f for f in common_files if f.startswith(text)]
            elif command in ['approve', 'deny']:
                # approve/deny <request_id>
                if len(words) == 1 and ends_with_space:
                    # After "approve " or "deny " - need request ID
                    pending_requests = self.file_manager.get_pending_requests()
                    request_ids = [str(req['id']) for req in pending_requests]
                    if not text:
                        return request_ids[:]
                    else:
                        return [req_id for req_id in request_ids if req_id.startswith(text)]
                elif len(words) == 2 and not ends_with_space:
                    # Typing request ID
                    pending_requests = self.file_manager.get_pending_requests()
                    request_ids = [str(req['id']) for req in pending_requests]
                    if not text:
                        return request_ids[:]
                    else:
                        return [req_id for req_id in request_ids if req_id.startswith(text)]
            elif command in ['model-set']:
                # model-set <level> <model>
                if len(words) == 1 and ends_with_space:
                    # After "model-set " - need level
                    levels = ['smart', 'normal']
                    if not text:
                        return levels[:]
                    else:
                        return [level for level in levels if level.startswith(text)]
                elif len(words) == 2 and not ends_with_space:
                    # Typing level
                    levels = ['smart', 'normal']
                    if not text:
                        return levels[:]
                    else:
                        return [level for level in levels if level.startswith(text)]
        except Exception:
            # If there's any error, return empty list to avoid breaking the CLI
            pass
            
        # Default: return empty list for no specific autocomplete
        return []

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
        elif command == "hire-specialist":
            self.handle_hire_specialist(parts[1:])
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
        elif command == "chat":
            self.handle_chat(parts[1:])
        elif command == "chat-start":
            self.handle_chat_start(parts[1:])
        elif command == "chat-stop":
            self.handle_chat_stop(parts[1:])
        elif command == "chat-status":
            self.handle_chat_status(parts[1:])
        elif command == "agents":
            self.handle_agents(parts[1:])
        elif command == "bridge":
            self.handle_bridge(parts[1:])
        elif command == "employees":
            self.handle_employees(parts[1:])
        elif command == "files":
            self.handle_files(parts[1:])
        elif command == "clear":
            self.handle_clear(parts[1:])
        elif command == "history":
            self.handle_history(parts[1:])
        elif command == "models":
            self.handle_models(parts[1:])
        elif command == "model-set":
            self.handle_model_set(parts[1:])
        elif command == "monitor" or command == "monitor-dashboard":
            self.handle_monitor(parts[1:])
        else:
            print(f"Unknown command: {command}")
            print("Type 'help' for available commands")

    def show_help(self):
        """Show available commands"""
        print("🔥 REAL OPENCODE EMPLOYEE SYSTEM - Available commands:")
        print("  hire <name> <role> [smartness]  - Hire a new employee (smartness: smart|normal)")
        print("  hire-specialist <category>      - Hire a specialized employee from a specific category")
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
        print("  models                          - Show configured models")
        print("  model-set <level> <model>       - Set model for smartness level")
        print("")
        print("🔥 CHAT COMMANDS:")
        print("  chat <message>                  - Send message to Telegram group")
        print("  chat-start                      - Start Telegram chat system")
        print("  chat-stop                       - Stop Telegram chat system")
        print("  chat-status                     - Show chat system status")
        print("  agents                          - Show communication agents status")
        print("  bridge                          - Show agent bridge status")
        print("  employees                       - List all employees and their status")
        print("  files [name]                    - Show locked files (for employee or all)")
        print("  history                         - Show command history")
        print("  clear                           - Clear the screen")
        print("  monitor                         - Show agent monitoring dashboard")
        print("  monitor-dashboard               - Interactive monitoring dashboard")
        print("  help                            - Show this help")
        print("  quit                            - Exit the server")
        print()
        print("🤖 SMARTNESS LEVELS:")
        print("  Employees can be hired with two smartness levels:")
        print("    - smart: High-performance models for complex planning")
        print("    - normal: Efficient models for code writing")
        print("  Models are automatically selected based on employee's smartness level")
        print()
        print("🚀 Examples:")
        print("  hire sarah developer smart      - Hire smart developer")
        print("  assign sarah 'implement user authentication'")
        print("  assign dev-2 'create API endpoints' claude-3.5")
        print("  model-set smart openrouter/anthropic/claude-3.5-sonnet")
        print("  status  # See complete system overview")

    def handle_assign(self, args):
        """Handle assign command - now with REAL opencode sessions"""
        if len(args) < 2:
            print("Usage: assign <name> <task_description> [model] [mode]")
            print("Example: assign sarah 'implement user auth' openrouter/qwen/qwen3-coder build")
            return
        
        name = args[0]
        task_description = args[1]
        model = args[2] if len(args) > 2 else None  # Use employee's default model if not specified
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
            print("Usage: hire <name> <role> [smartness]")
            print("Smartness levels: smart | normal")
            return
        
        name = args[0]
        role = args[1]
        smartness = args[2] if len(args) > 2 else "normal"  # default to normal
        
        # Validate smartness level
        if smartness not in ["smart", "normal"]:
            print("Invalid smartness level. Use 'smart' or 'normal'. Defaulting to 'normal'.")
            smartness = "normal"
        
        if self.file_manager.hire_employee(name, role, smartness):
            print(f"✅ Successfully hired {name} as a {role} ({smartness} smartness)!")
            
            # Create communication agent
            expertise = self.agent_manager._get_expertise_for_role(role)
            self.agent_manager.create_agent(name, role, expertise)
            
            # Show updated employee count
            employees = self.file_manager.list_employees()
            print(f"📊 Total employees: {len(employees)}")
            print(f"🤖 Communication agent created for {name}")
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
        
        # Remove communication agent
        self.agent_manager.remove_agent(name)
        
        if self.file_manager.fire_employee(name, self.session_manager.task_tracker):
            print(f"✅ Successfully fired {name} and cleaned up their session data.")
            print(f"🤖 Communication agent removed for {name}")
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

    def handle_chat(self, args):
        """Handle chat command - send message to Telegram group"""
        if not args:
            print("Usage: chat <message>")
            return
        
        message = " ".join(args)
        
        if not self.telegram_manager.is_connected():
            print("❌ Chat system not connected. Use 'chat-start' first.")
            return
        
        success = self.telegram_manager.send_message(message, "system")
        if success:
            print(f"✅ Message sent to chat: {message}")
        else:
            print("❌ Failed to send message")

    def handle_chat_start(self, args):
        """Handle chat-start command"""
        if self.chat_enabled:
            print("✅ Chat system is already running")
            return
        
        from src.chat.chat_config import config
        if not config.is_configured():
            print("❌ Chat system not configured.")
            print("Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables.")
            print("See TELEGRAM_SETUP.md for instructions.")
            return
        
        try:
            self.telegram_manager.start_polling()
            self.agent_bridge.start_monitoring()
            self.chat_enabled = True
            print("🚀 Chat system started!")
            print("💬 Employees can now be mentioned in the Telegram group")
            print("🔄 Task monitoring active")
        except Exception as e:
            print(f"❌ Failed to start chat system: {e}")

    def handle_chat_stop(self, args):
        """Handle chat-stop command"""
        if not self.chat_enabled:
            print("❌ Chat system is not running")
            return
        
        self.telegram_manager.stop_polling()
        self.chat_enabled = False
        print("🛑 Chat system stopped")

    def handle_chat_status(self, args):
        """Handle chat-status command"""
        from src.chat.chat_config import config
        
        print("📊 CHAT SYSTEM STATUS")
        print("=" * 50)
        
        # Configuration status
        print(f"🔧 Configuration: {'✅ Ready' if config.is_configured() else '❌ Not configured'}")
        print(f"🤖 Bot Token: {'✅ Set' if config.bot_token else '❌ Missing'}")
        print(f"💬 Chat ID: {'✅ Set' if config.chat_id else '❌ Missing'}")
        
        # Connection status
        connected = self.telegram_manager.is_connected()
        print(f"🌐 Connection: {'✅ Connected' if connected else '❌ Disconnected'}")
        print(f"🔄 Polling: {'✅ Active' if self.chat_enabled else '❌ Stopped'}")
        
        # Agent statistics
        stats = self.agent_manager.get_chat_statistics()
        print(f"👥 Total Agents: {stats['total_agents']}")
        print(f"🔥 Working: {stats['working_agents']}")
        print(f"😴 Idle: {stats['idle_agents']}")
        print(f"🆘 Stuck: {stats['stuck_agents']}")
        print(f"📬 Pending Help Requests: {stats['pending_help_requests']}")

    def handle_agents(self, args):
        """Handle agents command - show communication agents status"""
        agents_status = self.agent_manager.get_agent_status()
        
        if not agents_status:
            print("❌ No communication agents found")
            return
        
        print("👥 COMMUNICATION AGENTS STATUS")
        print("=" * 50)
        
        for name, status in agents_status.items():
            print(f"👤 {name} ({status['role']})")
            print(f"   Status: {status['worker_status']}")
            print(f"   Expertise: {', '.join(status['expertise'])}")
            if status['current_task']:
                print(f"   Current Task: {status['current_task'][:50]}...")
            if status['active_tasks']:
                print(f"   Active Tasks: {len(status['active_tasks'])}")
            if status['last_response']:
                print(f"   Last Response: {status['last_response']}")
            print()

    def handle_bridge(self, args):
        """Handle bridge command - show agent bridge status"""
        bridge_status = self.agent_bridge.get_bridge_status()
        
        print("🌉 AGENT BRIDGE STATUS")
        print("=" * 50)
        print(f"🔄 Active Tasks: {bridge_status['active_tasks']}")
        print(f"⏰ Stuck Timers: {bridge_status['stuck_timers']}")
        
        if bridge_status['tasks']:
            print("\n📋 CURRENT TASKS:")
            for employee, task_info in bridge_status['tasks'].items():
                print(f"👤 {employee}:")
                print(f"   Task: {task_info['task']}")
                print(f"   Status: {task_info['status']}")
                print(f"   Duration: {task_info['duration_minutes']:.1f} minutes")
                print()
        else:
            print("\n✅ No active tasks")

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

    def handle_models(self, args):
        """Handle models command - show configured models"""
        print("🤖 Configured AI Models:")
        print("=" * 50)
        
        models = models_config.get_all_models()
        for level, model_info in models.items():
            print(f"  {level.capitalize()} Level:")
            print(f"    Model: {model_info['name']}")
            print(f"    Description: {model_info['description']}")
            print(f"    Cost Level: {model_info['cost_level']}")
            print()
        
        print("💡 Usage:")
        print("  To set a model: model-set <level> <model_name>")
        print("  Example: model-set smart openrouter/anthropic/claude-3.5-sonnet")

    def handle_model_set(self, args):
        """Handle model-set command - configure model for smartness level"""
        if len(args) < 2:
            print("Usage: model-set <level> <model_name>")
            print("Example: model-set smart openrouter/anthropic/claude-3.5-sonnet")
            return
        
        level = args[0]
        model_name = args[1]
        
        # Validate level
        if level not in ["smart", "normal"]:
            print("Invalid level. Use 'smart' or 'normal'.")
            return
        
        # Validate model (basic check)
        if not model_name:
            print("Model name cannot be empty.")
            return
        
        # Update configuration
        description = f"{'High-performance' if level == 'smart' else 'Efficient'} model for {'complex planning and analysis' if level == 'smart' else 'code writing and execution'}"
        cost_level = "high" if level == "smart" else "low"
        
        models_config.update_model(level, model_name, description, cost_level)
        print(f"✅ Updated {level} model to: {model_name}")

    def handle_hire_specialist(self, args):
        """Handle hire-specialist command - hire a specialized employee from a specific category"""
        from pathlib import Path
        
        # Path to employee types directory
        employee_types_dir = Path(__file__).parent.parent / ".bmad-core" / "employee-types"
        
        if not employee_types_dir.exists():
            print("❌ Employee types directory not found!")
            return
        
        if len(args) < 1:
            # List available categories
            print("Available Employee Categories:")
            print("=" * 40)
            categories = [d.name for d in employee_types_dir.iterdir() if d.is_dir()]
            for i, category in enumerate(categories, 1):
                print(f"  {i}. {category.replace('-', ' ').title()}")
            print("\nUsage: hire-specialist <category>")
            print("Example: hire-specialist engineering")
            return
        
        category = args[0].lower().replace(" ", "-")
        category_dir = employee_types_dir / category
        
        if not category_dir.exists():
            print(f"❌ Category '{category}' not found!")
            print("\nAvailable categories:")
            categories = [d.name for d in employee_types_dir.iterdir() if d.is_dir()]
            for cat in categories:
                print(f"  - {cat.replace('-', ' ').title()}")
            return
        
        # List available employee types in this category
        employee_types = [f.stem for f in category_dir.iterdir() if f.suffix == ".md"]
        
        if not employee_types:
            print(f"❌ No employee types found in category '{category}'!")
            return
        
        print(f"Available {category.replace('-', ' ').title()} Specialists:")
        print("=" * 50)
        for i, emp_type in enumerate(employee_types, 1):
            name = emp_type.replace("-", " ").title()
            print(f"  {i}. {name}")
        
        print("\nUsage: hire <name> <specialty> [smartness]")
        print("Example: hire john frontend-developer smart")
    
    def handle_monitor(self, args):
        """Handle monitor command - show agent monitoring dashboard"""
        # Try to import monitoring components
        try:
            from src.monitoring.agent_health_monitor import AgentHealthMonitor
            from src.monitoring.agent_recovery_manager import AgentRecoveryManager
            from src.monitoring.monitoring_dashboard import MonitoringDashboard
        except ImportError as e:
            print("❌ Monitoring system not available:", str(e))
            return
        
        # Check if monitoring is set up
        if not hasattr(self, 'health_monitor') or not self.health_monitor:
            print("⚠️  Monitoring system not initialized")
            print("💡 Monitoring system is available but not initialized in this CLI session")
            print("   Start the full server to enable monitoring")
            return
        
        # If we have args, treat it as interactive mode
        if args:
            # Interactive dashboard mode
            if hasattr(self, 'monitoring_dashboard') and self.monitoring_dashboard:
                print("🔍 Starting interactive monitoring dashboard...")
                print("Type 'help' for commands, 'quit' to exit")
                self.monitoring_dashboard.run_interactive_dashboard()
            else:
                print("❌ Interactive monitoring dashboard not available")
            return
        
        # Static dashboard mode
        print("🔍 AGENT MONITORING DASHBOARD")
        print("=" * 50)
        
        # Show health summary
        if hasattr(self, 'health_monitor') and self.health_monitor:
            health_summary = self.health_monitor.get_agent_health_summary()
            if 'error' not in health_summary:
                print("\nOVERALL STATUS:")
                print(f"  Total Agents:     {health_summary['total_agents']}")
                print(f"  Healthy Agents:   {health_summary['healthy_agents']}")
                print(f"  Stuck Agents:      {health_summary['stuck_agents']}")
                print(f"  Stagnant Agents:   {health_summary['stagnant_agents']}")
                print(f"  Error Agents:      {health_summary['error_agents']}")
                
                print("\nAGENT DETAILS:")
                for agent_name, details in health_summary['agent_details'].items():
                    health_indicator = "✓"  # Healthy
                    if details['health_status'] == 'ERROR':
                        health_indicator = "✗"
                    elif details['health_status'] == 'STUCK':
                        health_indicator = "⊘"
                    elif details['health_status'] == 'STAGNANT':
                        health_indicator = "◐"
                    
                    print(f"  {health_indicator} {agent_name:<15} | "
                          f"Status: {details['worker_status']:<8} | "
                          f"Progress: {details['overall_progress']:>3}% | "
                          f"Task: {details['current_task'][:30]}{'...' if len(details['current_task']) > 30 else ''}")
            else:
                print(f"❌ Error: {health_summary['error']}")
        
        # Show recovery summary
        if hasattr(self, 'recovery_manager') and self.recovery_manager:
            recovery_summary = self.recovery_manager.get_recovery_summary()
            if 'error' not in recovery_summary:
                print("\nRECOVERY STATISTICS:")
                print(f"  Total Attempts:    {recovery_summary['total_recovery_attempts']}")
                print(f"  Successful:        {recovery_summary['successful_recoveries']}")
                print(f"  Failed:            {recovery_summary['failed_recoveries']}")
                print(f"  Escalations:       {recovery_summary['escalations']}")

def main():
    """Main function"""
    server = CLIServer()
    server.run()

if __name__ == "__main__":
    main()
