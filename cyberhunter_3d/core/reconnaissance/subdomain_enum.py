import concurrent.futures
import json
from typing import Set, List, Dict

import subprocess
import tempfile
import os
from .utils import get_logger, load_config
from .passive_engine import run_passive_enumeration
from .active_engine import run_active_enumeration
from ...plugins.recon.dnsgen import DnsgenPlugin
from ...plugins.recon.gotator import GotatorPlugin
from .js_engine import run_js_enumeration, run_github_dorking
from .visual_recon import run_visual_recon
from .tech_fingerprinting import run_tech_fingerprinting
from .cloud_asset_enum import find_cloud_assets

logger = get_logger(__name__)

def generate_custom_wordlist(subdomains: Set[str]) -> str:
    """
    Generates a custom wordlist from a set of known subdomains.
    """
    custom_words = set()
    for sub in subdomains:
        parts = sub.split('.')
        if len(parts) > 2:
            subdomain_part = '.'.join(parts[:-2])
            for word in subdomain_part.replace('-', '.').split('.'):
                if word and not word.isnumeric():
                    custom_words.add(word)

    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
        wordlist_filename = tmp_file.name
        for word in custom_words:
            tmp_file.write(f"{word}\n")

    return wordlist_filename

def enumerate_subdomains_v2(domain: str) -> List[Dict[str, str]]:
    """
    Runs the full V2 reconnaissance pipeline.
    """
    config = load_config()
    logger.info(f"Starting V2 reconnaissance for: {domain}")

    # --- Initial Enumeration ---
    passive_findings = run_passive_enumeration(domain)
    active_findings = run_active_enumeration(domain)

    # We need to work with sets for efficiency
    raw_subdomains = passive_findings.union(active_findings)

    # --- Permutation Enumeration ---
    if raw_subdomains:
        logger.info("Starting permutation enumeration.")
        custom_wordlist_path = generate_custom_wordlist(raw_subdomains)

        dnsgen_plugin = DnsgenPlugin()
        gotator_plugin = GotatorPlugin()

        # For simplicity, running sequentially. Can be parallelized.
        dnsgen_findings = dnsgen_plugin.run(list(raw_subdomains), custom_wordlist_path)
        gotator_findings = gotator_plugin.run(list(raw_subdomains), custom_wordlist_path)

        perm_subdomains = {f['evidence']['poc'] for f in dnsgen_findings if f['status'] == 'success'}
        perm_subdomains.update({f['evidence']['poc'] for f in gotator_findings if f['status'] == 'success'})

        raw_subdomains.update(perm_subdomains)
        os.remove(custom_wordlist_path)
    else:
        logger.warning("No known subdomains to permute. Skipping permutation step.")


    logger.info(f"Total raw subdomains found from all engines: {len(raw_subdomains)}")

    # --- Downstream Pipeline ---
    master_subdomains = resolve_and_validate(raw_subdomains)
    # ... (rest of the pipeline remains)

    assets = [{'type': 'subdomain', 'value': sub} for sub in master_subdomains]
    return assets


def resolve_and_validate(subdomains: Set[str]) -> Set[str]:
    # ... (implementation remains)
    pass
