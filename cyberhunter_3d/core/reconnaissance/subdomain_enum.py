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
from ...plugins.recon.dnsgen import DnsgenPlugin
from ...plugins.recon.gotator import GotatorPlugin
from .js_engine import run_js_enumeration, run_github_dorking
from .visual_recon import run_visual_recon
from .tech_fingerprinting import run_tech_fingerprinting
from .cloud_asset_enum import find_cloud_assets

logger = get_logger(__name__)

def generate_custom_wordlist(subdomains: List[str]) -> str:
    """Generates a custom wordlist from a set of known subdomains."""
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
        tmp_file.write('\n'.join(custom_words))
    return wordlist_filename

def enumerate_subdomains_v2(domain: str) -> List[Dict[str, str]]:
    """Runs the full V2 reconnaissance pipeline."""
    config = load_config()
    logger.info(f"Starting V2 reconnaissance for: {domain}")
    start_time = datetime.datetime.now()

    # --- Phase 1: Subdomain Enumeration (Passive & Active) ---
    passive_findings = run_passive_enumeration(domain)
    active_findings = run_active_enumeration(domain)
    all_findings = passive_findings + active_findings

    initial_raw_subdomains = sorted(list(set(
        f['evidence']['poc'] for f in all_findings if f['status'] == 'success'
    )))

    # --- Phase 2: Permutation Enumeration ---
    if initial_raw_subdomains:
        logger.info("Starting permutation enumeration.")
        custom_wordlist = generate_custom_wordlist(initial_raw_subdomains)

        perm_plugins = [DnsgenPlugin(), GotatorPlugin()]
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(perm_plugins)) as executor:
            future_to_plugin = {
                executor.submit(p.run, subdomains=initial_raw_subdomains, wordlist_path=custom_wordlist): p
                for p in perm_plugins
            }
            for future in concurrent.futures.as_completed(future_to_plugin):
                perm_findings = future.result()
                all_findings.extend(perm_findings)

        os.remove(custom_wordlist)
    else:
        logger.warning("No known subdomains to permute. Skipping permutation step.")

    # --- Post-Enumeration Processing ---
    final_raw_subdomains = sorted(list(set(
        f['evidence']['poc'] for f in all_findings if f['status'] == 'success'
    )))
    logger.info(f"Total raw unique subdomains found from all engines: {len(final_raw_subdomains)}")

    output_dir = config['recon_output_dir']
    os.makedirs(output_dir, exist_ok=True)

    with open(config['subdomains_all_file'], 'w') as f:
        f.write('\n'.join(final_raw_subdomains))
    logger.info(f"Raw subdomain list saved to {config['subdomains_all_file']}")

    logger.info("Starting DNS resolution and validation...")
    master_subdomains = resolve_and_validate(set(final_raw_subdomains), config)
    logger.info(f"Found {len(master_subdomains)} valid subdomains after resolution.")

    with open(config['master_subdomains_file'], 'w') as f:
        f.write('\n'.join(master_subdomains))

    # --- Metadata Generation ---
    end_time = datetime.datetime.now()
    metadata = {
        "domain": domain,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_seconds": (end_time - start_time).total_seconds(),
        "plugin_stats": collections.defaultdict(lambda: {"success": 0, "failed": 0, "input_count": 0, "output_count": 0}),
        "errors": []
    }
    for f in all_findings:
        stats = metadata["plugin_stats"][f['tool']]
        if f['status'] == 'success':
            stats['success'] += 1
            if f['phase'] == 'recon-permutation':
                stats['output_count'] += 1
        else:
            stats['failed'] += 1
            metadata["errors"].append(f)

    if 'dnsgen' in metadata['plugin_stats']:
        metadata['plugin_stats']['dnsgen']['input_count'] = len(initial_raw_subdomains)
    if 'gotator' in metadata['plugin_stats']:
        metadata['plugin_stats']['gotator']['input_count'] = len(initial_raw_subdomains)

    with open(config['subdomains_metadata_file'], 'w') as f:
        json.dump(metadata, f, indent=4)
    logger.info(f"Reconnaissance metadata saved to {config['subdomains_metadata_file']}")

    assets = [{'type': 'subdomain', 'value': sub} for sub in master_subdomains]
    return assets


def resolve_and_validate(subdomains: Set[str], config: dict) -> Set[str]:
    """Resolves a set of subdomains and filters out non-resolving ones."""
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
