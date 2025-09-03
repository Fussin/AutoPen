from cyberhunter_3d.web.models import db, Scan, Target, Asset
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains_v2
from cyberhunter_3d.core.reconnaissance.ip_scan import scan_ip_target
from cyberhunter_3d.core.reconnaissance.asn_lookup import get_cidrs_for_asn
from cyberhunter_3d.core.reconnaissance.org_lookup import get_assets_for_org
from cyberhunter_3d.core.reconnaissance.reverse_dns import get_hostnames_for_ips
from cyberhunter_3d.core.reconnaissance.analytics_correlation import find_related_domains_by_analytics
from cyberhunter_3d.core.scope_validator import ScopeValidator
from cyberhunter_3d.core.reconnaissance.url_discovery_manager import discover_urls
from .specialized_scan_manager import SpecializedScanManager
from .plugins.context import ScanContext
from .session_closure import SessionCloser

def run_url_discovery_phase(scan_id, app):
    """
    Performs the URL discovery and vulnerability scanning phase.
    """
    with app.app_context():
        scan = Scan.query.get(scan_id)
        if not scan:
            print(f"Error: Scan {scan_id} not found for URL discovery phase.")
            return

        for target in scan.targets:
            # Assuming the main target for URL discovery is the 'domain' type
            if target.type == 'domain':
                discover_urls(target.value, scan_id, app)

def _create_asset_if_new(scan_id, asset_type, value, validator, details=None):
    """Helper to create a new asset if it is in scope and doesn't already exist."""
    if not validator.is_in_scope(value):
        return False, 'out_of_scope'

    if not Asset.query.filter_by(scan_id=scan_id, type=asset_type, value=value).first():
        asset = Asset(
            scan_id=scan_id,
            type=asset_type,
            value=value,
            details=details
        )
        db.session.add(asset)
        return True, 'created'
    return False, 'exists'

def run_discovery_phase(scan_id, app):
    """
    Performs the initial discovery and expansion phases of a scan.
    This includes subdomain enumeration and expansion from ASN/Org targets.
    It persists discovered assets and sets the scan status to PENDING_REVIEW.
    """
    with app.app_context():
        scan = Scan.query.get(scan_id)
        if not scan:
            print(f"Error: Scan {scan_id} not found for discovery phase.")
            return

        try:
            scan.status = 'RUNNING'
            db.session.commit()
            print(f"Scan {scan_id} discovery phase started.")
            validator = ScopeValidator(scan.in_scope_rules, scan.out_of_scope_rules)

            in_scope_count = 0
            out_of_scope_count = 0

            targets_to_scan = list(scan.targets)
            i = 0
            while i < len(targets_to_scan):
                target = targets_to_scan[i]
                i += 1

                if target.type in ['asn', 'org_name']:
                    print(f"Expanding {target.type}: {target.value}")
                    assets_to_add = []
                    if target.type == 'asn':
                        assets_to_add = get_cidrs_for_asn(target.value)
                    elif target.type == 'org_name':
                        assets_to_add = get_assets_for_org(target.value)

                    for asset_data in assets_to_add:
                        targets_to_scan.append(Target(value=asset_data['value'], type=asset_data['type']))
                    continue

                elif target.type in ['domain', 'wildcard_domain']:
                    print(f"Finding subdomains for '{target.value}'...")
                    recon_data = enumerate_subdomains_v2(target.value)

                    # Persist assets directly from the recon data dictionary
                    for sub in recon_data.get('master_subdomains', []):
                        created, status = _create_asset_if_new(scan.id, 'subdomain', sub, validator)
                        if created: in_scope_count += 1
                        elif status == 'out_of_scope': out_of_scope_count += 1

                    for host in recon_data.get('live_hosts', []):
                        created, status = _create_asset_if_new(scan.id, 'live_host', host, validator)
                        if created: in_scope_count += 1
                        elif status == 'out_of_scope': out_of_scope_count += 1

                    for vuln in recon_data.get('subdomain_takeover_vulnerabilities', []):
                        host = vuln.get('host', 'unknown_host')
                        created, status = _create_asset_if_new(scan.id, 'vulnerability', host, validator, details=vuln)
                        if created: in_scope_count += 1
                        elif status == 'out_of_scope': out_of_scope_count += 1

                    for tech, details in recon_data.get('technology_and_ports', {}).items():
                        created, status = _create_asset_if_new(scan.id, 'technology', tech, validator, details=details)
                        if created: in_scope_count += 1
                        elif status == 'out_of_scope': out_of_scope_count += 1

                    for asset in recon_data.get('cloud_assets', []):
                        value = asset.get('value', 'unknown_asset')
                        created, status = _create_asset_if_new(scan.id, 'cloud_asset', value, validator, details=asset)
                        if created: in_scope_count += 1
                        elif status == 'out_of_scope': out_of_scope_count += 1

                elif target.type in ['ip_address', 'cidr']:
                    created, status = _create_asset_if_new(scan.id, target.type, target.value, validator)
                    if created: in_scope_count += 1
                    elif status == 'out_of_scope': out_of_scope_count += 1

                db.session.commit()

            scan.results = f"Discovery phase complete. Found {in_scope_count} new in-scope assets. Skipped {out_of_scope_count} out-of-scope items. Awaiting review to start intensive scan."
            scan.status = 'PENDING_REVIEW'
            print(f"Scan {scan_id} discovery phase complete.")

        except Exception as e:
            print(f"FATAL: Error in discovery phase for scan {scan_id}: {e}")
            scan.status = 'FAILED'
            scan.results = f"Discovery failed with error: {e}"
        finally:
            db.session.commit()
            print(f"Final discovery status for scan {scan_id} is {scan.status}.")


