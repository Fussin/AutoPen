import concurrent.futures
import re
import os
from typing import Set, List
from pathlib import Path
import logging

from .utils import load_config, get_logger, run_command
from ...plugins.recon.subfinder import SubfinderPlugin

config = load_config()
logger = get_logger(__name__)

def run_passive_enumeration(domain: str) -> Set[str]:
    """
    Run passive enumeration for domain and return set of discovered subdomains.
    """
    logger.info(f"Starting passive enumeration for: {domain}")
    all_subdomains: Set[str] = set()

    # --- Refactored: Use the Subfinder plugin ---
    try:
        subfinder_plugin = SubfinderPlugin()
        if subfinder_plugin.check_dependencies():
            subfinder_findings = subfinder_plugin.run([domain])
            subfinder_results = {f["evidence"]["poc"] for f in subfinder_findings}
            all_subdomains.update(subfinder_results)
            logger.info(f"Found {len(subfinder_results)} subdomains with Subfinder plugin.")
        else:
            logger.warning("Subfinder plugin reports missing dependencies; skipping.")
    except Exception as e:
        logger.exception(f"Error running Subfinder plugin: {e}")

    # --- Keep other command-line tools for now ---
    commands = [
        [config['tools']['amass'], 'enum', '-passive', '-d', '{domain}', '-o', '{output_file}'],
        [config['tools']['assetfinder'], '--subs-only', '{domain}'],
    ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(commands)) as executor:
        future_to_cmd = {executor.submit(run_command, cmd, domain): cmd for cmd in commands}
        for future in concurrent.futures.as_completed(future_to_cmd):
            cmd = future_to_cmd[future]
            try:
                result = future.result()
                if result:
                    pattern = re.compile(r'([A-Za-z0-9\-\_\.]*\.' + re.escape(domain) + ')')
                    for m in pattern.findall(str(result)):
                        all_subdomains.add(m)
            except Exception as e:
                logger.exception(f"Command {cmd} failed: {e}")

    logger.info(f"Total discovered subdomains for {domain}: {len(all_subdomains)}")
    return all_subdomains
