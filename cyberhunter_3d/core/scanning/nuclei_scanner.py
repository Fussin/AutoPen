import subprocess
import tempfile
import os
import json
from typing import List, Dict, Any

from ...common.log import get_rich_logger as get_logger
from ...common.utils import check_tool, load_config
from ...common.exceptions import ToolNotFoundError

logger = get_logger(__name__)
config = load_config()

def run_nuclei_scan(targets: List[str], output_dir: str) -> str:
    """
    Runs Nuclei on a list of targets and returns the path to the output file.

    Args:
        targets: A list of URLs to scan.
        output_dir: The directory to store the Nuclei output file.

    Returns:
        The path to the Nuclei output file.
    """
    logger.info(f"Starting Nuclei scan on {len(targets)} targets.")

    try:
        nuclei_path = check_tool("nuclei")
    except ToolNotFoundError as e:
        logger.error(f"[✘] {e.tool_name} not found. Aborting Nuclei scan.")
        logger.error(f"  To install, run: {e.install_cmd}")
        return ""

    nuclei_config = config.get('settings', {}).get('nuclei', {})
    templates = nuclei_config.get('templates', [])
    severity = nuclei_config.get('severity', 'medium,high,critical')

    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "nuclei_results.json")

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt") as f:
        f.write('\n'.join(targets))
        targets_file = f.name

    try:
        command = [
            nuclei_path,
            '-l', targets_file,
            '-t', ','.join(templates),
            '-s', severity,
            '-json',
            '-o', output_file,
            '-c', str(nuclei_config.get('concurrency', 20)),
        ]

        logger.info(f"Running Nuclei command: {' '.join(command)}")
        subprocess.run(command, capture_output=True, text=True, check=True)
        logger.info(f"Nuclei scan finished. Results saved to: {output_file}")

        return output_file

    except subprocess.CalledProcessError as e:
        logger.error(f"Nuclei scan failed with exit code {e.returncode}:")
        logger.error(e.stderr)
        return ""
    except Exception as e:
        logger.error(f"An unexpected error occurred during Nuclei scan: {e}")
        return ""
    finally:
        os.remove(targets_file)
