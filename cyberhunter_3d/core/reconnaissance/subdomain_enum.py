import json
import os
import tempfile
import asyncio
from typing import Set, List, Dict, Any

from ...common.log import get_rich_logger as get_logger
from ...common.utils import load_config
from .passive_engine import run_passive_enumeration
from .active_engine import run_active_enumeration
from .merger import merge_and_dedupe, bulk_check_liveness
from ..scanning.nuclei_scanner import run_nuclei_scan
from ..reporting.html_reporter import generate_html_report
from ..output_manager import OutputManager

logger = get_logger(__name__)

def enumerate_subdomains_v2(domain: str) -> Dict[str, Any]:
    config = load_config()
    output_dir = config.get('settings', {}).get('reporting', {}).get('output_directory', 'scan_reports')
    domain_output_dir = os.path.join(output_dir, domain)

    om = OutputManager(domain_output_dir)
    om.set_domain(domain)

    logger.info(f"Starting V2 reconnaissance for: {domain}")

    # Create a temporary directory for the enumeration output
    with tempfile.TemporaryDirectory() as temp_dir:
        logger.info(f"Created temporary directory for enumeration output: {temp_dir}")

        # --- Phase 1: Enumeration ---
        passive_output_paths = run_passive_enumeration(domain, os.path.join(temp_dir, "passive"))
        active_output_paths = run_active_enumeration(domain, os.path.join(temp_dir, "active"))

        all_output_paths = passive_output_paths + active_output_paths
        logger.info(f"Enumeration finished. Raw output files are in: {temp_dir}")

        # --- Phase 2: Merge and Deduplicate ---
        unique_subdomains = merge_and_dedupe(all_output_paths)
        logger.info(f"Found {len(unique_subdomains)} unique subdomains.")
        for sub in unique_subdomains:
            om.add_asset({'type': 'subdomain', 'value': sub, 'details': {}})

        # --- Phase 3: Liveness Check ---
        logger.info("Starting liveness check...")
        live_hosts = asyncio.run(bulk_check_liveness(unique_subdomains))
        logger.info(f"Found {len(live_hosts)} live hosts.")
        om.set_live_hosts(live_hosts)

        # --- Phase 4: Vulnerability Scanning ---
        logger.info("Starting vulnerability scanning with Nuclei...")
        live_urls = [host['url'] for host in live_hosts]
        nuclei_results_path = ""
        if live_urls:
            nuclei_results_path = run_nuclei_scan(live_urls, os.path.join(domain_output_dir, "scans"))

        nuclei_findings = []
        if nuclei_results_path and os.path.exists(nuclei_results_path):
            with open(nuclei_results_path, 'r') as f:
                for line in f:
                    try:
                        finding = json.loads(line)
                        nuclei_findings.append(finding)
                        om.add_vulnerability(finding, finding.get('info', {}).get('severity', ''))
                    except json.JSONDecodeError:
                        logger.warning(f"Could not decode line in nuclei output: {line}")

        om.set_nuclei_findings(nuclei_findings)


        # --- Final Report Generation ---
        final_recon_data = {
            'domain': domain,
            'live_hosts': live_hosts,
            'nuclei_findings': nuclei_findings,
            'assets': om.assets,
            'vulnerabilities': om.vulnerabilities,
        }

        # Save the final reports
        os.makedirs(domain_output_dir, exist_ok=True)
        final_json_report_path = os.path.join(domain_output_dir, "summary.json")
        with open(final_json_report_path, 'w') as f:
            json.dump(final_recon_data, f, indent=4)

        generate_html_report(final_recon_data, domain_output_dir)

        logger.info(f"Reconnaissance complete. Final reports at: {domain_output_dir}")

        return final_recon_data

def resolve_and_validate(subdomains: Set[str], config: dict) -> Set[str]:
    # ... (implementation remains)
    pass
