import os
import json
from typing import Set, List, Dict
from cyberhunter_3d.utils.logger import setup_logger
from .utils import load_config, save_to_json, detect_wildcard_ips, resolve_and_validate
from ..plugins.manager import PluginManager
from ..scoring.risk_scorer import calculate_risk
from cyberhunter_3d.reporting.reporting import generate_html_report, generate_delta_report
from flask import Flask
from cyberhunter_3d.web.models import db, Scan, Asset, Target

logger = setup_logger('Pipeline', 'pipeline.log')
config = load_config()

def save_results_to_db(domain: str, results: Dict[str, any]):
    pass

def perform_delta_scan(master_subdomains: Set[str], previous_subdomains: Set[str], logger, output_dir: str) -> Dict[str, str]:
    if not previous_subdomains:
        logger.info("No previous subdomains found. Skipping delta scan.")
        return {}

    new_subdomains = master_subdomains - previous_subdomains
    removed_subdomains = previous_subdomains - master_subdomains

    logger.info(f"Delta scan found {len(new_subdomains)} new and {len(removed_subdomains)} removed subdomains.")

    delta_paths = {}

    if new_subdomains:
        path = save_to_json(list(new_subdomains), os.path.join(output_dir, 'new_subdomains.json'), logger)
        if path:
            delta_paths['new_subdomains'] = path

    if removed_subdomains:
        path = save_to_json(list(removed_subdomains), os.path.join(output_dir, 'removed_subdomains.json'), logger)
        if path:
            delta_paths['removed_subdomains'] = path

    return delta_paths

def enumerate_subdomains_v2(domain: str, scan_id: int, app, previous_scan_dir: str = None, save_to_db: bool = False) -> List[Dict[str, str]]:
    logger.info(f"Starting V3 Plugin-Based Reconnaissance for: {domain}")

    # Find previous subdomains
    previous_subdomains = set()
    with app.app_context():
        # Find the most recent completed scan for the same domain
        previous_scan = Scan.query.filter(
            Scan.id < scan_id,
            Scan.targets.any(Target.value == domain),
            Scan.status == 'COMPLETED'
        ).order_by(Scan.created_at.desc()).first()

        if previous_scan and previous_scan.output_path and os.path.exists(previous_scan.output_path):
            logger.info(f"Found previous scan {previous_scan.id} to compare for delta.")
            with open(previous_scan.output_path, 'r') as f:
                old_data = json.load(f)
                previous_subdomains = set(old_data.get('all_subdomains', []))
        elif previous_scan:
            logger.warning(f"Previous scan {previous_scan.id} found, but no output path is set or file does not exist.")

    # --- Data buckets for the pipeline ---
    pipeline_data = {
        "target": domain,
        "all_subdomains": set(),
        "live_hosts": set(),
    }

    # --- Plugin Execution ---
    plugin_manager = PluginManager(plugin_dir="plugins/")
    plugins_to_run = plugin_manager.get_all_plugins()

    # Define the execution order of plugins
    # This is a simple way to manage dependencies between plugins
    plugin_order = [
        "Passive Enumeration",
        "Active Enumeration",
        "Permutation Enumeration",
        # Validation step
        "JS and Code Analysis",
        "Technology Fingerprinting",
        "Subdomain Takeover",
        "Cloud Enumeration",
        "CVE Mapper",
    ]

    plugin_results = {}

    for plugin_name in plugin_order:
        plugin = next((p for p in plugins_to_run if p.name == plugin_name), None)
        if plugin:
            logger.info(f"Running plugin: {plugin.name}")

            # Pass the necessary data to the plugin
            kwargs = {}
            if plugin_name == "Permutation Enumeration":
                kwargs['known_subdomains'] = pipeline_data['all_subdomains']
            elif plugin_name in ["JS and Code Analysis", "Technology Fingerprinting", "Subdomain Takeover"]:
                kwargs['live_hosts'] = pipeline_data['live_hosts']
            elif plugin_name == "Cloud Enumeration":
                kwargs['subdomains'] = pipeline_data['all_subdomains']
            elif plugin_name == "CVE Mapper":
                kwargs['tech_fingerprinting'] = plugin_results.get("Technology Fingerprinting", {}).get("tech_fingerprinting", {})

            results = plugin.run(target=domain, **kwargs)
            plugin_results[plugin.name] = results

            # Update data buckets
            if "passive_subdomains" in results:
                pipeline_data["all_subdomains"].update(results["passive_subdomains"])
            if "active_subdomains" in results:
                pipeline_data["all_subdomains"].update(results["active_subdomains"])
            if "permutation_subdomains" in results:
                pipeline_data["all_subdomains"].update(results["permutation_subdomains"])
            if "js_subdomains" in results:
                pipeline_data["all_subdomains"].update(results["js_subdomains"])

            # After enumeration plugins, run validation and live host detection
            if plugin_name == "Permutation Enumeration":
                logger.info("Validating all discovered subdomains...")
                wildcard_ips = detect_wildcard_ips(domain, logger)
                master_subdomains = resolve_and_validate(pipeline_data["all_subdomains"], wildcard_ips, logger)
                pipeline_data["all_subdomains"] = master_subdomains

                # This is a hacky way to get live hosts. A better pipeline would have a dedicated step.
                # For now, we assume resolve_and_validate gives us live hosts.
                pipeline_data["live_hosts"] = master_subdomains


    # --- Post-Plugin Processing ---
    risk_info = {}
    if "CVE Mapper" in plugin_results:
        cve_results = plugin_results["CVE Mapper"].get("cve_results", {})
        for host, cves_by_tech in cve_results.items():
            all_cves_for_host = [cve for cve_list in cves_by_tech.values() for cve in cve_list]
            risk_info[host] = calculate_risk(all_cves_for_host)

    # --- Final Aggregation and Reporting ---
    final_results = {
        "target": domain,
        "all_subdomains": list(pipeline_data['all_subdomains']),
        "live_hosts": list(pipeline_data['live_hosts']),
        "plugin_results": plugin_results,
        "risk_info": risk_info,
    }

    # Create a scan-specific output directory
    config = load_config()
    output_dir = os.path.join(config.get('recon_output_dir', 'recon_results'), f"scan_{scan_id}")
    os.makedirs(output_dir, exist_ok=True)

    # Save the final results to a JSON file
    final_output_path = save_to_json(final_results, os.path.join(output_dir, 'final_recon_data.json'), logger)

    # Perform delta scan and generate report
    if previous_subdomains:
        delta_paths = perform_delta_scan(pipeline_data['all_subdomains'], previous_subdomains, logger, output_dir)
        if delta_paths:
            generate_delta_report(output_dir, delta_paths)

    return [final_output_path] if final_output_path else []
