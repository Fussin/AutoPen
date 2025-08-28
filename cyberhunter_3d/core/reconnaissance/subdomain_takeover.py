import subprocess
import tempfile
import os
import json
from typing import List, Dict
from cyberhunter_3d.utils.logger import setup_logger
from .utils import load_config

logger = setup_logger('TakeoverEngine', 'takeover.log')
config = load_config()

def run_takeover_scan(subdomains: List[str]) -> List[Dict]:
    """
    Checks for subdomain takeover vulnerabilities using Nuclei.

    Args:
        subdomains: A list of subdomains to check.

    Returns:
        A list of dictionaries, where each dictionary represents a vulnerability found.
    """
    if not subdomains:
        logger.info("No subdomains provided for takeover scan.")
        return []

    nuclei_path = config['tools'].get('nuclei')
    if not nuclei_path or not os.path.exists(nuclei_path):
        logger.error("Nuclei tool not found or path not configured in recon_config.yaml. Skipping takeover scan.")
        return []

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as tmp_file:
        for subdomain in subdomains:
            tmp_file.write(f"{subdomain}\n")
        target_file = tmp_file.name

    logger.info(f"Starting subdomain takeover scan on {len(subdomains)} subdomains.")

    # Using Nuclei with the 'takeovers' template tag, which is a curated list for this purpose.
    # The output is in JSON format for easy parsing.
    command = [
        nuclei_path,
        "-l", target_file,
        "-t", "takeovers", # This tag filters for takeover templates
        "-json",
        "-silent", # Suppress progress bar and other noisy output
    ]

    vulnerabilities = []
    try:
        # We use subprocess.PIPE and text=True to capture stdout line by line
        # This is because Nuclei outputs a stream of JSON objects, not a single one
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')

        for line in process.stdout:
            try:
                if line.strip():
                    vulnerabilities.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning(f"Could not decode JSON line from Nuclei output: {line.strip()}")

        stderr_output = process.communicate()[1]
        if process.returncode != 0:
            logger.error(f"Nuclei process finished with error code {process.returncode}. Stderr: {stderr_output}")

    except FileNotFoundError:
        logger.error(f"Nuclei executable not found at '{nuclei_path}'. Please check your recon_config.yaml.")
    except Exception as e:
        logger.error(f"An unexpected error occurred while running Nuclei: {e}")
    finally:
        os.remove(target_file)

    logger.info(f"Subdomain takeover scan complete. Found {len(vulnerabilities)} potential vulnerabilities.")
    return vulnerabilities
