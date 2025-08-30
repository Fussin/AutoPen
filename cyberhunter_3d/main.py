import json
import os
import sys
import click
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains_v2
from cyberhunter_3d.core.reconnaissance.url_discovery_manager import discover_urls
from cyberhunter_3d.core.reconnaissance.utils import load_config
from cyberhunter_3d.utils.logger import setup_logger
from cyberhunter_3d.reporting.r2_uploader import upload_to_r2
from cyberhunter_3d.utils.file_utils import get_results_dir

def aggregate_results(output_paths: dict, domain: str, logger):
    """
    Aggregates all reconnaissance results into a single JSON file.
    """
    logger.info("Aggregating all reconnaissance data...")
    config = load_config()
    final_data = {"domain": domain, "hosts": []}
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

    # Load all data sources
    master_subdomains = load_json_data('master_subdomains')
    ip_mapping = load_json_data('subdomain_ip_mapping')
    asn_details = load_json_data('asn_details')
    live_hosts = load_json_data('live_hosts')
    tech_results = load_json_data('technology_and_ports')
    takeover_findings = load_json_data('takeover_vulnerabilities')
    cloud_assets = load_json_data('cloud_assets')
    ocr_results = load_json_data('ocr_results')
    risk_info = load_json_data('risk_info')

    if not master_subdomains:
        logger.warning("Master subdomains list not found. Skipping host aggregation.")
    else:
        # Initialize host map from master subdomains list
        for host in master_subdomains:
            host_map[host] = {
                "host": host,
                "alive": False,
            "ips": [],
            "asn_details": [],
            "open_ports": [],
            "technologies": [],
            "takeover_risk": False,
            "cloud_asset": False,
            "screenshot_tags": [],
            "cve_ids": [],
            "cvss_score": 0.0,
            "risk_level": "None",
            "known_exploits": False,
        }

    # Enrich with live status
    if live_hosts:
        for host in live_hosts:
            if host in host_map:
                host_map[host]['alive'] = True

    # Enrich with IP and ASN info
    if ip_mapping:
        for host, ips in ip_mapping.items():
            if host in host_map:
                host_map[host]['ips'] = ips
                # Add ASN details
                if asn_details:
                    host_asns = set()
                    for ip in ips:
                        for asn_ip, details in asn_details.items():
                            if ip == asn_ip:
                                host_asns.add(f"{details['asn']} - {details['org']}")
                    host_map[host]['asn_details'] = sorted(list(host_asns))


    # Enrich with technology and port info
    if tech_results:
        for result in tech_results:
            host = result.get('host')
            if host and host in host_map:
                host_map[host]['open_ports'] = result.get('ports', [])
                host_map[host]['technologies'] = result.get('technologies', [])

    # Enrich with takeover info
    if takeover_findings:
        for finding in takeover_findings:
            host = finding.get('host')
            if host and host in host_map:
                host_map[host]['takeover_risk'] = True

    # Enrich with cloud asset info
    if cloud_assets:
        for asset in cloud_assets:
            # Assuming cloud_assets is a list of hosts
            if asset in host_map:
                host_map[asset]['cloud_asset'] = True

    # Enrich with OCR screenshot tags
    if ocr_results:
        for host, tags in ocr_results.items():
            if host in host_map:
                host_map[host]['screenshot_tags'] = tags

    # Enrich with risk info
    if risk_info:
        for host, risk_data in risk_info.items():
            if host in host_map:
                host_map[host]['cve_ids'] = risk_data.get('cve_ids', [])
                host_map[host]['cvss_score'] = risk_data.get('cvss_score', 0.0)
                host_map[host]['risk_level'] = risk_data.get('risk_level', 'None')
                host_map[host]['known_exploits'] = risk_data.get('known_exploits', False)


    final_data["hosts"] = list(host_map.values())

    # Save the final aggregated file
    output_dir = config['recon_output_dir']
    final_output_path = os.path.join(output_dir, config['final_recon_file'])
    try:
        with open(final_output_path, 'w') as f:
            json.dump(final_data, f, indent=4)
        logger.info(f"Successfully aggregated results to {final_output_path}")
    except IOError as e:
        logger.error(f"Failed to write final aggregated file: {e}")


@click.command()
@click.option("-d", "--domain", required=True, help="The target domain for reconnaissance.")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output.")
@click.option("--upload-to-r2", is_flag=True, help="Upload results to Cloudflare R2.")
@click.option("--save-to-db", is_flag=True, help="Save the scan results to the database.")
@click.option("--previous-scan-dir", help="Path to the previous scan's output directory for delta detection.")
@click.option("--url-discovery", is_flag=True, help="Run the URL discovery phase.")
def main(domain, verbose, upload_to_r2, save_to_db, previous_scan_dir, url_discovery):
    """
    Main function to run the CyberHunter 3D reconnaissance V3 pipeline.
    """
    target_domain = domain
    log_level = 'DEBUG' if verbose else 'INFO'

    # Setup logger
    logger = setup_logger('Main', 'main.log', level=log_level)

    logger.info("--- Welcome to CyberHunter 3D - Reconnaissance Module (V3) ---")

    if url_discovery:
        logger.info(f"Starting URL discovery for: {target_domain}")
        from run_web import create_app
        from cyberhunter_3d.web.models import db, Scan, Target
        app = create_app()
        with app.app_context():
            target = Target(value=target_domain)
            scan = Scan(status='RUNNING')
            scan.targets.append(target)
            db.session.add(target)
            db.session.add(scan)
            db.session.commit()
            scan_id = scan.id

        discover_urls(target_domain, scan_id, app)

        results_dir = get_results_dir(target_domain, scan_id)
        aggregate_results({}, target_domain, logger, results_dir)

        logger.info("URL discovery finished.")
        return


    logger.info(f"Starting V3 reconnaissance pipeline for: {target_domain}")

    # Run the full enumeration pipeline
    output_paths = enumerate_subdomains_v2(
        target_domain,
        previous_scan_dir=previous_scan_dir,
        save_to_db=save_to_db
    )

    if not output_paths:
        logger.error("Reconnaissance pipeline did not produce any output. Exiting.")
        sys.exit(1)

    # Aggregate the results into the final JSON file
    aggregate_results(output_paths, target_domain, logger)

    logger.info(f"Reconnaissance complete for {target_domain}.")
    config = load_config()
    final_file_path = os.path.join(config['recon_output_dir'], config['final_recon_file'])
    logger.info(f"All findings have been aggregated into: {final_file_path}")

    # Upload to R2 if the flag is set
    if upload_to_r2:
        logger.info("R2 upload flag is set. Initiating upload...")
        screenshots_dir = output_paths.get('screenshots')
        upload_to_r2(logger, file_path=final_file_path, directory_path=screenshots_dir)
    else:
        logger.info("Skipping R2 upload as the flag was not provided.")

    if not save_to_db:
        logger.info("Output files generated:")
        for name, path in output_paths.items():
            logger.info(f"- {name.replace('_', ' ').title()}: {path}")
    else:
        logger.info("Results saved to the database.")

    logger.info("--- Pipeline Finished ---")


if __name__ == "__main__":
    main()
