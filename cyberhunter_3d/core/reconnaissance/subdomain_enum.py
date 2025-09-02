import logging
from ..plugins.manager import PluginManager
from ..plugins.context import ScanContext
from cyberhunter_3d.utils.file_utils import save_to_json, get_results_dir
from ...web.models import Scan, Asset, db

log = logging.getLogger(__name__)

def perform_delta_scan(master_subdomains: set, previous_subdomains: set, logger) -> dict:
    if not previous_subdomains:
        logger.info("No previous subdomains found. Skipping delta scan.")
        return {}

    new_subdomains = master_subdomains - previous_subdomains
    removed_subdomains = previous_subdomains - master_subdomains

    logger.info(f"Delta scan found {len(new_subdomains)} new and {len(removed_subdomains)} removed subdomains.")

    return {"new": new_subdomains, "removed": removed_subdomains}

def enumerate_subdomains_v2(domain: str, scan_id: int, app) -> dict:
    """
    Orchestrates the subdomain enumeration process using the new plugin architecture.
    """
    log.info(f"Starting V3 Plugin-Based Reconnaissance for: {domain}")

    with app.app_context():
        scan = Scan.query.get(scan_id)
        if not scan:
            log.error(f"Scan with ID {scan_id} not found.")
            return {}

        results_dir = get_results_dir(domain, scan_id)
        context = ScanContext(target_domain=domain, scan_id=scan_id, results_dir=results_dir)

        plugin_manager = PluginManager()

        # Exclude network scanning plugins from this phase
        network_plugins = ['Nmap Scan', 'Naabu Scan', 'Masscan Scan']
        plugins_to_run_names = [p.name for p in plugin_manager.plugins if p.name not in network_plugins]

        plugin_manager.run_all_plugins(context, include_plugins=plugins_to_run_names)

        all_subdomains = context.get('subdomains', set())

        final_results = {
            "target": domain,
            "scan_id": scan_id,
            "all_subdomains": list(all_subdomains),
            "validated_subdomains": list(context.get('validated_subdomains', set())),
            "cloud_assets": context.get('cloud_assets', []),
            "tech_fingerprints": context.get('tech_fingerprints', {}),
            "open_ports": context.get('open_ports', {}),
            "takeover_vulnerabilities": context.get('takeover_vulnerabilities', []),
            "cve_results": context.get('cve_results', {}),
            "secrets": context.get('secrets', []),
        }

        master_filepath = save_to_json(
            f"final_results_{scan_id}.json",
            final_results,
            results_dir
        )

        for sub in all_subdomains:
            asset = Asset(
                scan_id=scan_id,
                target_id=scan.targets[0].id,
                type='subdomain',
                value=sub
            )
            db.session.add(asset)

        scan.status = 'COMPLETED'
        db.session.commit()

        log.info(f"Scan {scan_id} for {domain} completed. Found {len(all_subdomains)} subdomains.")

        return {"master_results_list": master_filepath}
