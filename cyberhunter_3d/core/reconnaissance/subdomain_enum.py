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
from .js_engine import run_js_enumeration, run_github_dorking
from ..enrichment.enrichment_engine import run_enrichment_engine # Assuming this exists from previous work
from .cloud_asset_enum import find_cloud_assets

logger = get_logger(__name__)

def enumerate_subdomains_v2(domain: str) -> List[Dict[str, str]]:
    """
    Runs the full V2 reconnaissance pipeline.
    """
    config = load_config()
    logger.info(f"Starting V2 reconnaissance for: {domain}")
    start_time = datetime.datetime.now()

    # --- Phase 1: Subdomain Enumeration ---
    passive_findings = run_passive_enumeration(domain)
    active_findings = run_active_enumeration(domain)
    all_enum_findings = passive_findings + active_findings

    final_raw_subdomains = sorted(list(set(
        f['evidence']['poc'] for f in all_enum_findings if f['status'] == 'success'
    )))
    logger.info(f"Total raw unique subdomains found: {len(final_raw_subdomains)}")

    output_dir = config['recon_output_dir']
    os.makedirs(output_dir, exist_ok=True)

    # --- Phase 2: Validation ---
    logger.info("Starting DNS resolution and validation...")
    master_subdomains = resolve_and_validate(set(final_raw_subdomains), config)
    logger.info(f"Found {len(master_subdomains)} valid subdomains.")

    # --- Phase 3: Enrichment & Analysis ---
    enrichment_findings = run_enrichment_engine(master_subdomains)
    js_findings = run_js_enumeration(master_subdomains) # Use master_subdomains as input
    github_findings = run_github_dorking(master_subdomains)
    cloud_assets = find_cloud_assets(master_subdomains)

    all_findings = all_enum_findings + enrichment_findings + js_findings

    # --- Final Report Generation ---
    end_time = datetime.datetime.now()
    # ... (metadata generation logic)

    # Process enrichment findings for final report
    screenshots = [f['evidence']['screenshot_dir'] for f in enrichment_findings if f['phase'] == 'enrichment-screenshot' and f['status'] == 'success']
    tech_results = collections.defaultdict(lambda: {"ports": []})
    for f in enrichment_findings:
        if f['phase'] == 'enrichment-service-scan' and f['status'] == 'success':
            tech_results[f['target']]['ports'].append(f['evidence'])

    final_recon_data = {
        'domain': domain,
        'master_subdomains': list(master_subdomains),
        'screenshots': screenshots,
        'technology_and_ports': tech_results,
        'js_findings': js_findings,
        'cloud_assets': cloud_assets,
        'github_findings': github_findings,
    }
    with open(config.get('final_recon_file', 'final_recon_data.json'), 'w') as f_out:
        json.dump(final_recon_data, f_out, indent=4)

    assets = [{'type': 'subdomain', 'value': sub} for sub in master_subdomains]
    return assets


def resolve_and_validate(subdomains: Set[str], config: dict) -> Set[str]:
    # ... (implementation remains)
    pass
