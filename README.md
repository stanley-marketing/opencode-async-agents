# opencode-slack

A framework for managing multiple AI "employees" working in parallel with proper file ownership and task tracking.

## Overview

The opencode-slack system provides a robust foundation for managing multiple AI agents working on the same codebase without conflicts. It implements a mutex-based file locking system to prevent conflicts when multiple agents try to work on the same files.

## Key Features

### File Ownership System
- Database-based file locking prevents concurrent file access
- Request/approval workflow for safe collaboration
- Automatic file release when work is complete
- Graceful resource cleanup

### Employee Management
- Hire and fire AI employees with different roles
- Isolated session storage per employee
- Role-based access control
- Comprehensive employee lifecycle management

### Task Progress Tracking
- Detailed progress tracking per employee
- Task completion monitoring
- Automatic file release based on progress
- Comprehensive status reporting

## System Architecture

```
[Employees] → [FileOwnershipManager] → [SQLite Database]
                    ↓
         [TaskProgressTracker] → [Markdown Files]
                    ↓
          [Configuration & Logging]
```

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Command Line Interface (CLI)

The system includes a CLI server for local testing without Slack:

```bash
# Run the CLI server interactively
python3 src/cli_server.py

# Run with demo commands
./demo_cli.sh
```

### Programmatic Usage

```python
from src.managers.file_ownership import FileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker

# Initialize the system
file_manager = FileOwnershipManager()
task_tracker = TaskProgressTracker()

# Hire employees
file_manager.hire_employee("sarah", "developer")
file_manager.hire_employee("dev-2", "developer")

# Lock files for work
file_manager.lock_files("sarah", ["src/auth.py"], "implement auth feature")

# Request file from another employee
file_manager.request_file("dev-2", "src/auth.py", "need for API integration")

# Approve request
requests = file_manager.get_pending_requests("sarah")
file_manager.approve_request(requests[0]['id'])

# Release files when done
file_manager.release_files("dev-2", ["src/auth.py"])
```

### Components

#### FileOwnershipManager
Manages file locks and ownership in a SQLite database:

- `hire_employee(name, role)` - Add a new employee
- `fire_employee(name)` - Remove an employee and release their files
- `lock_files(employee_name, file_paths, task_description)` - Lock files for an employee
- `release_files(employee_name, file_paths=None)` - Release files owned by an employee
- `request_file(requester, file_path, reason)` - Request access to a file from another employee
- `approve_request(request_id)` - Approve a file request
- `deny_request(request_id)` - Deny a file request

#### TaskProgressTracker
Tracks progress of tasks in markdown files:

- `create_task_file(employee_name, task_description, files_needed)` - Create a new task progress file
- `get_task_progress(employee_name)` - Get progress for an employee
- `update_file_status(employee_name, file_path, percentage, status_note)` - Update status of a specific file
- `suggest_file_releases(employee_name)` - Suggest files that can be released

## Testing

```bash
# Run unit tests
python -m tests.test_file_ownership
python -m tests.test_task_progress

# Run integration tests
python -m tests.test_integration
```

## Configuration

The system can be configured through environment variables:

- `DATABASE_PATH` - Path to SQLite database
- `SESSIONS_DIR` - Directory for employee sessions
- `OPENCODE_COMMAND` - Command to run opencode
- `DEFAULT_MODEL` - Default AI model to use

## Benefits

✅ **Conflict Prevention** - No two employees can edit the same file simultaneously  
✅ **Collaboration** - Employees can request files from each other  
✅ **Progress Tracking** - See how much work each employee has completed  
✅ **Resource Management** - Automatically release files when work is done  
✅ **Scalability** - Easy to add more employees as needed  
✅ **Safety** - Employees can't accidentally overwrite each other's work  

## Project Structure

```
src/
├── managers/           # Business logic managers
│   ├── file_ownership.py  # File locking and ownership
├── trackers/           # Progress and status tracking
│   ├── task_progress.py    # Task progress tracking
├── bot/                # Slack bot framework
├── config/             # Configuration management
├── utils/              # Utility functions
└── main.py             # Main entry point
```

This system provides a robust foundation for managing multiple AI agents working on the same codebase without conflicts.