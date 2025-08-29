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
from .tech_correlation import correlate_tech_stack
from .asn_lookup import get_asn_for_ips
from .utils import resolve_subdomains_to_ips
from .ai.noise_filter import filter_false_positives
from .ai.ocr_tagger import generate_ocr_tags
from .threat_intel import enrich_ips_with_shodan, enrich_ips_with_censys, enrich_ips_with_fofa, enrich_ips_with_greynoise
from .passive_dns import get_passive_dns_for_domain
from .enrichment.cve_mapper import map_tech_to_cves
from ..scoring.risk_scorer import calculate_risk
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
        scan = Scan(user_id=1, in_scope_rules=domain)
        db.session.add(scan)
        db.session.flush()

        # Pre-process risk info for easy lookup
        risk_info = results.get('risk_info', {})
        host_risk_map = {host: data for host, data in risk_info.items()}

        for asset_type, data in results.items():
            if not data or asset_type == 'risk_info': # Skip risk_info as it's handled separately
                continue

            if isinstance(data, list):
                for item in data:
                    value = item.get('host') or item.get('value') if isinstance(item, dict) else item
                    details = item if isinstance(item, dict) else None

                    asset = Asset.query.filter_by(scan_id=scan.id, type=asset_type, value=str(value)).first()
                    if not asset:
                        asset = Asset(scan_id=scan.id, type=asset_type, value=str(value))
                        db.session.add(asset)

                    asset.details = details
                    asset.last_seen = db.func.now()

                    # Add risk info if this asset is a host with risk data
                    if value in host_risk_map:
                        risk_data = host_risk_map[value]
                        asset.risk_level = risk_data.get('risk_level')
                        asset.cvss_score = risk_data.get('cvss_score')
                        asset.known_exploits = risk_data.get('known_exploits')

            elif isinstance(data, dict):
                for key, value in data.items():
                    asset = Asset.query.filter_by(scan_id=scan.id, type=asset_type, value=str(key)).first()
                    if not asset:
                        asset = Asset(scan_id=scan.id, type=asset_type, value=str(key))
                        db.session.add(asset)

                    asset.details = value
                    asset.last_seen = db.func.now()

                    # Add risk info if this asset is a host with risk data
                    if key in host_risk_map:
                        risk_data = host_risk_map[key]
                        asset.risk_level = risk_data.get('risk_level')
                        asset.cvss_score = risk_data.get('cvss_score')
                        asset.known_exploits = risk_data.get('known_exploits')

        db.session.commit()
        logger.info(f"Results for domain {domain} saved to database with scan_id {scan.id}")

def perform_delta_scan(master_subdomains: Set[str], previous_subdomains: Set[str], logger) -> Dict[str, str]:
    """
    Performs a delta scan to identify new and removed subdomains.
    """
    delta_paths = {}
    if previous_subdomains:
        new_subdomains = master_subdomains - previous_subdomains
        removed_subdomains = previous_subdomains - master_subdomains
        if new_subdomains:
            path = save_to_json(list(new_subdomains), "new_subdomains.json", logger)
            if path: delta_paths['new_subdomains'] = path
        if removed_subdomains:
            path = save_to_json(list(removed_subdomains), "removed_subdomains.json", logger)
            if path: delta_paths['removed_subdomains'] = path
        logger.info(f"Delta detection complete. Found {len(new_subdomains)} new and {len(removed_subdomains)} removed subdomains.")
    return delta_paths

