import json
import os
import subprocess
import tempfile
import datetime
import collections
from typing import Set, List, Dict

from .utils import get_logger, load_config
from .passive_engine import run_passive_enumeration
from .active_engine import run_active_enumeration
# ... (keep other imports)
from .permutation_engine import run_permutation_enumeration
from .js_engine import run_js_enumeration, run_github_dorking
from .visual_recon import run_visual_recon
from .tech_fingerprinting import run_tech_fingerprinting
from .cloud_asset_enum import find_cloud_assets

logger = get_logger(__name__)

def enumerate_subdomains_v2(domain: str) -> List[Dict[str, str]]:
    """
    Runs the full V2 reconnaissance pipeline.
    """
    config = load_config() # Moved from module level to function level
    logger.info(f"Starting V2 reconnaissance for: {domain}")
    start_time = datetime.datetime.now()

    # --- Phase 1: Subdomain Enumeration ---
    passive_findings = run_passive_enumeration(domain)
    active_findings = run_active_enumeration(domain)
    all_findings = passive_findings + active_findings

    raw_subdomains = sorted(list(set(
        f['evidence']['poc'] for f in all_findings if f['status'] == 'success'
    )))
    logger.info(f"Total raw unique subdomains found from all engines: {len(raw_subdomains)}")

    output_dir = config['recon_output_dir']
    os.makedirs(output_dir, exist_ok=True)

    all_subs_file = config['subdomains_all_file']
    with open(all_subs_file, 'w') as f:
        for sub in raw_subdomains:
            f.write(f"{sub}\n")
    logger.info(f"Raw subdomain list saved to {all_subs_file}")

    # --- Permutation scan ---
    permutation_results = run_permutation_enumeration(domain, set(raw_subdomains))
    raw_subdomains.extend(list(permutation_results))
    raw_subdomains = sorted(list(set(raw_subdomains)))

    # --- Step 2: DNS Resolution and Validation ---
    logger.info("Starting DNS resolution and validation...")
    master_subdomains = resolve_and_validate(set(raw_subdomains), config) # Pass config
    logger.info(f"Found {len(master_subdomains)} valid subdomains after resolution.")

    master_subdomains_file = config['master_subdomains_file']
    with open(master_subdomains_file, 'w') as f:
        for sub in master_subdomains:
            f.write(f"{sub}\n")

    # --- Metadata Generation ---
    end_time = datetime.datetime.now()
    metadata = {
        "domain": domain,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": (end_time - start_time).total_seconds(),
        "plugin_stats": collections.defaultdict(lambda: {"success": 0, "failed": 0}),
        "errors": []
    }
    for f in all_findings:
        stats = metadata["plugin_stats"][f['tool']]
        if f['status'] == 'success':
            stats['success'] += 1
        else:
            stats['failed'] += 1
            metadata["errors"].append(f)

    metadata_file = config['subdomains_metadata_file']
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=4)
    logger.info(f"Reconnaissance metadata saved to {metadata_file}")

    # --- Subsequent pipeline steps ---
    live_hosts, screenshots = run_visual_recon(master_subdomains)
    assets = [{'type': 'subdomain', 'value': sub} for sub in master_subdomains]
    return assets


def resolve_and_validate(subdomains: Set[str], config: dict) -> Set[str]:
    """
    Resolves a set of subdomains and filters out non-resolving ones.
    """
    if not subdomains:
        return set()

    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
        input_filename = tmp_file.name
        for sub in subdomains:
            tmp_file.write(f"{sub}\n")

    resolved_subdomains = set()
    try:
        puredns_path = config.get('tools', {}).get('puredns', 'puredns')
        resolvers_path = config.get('wordlists', {}).get('resolvers')
        if not resolvers_path:
            raise FileNotFoundError("Resolvers list not found in config.")

        puredns_command = [
            puredns_path, 'resolve', input_filename,
            '-r', resolvers_path,
            '--quiet'
        ]
        result = subprocess.run(puredns_command, capture_output=True, text=True, check=True)

        for line in result.stdout.strip().split('\n'):
            if line:
                resolved_subdomains.add(line)

    except FileNotFoundError as e:
        logger.error(f"Error during resolution: {e}. Please ensure puredns is installed and paths in config are correct.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running puredns for resolution: {e}\nOutput: {e.stderr}")
    finally:
        os.remove(input_filename)

    return resolved_subdomains
