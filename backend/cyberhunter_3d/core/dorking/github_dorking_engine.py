from typing import Set, List, Dict

from ..reconnaissance.utils import get_logger
from ...plugins.dorking.gh_dork import GhDorkPlugin
from ...common.schema import Finding

logger = get_logger(__name__)

def run_github_dorking_engine(subdomains: Set[str]) -> List[Finding]:
    """
    Orchestrates the GitHub dorking phase.
    """
    logger.info(f"Starting GitHub dorking engine for {len(subdomains)} subdomains...")
    if not subdomains:
        logger.warning("No subdomains provided to GitHub dorking engine.")
        return []

    # Generate potential organization names from subdomains
    org_names = set()
    for sub in subdomains:
        if '.' in sub:
            # A simple heuristic: a.b.c -> b
            try:
                org = sub.split('.')[-2]
                if org and not org.isnumeric():
                    org_names.add(org)
            except IndexError:
                pass

    if not org_names:
        logger.warning("Could not derive any organization names for GitHub dorking.")
        return []

    dork_plugin = GhDorkPlugin()
    findings = dork_plugin.run(list(org_names))

    logger.info(f"GitHub dorking engine finished. Found {len(findings)} potential results.")
    return findings
