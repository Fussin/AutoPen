import concurrent.futures
from typing import Set, List, Dict

from .utils import get_logger
from ...plugins.js_analysis.linkfinder import LinkfinderPlugin
from ...plugins.js_analysis.nuclei_js_secrets import NucleiJsSecretsPlugin
from ...common.schema import Finding

logger = get_logger(__name__)

def run_js_enumeration(live_hosts: Set[str]) -> List[Finding]:
    """
    Runs JS/Code analysis tools in parallel using plugins.
    """
    logger.info(f"Starting JS/Code analysis for {len(live_hosts)} live hosts...")
    if not live_hosts:
        logger.warning("No live hosts to analyze. Skipping JS/Code analysis engine.")
        return []

    all_findings: List[Finding] = []

    linkfinder_plugin = LinkfinderPlugin()
    nuclei_plugin = NucleiJsSecretsPlugin()

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        linkfinder_futures = {executor.submit(linkfinder_plugin.run, [host]) for host in live_hosts}
        nuclei_future = executor.submit(nuclei_plugin.run, list(live_hosts))

        for future in concurrent.futures.as_completed(linkfinder_futures):
            try:
                all_findings.extend(future.result())
            except Exception as exc:
                logger.error(f"A Linkfinder task generated an exception: {exc}")

        try:
            all_findings.extend(nuclei_future.result())
        except Exception as exc:
            logger.error(f"The Nuclei JS secrets task generated an exception: {exc}")

    logger.info(f"Total findings from JS/Code analysis: {len(all_findings)}")
    return all_findings
