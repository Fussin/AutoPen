import subprocess
import tempfile
import os
import re
import concurrent.futures
from typing import Set, List

from .utils import load_config, get_logger, run_command

config = load_config()
logger = get_logger(__name__)

def run_active_enumeration(domain: str) -> Set[str]:
    """
    Runs active subdomain enumeration tools in parallel.
    """
    logger.info(f"Starting active enumeration for: {domain}")

    wordlist = config['wordlists']['dns_bruteforce']
    resolvers = config['wordlists']['resolvers']

    commands = [
        [config['tools']['gobuster'], 'dns', '-d', '{domain}', '-w', wordlist, '-o', '{output_file}', '-q'],
        [config['tools']['puredns'], 'bruteforce', wordlist, '{domain}', '-r', resolvers, '-w', '{output_file}'],
        [config['tools']['nmap'], '--script', 'dns-zone-transfer', '-p', '53', '{domain}', '-oN', '{output_file}']
    ]

    all_subdomains = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(commands)) as executor:
        future_to_command = {executor.submit(run_command, cmd, domain, wordlist): cmd for cmd in commands}
        for future in concurrent.futures.as_completed(future_to_command):
            command = future_to_command[future]
            try:
                subdomains = future.result()
                logger.info(f"Found {len(subdomains)} subdomains with {' '.join(command)}")
                all_subdomains.update(subdomains)
            except Exception as exc:
                logger.error(f"'{' '.join(command)}' generated an exception: {exc}")

    logger.info(f"Total unique active subdomains found: {len(all_subdomains)}")
    return all_subdomains
