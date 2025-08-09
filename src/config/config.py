import os
from pathlib import Path

class Config:
    # Database configuration
    DATABASE_PATH = os.environ.get('DATABASE_PATH', 'employees.db')

    # Session configuration
    SESSIONS_DIR = os.environ.get('SESSIONS_DIR', 'sessions')

    # Project root configuration
    PROJECT_ROOT = os.environ.get('PROJECT_ROOT', os.getcwd())

    # Slack configuration
    SLACK_SIGNING_SECRET = os.environ.get('SLACK_SIGNING_SECRET', '')
    SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN', '')

    # File ownership configuration
    DEFAULT_LOCK_TIMEOUT = int(os.environ.get('DEFAULT_LOCK_TIMEOUT', '3600'))  # 1 hour default

    # Task progress configuration
    PROGRESS_FILE_NAME = os.environ.get('PROGRESS_FILE_NAME', 'current_task.md')
    COMPLETED_TASKS_DIR = os.environ.get('COMPLETED_TASKS_DIR', 'completed_tasks')

    # Opencode configuration
    OPENCODE_COMMAND = os.environ.get('OPENCODE_COMMAND', 'opencode')
    DEFAULT_MODEL = os.environ.get('DEFAULT_MODEL', 'openrouter/google/gemini-2.5-pro')

    # Model configuration
    MODELS_CONFIG_FILE = os.environ.get('MODELS_CONFIG_FILE', 'models_config.json')

    @classmethod
    def init_app(cls, app):
        """Initialize the configuration with a Flask app"""
        # Create sessions directory if it doesn't exist
        Path(cls.SESSIONS_DIR).mkdir(parents=True, exist_ok=True)

        # Create completed tasks directory if it doesn't exist
        for employee_dir in Path(cls.SESSIONS_DIR).iterdir():
            if employee_dir.is_dir():
                completed_dir = employee_dir / cls.COMPLETED_TASKS_DIR
                completed_dir.mkdir(exist_ok=True)

        # Ensure project root directory exists
        Path(cls.PROJECT_ROOT).mkdir(parents=True, exist_ok=True)