def run_execution_phase(scan_id, app):
    """
    Performs the intensive execution phase of a scan on assets that have
    already been discovered and approved. This includes port scanning and
    further expansion.
    """
    with app.app_context():
        scan = Scan.query.get(scan_id)
        if not scan:
            print(f"Error: Scan {scan_id} not found for execution phase.")
            return

        try:
            scan.status = 'RUNNING'
            db.session.commit()
            print(f"Scan {scan_id} execution phase started.")
            validator = ScopeValidator(scan.in_scope_rules, scan.out_of_scope_rules)
            out_of_scope_count = 0 # We need to track this across phases

            # 1. Port Scanning
            ip_targets = Asset.query.filter(
                Asset.scan_id == scan.id,
                Asset.is_approved_for_scan == True,
                Asset.type.in_(['ip_address', 'cidr'])
            ).all()
            for target in ip_targets:
                print(f"Port scanning '{target.value}'...")
                ip_scan_assets = scan_ip_target(target.value)
                for asset_data in ip_scan_assets:
                    if not Asset.query.filter_by(scan_id=scan.id, type=asset_data['type'], value=asset_data['value']).first():
                        db.session.add(Asset(type=asset_data['type'], value=asset_data['value'], details=asset_data.get('details'), scan_id=scan.id))
            db.session.commit()

            # 2. Expansion Phase (Reverse DNS)
            print("Starting Expansion: Reverse DNS")
            ip_assets = Asset.query.filter(Asset.scan_id == scan.id, Asset.type == 'host_with_open_ports').all()
            unique_ips = list(set(asset.value for asset in ip_assets))
            rdns_found_count = 0
            if unique_ips:
                hostnames = get_hostnames_for_ips(unique_ips)
                for hostname in hostnames:
                    if validator.is_in_scope(hostname) and not Asset.query.filter_by(scan_id=scan.id, value=hostname).first():
                        db.session.add(Asset(type='subdomain', value=hostname, scan_id=scan.id))
                        rdns_found_count += 1
                    elif not validator.is_in_scope(hostname):
                        out_of_scope_count += 1
            print(f"rDNS complete. Found {rdns_found_count} new hostnames.")
            db.session.commit()

            # 3. Expansion Phase (Analytics Correlation)
            print("Starting Expansion: Analytics Correlation")
            domain_assets = Asset.query.filter(
                Asset.scan_id == scan.id,
                Asset.is_approved_for_scan == True,
                Asset.type.in_(['domain', 'subdomain'])
            ).all()
            unique_domains = list(set(asset.value for asset in domain_assets))
            analytics_found_count = 0
            if unique_domains:
                related_domains = find_related_domains_by_analytics(unique_domains)
                for domain in related_domains:
                    if validator.is_in_scope(domain) and not Asset.query.filter_by(scan_id=scan.id, value=domain).first():
                        db.session.add(Asset(type='subdomain', value=domain, scan_id=scan.id))
                        analytics_found_count += 1
                    elif not validator.is_in_scope(domain):
                        out_of_scope_count += 1
            print(f"Analytics complete. Found {analytics_found_count} new domains.")

            # 4. Finalize Scan
            final_asset_count = Asset.query.filter_by(scan_id=scan.id).count()
            scan.results = (
                f"Execution phase complete. Total in-scope assets: {final_asset_count} "
                f"(including {rdns_found_count} from rDNS and {analytics_found_count} from analytics). "
                f"Skipped {out_of_scope_count} out-of-scope items during expansion."
            )
            print(f"Scan {scan_id} execution phase complete.")
            exit_code = 0

        except Exception as e:
            print(f"FATAL: Error in execution phase for scan {scan_id}: {e}")
            scan.status = 'FAILED'
            scan.results = f"Execution failed with error: {e}"
            exit_code = 1
        finally:
            db.session.commit()
            print(f"Final execution status for scan {scan_id} is {scan.status}."

            # Since this is run from the web app, we need the domain to initialize the closer.
            target = Target.query.filter_by(scan_id=scan_id, type='domain').first()
            if target:
                session_closer = SessionCloser(
                    scan_id=scan_id,
                    app=app,
                    domain=target.value,
                    should_upload_to_r2=False, # Web scans currently don't have this option
                    keep_temp_files=False # Default to cleaning up
                )
                session_closer.finalize_session()
            else:
                print(f"Could not find domain for scan {scan_id} to finalize session.")

            # Since this is run from the web app, we need the domain to initialize the closer.
            target = Target.query.filter_by(scan_id=scan_id, type='domain').first()
            if target:
                session_closer = SessionCloser(
                    scan_id=scan_id,
                    app=app,
                    domain=target.value,
                    should_upload_to_r2=False, # Web scans currently don't have this option
                    keep_temp_files=False # Default to cleaning up
                )
                session_closer.finalize_session()
            else:
                print(f"Could not find domain for scan {scan_id} to finalize session.")



def launch_scan(scan_id, app):
    """
    Launches a full scan pipeline for a given scan_id.
    """
    print(f"--- Launching full scan for scan_id: {scan_id} ---")
    # The web UI flow has a manual approval step, so it calls these separately.
    # For autonomous scans, we run them back-to-back.
    run_discovery_phase(scan_id, app)
    run_execution_phase(scan_id, app)

    with app.app_context():
        scan = db.session.get(Scan, scan_id)
        if scan and scan.status == 'COMPLETED':
             _run_continuous_monitoring(scan, app)

    print(f"--- Full scan for scan_id: {scan_id} finished ---")


def _run_continuous_monitoring(scan, app):
    """
    Run the continuous monitor to compare the given scan with its baseline.
    """
    with app.app_context():
        if not scan.targets:
            print("No targets found for this scan. Cannot run monitor.")
            return
        target = scan.targets[0]

        print(f"Running continuous monitoring for {target.value}. Looking for baseline scan.")
        baseline_scan = Scan.query.join(Target).filter(
            Target.value == target.value,
            Scan.status == 'COMPLETED',
            Scan.id != scan.id
        ).order_by(Scan.created_at.desc()).first()

        if not baseline_scan:
            print(f"No previous completed scan found for {target.value}. This scan will be the new baseline.")
            return

        print(f"Found baseline scan {baseline_scan.id}. Running monitor against current scan {scan.id}.")
        monitor = ContinuousMonitor(baseline_scan_id=baseline_scan.id, current_scan_id=scan.id)
        changes = monitor.compare_assets()

        if not changes:
            print("No changes detected by the monitor.")
            return

        # --- Storing Alerts and Notifying ---
        alerts_to_notify = []
        for change in changes:
            alert = Alert(
                title=change.get('title', 'Untitled Alert'),
                description=change.get('description', 'No description.'),
                severity=change.get('severity', 'Info'),
                details=change.get('details', {}),
                scan_id=scan.id
            )
            db.session.add(alert)

            notification_event = change.copy()
            notification_event['type'] = 'alert'
            alerts_to_notify.append(notification_event)

        db.session.commit()
        print(f"Created {len(changes)} alerts in the database.")

        print("Sending alerts to notification channels...")
        event_engine = EventEngine(events=alerts_to_notify)
        event_engine.run()


        # Here you would process the final_context, e.g., save new targets
        # to the database.
        print("Specialized scanning complete. Context is now:", final_context.data)

def run_network_scan_phase(scan_id, app):
    """
    Performs the network scanning phase of a scan on discovered assets.
    """
    with app.app_context():
        scan = Scan.query.get(scan_id)
        if not scan:
            print(f"Error: Scan {scan_id} not found for network scan phase.")
            return

        domain_target = Target.query.filter_by(scan_id=scan_id, type='domain').first()
        if not domain_target:
            print(f"Error: No domain target found for scan {scan_id} to initialize context.")
            return

        from cyberhunter_3d.utils.file_utils import get_results_dir
        results_dir = get_results_dir(domain_target.value, scan.id)

        context = ScanContext(
            target_domain=domain_target.value,
            scan_id=scan.id,
            results_dir=results_dir
        )

        live_hosts = {asset.value for asset in Asset.query.filter_by(scan_id=scan_id, type='live_host').all()}
        context.set('validated_subdomains', live_hosts)

        plugin_manager = PluginManager()
        network_plugins = ['Nmap Scan', 'Naabu Scan', 'Masscan Scan']
        plugin_manager.run_all_plugins(context, include_plugins=network_plugins)

        # Persist results
        open_ports = context.get('open_ports', {})
        for host, ports in open_ports.items():
            asset = Asset.query.filter_by(scan_id=scan_id, value=host).first()
            if asset:
                if asset.details:
                    asset.details['open_ports'] = ports
                else:
                    asset.details = {'open_ports': ports}
        db.session.commit()
        print(f"Network scan phase for scan {scan_id} complete.")

def run_vulnerability_scan_phase(scan_id, app):
    """
    Wrapper for the specialized scanning phase which includes vulnerability scanning.
    """
    print(f"Starting vulnerability scan phase for scan {scan_id}.")
    run_specialized_scans(scan_id, app)
    print(f"Vulnerability scan phase for scan {scan_id} complete.")


