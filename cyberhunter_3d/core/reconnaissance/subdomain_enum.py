import concurrent.futures
import json
from typing import Set, List, Dict

import subprocess
import tempfile
import os
import re
from cyberhunter_3d.utils.logger import setup_logger
from .utils import load_config, detect_wildcard_ips, save_to_json
from .passive_engine import run_passive_enumeration
from .active_engine import run_active_enumeration
from .permutation_engine import run_permutation_enumeration
from .js_engine import run_js_and_code_analysis
from .visual_recon import run_visual_recon
from .tech_fingerprinting import run_tech_fingerprinting
from .cloud_asset_enum import find_cloud_assets
from .subdomain_takeover import run_takeover_scan
from .analytics_correlation import correlate_tech_stack
from .asn_lookup import get_asn_for_ips
from .utils import resolve_subdomains_to_ips
from .threat_intel import enrich_ips_with_shodan, enrich_ips_with_censys
from cyberhunter_3d.reporting.reporting import generate_html_report
from flask import Flask
from cyberhunter_3d.web.models import db, Scan, Asset

logger = setup_logger('Pipeline', 'pipeline.log')
config = load_config()

def save_results_to_db(domain: str, results: Dict[str, any]):
    """
    Saves the reconnaissance results to the database.
    """
    app = Flask(__name__)
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'cyberhunter.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    with app.app_context():
        # Create a new scan object
        scan = Scan(user_id=1, in_scope_rules=domain) # Assuming user_id 1 for CLI scans
        db.session.add(scan)
        db.session.flush()

        for asset_type, data in results.items():
            if not data:
                continue

            if isinstance(data, list):
                for item in data:
                    value = item.get('value') if isinstance(item, dict) else item
                    details = item if isinstance(item, dict) else None
                    asset = Asset(scan_id=scan.id, type=asset_type, value=str(value), details=details)
                    db.session.add(asset)
            elif isinstance(data, dict):
                for key, value in data.items():
                    asset = Asset(scan_id=scan.id, type=asset_type, value=str(key), details=value)
                    db.session.add(asset)

        db.session.commit()
        logger.info(f"Results for domain {domain} saved to database with scan_id {scan.id}")


