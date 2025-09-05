import concurrent.futures
import json
from typing import Set, List, Dict

import subprocess
import tempfile
import os
from .utils import get_logger, load_config
from .passive_engine import run_passive_enumeration
from .active_engine import run_active_enumeration
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
    logger.info(f"Starting V2 reconnaissance for: {domain}")
    config = load_config()

    raw_subdomains = set()

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        # Submit each engine to the executor
        passive_future = executor.submit(run_passive_enumeration, domain)
        # active_future = executor.submit(run_active_enumeration, domain)
        # permutation_future = executor.submit(run_permutation_enumeration, domain)
        # js_future = executor.submit(run_js_enumeration, domain)

        # Gather results as they complete
        passive_results = passive_future.result()
        raw_subdomains.update(passive_results)

        # For now, we will run the other engines sequentially on the results of the passive scan
        active_results = run_active_enumeration(domain)
        raw_subdomains.update(active_results)

        permutation_results = run_permutation_enumeration(domain, passive_results)
        raw_subdomains.update(permutation_results)

    logger.info(f"Total raw subdomains found from all engines: {len(raw_subdomains)}")

    # Step 1: DNS Resolution and Validation
    logger.info("Starting DNS resolution and validation...")
    master_subdomains = resolve_and_validate(raw_subdomains)
    logger.info(f"Found {len(master_subdomains)} valid subdomains after resolution.")

    # Create output directory if it doesn't exist
    output_dir = config['recon_output_dir']
    os.makedirs(output_dir, exist_ok=True)

    # Save to master_subdomains.txt
    master_subdomains_file = os.path.join(output_dir, config['master_subdomains_file'])
    with open(master_subdomains_file, 'w') as f:
        for sub in master_subdomains:
            f.write(f"{sub}\n")

    # Step 2: Live Host Detection and Visual Recon
    live_hosts, screenshots = run_visual_recon(master_subdomains)
    print(f"Found {len(live_hosts)} live hosts.")
    print(f"Screenshots saved in: {screenshots}")

    # Step 3: JS/Code Analysis
    js_findings = run_js_enumeration(live_hosts)

    # Step 4: Technology Fingerprinting and Port Scanning
    tech_results = run_tech_fingerprinting(live_hosts)

    # Step 5: Cloud Asset Identification
    cloud_assets = find_cloud_assets(master_subdomains)

    # Step 6: GitHub Dorking
    github_findings = run_github_dorking(master_subdomains)

    # Step 7: Consolidate all information into the final JSON structure
    final_recon_data = {
        'domain': domain,
        'master_subdomains': list(master_subdomains),
        'live_hosts': list(live_hosts),
        'screenshots': screenshots,
        'technology_and_ports': tech_results,
        'js_findings': list(js_findings),
        'cloud_assets': cloud_assets,
        'github_findings': github_findings,
    }

    final_recon_file = os.path.join(output_dir, config['final_recon_file'])
    with open(final_recon_file, 'w') as f_out:
        json.dump(final_recon_data, f_out, indent=4)

    # For now, just return the valid subdomains as assets
    assets = [{'type': 'subdomain', 'value': sub} for sub in master_subdomains]

    return assets


def resolve_and_validate(subdomains: Set[str]) -> Set[str]:
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
        # Use puredns to resolve and validate the subdomains
        puredns_command = [
            'puredns', 'resolve', input_filename,
            '-r', '/usr/share/seclists/Discovery/DNS/resolvers.txt',
            '--quiet'
        ]
        result = subprocess.run(puredns_command, capture_output=True, text=True, check=True)

        for line in result.stdout.strip().split('\n'):
            if line:
                resolved_subdomains.add(line)

    except FileNotFoundError:
        print("Error: 'puredns' not found. Please ensure it is installed and in your PATH.")
    except subprocess.CalledProcessError as e:
        print(f"Error running puredns for resolution: {e}\nOutput: {e.stderr}")
    finally:
        os.remove(input_filename)

    return resolved_subdomains
