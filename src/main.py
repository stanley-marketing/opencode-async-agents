# SPDX-License-Identifier: MIT
#!/usr/bin/env python3
"""
Main entry point for the opencode-slack system.
"""

from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.managers.file_ownership import FileOwnershipManager
from src.trackers.task_progress import TaskProgressTracker

def main():
    """Main function to demonstrate the system"""
    print("=== opencode-slack System ===")
    print("Initializing components...")

    # Initialize core components
    file_manager = FileOwnershipManager(":memory:")  # Use in-memory database for demo
    task_tracker = TaskProgressTracker("/tmp/opencode_sessions")  # Use temp directory for demo

    print("✅ System initialized successfully!")
    print("\nAvailable components:")
    print("- FileOwnershipManager: Manages file locks and ownership")
    print("- TaskProgressTracker: Tracks task progress for employees")
    print("- SlackBot: Framework for Slack integration (not implemented yet)")
    print("- CLI Server: Command-line interface for local testing")
    print("- Configuration system: Environment-based configuration")
    print("- Logging system: Comprehensive logging")

    print("\nTo use the CLI server:")
    print("  python3 src/cli_server.py")

    print("\nTo run demo:")
    print("  ./demo_cli.sh")

    print("\nSystem is ready for use!")
    print("Import the components in your code to start managing employees.")

if __name__ == "__main__":
    main()