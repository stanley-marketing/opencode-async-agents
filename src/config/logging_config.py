import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging(log_level=logging.INFO):
    """Set up logging for the application"""
    
    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
        handlers=[
            RotatingFileHandler(
                os.path.join(log_dir, 'app.log'), 
                maxBytes=1024*1024*5,  # 5 MB
                backupCount=5
            ),
            logging.StreamHandler()  # Also log to console
        ]
    )
    
    # Set up logging for specific modules
    logging.getLogger('werkzeug').setLevel(logging.WARNING)  # Reduce Flask noise
    
    return logging.getLogger(__name__)

# Create a global logger instance
logger = setup_logging()