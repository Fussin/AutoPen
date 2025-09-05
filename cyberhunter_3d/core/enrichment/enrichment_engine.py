import concurrent.futures
from typing import List, Dict, Set

from ..reconnaissance.utils import get_logger, load_config
from ...plugins.enrichment.httpx import HttpxPlugin
from ...plugins.enrichment.gowitness import GowitnessPlugin
from ...plugins.enrichment.aquatone import AquatonePlugin
from ...plugins.enrichment.naabu import NaabuPlugin
from ...plugins.enrichment.nmap_scan import NmapScanPlugin
from ...common.schema import Finding

config = load_config()
logger = get_logger(__name__)

def run_enrichment_engine(subdomains: Set[str]) -> List[Finding]:
    """
    Orchestrates the enrichment phase of the pipeline.
    """
    logger.info(f"Starting enrichment engine for {len(subdomains)} subdomains.")
    all_findings: List[Finding] = []

    if not subdomains:
        logger.warning("No subdomains provided to enrichment engine.")
        return all_findings

    # Step 1: Discover live hosts
    httpx_plugin = HttpxPlugin()
    live_host_findings = httpx_plugin.run(list(subdomains))
    live_urls = [f['evidence']['live_url'] for f in live_host_findings if f['status'] == 'success']
    all_findings.extend(live_host_findings)

    if not live_urls:
        logger.warning("No live hosts found from subdomains. Ending enrichment phase.")
        return all_findings

    logger.info(f"Found {len(live_urls)} live URLs. Starting parallel enrichment tasks.")

    # Step 2: Run screenshot and portscan plugins in parallel on live URLs
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        screenshot_plugins = [GowitnessPlugin(), AquatonePlugin()]
        naabu_plugin = NaabuPlugin()

        screenshot_futures = {executor.submit(p.run, live_urls) for p in screenshot_plugins}
        naabu_future = executor.submit(naabu_plugin.run, live_urls)

        for future in concurrent.futures.as_completed(screenshot_futures):
            all_findings.extend(future.result())

        naabu_findings = naabu_future.result()
        all_findings.extend(naabu_findings)

    # Step 3: Run detailed Nmap scan on ports found by Naabu
    naabu_successes = [f for f in naabu_findings if f['status'] == 'success']
    if naabu_successes:
        nmap_targets = [{'host': f['target'], 'port': f['evidence']['port']} for f in naabu_successes]
        logger.info(f"Found {len(nmap_targets)} open ports. Starting detailed Nmap service scans.")
        nmap_plugin = NmapScanPlugin()
        nmap_findings = nmap_plugin.run(nmap_targets)
        all_findings.extend(nmap_findings)

    logger.info("Enrichment engine phase complete.")
    return all_findings
