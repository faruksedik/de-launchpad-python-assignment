import logging
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = "logs"
# Ensure the log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

def get_logger(name=__name__):
    """
    Configures and returns a logger instance.

    Both the file log and the console log will use the same detailed format, 
    which includes the function name.
    """
    logger = logging.getLogger(name)
    # Prevent adding multiple handlers if the logger is retrieved multiple times
    if logger.handlers:
        return logger

    # Set the minimum logging level for the logger instance
    logger.setLevel(logging.DEBUG)

    # Define a single detailed formatter (includes function name: %(funcName)s)
    # Format: Timestamp - LogLevel - LoggerName - (FunctionName) - Message
    fmt = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - (%(funcName)s) - %(message)s"
    )

    # 1. File Handler (Detailed Log to logs/app.log)
    fh = RotatingFileHandler(
        os.path.join(LOG_DIR, "app.log"),
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding='utf-8'
    )
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