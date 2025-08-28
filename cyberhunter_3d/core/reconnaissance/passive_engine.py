import subprocess
import tempfile
import os
import re
import concurrent.futures
from typing import Set, List

from cyberhunter_3d.utils.logger import setup_logger
from .utils import load_config, run_command

config = load_config()
logger = setup_logger('PassiveEngine', 'passive.log')

def run_passive_enumeration(domain: str) -> Set[str]:
    """
    Runs passive subdomain enumeration tools in parallel.
    """
    logger.info(f"Starting passive enumeration for: {domain}")

    commands = [
        [config['tools']['subfinder'], '-d', '{domain}', '-o', '{output_file}', '-silent'],
        [config['tools']['amass'], 'enum', '-passive', '-d', '{domain}', '-o', '{output_file}'],
        [config['tools']['assetfinder'], '--subs-only', '{domain}'],
        [config['tools']['waybackurls'], '{domain}'], # This one prints to stdout
    ]

    all_subdomains = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(commands)) as executor:
        future_to_command = {executor.submit(run_command, cmd, domain, logger): cmd for cmd in commands}
        for future in concurrent.futures.as_completed(future_to_command):
            command = future_to_command[future]
            try:
                subdomains = future.result()
                logger.info(f"Found {len(subdomains)} subdomains with {' '.join(command)}")
                all_subdomains.update(subdomains)
            except Exception as exc:
                logger.error(f"'{' '.join(command)}' generated an exception: {exc}")

    logger.info(f"Total unique passive subdomains found: {len(all_subdomains)}")
    return all_subdomains