def enumerate_subdomains_v2(domain: str, previous_scan_dir: str = None, save_to_db: bool = False) -> List[Dict[str, str]]:
    """
    Runs the full V2 reconnaissance pipeline and performs delta detection if a previous scan is provided.
    """
    logger.info(f"Starting V2 reconnaissance for: {domain}")

    # Load previous scan's subdomains for delta detection
    previous_subdomains = set()
    if previous_scan_dir:
        previous_subdomains_file = os.path.join(previous_scan_dir, "subdomains_verified.json")
        if os.path.exists(previous_subdomains_file):
            with open(previous_subdomains_file, 'r') as f:
                previous_subdomains = set(json.load(f))
            logger.info(f"Loaded {len(previous_subdomains)} subdomains from previous scan for delta detection.")

    # Step 0: Wildcard Detection
    # Run this first to avoid polluting results from active and permutation engines.
    wildcard_ips = detect_wildcard_ips(domain, logger)

    raw_subdomains = set()
    initial_subdomains = set()

    logger.info("Running passive and active enumeration engines in parallel...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        # Submit passive and active engines
        future_to_engine = {
            executor.submit(run_passive_enumeration, domain): "Passive",
            executor.submit(run_active_enumeration, domain): "Active"
        }

        for future in concurrent.futures.as_completed(future_to_engine):
            engine_name = future_to_engine[future]
            try:
                results = future.result()
                logger.info(f"{engine_name} engine found {len(results)} subdomains.")
                initial_subdomains.update(results)
            except Exception as exc:
                logger.error(f"{engine_name} engine generated an exception: {exc}")

    raw_subdomains.update(initial_subdomains)
    logger.info(f"Found {len(initial_subdomains)} subdomains from passive and active scans.")

    # Now, run the permutation engine with the results from the initial scans
    logger.info("Running permutation engine...")
    permutation_results = run_permutation_enumeration(domain, initial_subdomains)
    raw_subdomains.update(permutation_results)
    logger.info(f"Found {len(permutation_results)} new subdomains from permutation engine.")

    logger.info(f"Total raw subdomains found from all engines: {len(raw_subdomains)}")

    # Step 1: DNS Resolution and Validation
    logger.info("Starting DNS resolution and validation...")
    master_subdomains = resolve_and_validate(raw_subdomains, wildcard_ips, logger)
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
    logger.info(f"Found {len(live_hosts)} live hosts.")
    logger.info(f"Screenshots saved in: {screenshots}")

    # Step 3: Subdomain Takeover Scan
    logger.info("Starting subdomain takeover scan...")
    takeover_findings = run_takeover_scan(live_hosts)
    logger.info(f"Found {len(takeover_findings)} potential takeover vulnerabilities.")

    # Step 4: JS & Code Analysis Engine
    logger.info("Starting JS & Code analysis...")
    code_analysis_subdomains, secrets_and_endpoints = run_js_and_code_analysis(domain, live_hosts)
    logger.info(f"Found {len(code_analysis_subdomains)} subdomains from code analysis.")
    # Add these to the master list, as they might be new
    master_subdomains.update(code_analysis_subdomains)


    # Step 5: Technology Fingerprinting and Port Scanning
    logger.info("Starting technology fingerprinting and port scanning...")
    tech_results = run_tech_fingerprinting(live_hosts)

    # Correlate technology stacks
    logger.info("Correlating technology stacks...")
    tech_clusters = correlate_tech_stack(tech_results)
    if tech_clusters:
        logger.info(f"Found {len(tech_clusters)} technology clusters.")

    # Step 6: Cloud Asset Identification
    logger.info("Starting cloud asset identification...")
    cloud_assets = find_cloud_assets(master_subdomains)

    # Step 7: IP and ASN Enrichment
    logger.info("Starting IP and ASN enrichment...")
    subdomain_ip_mapping = resolve_subdomains_to_ips(master_subdomains, logger)

    # Collect all unique IPs from the mapping
    all_ips = set()
    for ip_list in subdomain_ip_mapping.values():
        all_ips.update(ip_list)

    asn_details = get_asn_for_ips(all_ips)
    logger.info(f"Completed IP and ASN enrichment for {len(all_ips)} unique IPs.")

    # Threat Intel Enrichment
    logger.info("Starting Threat Intelligence enrichment...")
    shodan_data = enrich_ips_with_shodan(all_ips)
    censys_data = enrich_ips_with_censys(all_ips)
    logger.info("Threat Intelligence enrichment complete.")

    # Step 8: Save all datasets to structured files
    logger.info("Saving all datasets to structured output files...")
    output_file_paths = {}

    # Prepare structured data
    tech_fingerprinting = {host: data.get('technologies', []) for host, data in tech_results.items()}
    ports_services = {host: data.get('ports', []) for host, data in tech_results.items()}

    # Define datasets
    datasets = {
        "subdomains_verified": list(master_subdomains),
        "subdomain_ip_mapping": subdomain_ip_mapping,
        "asn_details": asn_details,
        "live_hosts": list(live_hosts),
        "tech_fingerprinting": tech_fingerprinting,
        "ports_services": ports_services,
        "takeover_vulnerabilities": takeover_findings,
        "code_analysis_subdomains": list(code_analysis_subdomains),
        "cloud_assets": cloud_assets,
        "secrets_and_endpoints": secrets_and_endpoints,
        "tech_clusters": tech_clusters,
        "shodan_enrichment": shodan_data,
        "censys_enrichment": censys_data,
    }

    if save_to_db:
        save_results_to_db(domain, datasets)
    else:
        for filename, data in datasets.items():
            if data: # Only save if there is data
                path = save_to_json(data, f"{filename}.json", logger)
                if path:
                    output_file_paths[filename] = path

    # Also include the path to the screenshots directory
    output_file_paths['screenshots'] = screenshots

    # Delta Detection
    if previous_subdomains:
        new_subdomains = master_subdomains - previous_subdomains
        removed_subdomains = previous_subdomains - master_subdomains

        if new_subdomains:
            path = save_to_json(list(new_subdomains), "new_subdomains.json", logger)
            if path: output_file_paths['new_subdomains'] = path

        if removed_subdomains:
            path = save_to_json(list(removed_subdomains), "removed_subdomains.json", logger)
            if path: output_file_paths['removed_subdomains'] = path

        logger.info(f"Delta detection complete. Found {len(new_subdomains)} new and {len(removed_subdomains)} removed subdomains.")

    # Generate HTML report
    if not save_to_db:
        logger.info("Generating HTML report...")
        report_path = os.path.join(output_dir, "recon_report.html")
        generate_html_report(output_dir, report_path)
        output_file_paths['html_report'] = report_path
        logger.info(f"HTML report generated at {report_path}")

    logger.info("Reconnaissance pipeline complete.")
    return output_file_paths


def resolve_and_validate(subdomains: Set[str], wildcard_ips: Set[str], logger) -> Set[str]:
    """
    Resolves a set of subdomains and filters out non-resolving and wildcard ones.
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
        puredns_path = config['tools']['puredns']
        resolvers_list = config['wordlists']['resolvers']
        puredns_command = [
            puredns_path, 'resolve', input_filename,
            '-r', resolvers_list,
            '--quiet'
        ]
        result = subprocess.run(puredns_command, capture_output=True, text=True, check=True)

        for line in result.stdout.strip().split('\n'):
            if line:
                resolved_subdomains.add(line)

    except FileNotFoundError:
        logger.error("Error: 'puredns' not found. Please ensure it is installed and in your PATH.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running puredns for resolution: {e}\nOutput: {e.stderr}")
    finally:
        os.remove(input_filename)

    if not wildcard_ips or not resolved_subdomains:
        return resolved_subdomains

    # Step 2: Filter out any subdomains that resolve to the wildcard IPs
    logger.info(f"Filtering {len(resolved_subdomains)} resolved subdomains against {len(wildcard_ips)} wildcard IPs...")

    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as subs_to_filter_file:
        subs_to_filter_filename = subs_to_filter_file.name
        for sub in resolved_subdomains:
            subs_to_filter_file.write(f"{sub}\n")

    final_subdomains = set()
    try:
        dnsx_path = config['tools']['dnsx']
        # Get A records for all resolved subdomains
        dnsx_command = [dnsx_path, '-l', subs_to_filter_filename, '-a', '-resp', '-silent']
        result = subprocess.run(dnsx_command, capture_output=True, text=True, check=True)

        ip_regex = re.compile(r'\[(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\]')
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue

            # Line is like "sub.example.com [1.2.3.4]"
            subdomain = line.split()[0]
            ip_match = ip_regex.search(line)

            if ip_match:
                ip = ip_match.group(1)
                if ip not in wildcard_ips:
                    final_subdomains.add(subdomain)

        filtered_count = len(resolved_subdomains) - len(final_subdomains)
        logger.info(f"Filtered out {filtered_count} wildcard subdomains.")

    except FileNotFoundError:
        logger.error(f"Error: '{dnsx_path}' not found. Skipping wildcard filtering.")
        return resolved_subdomains # Return unfiltered list if dnsx is missing
    except Exception as e:
        logger.error(f"An error occurred during wildcard filtering with dnsx: {e}")
        return resolved_subdomains # Return unfiltered list on error
    finally:
        os.remove(subs_to_filter_filename)

    return final_subdomains
