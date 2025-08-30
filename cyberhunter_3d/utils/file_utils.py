import subprocess
import logging
import os
import json
from typing import Dict, Any

log = logging.getLogger(__name__)

def get_results_dir(domain: str, scan_id: int) -> str:
    """Creates and returns the path to the results directory for a scan."""
    # This would typically read a base path from a config file
    base_dir = "recon_results"
    results_dir = os.path.join(base_dir, f"{domain.replace('.', '_')}_{scan_id}")
    os.makedirs(results_dir, exist_ok=True)
    return results_dir

def save_to_json(filename: str, data: Dict[str, Any], results_dir: str) -> str:
    """Saves a dictionary to a JSON file in the specified directory."""
    filepath = os.path.join(results_dir, filename)
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
        log.info(f"Successfully saved results to {filepath}")
        return filepath
    except Exception as e:
        log.error(f"Error saving data to {filepath}: {e}")
        return ""

def run_command(command: list) -> str:
    """
    Runs a command and returns its stdout.
    Raises an exception if the command fails.
    """
    try:
        process = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        return process.stdout
    except FileNotFoundError:
        log.error(f"Command not found: {command[0]}")
        raise
    except subprocess.CalledProcessError as e:
        log.error(f"Command '{' '.join(command)}' failed with exit code {e.returncode}")
        log.error(f"Stderr: {e.stderr}")
        raise
    except Exception as e:
        log.error(f"An unexpected error occurred while running command: {' '.join(command)}")
        log.error(f"Error: {e}")
        raise
