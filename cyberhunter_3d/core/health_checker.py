import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)

def check_command(command: str) -> bool:
    """
    Checks if a command is available in the system's PATH.

    Args:
        command (str): The command to check.

    Returns:
        bool: True if the command is available, False otherwise.
    """
    return shutil.which(command) is not None

def run_health_checks():
    """
    Runs a series of health checks to ensure the environment is set up correctly.
    """
    logger.info("Running pre-scan health checks...")
    all_checks_passed = True

    # Check for essential command-line tools
    required_tools = ["amass", "nmap", "subfinder", "httpx", "gowitness", "subzy"]
    for tool in required_tools:
        if not check_command(tool):
            logger.error(f"Health check failed: Required tool '{tool}' not found in PATH.")
            all_checks_passed = False
        else:
            logger.info(f"Health check passed: Found required tool '{tool}'.")

    # In the future, we can add more checks here, such as:
    # - Verifying API keys are set
    # - Checking for write permissions to the results directory
    # - Ensuring database connectivity

    if all_checks_passed:
        logger.info("All health checks passed successfully.")
    else:
        logger.warning("Some health checks failed. The scan may not run as expected.")

    return all_checks_passed
