from cyberhunter_3d.web.models import db, Scan, Target, Asset, ScanProgress
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains_v2
from cyberhunter_3d.core.reconnaissance.ip_scan import scan_ip_target
from cyberhunter_3d.core.reconnaissance.asn_lookup import get_cidrs_for_asn
from cyberhunter_3d.core.reconnaissance.org_lookup import get_assets_for_org
from cyberhunter_3d.core.reconnaissance.reverse_dns import get_hostnames_for_ips
from cyberhunter_3d.core.reconnaissance.analytics_correlation import find_related_domains_by_analytics
from cyberhunter_3d.core.scope_validator import ScopeValidator
from cyberhunter_3d.core.reconnaissance.url_discovery_manager import discover_urls

def run_url_discovery_phase(scan_id, app):
    """
    Performs the URL discovery and vulnerability scanning phase.
    """
    with app.app_context():
        scan = db.session.get(Scan, scan_id)
        if not scan:
            print(f"Error: Scan {scan_id} not found for URL discovery phase.")
            return

        for target in scan.targets:
            # Assuming the main target for URL discovery is the 'domain' type
            if target.type == 'domain':
                discover_urls(target.value, scan_id, app)

def _update_progress(scan_id, module_name, progress):
    """Helper to update the progress of a scan module."""
    progress_entry = ScanProgress.query.filter_by(scan_id=scan_id, module_name=module_name).first()
    if progress_entry:
        progress_entry.progress = progress
    else:
        progress_entry = ScanProgress(scan_id=scan_id, module_name=module_name, progress=progress)
        db.session.add(progress_entry)
    db.session.commit()

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
        scan = db.session.get(Scan, scan_id)
        if not scan:
            print(f"Error: Scan {scan_id} not found for discovery phase.")
            return

        try:
            scan.status = 'RUNNING'
            db.session.commit()
            _update_progress(scan_id, 'Discovery', 5)
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
                    _update_progress(scan_id, 'Subdomain Discovery', 20)
                    recon_data = enumerate_subdomains_v2(target.value)
                    _update_progress(scan_id, 'Subdomain Discovery', 80)

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
            _update_progress(scan_id, 'Discovery', 100)
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
            _update_progress(scan_id, 'Execution', 5)
            print(f"Scan {scan_id} execution phase started.")
            validator = ScopeValidator(scan.in_scope_rules, scan.out_of_scope_rules)
            out_of_scope_count = 0 # We need to track this across phases

            # 1. Port Scanning
            _update_progress(scan_id, 'Network Scanning', 10)
            ip_targets = Asset.query.filter(
                Asset.scan_id == scan.id,
                Asset.is_approved_for_scan == True,
                Asset.type.in_(['ip_address', 'cidr'])
            ).all()
            for i, target in enumerate(ip_targets):
                print(f"Port scanning '{target.value}'...")
                ip_scan_assets = scan_ip_target(target.value)
                for asset_data in ip_scan_assets:
                    if not Asset.query.filter_by(scan_id=scan.id, type=asset_data['type'], value=asset_data['value']).first():
                        db.session.add(Asset(type=asset_data['type'], value=asset_data['value'], details=asset_data.get('details'), scan_id=scan.id))
                _update_progress(scan_id, 'Network Scanning', 10 + int(60 * (i + 1) / len(ip_targets)))
            db.session.commit()
            _update_progress(scan_id, 'Network Scanning', 70)

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
            scan.status = 'COMPLETED'
            _update_progress(scan_id, 'Execution', 100)
            _update_progress(scan_id, 'Network Scanning', 100)
            print(f"Scan {scan_id} execution phase complete.")

        except Exception as e:
            print(f"FATAL: Error in execution phase for scan {scan_id}: {e}")
            scan.status = 'FAILED'
            scan.results = f"Execution failed with error: {e}"
        finally:
            db.session.commit()
            print(f"Final execution status for scan {scan_id} is {scan.status}.")
