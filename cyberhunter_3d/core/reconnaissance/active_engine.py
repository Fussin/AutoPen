import concurrent.futures
import logging
from typing import Set, List, Dict

from .utils import get_logger
from ...common.utils import load_config
from ...common.schema import Finding
from ...plugins.recon.gobuster import GobusterPlugin
from ...plugins.recon.puredns import PureDNSPlugin
from ...plugins.recon.nmap_dns import NmapDnsPlugin

config = load_config()
logger = get_logger(__name__)

def run_active_enumeration(domain: str) -> List[Finding]:
    """
    Runs active subdomain enumeration tools in parallel using plugins.
    """
    logger.info(f"Starting active enumeration for: {domain}")
    all_findings: List[Finding] = []

    # Load resilience and wordlist settings from config
    resilience_config = config.get('resilience', {})
    retries = resilience_config.get('retries', 1)
    timeout = resilience_config.get('timeout_active', 600)
    wordlist = config['wordlists']['dns_bruteforce']
    resolvers = config['wordlists']['resolvers']

    # Instantiate plugins
    gobuster_plugin = GobusterPlugin()
    puredns_plugin = PureDNSPlugin()
    nmap_plugin = NmapDnsPlugin()

    # Create a dictionary mapping a plugin name to its instance and a zero-argument lambda runner
    plugin_runners = {
        "gobuster": (gobuster_plugin, lambda: gobuster_plugin.run([domain], wordlist=wordlist, retries=retries, timeout=timeout)),
        "puredns": (puredns_plugin, lambda: puredns_plugin.run([domain], wordlist=wordlist, resolvers=resolvers, retries=retries, timeout=timeout)),
        "nmap_dns": (nmap_plugin, lambda: nmap_plugin.run([domain], retries=retries, timeout=timeout)),
    }

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(plugin_runners)) as executor:
        future_to_plugin_name = {
            executor.submit(runner): name
            for name, (plugin, runner) in plugin_runners.items()
            if plugin.check_dependencies()
        }

        for future in concurrent.futures.as_completed(future_to_plugin_name):
            name = future_to_plugin_name[future]
            try:
                findings = future.result()
                all_findings.extend(findings)

                # Log summary for this plugin run
                successful_findings = sum(1 for f in findings if f['status'] == 'success')
                failed_findings = len(findings) - successful_findings
                if successful_findings > 0:
                    logger.info(f"Plugin {name} found {successful_findings} subdomains.")
                if failed_findings > 0:
                    logger.warning(f"Plugin {name} reported {failed_findings} failures.")

            except Exception as exc:
                logger.exception(f"An unexpected error occurred with plugin {name}: {exc}")

    successful_count = sum(1 for f in all_findings if f['status'] == 'success')
    logger.info(f"Active enumeration complete. Total successful findings: {successful_count}")
    return all_findings
