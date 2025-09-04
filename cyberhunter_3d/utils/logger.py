import logging
import os
import sys

LOGS_DIR = "logs"

def setup_logger(log_file: str, level=logging.INFO):
    """
    Sets up the root logger to write to both the console and a specified file.
    """
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)

    log_path = os.path.join(LOGS_DIR, log_file)

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # To prevent duplicate logs if the logger is already configured,
    # clear existing handlers.
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Create a formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create a handler for the console
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    # Create a handler for the file
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    return root_logger
