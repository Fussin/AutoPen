from cyberhunter_3d.web.models import db, Scan, Target, Asset
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains
from cyberhunter_3d.core.reconnaissance.ip_scan import scan_ip_target
from cyberhunter_3d.core.reconnaissance.asn_lookup import get_cidrs_for_asn
from cyberhunter_3d.core.reconnaissance.org_lookup import get_assets_for_org
from cyberhunter_3d.core.reconnaissance.reverse_dns import get_hostnames_for_ips
from cyberhunter_3d.core.reconnaissance.analytics_correlation import find_related_domains_by_analytics
from cyberhunter_3d.core.scope_validator import ScopeValidator

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
            # 1. Initialization
            scan.status = 'RUNNING'
            db.session.commit()
            print(f"Scan {scan_id} discovery phase started.")
            validator = ScopeValidator(scan.in_scope_rules, scan.out_of_scope_rules)

            # Prepare for processing
            discovered_assets = []
            targets_to_scan = list(scan.targets)

            # 2. Expansion and Discovery Loop (non-intensive tasks)
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
                    assets = enumerate_subdomains(target.value)
                    discovered_assets.extend(assets)

                elif target.type in ['ip_address', 'cidr']:
                    # Add IPs and CIDRs to be scanned in the execution phase
                    discovered_assets.append({'type': target.type, 'value': target.value})
                else:
                    print(f"Skipping target with unknown type: {target.type}")

            # 3. Validation and Persistence of discovered domains/IPs
            print(f"Persisting {len(discovered_assets)} initially discovered assets...")
            in_scope_count = 0
            out_of_scope_count = 0
            for asset_data in discovered_assets:
                if validator.is_in_scope(asset_data['value']):
                    if not Asset.query.filter_by(scan_id=scan.id, type=asset_data['type'], value=asset_data['value']).first():
                        db.session.add(Asset(type=asset_data['type'], value=asset_data['value'], scan_id=scan.id))
                        in_scope_count += 1
                else:
                    out_of_scope_count += 1

            scan.results = f"Discovery phase complete. Found {in_scope_count} assets. Skipped {out_of_scope_count} out-of-scope items. Awaiting review to start intensive scan."
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
            ip_targets = Asset.query.filter(Asset.scan_id == scan.id, Asset.type.in_(['ip_address', 'cidr'])).all()
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
            domain_assets = Asset.query.filter(Asset.scan_id == scan.id, Asset.type.in_(['domain', 'subdomain'])).all()
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
            print(f"Scan {scan_id} execution phase complete.")

        except Exception as e:
            print(f"FATAL: Error in execution phase for scan {scan_id}: {e}")
            scan.status = 'FAILED'
            scan.results = f"Execution failed with error: {e}"
        finally:
            db.session.commit()
            print(f"Final execution status for scan {scan_id} is {scan.status}.")
