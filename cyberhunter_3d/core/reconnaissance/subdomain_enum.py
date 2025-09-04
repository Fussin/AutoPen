import logging
from ..plugins.manager import PluginManager
from ..plugins.context import ScanContext
from cyberhunter_3d.utils.file_utils import save_to_json, get_results_dir
from ..ai.scan_config_selector import AIScanConfigSelector
from ...web.models import Scan, Asset, Finding, db
from ..error_handler import handle_module_errors, CriticalError
from ..triage_engine import TriageEngine
from ..response_engine import ResponseEngine

log = logging.getLogger(__name__)

def perform_delta_scan(master_subdomains: set, previous_subdomains: set, logger) -> dict:
    if not previous_subdomains:
        logger.info("No previous subdomains found. Skipping delta scan.")
        return {}

    new_subdomains = master_subdomains - previous_subdomains
    removed_subdomains = previous_subdomains - master_subdomains

    logger.info(f"Delta scan found {len(new_subdomains)} new and {len(removed_subdomains)} removed subdomains.")

    return {"new": new_subdomains, "removed": removed_subdomains}

@handle_module_errors(retries=2, fallback_return=({}, None, None), error_severity=CriticalError)
def enumerate_subdomains_v2(domain: str, scan_id: int, app) -> dict:
    """
    Orchestrates the subdomain enumeration process using the new plugin architecture.
    """
    log.info(f"Starting V3 Plugin-Based Reconnaissance for: {domain}")

    with app.app_context():
        scan = db.session.get(Scan, scan_id)
        if not scan:
            log.error(f"Scan with ID {scan_id} not found.")
            return {}

        results_dir = get_results_dir(domain, scan_id)
        context = ScanContext(target_domain=domain, scan_id=scan_id, results_dir=results_dir)
        context.add_event("INFO", "Starting V3 Plugin-Based Reconnaissance.")

        # AI-Powered Scan Configuration
        ai_selector = AIScanConfigSelector()
        # Use the scan_type from the database to drive the AI's decision
        target_info = {'scan_type': scan.scan_type}
        recommended_plugins = ai_selector.select_plugins(target_info)

        context.add_event("INFO", f"AI recommended plugins: {recommended_plugins}")

        plugin_manager = PluginManager()
        plugin_manager.run_all_plugins(context, include_plugins=recommended_plugins)

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

        # --- Automated Triage ---
        log.info(f"Scan {scan_id}: Starting automated triage process...")
        context.add_event("INFO", "Starting automated triage process...")
        triage_engine = TriageEngine(context)
        triaged_findings = triage_engine.run()

        # --- Automated Response ---
        log.info(f"Scan {scan_id}: Starting automated response process...")
        context.add_event("INFO", "Starting automated response process...")
        response_engine = ResponseEngine(triaged_findings)
        final_findings = response_engine.run()

        for finding_data in final_findings:
            # The TriageEngine may return keys not in the DB model, so we filter
            db_finding = Finding(
                scan_id=scan_id,
                title=finding_data.get('title'),
                severity=finding_data.get('severity'),
                confidence=finding_data.get('confidence'),
                status=finding_data.get('status'),
                description=finding_data.get('description'),
                raw_evidence=finding_data.get('raw_evidence'),
                finding_signature=finding_data.get('finding_signature'),
                asset_context=finding_data.get('asset_context'),
                validation_outcome=finding_data.get('validation_outcome'),
                disposition=finding_data.get('disposition'),
            )
            db.session.add(db_finding)
        log.info(f"Scan {scan_id}: Saved {len(triaged_findings)} findings to the database.")
        context.add_event("INFO", f"Saved {len(triaged_findings)} findings to the database.")

        scan.status = 'COMPLETED'
        db.session.commit()

        log.info(f"Scan {scan_id} for {domain} completed. Found {len(all_subdomains)} subdomains.")
        context.add_event("INFO", f"Scan completed. Found {len(all_subdomains)} subdomains.")

        return {"master_results_list": master_filepath}, context, None
