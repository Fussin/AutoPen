import concurrent.futures
import logging
from typing import Set, List

from .utils import get_logger
from ...common.utils import load_config
from ...plugins.recon.gobuster import GobusterPlugin
from ...plugins.recon.puredns import PureDNSPlugin
from ...plugins.recon.nmap_dns import NmapDnsPlugin

config = load_config()
logger = get_logger(__name__)

def run_active_enumeration(domain: str) -> Set[str]:
    """
    Runs active subdomain enumeration tools in parallel using plugins.
    """
    logger.info(f"Starting active enumeration for: {domain}")
    all_subdomains: Set[str] = set()

    wordlist = config['wordlists']['dns_bruteforce']
    resolvers = config['wordlists']['resolvers']

    # Instantiate plugins
    gobuster_plugin = GobusterPlugin()
    puredns_plugin = PureDNSPlugin()
    nmap_plugin = NmapDnsPlugin()

    # Create a dictionary mapping a plugin name to its instance and a zero-argument lambda runner
    plugin_runners = {
        "gobuster": (gobuster_plugin, lambda: gobuster_plugin.run([domain], wordlist=wordlist)),
        "puredns": (puredns_plugin, lambda: puredns_plugin.run([domain], wordlist=wordlist, resolvers=resolvers)),
        "nmap_dns": (nmap_plugin, lambda: nmap_plugin.run([domain])),
    }

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(plugin_runners)) as executor:
        # Filter plugins by dependencies and submit their runners to the executor
        future_to_plugin_name = {
            executor.submit(runner): name
            for name, (plugin, runner) in plugin_runners.items()
            if plugin.check_dependencies()
        }

        for future in concurrent.futures.as_completed(future_to_plugin_name):
            name = future_to_plugin_name[future]
            try:
                findings = future.result()
                if findings:
                    results = {f["evidence"]["poc"] for f in findings}
                    all_subdomains.update(results)
                    logger.info(f"Found {len(results)} subdomains with {name} plugin.")
            except Exception as exc:
                logger.error(f"Plugin '{name}' generated an exception: {exc}", exc_info=True)

    logger.info(f"Total unique active subdomains found: {len(all_subdomains)}")
    return all_subdomains