def enumerate_subdomains_v2(domain: str, previous_scan_dir: str = None, save_to_db: bool = False) -> List[Dict[str, str]]:
    """
    Runs the full V2 reconnaissance pipeline and performs delta detection if a previous scan is provided.
    """
    logger.info(f"Starting V3 reconnaissance for: {domain}")

    previous_subdomains = set()
    if previous_scan_dir:
        previous_subdomains_file = os.path.join(previous_scan_dir, "subdomains_verified.json")
        if os.path.exists(previous_subdomains_file):
            with open(previous_subdomains_file, 'r') as f:
                previous_subdomains = set(json.load(f))
            logger.info(f"Loaded {len(previous_subdomains)} subdomains from previous scan for delta detection.")

    wildcard_ips = detect_wildcard_ips(domain, logger)
    raw_subdomains = set()
    initial_subdomains = set()

    logger.info("Running passive and active enumeration engines in parallel...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
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

    logger.info("Running permutation engine...")
    permutation_results = run_permutation_enumeration(domain, initial_subdomains)
    raw_subdomains.update(permutation_results)
    logger.info(f"Found {len(permutation_results)} new subdomains from permutation engine.")

    logger.info(f"Total raw subdomains found from all engines: {len(raw_subdomains)}")

    master_subdomains = resolve_and_validate(raw_subdomains, wildcard_ips, logger)
    logger.info(f"Found {len(master_subdomains)} valid subdomains after resolution.")

    try:
        master_subdomains = set(filter_false_positives(master_subdomains))
    except TypeError:
        master_subdomains = set(filter_false_positives(master_subdomains, logger))
    logger.info(f"{len(master_subdomains)} subdomains remain after AI noise filtering.")

    output_dir = config['recon_output_dir']
    os.makedirs(output_dir, exist_ok=True)
    master_subdomains_file = os.path.join(output_dir, config['master_subdomains_file'])
    with open(master_subdomains_file, 'w') as f:
        for sub in master_subdomains:
            f.write(f"{sub}\n")

    live_hosts, screenshots_dir = run_visual_recon(master_subdomains)
    logger.info(f"Found {len(live_hosts)} live hosts.")
    logger.info(f"Screenshots saved in: {screenshots_dir}")

    ocr_results = generate_ocr_tags(screenshots_dir, logger)
    logger.info(f"Generated OCR tags for {len(ocr_results)} screenshots.")

    takeover_findings = run_takeover_scan(live_hosts)
    logger.info(f"Found {len(takeover_findings)} potential takeover vulnerabilities.")

    code_analysis_subdomains, secrets_and_endpoints = run_js_and_code_analysis(domain, live_hosts)
    logger.info(f"Found {len(code_analysis_subdomains)} subdomains from code analysis.")
    master_subdomains.update(code_analysis_subdomains)

    tech_results = run_tech_fingerprinting(live_hosts)
    logger.info("Correlating technology stacks...")
    tech_clusters = correlate_tech_stack(tech_results)
    if tech_clusters:
        logger.info(f"Found {len(tech_clusters)} technology clusters.")

    cloud_assets = find_cloud_assets(master_subdomains)
    subdomain_ip_mapping = resolve_subdomains_to_ips(master_subdomains, logger)
    all_ips = set(ip for ip_list in subdomain_ip_mapping.values() for ip in ip_list)
    asn_details = get_asn_for_ips(all_ips)
    logger.info(f"Completed IP and ASN enrichment for {len(all_ips)} unique IPs.")

    logger.info("Starting Threat Intelligence enrichment...")
    shodan_data = enrich_ips_with_shodan(all_ips)
    censys_data = enrich_ips_with_censys(all_ips)
    fofa_data = enrich_ips_with_fofa(all_ips)
    greynoise_data = enrich_ips_with_greynoise(all_ips)
    passive_dns_data = get_passive_dns_for_domain(domain)
    logger.info("Threat Intelligence enrichment complete.")

    logger.info("Starting CVE mapping and risk scoring...")
    risk_info = {}
    tech_fingerprinting = {host: data.get('technologies', []) for host, data in tech_results.items()}
    for host, techs in tech_fingerprinting.items():
        if techs:
            cve_results = map_tech_to_cves(techs, logger)
            if cve_results:
                # cve_results is a dict of {tech: [cve_list]}, we need to flatten the list of cves
                all_cves_for_host = [cve for cve_list in cve_results.values() for cve in cve_list]
                risk_info[host] = calculate_risk(all_cves_for_host)
    logger.info("CVE mapping and risk scoring complete.")

    logger.info("Saving all datasets to structured output files...")
    ports_services = {host: data.get('ports', []) for host, data in tech_results.items()}

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
        "fofa_enrichment": fofa_data,
        "greynoise_enrichment": greynoise_data,
        "passive_dns": passive_dns_data,
        "ocr_results": ocr_results,
        "risk_info": risk_info,
    }

    output_file_paths = {}
    if save_to_db:
        save_results_to_db(domain, datasets)
    else:
        for filename, data in datasets.items():
            if data:
                path = save_to_json(data, f"{filename}.json", logger)
                if path:
                    output_file_paths[filename] = path

    output_file_paths['screenshots'] = screenshots_dir

    if previous_subdomains:
        delta_paths = perform_delta_scan(master_subdomains, previous_subdomains, logger)
        output_file_paths.update(delta_paths)

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

    logger.info(f"Filtering {len(resolved_subdomains)} resolved subdomains against {len(wildcard_ips)} wildcard IPs...")
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as subs_to_filter_file:
        subs_to_filter_filename = subs_to_filter_file.name
        for sub in resolved_subdomains:
            subs_to_filter_file.write(f"{sub}\n")

    final_subdomains = set()
    try:
        dnsx_path = config['tools']['dnsx']
        dnsx_command = [dnsx_path, '-l', subs_to_filter_filename, '-a', '-resp', '-silent']
        result = subprocess.run(dnsx_command, capture_output=True, text=True, check=True)
        ip_regex = re.compile(r'\[(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\]')
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
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
        return resolved_subdomains
    except Exception as e:
        logger.error(f"An error occurred during wildcard filtering with dnsx: {e}")
        return resolved_subdomains
    finally:
        os.remove(subs_to_filter_filename)

    return final_subdomains
