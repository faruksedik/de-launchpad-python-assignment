
"""Logging setup: DEBUG to file, INFO to console."""
import logging
from logging.handlers import RotatingFileHandler
from config import LOG_FILE

def setup_logger(name: str) -> logging.Logger:
    """Configure and return a logger that logs DEBUG to file and INFO to console,
    including the function name in the log message.

    Args:
        name: module logger name (usually __name__)

    Returns:
        logging.Logger: configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Return the existing logger instance if it already has handlers to prevent duplicates
    if logger.handlers:
        return logger

    # Define a single detailed formatter (includes function name: %(funcName)s)
    # Format: Timestamp - LogLevel - LoggerName - (FunctionName) - Message
    fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - (%(funcName)s) - %(message)s')

    # File handler (DEBUG+)
    # Logs all messages (DEBUG, INFO, WARNING, ERROR, CRITICAL) to the file.
    fh = RotatingFileHandler(filename=str(LOG_FILE), maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Console handler (INFO+)
    # Logs only INFO, WARNING, ERROR, and CRITICAL messages to the console.
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger
