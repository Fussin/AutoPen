from cyberhunter_3d.web.models import db, Scan, Target
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains
from cyberhunter_3d.core.reconnaissance.ip_scan import scan_ip_target
from cyberhunter_3d.core.reconnaissance.asn_lookup import get_cidrs_for_asn
from cyberhunter_3d.core.reconnaissance.org_lookup import get_assets_for_org
from cyberhunter_3d.core.scope_validator import ScopeValidator

def run_scan(scan_id, app):
    """
    The core function that executes a scan.
    This is intended to be run in a background thread.
    It acts as a dispatcher, routing targets to the correct scanner.
    """
    with app.app_context():
        print(f"Starting scan for scan_id: {scan_id}")
        scan = Scan.query.get(scan_id)
        if not scan:
            print(f"Error: Scan with id {scan_id} not found.")
            return

        try:
            # 1. Update status to RUNNING and initialize validator
            scan.status = 'RUNNING'
            db.session.commit()
            print(f"Scan {scan_id} status updated to RUNNING.")

            validator = ScopeValidator(scan.in_scope_rules, scan.out_of_scope_rules)

            # 2. Process targets, expanding and validating
            all_results = []
            out_of_scope_items = set()
            targets_to_scan = list(scan.targets)

            i = 0
            while i < len(targets_to_scan):
                target = targets_to_scan[i]
                i += 1

                if target.type == 'asn':
                    print(f"Expanding ASN: AS{target.value}")
                    cidrs = get_cidrs_for_asn(target.value)
                    if cidrs:
                        print(f"Found {len(cidrs)} CIDRs for AS{target.value}. Adding to scan queue.")
                        for cidr in cidrs:
                            targets_to_scan.append(Target(value=cidr, type='cidr'))
                    continue

                elif target.type == 'org_name':
                    print(f"Expanding Organization: {target.value}")
                    assets = get_assets_for_org(target.value)
                    if assets:
                        print(f"Found {len(assets)} assets for {target.value}. Adding to scan queue.")
                        for asset_value, asset_type in assets:
                            targets_to_scan.append(Target(value=asset_value, type=asset_type))
                    continue

                elif target.type in ['domain', 'wildcard_domain']:
                    print(f"Finding subdomains for '{target.value}'...")
                    subdomains = enumerate_subdomains(target.value)
                    in_scope_subdomains = []
                    for sub in subdomains:
                        if validator.is_in_scope(sub):
                            in_scope_subdomains.append(sub)
                        else:
                            out_of_scope_items.add(f"{sub} (from {target.value})")

                    if in_scope_subdomains:
                        all_results.append(f"--- In-Scope Subdomains for {target.value} ---")
                        all_results.extend(sorted(in_scope_subdomains))
                        all_results.append("\n")

                elif target.type in ['ip_address', 'cidr']:
                    # For now, we assume primary targets like IPs/CIDRs are in scope
                    # by definition, but we could add validation here too if needed.
                    # The main validation is for assets discovered *from* these targets.
                    print(f"Dispatching '{target.value}' to IP/port scanner.")
                    ip_scan_results = scan_ip_target(target.value)
                    if ip_scan_results:
                        all_results.append(f"--- Nmap Scan Results for {target.value} ---")
                        all_results.append(ip_scan_results)
                        all_results.append("\n")
                else:
                    print(f"Skipping target with unknown type: {target.type}")

            # 3. Store consolidated results, including out-of-scope items
            if out_of_scope_items:
                all_results.append("--- Skipped (Out of Scope) ---")
                all_results.extend(sorted(list(out_of_scope_items)))
                all_results.append("\n")

            if all_results:
                scan.results = "\n".join(all_results)
            else:
                scan.results = "Scan completed. No in-scope results were found."

            print(f"Scan {scan_id} processing complete.")

            # 4. Update status to COMPLETED
            scan.status = 'COMPLETED'
            print(f"Scan {scan_id} completed successfully.")

        except Exception as e:
            print(f"Error running scan {scan_id}: {e}")
            scan.status = 'FAILED'

        finally:
            # 5. Commit final status to the database
            db.session.commit()
            print(f"Final status for scan {scan_id} is {scan.status}.")
