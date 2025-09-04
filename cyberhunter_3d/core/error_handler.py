import logging
import time
from functools import wraps

# Get a logger instance
logger = logging.getLogger(__name__)

# Custom Exception Classes for Error Classification
class ModuleError(Exception):
    """Base exception for module-related errors."""
    pass

class CriticalError(ModuleError):
    """For errors that should stop the execution of a major pipeline component."""
    pass

class MinorError(ModuleError):
    """For errors that can be recovered from, allowing the pipeline to continue."""
    pass

def handle_module_errors(retries=1, delay=2, fallback_return=None, error_severity=MinorError):
    """
    A decorator to handle errors in reconnaissance modules gracefully.

    Args:
        retries (int): The number of times to retry the decorated function.
        delay (int): The delay in seconds between retries.
        fallback_return: The value to return if the function fails after all retries.
        error_severity (Exception): The type of error to raise if all retries fail.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        f"Attempt {attempt + 1}/{retries} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay} seconds..."
                    )
                    time.sleep(delay)

            logger.error(f"All {retries} retries failed for {func.__name__}. Last error: {last_exception}")

            # If a fallback is defined, return it to allow for graceful degradation
            if fallback_return is not None:
                logger.info(f"Returning fallback value for {func.__name__}: {fallback_return}")
                return fallback_return

            # Otherwise, raise the specified error to be handled by the caller
            raise error_severity(f"Module {func.__name__} failed permanently.") from last_exception

        return wrapper
    return decorator
