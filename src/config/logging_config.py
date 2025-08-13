# SPDX-License-Identifier: MIT
from logging.handlers import RotatingFileHandler
import logging
import os

def setup_logging(log_level=logging.INFO, cli_mode=False):
    """Set up logging for the application"""

    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Configure handlers based on mode
    handlers = [
        RotatingFileHandler(
            os.path.join(log_dir, 'app.log'),
            maxBytes=1024*1024*5,  # 5 MB
            backupCount=5
        )
    ]

    # Only add console handler if not in CLI mode
    if not cli_mode:
        handlers.append(logging.StreamHandler())

    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
        handlers=handlers,
        force=True  # Override any existing configuration
    )

    # Set up logging for specific modules
    logging.getLogger('werkzeug').setLevel(logging.WARNING)  # Reduce Flask noise

    return logging.getLogger(__name__)

# Create a global logger instance (will be reconfigured by CLI if needed)
logger = setup_logging()