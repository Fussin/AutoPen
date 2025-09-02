import json
import os
import sys
import click
import concurrent.futures
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains_v2
from cyberhunter_3d.core.scan_manager import run_url_discovery_phase, run_network_scan_phase, run_vulnerability_scan_phase
from cyberhunter_3d.core.reconnaissance.utils import load_config
from cyberhunter_3d.utils.logger import setup_logger
from cyberhunter_3d.reporting.r2_uploader import upload_to_r2
from cyberhunter_3d.utils.file_utils import get_results_dir

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


@click.command()
@click.option("-d", "--domain", required=True, help="The target domain for reconnaissance.")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output.")
@click.option("--upload-to-r2", is_flag=True, help="Upload results to Cloudflare R2.")
@click.option("--save-to-db", is_flag=True, help="Save the scan results to the database.")
@click.option("--previous-scan-dir", help="Path to the previous scan's output directory for delta detection.")
@click.option("--url-discovery", is_flag=True, help="Run the URL discovery and vulnerability scanning phase.")
@click.option("--generate-report", is_flag=True, help="Generate a PDF report after the scan.")

def scan_command(domain, verbose, upload_to_r2, save_to_db, previous_scan_dir, url_discovery, generate_report):

def main(domain, verbose, upload_to_r2, save_to_db, previous_scan_dir, url_discovery, generate_report):

    """
    Main function to run the CyberHunter 3D reconnaissance V3 pipeline.
    """
    log_level = 'DEBUG' if verbose else 'INFO'
    logger = setup_logger('main.log', level=log_level)
    logger.info("--- Welcome to CyberHunter 3D - Reconnaissance Module (V3) ---")

    from run_web import create_app
    from cyberhunter_3d.web.models import db, Scan, Target
    app = create_app()
    with app.app_context():
        # For CLI runs, we create a new scan object to track the operation.
        target = Target(value=domain, type='domain')
        # Assuming user_id=1 for all CLI-initiated scans.
        scan = Scan(status='RUNNING', user_id=1)
        scan.targets.append(target)
        db.session.add(target)
        db.session.add(scan)
        db.session.commit()
        scan_id = scan.id

    results_dir = get_results_dir(domain, scan_id)

    if url_discovery:
        logger.info(f"Starting URL discovery for: {domain}")
        run_url_discovery_phase(scan_id, app)
        logger.info("URL discovery finished.")
    else:
        logger.info(f"Starting V3 reconnaissance pipeline for: {domain}")
        # Run the subdomain enumeration phase first
        output_paths, _, _ = enumerate_subdomains_v2(
            domain=domain,
            scan_id=scan_id,
            app=app
        )
        if not output_paths:
            logger.error("Reconnaissance pipeline did not produce any output. Exiting.")
            sys.exit(1)
        logger.info(f"Subdomain enumeration complete for {domain}.")

        # Now run the other phases in parallel
        logger.info("Starting parallel scan phases (URL, Network, Vulnerability)...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_phase = {
                executor.submit(run_url_discovery_phase, scan_id, app): "URL Discovery",
                executor.submit(run_network_scan_phase, scan_id, app): "Network Scan",
                executor.submit(run_vulnerability_scan_phase, scan_id, app): "Vulnerability Scan"
            }

            for future in concurrent.futures.as_completed(future_to_phase):
                phase = future_to_phase[future]
                try:
                    future.result()
                    logger.info(f"{phase} phase completed.")
                except Exception as exc:
                    logger.error(f'{phase} phase generated an exception: {exc}')
        logger.info("All parallel scan phases complete.")


    # Always aggregate results at the end

    aggregate_results({}, domain, logger, results_dir, scan_id)

    config = load_config()
    final_file_path = os.path.join(config['recon_output_dir'], config['final_recon_file'])
    logger.info(f"All findings have been aggregated into: {final_file_path}")

    if upload_to_r2:
        logger.info("R2 upload flag is set. Initiating upload...")
        upload_to_r2(logger, file_path=final_file_path)

    if generate_report:
        from cyberhunter_3d.reporting.pdf_generator import generate_pdf_report
        logger.info("Generating PDF report...")
        generate_pdf_report(scan_id, domain, app)

    logger.info("--- Pipeline Finished ---")


@cli.command(name='monitor')
@click.option("--target", required=True, help="The target value to manage.")
@click.option("--set-schedule", type=click.Choice(['daily', 'weekly', 'monthly']), help="Set the monitoring schedule.")
@click.option("--remove-schedule", is_flag=True, help="Remove the monitoring schedule for the target.")
def monitor_command(target, set_schedule, remove_schedule):
    """
    Manage the monitoring schedule for a target.
    """
    if set_schedule and remove_schedule:
        click.echo("Error: Please use either --set-schedule or --remove-schedule, not both.", err=True)
        sys.exit(1)
    if not set_schedule and not remove_schedule:
        click.echo("Error: Please specify an action, either --set-schedule or --remove-schedule.", err=True)
        sys.exit(1)

    from run_web import create_app
    from cyberhunter_3d.web.models import db, Target, Schedule

    app = create_app()
    with app.app_context():
        target_obj = Target.query.filter_by(value=target).first()
        if not target_obj:
            click.echo(f"Error: Target '{target}' not found in the database. A scan must be run on the target first.", err=True)
            sys.exit(1)

        if set_schedule:
            schedule_obj = target_obj.schedule
            if schedule_obj:
                schedule_obj.frequency = set_schedule
                schedule_obj.is_active = True
                click.echo(f"Updated schedule for '{target}' to '{set_schedule}'.")
            else:
                schedule_obj = Schedule(target_id=target_obj.id, frequency=set_schedule)
                db.session.add(schedule_obj)
                click.echo(f"Set new schedule for '{target}' to '{set_schedule}'.")

        elif remove_schedule:
            if target_obj.schedule:
                db.session.delete(target_obj.schedule)
                click.echo(f"Removed monitoring schedule for '{target}'.")
            else:
                click.echo(f"No schedule found for '{target}'. Nothing to remove.")

        db.session.commit()



if __name__ == "__main__":
    main()
