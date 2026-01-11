import logging
import sys
import os
from logging.handlers import RotatingFileHandler

# Define log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

def setup_logger(name: str = "invest_journal") -> logging.Logger:
    """
    Configure and return a standard logger for the application.
    """
    logger = logging.getLogger(name)
    
    # Set default level from environment or INFO
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Avoid duplicate handlers if setup_logger is called multiple times
    if not logger.handlers:
        # Stream Handler (Console)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(stream_handler)

        # File Handler (Optional - for production audit)
        log_file = os.getenv("LOG_FILE_PATH", "app.log")
        try:
            file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
            file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
            logger.addHandler(file_handler)
        except Exception as e:
            # If we can't write to file, just print a warning and continue with stream
            print(f"Warning: Could not setup file logging: {e}")

    return logger

# Global application logger
logger = setup_logger()
