# opencode-slack Project Structure

## Directory Layout

```
opencode-slack/
├── src/                    # Source code
│   ├── __init__.py         # Package initializer
│   ├── main.py             # Main entry point
│   ├── managers/           # Business logic managers
│   │   ├── __init__.py
│   │   └── file_ownership.py  # File locking and ownership
│   ├── trackers/           # Progress and status tracking
│   │   ├── __init__.py
│   │   └── task_progress.py    # Task progress tracking
│   ├── bot/                # Slack bot framework
│   │   ├── __init__.py
│   │   ├── bot.py          # Bot command handling
│   │   └── slack_app.py    # Flask Slack app
│   ├── config/             # Configuration management
│   │   ├── __init__.py
│   │   ├── config.py       # System configuration
│   │   └── logging_config.py # Logging configuration
│   └── utils/              # Utility functions
│       ├── __init__.py
│       └── opencode_wrapper.py # opencode command wrapper
├── tests/                  # Test suite
│   ├── __init__.py
│   ├── test_file_ownership.py
│   ├── test_task_progress.py
│   ├── test_integration.py
│   └── test_slack_app.py
├── sessions/               # Employee session data
├── logs/                   # Log files
├── docs/                   # Documentation
├── employees.db            # SQLite database
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
├── TODO.md                 # Development progress tracking
├── SUMMARY.md              # System summary
├── CONCLUSION.md           # Project conclusion
├── PROJECT_COMPLETE.md     # Final status report
├── FINAL_STATUS.md         # Final status report
├── PROJECT_STRUCTURE.md   # This file
└── demo.py                 # Demonstration scripts
```

## Component Descriptions

### src/managers/
Contains business logic managers for core system functions.

**file_ownership.py**
- Manages file locks using SQLite database
- Handles employee hiring/firing
- Implements request/approval workflow
- Provides file ownership queries

### src/trackers/
Contains components for tracking progress and status.

**task_progress.py**
- Tracks task progress using markdown files
- Parses progress information from task files
- Suggests file releases based on completion
- Manages employee task directories

### src/bot/
Contains the Slack bot framework and command handling.

**bot.py**
- Handles Slack commands for employee management
- Processes file locking/unlocking requests
- Manages progress tracking commands
- Coordinates request/approval workflow

**slack_app.py**
- Flask application for Slack integration
- Handles incoming Slack commands
- Routes commands to appropriate handlers

### src/config/
Contains configuration and logging setup.

**config.py**
- System configuration settings
- Environment variable handling
- Default values and constants

**logging_config.py**
- Logging setup and configuration
- Log file management
- Logger initialization

### src/utils/
Contains utility functions and helpers.

**opencode_wrapper.py**
- Wrapper for opencode command execution
- Process management for AI agents
- Integration with employee management system

## Usage Examples

### Importing Components
```python
from src.managers.file_ownership import FileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker

# Initialize managers
file_manager = FileOwnershipManager()
task_tracker = TaskProgressTracker()
```

### Running the System
```bash
# Run the main entry point
python src/main.py

# Run tests
python -m tests.test_file_ownership
python -m tests.test_task_progress
python -m tests.test_integration
```

## Key Benefits of This Structure

### ✅ Modularity
- Clear separation of concerns
- Each component has a single responsibility
- Easy to extend and maintain

### ✅ Testability
- Comprehensive test suite included
- Each component can be tested independently
- Integration tests for complex workflows

### ✅ Scalability
- Modular design allows for easy extension
- Configuration-driven approach
- Well-defined interfaces between components

### ✅ Maintainability
- Clear directory structure
- Well-documented components
- Consistent naming conventions
- Comprehensive logging

### ✅ Production Ready
- Resource cleanup and safety
- Error handling and recovery
- Performance optimization
- Security considerations

## Getting Started

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the system:
   ```bash
   python src/main.py
   ```

3. Run tests:
   ```bash
   python -m tests.test_file_ownership
   python -m tests.test_task_progress
   python -m tests.test_integration
   ```

This structure provides a solid foundation for the opencode-slack system, making it easy to maintain, extend, and deploy.