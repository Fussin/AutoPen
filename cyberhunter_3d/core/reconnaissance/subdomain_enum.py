import os
import json
from typing import Set, List, Dict
from cyberhunter_3d.utils.logger import setup_logger
from .utils import load_config, save_to_json
from ..plugins.manager import PluginManager
from ..core.context import ScanContext
from cyberhunter_3d.reporting.reporting import generate_html_report, generate_delta_report
from cyberhunter_3d.web.models import Scan, Target

logger = setup_logger('Pipeline', 'pipeline.log')
config = load_config()

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

    # --- Setup ---
    context = ScanContext(target=domain)
    plugin_manager = PluginManager(plugin_dir="plugins/")

    # --- Plugin Execution ---
    plugin_manager.run_all_plugins(context)

    # --- Post-Plugin Processing ---
    # The new schema generation and reporting will be handled here
    # For now, we just save the context data to a file

    # Create a scan-specific output directory
    config = load_config()
    output_dir = os.path.join(config.get('recon_output_dir', 'recon_results'), f"scan_{scan_id}")
    os.makedirs(output_dir, exist_ok=True)

    # Save the final results to a JSON file
    final_output_path = save_to_json(context.data, os.path.join(output_dir, 'final_recon_data.json'), logger)

    # Find previous subdomains and perform delta scan
    previous_subdomains = set()
    with app.app_context():
        previous_scan = Scan.query.filter(
            Scan.id < scan_id,
            Scan.targets.any(Target.value == domain),
            Scan.status == 'COMPLETED'
        ).order_by(Scan.created_at.desc()).first()

        if previous_scan and previous_scan.output_path and os.path.exists(previous_scan.output_path):
            logger.info(f"Found previous scan {previous_scan.id} to compare for delta.")
            with open(previous_scan.output_path, 'r') as f:
                old_data = json.load(f)
                previous_subdomains = set(old_data.get('subdomains', []))
        elif previous_scan:
            logger.warning(f"Previous scan {previous_scan.id} found, but no output path is set or file does not exist.")

    if previous_subdomains:
        delta_paths = perform_delta_scan(context.get("subdomains"), previous_subdomains, logger, output_dir)
        if delta_paths:
            generate_delta_report(output_dir, delta_paths)

    return [final_output_path] if final_output_path else []
