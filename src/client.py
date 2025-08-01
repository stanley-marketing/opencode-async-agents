#!/usr/bin/env python3
"""
CLI client for opencode-slack system.
Connects to the opencode-slack server and provides interactive commands.
"""

import sys
import os
import json
import requests
from pathlib import Path
from urllib.parse import urljoin
import argparse

try:
    import readline
    readline_available = True
except ImportError:
    readline_available = False


class OpencodeSlackClient:
    """CLI client for opencode-slack server"""
    
    def __init__(self, server_url="http://localhost:8080"):
        self.server_url = server_url.rstrip('/')
        self.running = True
        self.command_history_file = os.path.expanduser("~/.opencode_slack_client_history")
        self.load_history()
        self._setup_autocomplete()
        
        # Test connection
        if not self._test_connection():
            print(f"❌ Cannot connect to server at {self.server_url}")
            print("   Make sure the server is running with: python -m src.server")
            sys.exit(1)
        
        print(f"=== opencode-slack CLI Client ===")
        print(f"🔗 Connected to: {self.server_url}")
        print("Type 'help' for available commands")
        print("Use ↑/↓ arrows for command history")
        print("Use TAB for command completion")
        print("Type 'quit' to exit")
        print()
    
    def _test_connection(self):
        """Test connection to server"""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _make_request(self, method, endpoint, data=None, params=None):
        """Make HTTP request to server"""
        url = urljoin(self.server_url + '/', endpoint.lstrip('/'))
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, params=params, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, timeout=30)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            return response
        except requests.exceptions.RequestException as e:
            print(f"❌ Connection error: {e}")
            return None
    
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
            'status', 'sessions', 'lock', 'release', 'progress', 'files',
            'employees', 'chat', 'chat-start', 'chat-stop', 'chat-status',
            'agents', 'bridge', 'health', 'clear', 'history', 'chat-debug',
            'project-root', 'hire-specialist'
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
                # For client, we can't access server data directly, so provide basic completion
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
                # hire <name> <role>
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
            elif command in ['hire-specialist']:
                # hire-specialist <category>
                if len(words) == 1 and ends_with_space:
                    # After "hire-specialist " - need category
                    categories = ['engineering', 'design', 'product', 'testing', 'project-management']
                    if not text:
                        return categories[:]
                    else:
                        return [cat for cat in categories if cat.startswith(text)]
                elif len(words) == 2 and not ends_with_space:
                    # Typing category
                    categories = ['engineering', 'design', 'product', 'testing', 'project-management']
                    if not text:
                        return categories[:]
                    else:
                        return [cat for cat in categories if cat.startswith(text)]
            elif command in ['fire', 'assign', 'start', 'stop', 'progress']:
                # These commands need employee names - provide common placeholders
                if len(words) == 1 and ends_with_space:
                    # After "fire " - need employee name
                    common_names = ['john', 'jane', 'sarah', 'dev-1', 'dev-2', 'analyst-1']
                    if not text:
                        return common_names[:]
                    else:
                        return [name for name in common_names if name.startswith(text)]
                elif len(words) == 2 and not ends_with_space:
                    # Typing employee name
                    common_names = ['john', 'jane', 'sarah', 'dev-1', 'dev-2', 'analyst-1']
                    if not text:
                        return common_names[:]
                    else:
                        return [name for name in common_names if name.startswith(text)]
            elif command in ['lock']:
                # lock <name> <files> <desc>
                if len(words) == 1 and ends_with_space:
                    # After "lock " - need employee name
                    common_names = ['john', 'jane', 'sarah', 'dev-1', 'dev-2', 'analyst-1']
                    if not text:
                        return common_names[:]
                    else:
                        return [name for name in common_names if name.startswith(text)]
                elif len(words) == 2 and not ends_with_space:
                    # Typing employee name
                    common_names = ['john', 'jane', 'sarah', 'dev-1', 'dev-2', 'analyst-1']
                    if not text:
                        return common_names[:]
                    else:
                        return [name for name in common_names if name.startswith(text)]
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
                    common_names = ['john', 'jane', 'sarah', 'dev-1', 'dev-2', 'analyst-1']
                    if not text:
                        return common_names[:]
                    else:
                        return [name for name in common_names if name.startswith(text)]
                elif len(words) == 2 and not ends_with_space:
                    # Typing employee name
                    common_names = ['john', 'jane', 'sarah', 'dev-1', 'dev-2', 'analyst-1']
                    if not text:
                        return common_names[:]
                    else:
                        return [name for name in common_names if name.startswith(text)]
            elif command in ['request']:
                # request <name> <file> <desc>
                if len(words) == 1 and ends_with_space:
                    # After "request " - need requester name
                    common_names = ['john', 'jane', 'sarah', 'dev-1', 'dev-2', 'analyst-1']
                    if not text:
                        return common_names[:]
                    else:
                        return [name for name in common_names if name.startswith(text)]
                elif len(words) == 2 and not ends_with_space:
                    # Typing requester name
                    common_names = ['john', 'jane', 'sarah', 'dev-1', 'dev-2', 'analyst-1']
                    if not text:
                        return common_names[:]
                    else:
                        return [name for name in common_names if name.startswith(text)]
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
                    # Provide common request IDs as examples
                    request_ids = ['1', '2', '3', '4', '5']
                    if not text:
                        return request_ids[:]
                    else:
                        return [req_id for req_id in request_ids if req_id.startswith(text)]
                elif len(words) == 2 and not ends_with_space:
                    # Typing request ID
                    request_ids = ['1', '2', '3', '4', '5']
                    if not text:
                        return request_ids[:]
                    else:
                        return [req_id for req_id in request_ids if req_id.startswith(text)]
            elif command in ['project-root']:
                # project-root [path]
                if len(words) == 1 and ends_with_space:
                    # After "project-root " - need path
                    common_paths = ['.', './', '/home/', '/Users/', '/projects/']
                    if not text:
                        return common_paths[:]
                    else:
                        return [path for path in common_paths if path.startswith(text)]
                elif len(words) == 2 and not ends_with_space:
                    # Typing path
                    common_paths = ['.', './', '/home/', '/Users/', '/projects/']
                    if not text:
                        return common_paths[:]
                    else:
                        return [path for path in common_paths if path.startswith(text)]
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
        """Main client loop"""
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
        elif command == "progress":
            self.handle_progress(parts[1:])
        elif command == "files":
            self.handle_files(parts[1:])
        elif command == "employees":
            self.handle_employees(parts[1:])
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
        elif command == "health":
            self.handle_health(parts[1:])
        elif command == "clear":
            self.handle_clear(parts[1:])
        elif command == "history":
            self.handle_history(parts[1:])
        elif command == "chat-debug":
            self.handle_chat_debug(parts[1:])
        elif command == "project-root":
            self.handle_project_root(parts[1:])
        else:
            print(f"Unknown command: {command}")
            print("Type 'help' for available commands")
    
    def show_help(self):
        """Show available commands"""
        print("🔥 OPENCODE-SLACK CLIENT - Available commands:")
        print("  hire <name> <role>              - Hire a new employee")
        print("  hire-specialist [category]     - List available specialists by category")
        print("  fire <name>                     - Fire an employee")
        print("  assign <name> '<task>' [model]  - Assign task to employee")
        print("  start <name> '<task>' [model]   - Start employee working on task")
        print("  stop <name>                     - Stop employee's task")
        print("  status                          - Show comprehensive system status")
        print("  sessions                        - Show active sessions")
        print("  lock <name> <files> <desc>      - Lock files for work")
        print("  release <name> [files]          - Release files")
        print("  progress [name]                 - Show progress for employee (or all)")
        print("  files                           - Show locked files")
        print("  employees                       - List all employees")
        print("")
        print("🔥 CHAT COMMANDS:")
        print("  chat <message>                  - Send message to Telegram group")
        print("  chat-start                      - Start Telegram chat system")
        print("  chat-stop                       - Stop Telegram chat system")
        print("  chat-status                     - Show chat system status")
        print("  chat-debug                      - Debug Telegram connection issues")
        print("  agents                          - Show communication agents status")
        print("  bridge                          - Show agent bridge status")
        print("")
        print("🔧 SYSTEM COMMANDS:")
        print("  health                          - Check server health")
        print("  history                         - Show command history")
        print("  clear                           - Clear the screen")
        print("  help                            - Show this help")
        print("  quit                            - Exit the client")
        print("")
        print("📂 PROJECT ROOT COMMANDS:")
        print("  project-root                    - Show current project root directory")
        print("  project-root <path>             - Set project root directory")
        print()
        print("🚀 Examples:")
        print("  assign sarah 'implement user authentication'")
        print("  assign dev-2 'create API endpoints' claude-3.5")
        print("  status  # See complete system overview")
    
    def handle_hire(self, args):
        """Handle hire command"""
        if len(args) < 2:
            print("Usage: hire <name> <role>")
            return
        
        name = args[0]
        role = " ".join(args[1:])
        
        response = self._make_request('POST', '/employees', {
            'name': name,
            'role': role
        })
        
        if response and response.status_code == 200:
            data = response.json()
            print(f"✅ {data['message']}")
        elif response:
            data = response.json()
            print(f"❌ {data.get('error', 'Unknown error')}")
        else:
            print("❌ Failed to communicate with server")
    
    def handle_fire(self, args):
        """Handle fire command"""
        if len(args) < 1:
            print("Usage: fire <name>")
            return
        
        name = args[0]
        
        response = self._make_request('DELETE', f'/employees/{name}')
        
        if response and response.status_code == 200:
            data = response.json()
            print(f"✅ {data['message']}")
        elif response:
            data = response.json()
            print(f"❌ {data.get('error', 'Unknown error')}")
        else:
            print("❌ Failed to communicate with server")
    
    def handle_assign(self, args):
        """Handle assign command"""
        if len(args) < 2:
            print("Usage: assign <name> <task_description> [model] [mode]")
            print("Example: assign sarah 'implement user auth' openrouter/qwen/qwen3-coder build")
            return
        
        name = args[0]
        task_description = args[1]
        model = args[2] if len(args) > 2 else "openrouter/qwen/qwen3-coder"
        mode = args[3] if len(args) > 3 else "build"
        
        response = self._make_request('POST', '/tasks', {
            'name': name,
            'task': task_description,
            'model': model,
            'mode': mode
        })
        
        if response and response.status_code == 200:
            data = response.json()
            print(f"🚀 {data['message']}")
            if 'session_id' in data:
                print(f"📋 Session ID: {data['session_id']}")
        elif response:
            data = response.json()
            print(f"❌ {data.get('error', 'Unknown error')}")
        else:
            print("❌ Failed to communicate with server")
    
    def handle_stop(self, args):
        """Handle stop command"""
        if len(args) < 1:
            print("Usage: stop <name>")
            return
        
        name = args[0]
        
        response = self._make_request('DELETE', f'/tasks/{name}')
        
        if response and response.status_code == 200:
            data = response.json()
            print(f"✅ {data['message']}")
        else:
            print("❌ Failed to communicate with server")
    
    def handle_status(self, args):
        """Handle status command"""
        response = self._make_request('GET', '/status')
        
        if not response or response.status_code != 200:
            print("❌ Failed to get status")
            return
        
        data = response.json()
        
        print("📊 SYSTEM STATUS OVERVIEW")
        print("=" * 50)
        
        # Show active sessions
        active_sessions = data.get('active_sessions', {})
        if active_sessions:
            print("\n🔥 ACTIVE SESSIONS:")
            for employee_name, session_info in active_sessions.items():
                status = "🔥 RUNNING" if session_info['is_running'] else "⏸️  PAUSED"
                print(f"  👤 {employee_name} - {status}")
                print(f"     🧠 Task: {session_info['task'][:60]}{'...' if len(session_info['task']) > 60 else ''}")
                if session_info.get('files_locked'):
                    locked_files = session_info['files_locked'][:3]
                    more_files = len(session_info['files_locked']) - 3
                    files_display = ', '.join(locked_files)
                    if more_files > 0:
                        files_display += f" (+{more_files} more)"
                    print(f"     🔒 Files: {files_display}")
        else:
            print("\n✅ No active sessions")
        
        # Show file locks
        locked_files = data.get('locked_files', [])
        if locked_files:
            print("\n📁 LOCKED FILES:")
            for file_info in locked_files:
                print(f"  🔒 {file_info['file_path']} - locked by {file_info['employee_name']}")
                if file_info.get('task_description'):
                    print(f"     📝 Task: {file_info['task_description'][:60]}{'...' if len(file_info['task_description']) > 60 else ''}")
        else:
            print("\n🔓 No files currently locked")
        
        # Show employees
        employees = data.get('employees', [])
        if employees:
            print(f"\n👥 ALL EMPLOYEES ({len(employees)} total):")
            for emp in employees:
                print(f"  👤 {emp['name']} ({emp['role']})")
        else:
            print("\n👥 No employees hired")
        
        # Show chat status
        if data.get('chat_enabled'):
            stats = data.get('chat_statistics', {})
            print(f"\n💬 CHAT SYSTEM: ✅ Active")
            print(f"   👥 Total Agents: {stats.get('total_agents', 0)}")
            print(f"   🔥 Working: {stats.get('working_agents', 0)}")
            print(f"   😴 Idle: {stats.get('idle_agents', 0)}")
        else:
            print("\n💬 CHAT SYSTEM: ❌ Inactive")
        
        print("\n" + "=" * 50)
    
    def handle_sessions(self, args):
        """Handle sessions command"""
        response = self._make_request('GET', '/sessions')
        
        if not response or response.status_code != 200:
            print("❌ Failed to get sessions")
            return
        
        data = response.json()
        sessions = data.get('sessions', {})
        
        if not sessions:
            print("No active sessions")
            return
        
        print("🔥 Active sessions:")
        for employee_name, session_info in sessions.items():
            status = "🔥 RUNNING" if session_info['is_running'] else "⏸️  PAUSED"
            print(f"  👤 {employee_name} - {status}")
            print(f"     🧠 Task: {session_info['task']}")
            print(f"     📋 Session: {session_info['session_id']}")
            if session_info.get('files_locked'):
                print(f"     🔒 Files: {', '.join(session_info['files_locked'])}")
    
    def handle_lock(self, args):
        """Handle lock command"""
        if len(args) < 3:
            print("Usage: lock <name> <file1,file2,...> <description>")
            return
        
        name = args[0]
        files_str = args[1]
        description = " ".join(args[2:])
        
        files = [f.strip() for f in files_str.split(",")]
        
        response = self._make_request('POST', '/files/lock', {
            'name': name,
            'files': files,
            'description': description
        })
        
        if response and response.status_code == 200:
            data = response.json()
            result = data.get('result', {})
            
            print(f"Files locked for {name}:")
            for file_path, status in result.items():
                print(f"  - {file_path}: {status}")
            
            if any("locked" in status for status in result.values()):
                print("✅ Files locked successfully!")
        else:
            print("❌ Failed to lock files")
    
    def handle_release(self, args):
        """Handle release command"""
        if len(args) < 1:
            print("Usage: release <name> [files]")
            return
        
        name = args[0]
        files = args[1:] if len(args) > 1 else None
        
        response = self._make_request('POST', '/files/release', {
            'name': name,
            'files': files
        })
        
        if response and response.status_code == 200:
            data = response.json()
            released = data.get('released', [])
            if released:
                print(f"✅ Released files for {name}: {', '.join(released)}")
            else:
                print(f"❌ No files to release for {name}")
        else:
            print("❌ Failed to release files")
    
    def handle_progress(self, args):
        """Handle progress command"""
        name = args[0] if args else None
        params = {'name': name} if name else None
        
        response = self._make_request('GET', '/progress', params=params)
        
        if not response or response.status_code != 200:
            print("❌ Failed to get progress")
            return
        
        data = response.json()
        progress_data = data.get('progress', {})
        
        if name:
            # Single employee progress
            if progress_data:
                print(f"Progress for {name}:")
                print(f"  Task: {progress_data.get('task_description', 'N/A')}")
                print(f"  Overall Progress: {progress_data.get('overall_progress', 0)}%")
                print(f"  Files ready to release: {', '.join(progress_data.get('ready_to_release', [])) or 'None'}")
                print(f"  Still working on: {', '.join(progress_data.get('still_working_on', [])) or 'None'}")
            else:
                print(f"❌ No progress found for {name}")
        else:
            # All employees progress
            if progress_data:
                print("Employee Progress:")
                for emp_name, emp_progress in progress_data.items():
                    if emp_progress:
                        print(f"  {emp_name}: {emp_progress.get('overall_progress', 0)}% complete")
                    else:
                        print(f"  {emp_name}: No progress data")
            else:
                print("❌ No progress data available")
    
    def handle_files(self, args):
        """Handle files command"""
        response = self._make_request('GET', '/files')
        
        if not response or response.status_code != 200:
            print("❌ Failed to get files")
            return
        
        data = response.json()
        files = data.get('files', [])
        
        if files:
            print("📁 LOCKED FILES:")
            for file_info in files:
                print(f"  🔒 {file_info['file_path']} - locked by {file_info['employee_name']}")
                if file_info.get('task_description'):
                    print(f"     📝 Task: {file_info['task_description']}")
        else:
            print("🔓 No files currently locked")
    
    def handle_employees(self, args):
        """Handle employees command"""
        response = self._make_request('GET', '/employees')
        
        if not response or response.status_code != 200:
            print("❌ Failed to get employees")
            return
        
        data = response.json()
        employees = data.get('employees', [])
        
        if employees:
            print("👥 EMPLOYEES:")
            for employee in employees:
                print(f"  👤 {employee['name']} ({employee['role']})")
        else:
            print("❌ No employees found")
    
    def handle_chat(self, args):
        """Handle chat command"""
        if not args:
            print("Usage: chat <message>")
            return
        
        message = " ".join(args)
        
        response = self._make_request('POST', '/chat/send', {
            'message': message,
            'sender': 'cli-user'
        })
        
        if response and response.status_code == 200:
            data = response.json()
            print(f"✅ {data['message']}")
        elif response:
            data = response.json()
            print(f"❌ {data.get('error', 'Unknown error')}")
        else:
            print("❌ Failed to send message")
    
    def handle_chat_start(self, args):
        """Handle chat-start command"""
        response = self._make_request('POST', '/chat/start')
        
        if response and response.status_code == 200:
            data = response.json()
            print(f"🚀 {data['message']}")
        elif response:
            data = response.json()
            print(f"❌ {data.get('error', 'Unknown error')}")
        else:
            print("❌ Failed to start chat")
    
    def handle_chat_stop(self, args):
        """Handle chat-stop command"""
        response = self._make_request('POST', '/chat/stop')
        
        if response and response.status_code == 200:
            data = response.json()
            print(f"🛑 {data['message']}")
        elif response:
            data = response.json()
            print(f"❌ {data.get('error', 'Unknown error')}")
        else:
            print("❌ Failed to stop chat")
    
    def handle_chat_status(self, args):
        """Handle chat-status command"""
        response = self._make_request('GET', '/chat/status')
        
        if not response or response.status_code != 200:
            print("❌ Failed to get chat status")
            return
        
        data = response.json()
        
        print("📊 CHAT SYSTEM STATUS")
        print("=" * 50)
        print(f"🔧 Configuration: {'✅ Ready' if data.get('configured') else '❌ Not configured'}")
        print(f"🌐 Connection: {'✅ Connected' if data.get('connected') else '❌ Disconnected'}")
        print(f"🔄 Polling: {'✅ Active' if data.get('polling') else '❌ Stopped'}")
        
        stats = data.get('statistics', {})
        if stats:
            print(f"👥 Total Agents: {stats.get('total_agents', 0)}")
            print(f"🔥 Working: {stats.get('working_agents', 0)}")
            print(f"😴 Idle: {stats.get('idle_agents', 0)}")
            print(f"🆘 Stuck: {stats.get('stuck_agents', 0)}")
    
    def handle_agents(self, args):
        """Handle agents command"""
        response = self._make_request('GET', '/agents')
        
        if not response or response.status_code != 200:
            print("❌ Failed to get agents")
            return
        
        data = response.json()
        agents = data.get('agents', {})
        
        if not agents:
            print("❌ No communication agents found")
            return
        
        print("👥 COMMUNICATION AGENTS STATUS")
        print("=" * 50)
        
        for name, status in agents.items():
            print(f"👤 {name} ({status.get('role', 'unknown')})")
            print(f"   Status: {status.get('worker_status', 'unknown')}")
            print(f"   Expertise: {', '.join(status.get('expertise', []))}")
            if status.get('current_task'):
                print(f"   Current Task: {status['current_task'][:50]}...")
            if status.get('active_tasks'):
                print(f"   Active Tasks: {len(status['active_tasks'])}")
            if status.get('last_response'):
                print(f"   Last Response: {status['last_response']}")
            print()
    
    def handle_bridge(self, args):
        """Handle bridge command"""
        response = self._make_request('GET', '/bridge')
        
        if not response or response.status_code != 200:
            print("❌ Failed to get bridge status")
            return
        
        data = response.json()
        bridge = data.get('bridge', {})
        
        print("🌉 AGENT BRIDGE STATUS")
        print("=" * 50)
        print(f"🔄 Active Tasks: {bridge.get('active_tasks', 0)}")
        print(f"⏰ Stuck Timers: {bridge.get('stuck_timers', 0)}")
        
        tasks = bridge.get('tasks', {})
        if tasks:
            print("\n📋 CURRENT TASKS:")
            for employee, task_info in tasks.items():
                print(f"👤 {employee}:")
                print(f"   Task: {task_info.get('task', 'N/A')}")
                print(f"   Status: {task_info.get('status', 'unknown')}")
                print(f"   Duration: {task_info.get('duration_minutes', 0):.1f} minutes")
                print()
        else:
            print("\n✅ No active tasks")
    
    def handle_health(self, args):
        """Handle health command"""
        response = self._make_request('GET', '/health')
        
        if not response or response.status_code != 200:
            print("❌ Server is not healthy")
            return
        
        data = response.json()
        
        print("🏥 SERVER HEALTH")
        print("=" * 30)
        print(f"Status: ✅ {data.get('status', 'unknown')}")
        print(f"Chat Enabled: {'✅ Yes' if data.get('chat_enabled') else '❌ No'}")
        print(f"Active Sessions: {data.get('active_sessions', 0)}")
        print(f"Total Agents: {data.get('total_agents', 0)}")
    
    def handle_clear(self, args):
        """Handle clear command"""
        os.system("clear" if os.name == "posix" else "cls")
        print(f"=== opencode-slack CLI Client ===")
        print(f"🔗 Connected to: {self.server_url}")
        print("Type 'help' for available commands")
        print("Use TAB for command completion")
        print()
    
    def handle_chat_debug(self, args):
        """Handle chat-debug command"""
        response = self._make_request('GET', '/chat/debug')
        
        if not response or response.status_code != 200:
            print("❌ Failed to get chat debug info")
            return
        
        data = response.json()
        
        print("🔍 TELEGRAM DEBUG INFORMATION")
        print("=" * 50)
        
        # Basic connection info
        print(f"🔧 Bot Configured: {'✅ Yes' if data.get('configured') else '❌ No'}")
        print(f"🌐 Bot Connected: {'✅ Yes' if data.get('connected') else '❌ No'}")
        print(f"🔄 Polling Active: {'✅ Yes' if data.get('polling') else '❌ No'}")
        
        # Webhook information
        webhook_info = data.get('webhook_info', {})
        if webhook_info:
            print(f"\n📡 WEBHOOK STATUS:")
            print(f"   URL: {webhook_info.get('url', 'None')}")
            print(f"   Has Custom Certificate: {webhook_info.get('has_custom_certificate', False)}")
            print(f"   Pending Updates: {webhook_info.get('pending_update_count', 0)}")
            if webhook_info.get('last_error_date'):
                print(f"   Last Error: {webhook_info.get('last_error_message', 'Unknown')}")
        
        # Bot information
        bot_info = data.get('bot_info', {})
        if bot_info:
            print(f"\n🤖 BOT INFORMATION:")
            print(f"   Username: @{bot_info.get('username', 'unknown')}")
            print(f"   First Name: {bot_info.get('first_name', 'unknown')}")
            print(f"   Can Join Groups: {bot_info.get('can_join_groups', False)}")
            print(f"   Can Read All Group Messages: {bot_info.get('can_read_all_group_messages', False)}")
        
        # Troubleshooting tips
        if not data.get('polling') and webhook_info.get('url'):
            print(f"\n⚠️  ISSUE DETECTED:")
            print(f"   Webhook is set but polling is not active.")
            print(f"   This can cause 409 Conflict errors.")
            print(f"   Try: chat-stop then chat-start to clear webhook.")
    
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
    
    def handle_project_root(self, args):
        """Handle project-root command"""
        if not args:
            # Get current project root
            response = self._make_request('GET', '/project-root')
            
            if response and response.status_code == 200:
                data = response.json()
                project_root = data.get('project_root', 'Unknown')
                print(f"📂 Current project root directory: {project_root}")
            else:
                print("❌ Failed to get project root")
        else:
            # Set project root
            project_root = args[0]
            response = self._make_request('POST', '/project-root', {
                'project_root': project_root
            })
            
            if response and response.status_code == 200:
                data = response.json()
                print(f"✅ {data['message']}")
            elif response:
                data = response.json()
                print(f"❌ {data.get('error', 'Unknown error')}")
            else:
                print("❌ Failed to set project root")


