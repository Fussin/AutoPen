import os
import json
import logging
from typing import Dict, Any

log = logging.getLogger(__name__)

def get_results_dir(domain: str, scan_id: int) -> str:
    """Creates and returns the path to the results directory for a scan."""
    base_dir = "recon_results"
    results_dir = os.path.join(base_dir, f"{domain.replace('.', '_')}_{scan_id}")
    os.makedirs(results_dir, exist_ok=True)
    return results_dir

def save_to_json(filename: str, data: Dict[str, Any], results_dir: str) -> str:
    """Saves a dictionary to a JSON file in the specified directory."""
    filepath = os.path.join(results_dir, filename)
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4, default=str)
        log.info(f"Successfully saved results to {filepath}")
        return filepath
    except Exception as e:
        log.error(f"Error saving data to {filepath}: {e}")
        return ""
