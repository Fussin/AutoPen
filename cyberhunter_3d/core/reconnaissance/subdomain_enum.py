import json
import os
import subprocess
import tempfile
from typing import Set, List, Dict

from .utils import get_logger, load_config
from .passive_engine import run_passive_enumeration
from .active_engine import run_active_enumeration
from ..enrichment.enrichment_engine import run_enrichment_engine
from .js_engine import run_js_enumeration
from .cloud_asset_enum import find_cloud_assets

logger = get_logger(__name__)

def enumerate_subdomains_v2(domain: str) -> List[Dict[str, str]]:
    config = load_config()
    logger.info(f"Starting V2 reconnaissance for: {domain}")

    # --- Phase 1: Enumeration ---
    passive_findings = run_passive_enumeration(domain)
    active_findings = run_active_enumeration(domain)
    all_enum_findings = passive_findings + active_findings
    raw_subdomains = {f['evidence']['poc'] for f in all_enum_findings if f['status'] == 'success'}

    # --- Phase 2: Validation ---
    logger.info("Starting DNS resolution and validation...")
    master_subdomains = resolve_and_validate(raw_subdomains, config)
    logger.info(f"Found {len(master_subdomains)} valid subdomains.")

    # --- Phase 3: Enrichment & Analysis ---
    enrichment_findings = run_enrichment_engine(master_subdomains)
    js_findings = run_js_enumeration(master_subdomains)
    cloud_assets = find_cloud_assets(master_subdomains)

    # --- Final Report Generation ---
    screenshots = [f['evidence']['screenshot_dir'] for f in enrichment_findings if f['phase'] == 'enrichment-screenshot' and f['status'] == 'success']
    tech_results = {}
    for f in enrichment_findings:
        if f['phase'] == 'enrichment-service-scan' and f['status'] == 'success':
            host = f['target']
            if host not in tech_results:
                tech_results[host] = {'ports': []}
            tech_results[host]['ports'].append(f['evidence'])

    final_recon_data = {
        'domain': domain,
        'master_subdomains': sorted(list(master_subdomains)),
        'screenshots': screenshots,
        'technology_and_ports': tech_results,
        'js_findings': js_findings,
        'cloud_assets': cloud_assets,
    }

    final_recon_file = os.path.join(config['recon_output_dir'], config['final_recon_file'])
    os.makedirs(config['recon_output_dir'], exist_ok=True)
    with open(final_recon_file, 'w') as f_out:
        json.dump(final_recon_data, f_out, indent=4)

    assets = [{'type': 'subdomain', 'value': sub} for sub in master_subdomains]
    return assets

def resolve_and_validate(subdomains: Set[str], config: dict) -> Set[str]:
    if not subdomains: return set()
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
        input_filename = tmp_file.name
        for sub in subdomains: tmp_file.write(f"{sub}\n")
    resolved_subdomains = set()
    try:
        puredns_command = [config['tools']['puredns'], 'resolve', input_filename, '-r', config['wordlists']['resolvers'], '--quiet']
        result = subprocess.run(puredns_command, capture_output=True, text=True, check=True)
        for line in result.stdout.strip().split('\n'):
            if line: resolved_subdomains.add(line)
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        logger.error(f"Error during resolution with puredns: {e}")
    finally:
        os.remove(input_filename)
    return resolved_subdomains
