import json
import os
import subprocess
import tempfile
import datetime
import collections
import concurrent.futures
from typing import Set, List, Dict

from .utils import get_logger, load_config
from .passive_engine import run_passive_enumeration
from .active_engine import run_active_enumeration
from .js_engine import run_js_enumeration
from .visual_recon import run_visual_recon
from .tech_fingerprinting import run_tech_fingerprinting
from .cloud_asset_enum import find_cloud_assets

logger = get_logger(__name__)

def enumerate_subdomains_v2(domain: str) -> List[Dict[str, str]]:
    """
    Runs the full V2 reconnaissance pipeline.
    """
    config = load_config()
    logger.info(f"Starting V2 reconnaissance for: {domain}")

    # --- Step 1: Subdomain Enumeration ---
    passive_subdomains = run_passive_enumeration(domain)
    active_subdomains = run_active_enumeration(domain)
    raw_subdomains = passive_subdomains.union(active_subdomains)

    # --- Step 2: DNS Resolution and Validation ---
    logger.info("Starting DNS resolution and validation...")
    master_subdomains = resolve_and_validate(raw_subdomains)
    logger.info(f"Found {len(master_subdomains)} valid subdomains after resolution.")

    # --- Step 3: Enrichment & Analysis ---
    live_hosts, screenshots = run_visual_recon(master_subdomains)
    tech_results = run_tech_fingerprinting(live_hosts)
    js_findings = run_js_enumeration(live_hosts) # This now returns List[Finding]
    cloud_assets = find_cloud_assets(master_subdomains)

    # --- Step 4: Final Report Generation ---
    final_recon_data = {
        'domain': domain,
        'master_subdomains': sorted(list(master_subdomains)),
        'live_hosts': sorted(list(live_hosts)),
        'screenshots': screenshots,
        'technology_and_ports': tech_results,
        'js_findings': js_findings, # Already in the correct format
        'cloud_assets': cloud_assets,
    }

    final_recon_file = os.path.join(config['recon_output_dir'], config['final_recon_file'])
    os.makedirs(config['recon_output_dir'], exist_ok=True)
    with open(final_recon_file, 'w') as f_out:
        json.dump(final_recon_data, f_out, indent=4)

    assets = [{'type': 'subdomain', 'value': sub} for sub in master_subdomains]
    return assets


def resolve_and_validate(subdomains: Set[str]) -> Set[str]:
    # ... (original implementation)
    pass
