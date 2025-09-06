from cyberhunter_3d.web.models import db, Scan, Target, Asset
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains_v2
from cyberhunter_3d.core.reconnaissance.ip_scan import scan_ip_target
from cyberhunter_3d.core.reconnaissance.asn_lookup import get_cidrs_for_asn
from cyberhunter_3d.core.reconnaissance.org_lookup import get_assets_for_org
from cyberhunter_3d.core.reconnaissance.reverse_dns import get_hostnames_for_ips
from cyberhunter_3d.core.reconnaissance.analytics_correlation import find_related_domains_by_analytics
from cyberhunter_3d.core.scope_validator import ScopeValidator
from cyberhunter_3d.core.decision_tree import DecisionTree
from .output_manager import create_output_directory

def run_discovery_phase(scan_id, app):
    """
    Performs the initial discovery and expansion phases of a scan using the DecisionTree.
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

            # Create output directory
            output_dir = create_output_directory(scan_id)
            scan.output_dir = output_dir

            # 2. Use DecisionTree to process targets
            decision_tree = DecisionTree(scan_id, app)
            initial_targets = list(scan.targets) # Create a copy
            for target in initial_targets:
                decision_tree.process_target(target)

            # 3. Persist the results from the DecisionTree
            in_scope_count, out_of_scope_count = decision_tree.persist_discovered_assets()

            # 4. Finalize Discovery Phase
            scan.results = f"Discovery phase complete. Found {in_scope_count} new assets. Skipped {out_of_scope_count} out-of-scope items. Awaiting review to start intensive scan."
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
            scan.status = 'COMPLETED'
            print(f"Scan {scan_id} execution phase complete.")

        except Exception as e:
            print(f"FATAL: Error in execution phase for scan {scan_id}: {e}")
            scan.status = 'FAILED'
            scan.results = f"Execution failed with error: {e}"
        finally:
            db.session.commit()
            print(f"Final execution status for scan {scan_id} is {scan.status}.")
