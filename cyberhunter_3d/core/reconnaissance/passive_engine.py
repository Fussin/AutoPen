import concurrent.futures
import logging
from typing import Set, List

from .utils import get_logger
from ...common.utils import load_config
from ...plugins.recon.subfinder import SubfinderPlugin
from ...plugins.recon.amass import AmassPlugin
from ...plugins.recon.assetfinder import AssetfinderPlugin

config = load_config()
logger = get_logger(__name__)

def run_passive_enumeration(domain: str) -> Set[str]:
    """
    Run passive enumeration for a domain using multiple plugins
    and return a set of discovered subdomains.
    """
    logger.info(f"Starting passive enumeration for: {domain}")
    all_subdomains: Set[str] = set()

    resilience_config = config.get('resilience', {})
    retries = resilience_config.get('retries', 1)
    timeout = resilience_config.get('timeout_passive', 300)

    plugins = [
        SubfinderPlugin(),
        AmassPlugin(),
        AssetfinderPlugin()
    ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(plugins)) as executor:
        # Schedule each plugin to run with resilience settings
        future_to_plugin = {
            executor.submit(plugin.run, [domain], retries=retries, timeout=timeout): plugin
            for plugin in plugins
        }

        for future in concurrent.futures.as_completed(future_to_plugin):
            plugin = future_to_plugin[future]
            try:
                findings = future.result()
                successful_findings = 0
                for finding in findings:
                    if finding['status'] == 'success':
                        all_subdomains.add(finding['evidence']['poc'])
                        successful_findings += 1
                    else:
                        logger.error(f"Plugin {plugin.name()} failed on target {finding['target']}: {finding['error']}")

                if successful_findings > 0:
                    logger.info(f"Found {successful_findings} subdomains with {plugin.name()} plugin.")

            except Exception as e:
                logger.exception(f"An unexpected error occurred with plugin {plugin.name()}: {e}")

    logger.info(f"Total discovered passive subdomains for {domain}: {len(all_subdomains)}")
    return all_subdomains
