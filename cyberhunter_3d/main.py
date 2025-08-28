import argparse
import json
import os
import sys
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains_v2
from cyberhunter_3d.core.reconnaissance.utils import load_config
from cyberhunter_3d.utils.logger import setup_logger
from cyberhunter_3d.reporting.r2_uploader import upload_to_r2

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

    if not master_subdomains:
        logger.error("Master subdomains list is empty. Cannot aggregate results.")
        return

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
            "screenshot_tags": [], # Placeholder for AI OCR tagger
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


def main():
    """
    Main function to run the CyberHunter 3D reconnaissance V3 pipeline.
    """
    parser = argparse.ArgumentParser(description="CyberHunter 3D - V3 Reconnaissance Pipeline")
    parser.add_argument("-d", "--domain", required=True, help="The target domain for reconnaissance.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output.")
    parser.add_argument("--upload-to-r2", action="store_true", help="Upload results to Cloudflare R2.")

    parser = argparse.ArgumentParser(description="A futuristic bug bounty automation platform.")
    parser.add_argument("-d", "--domain", required=True, help="The target domain to perform reconnaissance on.")

    parser.add_argument("--save-to-db", action="store_true", help="Save the scan results to the database.")
    parser.add_argument("--previous-scan-dir", help="Path to the previous scan's output directory for delta detection.")

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    target_domain = args.domain
    log_level = 'DEBUG' if args.verbose else 'INFO'

    # Setup logger
    logger = setup_logger('Main', 'main.log', level=log_level)


    logger.info("--- Welcome to CyberHunter 3D - Reconnaissance Module (V3) ---")
    logger.info(f"Starting V3 reconnaissance pipeline for: {target_domain}")

    # Run the full enumeration pipeline
    output_paths = enumerate_subdomains_v2(

    # Run the full V2 enumeration pipeline
    output_files = enumerate_subdomains_v2(

        target_domain,
        previous_scan_dir=args.previous_scan_dir,
        save_to_db=args.save_to_db
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
    if args.upload_to_r2:
        logger.info("R2 upload flag is set. Initiating upload...")
        screenshots_dir = output_paths.get('screenshots')
        upload_to_r2(logger, file_path=final_file_path, directory_path=screenshots_dir)
    else:
        logger.info("Skipping R2 upload as the flag was not provided.")

    if not args.save_to_db:
        logger.info("Output files generated:")
        for name, path in output_paths.items():
            logger.info(f"- {name.replace('_', ' ').title()}: {path}")
    else:
        logger.info("Results saved to the database.")

    logger.info("--- Pipeline Finished ---")


    if not args.save_to_db:
        print("\nReconnaissance complete.")
        print("Output files generated:")
        for name, path in output_files.items():
            print(f"- {name.replace('_', ' ').title()}: {path}")
    else:
        print("\nReconnaissance complete and results saved to the database.")


if __name__ == "__main__":
    main()
