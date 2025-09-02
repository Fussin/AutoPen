import json
import os
from cyberhunter_3d.core.reconnaissance.utils import load_config

def aggregate_results(output_paths: dict, domain: str, logger, results_dir: str, scan_id: int):
    """
    Aggregates all reconnaissance results into a single JSON file.
    """
    logger.info("Aggregating all reconnaissance data...")
    config = load_config()
    final_data = {"domain": domain, "hosts": [], "url_discovery": {}, "vulnerabilities": []}
    host_map = {}

    # Helper to load JSON files safely
    def load_json_data(path_key):
        if path_key not in output_paths:
            logger.warning(f"Output path for '{path_key}' not found. Skipping.")
            return None
        try:
            with open(output_paths[path_key], 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Could not read or parse {output_paths[path_key]}: {e}")
            return None

    # Load host-based data sources
    master_subdomains = load_json_data('master_subdomains')
    if not master_subdomains:
        logger.warning("Master subdomains list not found. Skipping host aggregation.")
    else:
        ip_mapping = load_json_data('subdomain_ip_mapping')
        asn_details = load_json_data('asn_details')
        live_hosts = load_json_data('live_hosts')
        tech_results = load_json_data('technology_and_ports')
        takeover_findings = load_json_data('takeover_vulnerabilities')
        cloud_assets = load_json_data('cloud_assets')
        ocr_results = load_json_data('ocr_results')
        risk_info = load_json_data('risk_info')

        for host in master_subdomains:
            host_map[host] = {"host": host, "alive": False, "ips": [], "asn_details": [], "open_ports": [], "technologies": [], "takeover_risk": False, "cloud_asset": False, "screenshot_tags": [], "cve_ids": [], "cvss_score": 0.0, "risk_level": "None", "known_exploits": False}
        if live_hosts:
            for host in live_hosts:
                if host in host_map: host_map[host]['alive'] = True
        if ip_mapping:
            for host, ips in ip_mapping.items():
                if host in host_map:
                    host_map[host]['ips'] = ips
                    if asn_details:
                        host_asns = set()
                        for ip in ips:
                            for asn_ip, details in asn_details.items():
                                if ip == asn_ip: host_asns.add(f"{details['asn']} - {details['org']}")
                        host_map[host]['asn_details'] = sorted(list(host_asns))
        if tech_results:
            for result in tech_results:
                host = result.get('host')
                if host and host in host_map:
                    host_map[host]['open_ports'] = result.get('ports', [])
                    host_map[host]['technologies'] = result.get('technologies', [])
        if takeover_findings:
            for finding in takeover_findings:
                host = finding.get('host')
                if host and host in host_map: host_map[host]['takeover_risk'] = True
        if cloud_assets:
            for asset in cloud_assets:
                if asset in host_map: host_map[asset]['cloud_asset'] = True
        if ocr_results:
            for host, tags in ocr_results.items():
                if host in host_map: host_map[host]['screenshot_tags'] = tags
        if risk_info:
            for host, risk_data in risk_info.items():
                if host in host_map:
                    host_map[host]['cve_ids'] = risk_data.get('cve_ids', [])
                    host_map[host]['cvss_score'] = risk_data.get('cvss_score', 0.0)
                    host_map[host]['risk_level'] = risk_data.get('risk_level', 'None')
                    host_map[host]['known_exploits'] = risk_data.get('known_exploits', False)

    final_data["hosts"] = list(host_map.values())

    # Helper to load text files safely
    def load_text_data(filename):
        filepath = os.path.join(results_dir, filename)
        try:
            with open(filepath, 'r') as f: return [line.strip() for line in f.readlines()]
        except FileNotFoundError: return []

    # Aggregate URL discovery results
    final_data["url_discovery"] = {
        "alive_urls": load_text_data(f"alive_urls_{scan_id}.txt"),
        "dead_urls": load_text_data(f"dead_urls_{scan_id}.txt"),
        "redirect_urls": load_text_data(f"redirect_urls_{scan_id}.txt"),
        "parameters": load_text_data(f"parameters_{scan_id}.txt"),
    }

    # Aggregate vulnerability scan results
    vuln_file_path = os.path.join(results_dir, f"vulnerabilities_{scan_id}.json")
    if os.path.exists(vuln_file_path):
        with open(vuln_file_path, 'r') as f:
            try: final_data["vulnerabilities"] = json.load(f)
            except json.JSONDecodeError: logger.error(f"Could not decode vulnerabilities file: {vuln_file_path}")

    # Aggregate content discovery results
    content_file_path = os.path.join(results_dir, f"discovered_paths_{scan_id}.json")
    if os.path.exists(content_file_path):
        with open(content_file_path, 'r') as f:
            try: final_data["content_discovery"] = json.load(f)
            except json.JSONDecodeError: logger.error(f"Could not decode content discovery file: {content_file_path}")

    # Aggregate JavaScript analysis results
    js_endpoints_file_path = os.path.join(results_dir, f"js_endpoints_{scan_id}.json")
    if os.path.exists(js_endpoints_file_path):
        with open(js_endpoints_file_path, 'r') as f:
            try: final_data["js_analysis"] = json.load(f)
            except json.JSONDecodeError: logger.error(f"Could not decode JS analysis file: {js_endpoints_file_path}")

    # Save the final aggregated file
    output_dir = config['recon_output_dir']
    final_output_path = os.path.join(output_dir, config['final_recon_file'])
    try:
        with open(final_output_path, 'w') as f: json.dump(final_data, f, indent=4)
        logger.info(f"Successfully aggregated results to {final_output_path}")
    except IOError as e:
        logger.error(f"Failed to write final aggregated file: {e}")
