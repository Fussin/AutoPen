import logging
from rich.logging import RichHandler

def get_rich_logger(name: str) -> logging.Logger:
    """
    Returns a logger that uses rich for beautiful, colored output.
    """
    # Create a logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Prevent the logger from propagating messages to the root logger
    logger.propagate = False

    # Check if the logger already has handlers
    if not logger.handlers:
        # Create a handler with rich formatting
        handler = RichHandler(
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            markup=True
        )
        # Set the formatter for the handler
        formatter = logging.Formatter(
            fmt="%(message)s",
            datefmt="[%X]"
        )
        handler.setFormatter(formatter)
        # Add the handler to the logger
        logger.addHandler(handler)

    return logger
