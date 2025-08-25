from cyberhunter_3d.web.models import db, Scan
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains
from cyberhunter_3d.core.reconnaissance.ip_scan import scan_ip_target

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

            # 2. Dispatch targets to appropriate scanners
            all_results = []
            for target in scan.targets:
                if target.type in ['domain', 'wildcard_domain']:
                    print(f"Dispatching '{target.value}' to subdomain enumerator.")
                    subdomains = enumerate_subdomains(target.value)
                    if subdomains:
                        result_header = f"--- Subdomains for {target.value} ---"
                        all_results.append(result_header)
                        all_results.extend(sorted(list(subdomains)))
                        all_results.append("\n") # Add spacing

                elif target.type in ['ip_address', 'cidr']:
                    print(f"Dispatching '{target.value}' to IP/port scanner.")
                    ip_scan_results = scan_ip_target(target.value)
                    if ip_scan_results:
                        result_header = f"--- Nmap Scan Results for {target.value} ---"
                        all_results.append(result_header)
                        all_results.append(ip_scan_results)
                        all_results.append("\n") # Add spacing
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
