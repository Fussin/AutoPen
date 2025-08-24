from cyberhunter_3d.web.models import db, Scan
from cyberhunter_3d.core.reconnaissance.subdomain_enum import enumerate_subdomains

def run_scan(scan_id, app):
    """
    The core function that executes a scan.
    This is intended to be run in a background thread.
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

            # 2. Run enumeration for all targets
            all_found_subdomains = set()
            for target in scan.targets:
                print(f"Enumerating subdomains for target: {target.value}")
                # Note: enumerate_subdomains prints its own progress
                subdomains = enumerate_subdomains(target.value)
                all_found_subdomains.update(subdomains)

            # 3. Store results
            results_str = "\n".join(sorted(list(all_found_subdomains)))
            scan.results = results_str
            print(f"Found a total of {len(all_found_subdomains)} unique subdomains for scan {scan_id}.")

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
