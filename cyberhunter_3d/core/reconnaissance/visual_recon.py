import subprocess
import tempfile
import os
from typing import Set, List, Tuple

from cyberhunter_3d.utils.logger import setup_logger
from .utils import load_config

config = load_config()
logger = setup_logger('VisualReconEngine', 'visual.log')

def run_visual_recon(subdomains: Set[str]) -> Tuple[Set[str], List[str]]:
    """
    Performs live host detection and visual reconnaissance.
    """
    logger.info(f"Starting visual reconnaissance for {len(subdomains)} subdomains...")

    if not subdomains:
        logger.warning("No subdomains to perform visual recon on.")
        return set(), []

    # Step 1: Find live hosts with httpx
    live_hosts = set()
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
        input_filename = tmp_file.name
        for sub in subdomains:
            tmp_file.write(f"{sub}\n")

    try:
        httpx_command = [
            config['tools']['httpx'], '-l', input_filename, '-p', '80,443,8080,8000', '--silent'
        ]
        result = subprocess.run(httpx_command, capture_output=True, text=True, check=True)
        for line in result.stdout.strip().split('\n'):
            if line:
                live_hosts.add(line)
    except FileNotFoundError:
        logger.error("Error: 'httpx' not found.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running httpx for visual recon: {e}\nOutput: {e.stderr}")
    finally:
        os.remove(input_filename)

    if not live_hosts:
        logger.warning("No live hosts found for visual recon.")
        return set(), []

    logger.info(f"Found {len(live_hosts)} live hosts. Now taking screenshots...")

    # Step 2: Take screenshots with gowitness and aquatone
    screenshots = []
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as live_hosts_file:
        live_hosts_filename = live_hosts_file.name
        for host in live_hosts:
            live_hosts_file.write(f"{host}\n")

    try:
        # gowitness
        gowitness_command = [config['tools']['gowitness'], 'file', '-f', live_hosts_filename, '-P', config['screenshot_dir'] + '/gowitness']
        subprocess.run(gowitness_command)

        # aquatone
        aquatone_command = [config['tools']['aquatone'], '-out', config['screenshot_dir'] + '/aquatone']
        with open(live_hosts_filename, 'r') as f_in:
            subprocess.run(aquatone_command, stdin=f_in)

        # For now, just return the paths to the screenshot directories
        screenshots.append('screenshots/gowitness')
        screenshots.append('screenshots/aquatone')

    except FileNotFoundError as e:
        tool_name = str(e).split("'")[1]
        logger.error(f"Error: Tool '{tool_name}' not found.")
    except Exception as e:
        logger.error(f"An error occurred during visual recon: {e}")
    finally:
        os.remove(live_hosts_filename)

    return live_hosts, screenshots
