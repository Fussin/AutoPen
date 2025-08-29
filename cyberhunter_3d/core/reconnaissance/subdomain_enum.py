import os
import json
from typing import Set, List, Dict
from cyberhunter_3d.utils.logger import setup_logger
from .utils import load_config, save_to_json, detect_wildcard_ips, resolve_and_validate
from ..plugins.manager import PluginManager
from cyberhunter_3d.reporting.reporting import generate_html_report
from .asn_lookup import get_asn_for_ips

logger = setup_logger('Pipeline', 'pipeline.log')
config = load_config()

def transform_to_standard_schema(domain: str, pipeline_data: Dict, plugin_results: Dict) -> Dict:
    """Transforms the raw scan results into the standardized JSON schema."""
    import uuid
    from datetime import datetime

    assets = []

    # Create a mapping from host to its details from various plugins
    host_details = {}

    tech_results = plugin_results.get("Technology Fingerprinting", {}).get("tech_fingerprinting", {})
    for item in tech_results:
        host = item.get("host")
        if host not in host_details:
            host_details[host] = {}
        host_details[host].setdefault("technologies", []).append({"name": item.get("tech"), "version": item.get("version"), "confidence": 100})
        host_details[host].setdefault("ports", []).extend(item.get("ports", []))

    takeover_results = plugin_results.get("Subdomain Takeover", {}).get("takeover_vulnerabilities", [])
    for item in takeover_results:
        host = item.get("host")
        if host not in host_details:
            host_details[host] = {}
        host_details[host]["takeover_risk"] = True

    cve_results = plugin_results.get("CVE Mapper", {}).get("cve_results", {})
    for host, cves_by_tech in cve_results.items():
        if host not in host_details:
            host_details[host] = {}
        for tech, cve_list in cves_by_tech.items():
            for cve_data in cve_list:
                cve_id = cve_data.get("cve", {}).get("id")
                cvss_score = cve_data.get("cve", {}).get("metrics", {}).get("cvssMetricV31", [{}])[0].get("cvssData", {}).get("baseScore")
                summary = cve_data.get("cve", {}).get("descriptions", [{}])[0].get("value")
                host_details[host].setdefault("vulnerabilities", []).append({
                    "cve_id": cve_id,
                    "cvss_score": cvss_score,
                    "summary": summary,
                    "source": "NVD"
                })

    cloud_assets = plugin_results.get("Cloud Enumeration", {}).get("cloud_assets", [])
    for item in cloud_assets:
        # This assumes cloud assets are identified by a value that can be mapped back to a host
        # This is a simplification and might need a more robust mapping in a real scenario
        host = item.get("value")
        if host in host_details:
            host_details[host]["is_cloud_asset"] = True


    ip_map = pipeline_data.get("ip_map", {})
    all_ips = [ip for ip_list in ip_map.values() for ip in ip_list]
    asn_map = get_asn_for_ips(all_ips)

    for host in pipeline_data.get('live_hosts', []):
        details = host_details.get(host, {})
        ip_addresses = ip_map.get(host, [])
        asn_info = asn_map.get(ip_addresses[0]) if ip_addresses else {}

        asset = {
            "asset_type": "domain",
            "value": host,
            "ip_addresses": ip_addresses,
            "asn": {
                "id": asn_info.get("asn"),
                "description": asn_info.get("description")
            },
            "ports": [{"port": p, "service_name": "unknown", "transport_protocol": "tcp"} for p in sorted(list(set(details.get("ports", []))))],
            "technologies": details.get("technologies", []),
            "vulnerabilities": details.get("vulnerabilities", []),
            "takeover_risk": details.get("takeover_risk", False),
            "is_cloud_asset": details.get("is_cloud_asset", False),
            "screenshot_path": f"screenshots/gowitness/{host.replace('://', '_')}.png",
            "tags": []
        }
        assets.append(asset)

    standardized_output = {
        "metadata": {
            "target": domain,
            "scan_id": str(uuid.uuid4()),
            "timestamp_utc": datetime.utcnow().isoformat()
        },
        "assets": assets
    }
    return standardized_output

def perform_delta_scan(master_subdomains: Set[str], previous_subdomains: Set[str], logger) -> Dict[str, str]:
    if not previous_subdomains:
        logger.info("No previous subdomains found. Skipping delta scan.")
        return {}

    new_subdomains = master_subdomains - previous_subdomains
    removed_subdomains = previous_subdomains - master_subdomains

    logger.info(f"Delta scan found {len(new_subdomains)} new and {len(removed_subdomains)} removed subdomains.")

    delta_paths = {}

    if new_subdomains:
        path = save_to_json(list(new_subdomains), 'new_subdomains.json', logger)
        if path:
            delta_paths['new_subdomains'] = path

    if removed_subdomains:
        path = save_to_json(list(removed_subdomains), 'removed_subdomains.json', logger)
        if path:
            delta_paths['removed_subdomains'] = path

    return delta_paths

def enumerate_subdomains_v2(domain: str, previous_scan_dir: str = None, save_to_db: bool = False) -> List[Dict[str, str]]:
    logger.info(f"Starting V3 Plugin-Based Reconnaissance for: {domain}")

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
                live_subdomains_map = resolve_and_validate(pipeline_data["all_subdomains"], wildcard_ips, logger)
                pipeline_data["all_subdomains"] = set(live_subdomains_map.keys())
                pipeline_data["live_hosts"] = set(live_subdomains_map.keys())
                pipeline_data["ip_map"] = live_subdomains_map


    # --- Final Aggregation and Reporting ---
    # Transform to the standardized schema
    standardized_output = transform_to_standard_schema(domain, pipeline_data, plugin_results)

    # Save the standardized results to a JSON file
    final_output_path = save_to_json(standardized_output, 'final_recon_data.json', logger)

    # Placeholder for delta scan and reporting, assuming they are needed
    # previous_subdomains = ... # This would need to be loaded from a previous scan
    # perform_delta_scan(pipeline_data['all_subdomains'], previous_subdomains, logger)
    # if final_output_path:
    #    generate_html_report(final_output_path)

    return [final_output_path] if final_output_path else []
