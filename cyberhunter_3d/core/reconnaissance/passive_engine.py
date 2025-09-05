import concurrent.futures
import logging
from typing import Set, List

from .utils import get_logger
from ...plugins.recon.subfinder import SubfinderPlugin
from ...plugins.recon.amass import AmassPlugin
from ...plugins.recon.assetfinder import AssetfinderPlugin

logger = get_logger(__name__)

def run_passive_enumeration(domain: str) -> Set[str]:
    """
    Run passive enumeration for a domain using multiple plugins
    and return a set of discovered subdomains.
    """
    logger.info(f"Starting passive enumeration for: {domain}")
    all_subdomains: Set[str] = set()

    plugins = [
        SubfinderPlugin(),
        AmassPlugin(),
        AssetfinderPlugin()
    ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(plugins)) as executor:
        # Schedule each plugin to run
        future_to_plugin = {executor.submit(plugin.run, [domain]): plugin for plugin in plugins}

        for future in concurrent.futures.as_completed(future_to_plugin):
            plugin = future_to_plugin[future]
            try:
                findings = future.result()
                if findings:
                    # Extract the subdomain from the 'poc' field in evidence
                    results = {f["evidence"]["poc"] for f in findings}
                    all_subdomains.update(results)
                    logger.info(f"Found {len(results)} subdomains with {plugin.name()} plugin.")
            except Exception as e:
                logger.exception(f"Plugin {plugin.name()} failed: {e}")

    logger.info(f"Total discovered passive subdomains for {domain}: {len(all_subdomains)}")
    return all_subdomains
