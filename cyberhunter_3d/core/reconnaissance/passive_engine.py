import concurrent.futures
import logging
from typing import Set, List, Dict

from .utils import get_logger
from ...common.utils import load_config
from ...common.schema import Finding
from ...plugins.recon.subfinder import SubfinderPlugin
from ...plugins.recon.amass import AmassPlugin
from ...plugins.recon.assetfinder import AssetfinderPlugin

config = load_config()
logger = get_logger(__name__)

def run_passive_enumeration(domain: str) -> List[Finding]:
    """
    Run passive enumeration for a domain using multiple plugins
    and return a list of Finding objects.
    """
    logger.info(f"Starting passive enumeration for: {domain}")
    all_findings: List[Finding] = []

    resilience_config = config.get('resilience', {})
    retries = resilience_config.get('retries', 1)
    timeout = resilience_config.get('timeout_passive', 300)

    plugins = [
        SubfinderPlugin(),
        AmassPlugin(),
        AssetfinderPlugin()
    ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(plugins)) as executor:
        future_to_plugin = {
            executor.submit(plugin.run, [domain], retries=retries, timeout=timeout): plugin
            for plugin in plugins
        }

        for future in concurrent.futures.as_completed(future_to_plugin):
            plugin = future_to_plugin[future]
            try:
                findings = future.result()
                all_findings.extend(findings)

                # Log summary for this plugin run
                successful_findings = sum(1 for f in findings if f['status'] == 'success')
                failed_findings = len(findings) - successful_findings
                if successful_findings > 0:
                    logger.info(f"Plugin {plugin.name()} found {successful_findings} subdomains.")
                if failed_findings > 0:
                    logger.warning(f"Plugin {plugin.name()} reported {failed_findings} failures.")

            except Exception as e:
                logger.exception(f"An unexpected error occurred with plugin {plugin.name()}: {e}")

    successful_count = sum(1 for f in all_findings if f['status'] == 'success')
    logger.info(f"Passive enumeration complete. Total successful findings: {successful_count}")
    return all_findings
