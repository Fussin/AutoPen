import concurrent.futures
import re
import os
from typing import Set, List
from pathlib import Path
import logging

from .utils import load_config, run_command
from ...plugins.recon.subfinder import SubfinderPlugin
from ...common.utils import check_tool
from ...common.exceptions import ToolNotFoundError
from ...common.log import get_rich_logger as get_logger

config = load_config()
logger = get_logger(__name__)

def run_passive_enumeration(domain: str) -> Set[str]:
    """
    Run passive enumeration for domain and return set of discovered subdomains.
    """
    logger.info(f"Starting passive enumeration for: {domain}")
    all_subdomains: Set[str] = set()

    # --- Tool Definitions ---
    # Tool name from config -> install command
    recon_tools = {
        "amass": "go install -v github.com/owasp-amass/amass/v3/cmd/amass@latest",
        "assetfinder": "go install -v github.com/tomnomnom/assetfinder@latest",
        "subfinder": "go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest"
    }

    # --- Check for available tools ---
    available_tools = {}
    for tool, install_cmd in recon_tools.items():
        try:
            tool_path = check_tool(tool, install_cmd)
            available_tools[tool] = tool_path
            logger.info(f"[✓] {tool} found at {tool_path}")
        except ToolNotFoundError as e:
            logger.warning(f"[✘] {e.tool_name} not found. Skipping.")
            logger.warning(f"  To install, run: {e.install_cmd}")

    if not available_tools:
        logger.error("No reconnaissance tools found. Aborting passive enumeration.")
        return set()

    # --- Build commands for available tools ---
    commands = []
    if 'amass' in available_tools:
        commands.append([available_tools['amass'], 'enum', '-passive', '-d', '{domain}', '-o', '{output_file}'])
    if 'assetfinder' in available_tools:
        commands.append([available_tools['assetfinder'], '--subs-only', '{domain}'])
    if 'subfinder' in available_tools:
        commands.append([available_tools['subfinder'], '-d', '{domain}', '-o', '{output_file}'])

    # --- Run commands concurrently ---
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(commands)) as executor:
        future_to_cmd = {executor.submit(run_command, cmd, domain): cmd for cmd in commands}
        for future in concurrent.futures.as_completed(future_to_cmd):
            cmd = future_to_cmd[future]
            try:
                result = future.result()
                if result:
                    # Generic pattern to find subdomains of the target domain
                    pattern = re.compile(r'([a-zA-Z0-9\.\-\_]+\.' + re.escape(domain) + ')')
                    found = pattern.findall(str(result))
                    logger.info(f"Found {len(found)} subdomains with {' '.join(cmd)}")
                    for sub in found:
                        all_subdomains.add(sub.strip().lower())
            except Exception as e:
                logger.exception(f"Command {' '.join(cmd)} failed: {e}")

    logger.info(f"Total unique discovered subdomains for {domain}: {len(all_subdomains)}")
    return all_subdomains
