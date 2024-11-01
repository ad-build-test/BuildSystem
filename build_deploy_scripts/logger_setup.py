# Logging setup for all build containers
import logging

class CustomFormatter(logging.Formatter):
    """Custom formatter to change the format based on log level."""
    
    def format(self, record):
        if record.levelno == logging.DEBUG: # Debug format empty
            self._style._fmt = '%(message)s'
        elif record.levelno == logging.INFO: # custom time format (YYYY-MM-DD HH:MM:SS)
            self._style._fmt = '%(asctime)s %(levelname)s - %(message)s'
        
        return super().format(record)

def setup_logger(filepath: str):
    logger = logging.getLogger('my_logger')
    if logger.hasHandlers():  # Check if the logger is already set up
        return logger

    logger.setLevel(logging.DEBUG)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)  # Set level for console

    # Create file handler
    file_handler = logging.FileHandler(filepath)
    file_handler.setLevel(logging.DEBUG)  # Set level for file

    # Create a formatter
    formatter = CustomFormatter(datefmt='%Y-%m-%d %H:%M:%S')

    # Set formatter for both handlers
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
