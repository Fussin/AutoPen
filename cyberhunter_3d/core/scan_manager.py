from cyberhunter_3d.web.models import db, Scan, Target
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains
from cyberhunter_3d.core.reconnaissance.ip_scan import scan_ip_target
from cyberhunter_3d.core.reconnaissance.asn_lookup import get_cidrs_for_asn

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
            # 1. Update status to RUNNING
            scan.status = 'RUNNING'
            db.session.commit()
            print(f"Scan {scan_id} status updated to RUNNING.")

            # 2. Process targets, expanding where necessary (e.g., ASNs)
            all_results = []
            # Make a mutable copy of the targets to process
            targets_to_scan = list(scan.targets)

            i = 0
            while i < len(targets_to_scan):
                target = targets_to_scan[i]
                i += 1 # Increment early to avoid infinite loops on expansion

                if target.type == 'asn':
                    print(f"Expanding ASN: AS{target.value}")
                    cidrs = get_cidrs_for_asn(target.value)
                    if cidrs:
                        print(f"Found {len(cidrs)} CIDRs for AS{target.value}. Adding to scan queue.")
                        for cidr in cidrs:
                            # Create a new "virtual" target to be scanned
                            virtual_target = Target(value=cidr, type='cidr')
                            targets_to_scan.append(virtual_target)
                    continue # Move to the next target, skip scanning the ASN itself

                elif target.type in ['domain', 'wildcard_domain']:
                    print(f"Dispatching '{target.value}' to subdomain enumerator.")
                    subdomains = enumerate_subdomains(target.value)
                    if subdomains:
                        result_header = f"--- Subdomains for {target.value} ---"
                        all_results.append(result_header)
                        all_results.extend(sorted(list(subdomains)))
                        all_results.append("\n")

                elif target.type in ['ip_address', 'cidr']:
                    print(f"Dispatching '{target.value}' to IP/port scanner.")
                    ip_scan_results = scan_ip_target(target.value)
                    if ip_scan_results:
                        result_header = f"--- Nmap Scan Results for {target.value} ---"
                        all_results.append(result_header)
                        all_results.append(ip_scan_results)
                        all_results.append("\n")
                else:
                    print(f"Skipping target with unknown type: {target.type}")

            # 3. Store consolidated results
            if all_results:
                scan.results = "\n".join(all_results)
            else:
                scan.results = "Scan completed, but no results were found."

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
