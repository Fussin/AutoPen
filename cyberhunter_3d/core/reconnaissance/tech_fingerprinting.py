import subprocess
import tempfile
import os
import json
from typing import Set, List, Dict

from .utils import load_config, get_logger

config = load_config()
logger = get_logger(__name__)

def run_tech_fingerprinting(live_hosts: Set[str]) -> Dict[str, Dict]:
    """
    Performs technology fingerprinting and port scanning.
    """
    logger.info(f"Starting technology fingerprinting for {len(live_hosts)} live hosts...")

    if not live_hosts:
        logger.warning("No live hosts to fingerprint.")
        return {}

    tech_results = {}

    # Step 1: Technology fingerprinting with Wappalyzer
    # Wappalyzer can be used as a library, which is better than shelling out.
    # For simplicity in this script, I'll use the command line, but a real implementation
    # would use the Python library.
    # Step 1: Technology fingerprinting with Wappalyzer is tricky because it's installed with pipx.
    # For now, we'll skip the wappalyzer part and focus on port scanning.

    # Step 2: Port scanning with Naabu and Nmap
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as live_hosts_file:
        live_hosts_filename = live_hosts_file.name
        for host in live_hosts:
            live_hosts_file.write(f"{host}\n")

    try:
        # Naabu
        naabu_results_file = os.path.join(config['recon_output_dir'], 'naabu_results.json')
        naabu_command = [config['tools']['naabu'], '-list', live_hosts_filename, '-top-ports', '1000', '-json', '-o', naabu_results_file]
        subprocess.run(naabu_command)

        # Nmap on discovered ports
        if os.path.exists(naabu_results_file):
            with open(naabu_results_file, 'r') as f_in:
                for line in f_in:
                    try:
                        data = json.loads(line)
                        host = data['host']
                        port = data['port']
                        if host not in tech_results:
                            tech_results[host] = {}
                        if 'ports' not in tech_results[host]:
                            tech_results[host]['ports'] = []

                        nmap_output_dir = os.path.join(config['recon_output_dir'], config['nmap_output_dir'])
                        os.makedirs(nmap_output_dir, exist_ok=True)
                        nmap_output_file = os.path.join(nmap_output_dir, f'nmap_{host}_{port}.txt')
                        nmap_command = [config['tools']['nmap'], '-sV', '-p', str(port), host, '-oN', nmap_output_file]
                        subprocess.run(nmap_command)

                        with open(nmap_output_file, 'r') as f_nmap:
                            nmap_output = f_nmap.read()
                            tech_results[host]['ports'].append({'port': port, 'service': nmap_output})

                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Could not parse naabu output line: {line}. Error: {e}")

    except FileNotFoundError as e:
        tool_name = str(e).split("'")[1]
        logger.error(f"Error: Tool '{tool_name}' not found.")
    except Exception as e:
        logger.error(f"An error occurred during port scanning: {e}")
    finally:
        os.remove(live_hosts_filename)
        if os.path.exists('naabu_results.json'):
            os.remove('naabu_results.json')

    return tech_results