def handle_hire_specialist(self, args):
        """Handle hire-specialist command"""
        # Since this is a client-side command that doesn't require server interaction,
        # we'll just display information about available employee types
        
        # Define available categories and their employee types
        employee_types = {
            'engineering': [
                'Frontend Developer', 'Mobile App Builder', 'AI Engineer',
                'DevOps Automator', 'Backend Architect', 'Test Writer Fixer',
                'Rapid Prototyper'
            ],
            'design': [
                'UI Designer', 'UX Researcher', 'Visual Storyteller',
                'Brand Guardian', 'Whimsy Injector'
            ],
            'product': [
                'Product Manager', 'Sprint Prioritizer', 'Trend Researcher',
                'Feedback Synthesizer'
            ],
            'testing': [
                'API Tester', 'Performance Benchmarker', 'Test Results Analyzer',
                'Tool Evaluator', 'Workflow Optimizer'
            ],
            'project-management': [
                'Studio Producer', 'Project Shipper', 'Experiment Tracker'
            ]
        }
        
        if len(args) < 1:
            # List all categories
            print("Available Employee Categories:")
            print("=" * 40)
            for i, category in enumerate(employee_types.keys(), 1):
                print(f"  {i}. {category.replace('-', ' ').title()}")
            print("\nUsage: hire-specialist <category>")
            print("Example: hire-specialist engineering")
            return
        
        category = args[0].lower().replace(" ", "-")
        
        if category not in employee_types:
            print(f"❌ Category '{category}' not found!")
            print("\nAvailable categories:")
            for cat in employee_types.keys():
                print(f"  - {cat.replace('-', ' ').title()}")
            return
        
        # List employee types in this category
        types = employee_types[category]
        print(f"Available {category.replace('-', ' ').title()} Specialists:")
        print("=" * 50)
        for i, emp_type in enumerate(types, 1):
            print(f"  {i}. {emp_type}")
        
        print("\nTo hire one of these specialists, use the hire command:")
        print("Example: hire john 'frontend developer'")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='OpenCode-Slack CLI Client')
    parser.add_argument('--server', '-s', default='http://localhost:8080',
                       help='Server URL (default: http://localhost:8080)')
    
    args = parser.parse_args()
    
    client = OpencodeSlackClient(args.server)
    client.run()


if __name__ == "__main__":
    main()