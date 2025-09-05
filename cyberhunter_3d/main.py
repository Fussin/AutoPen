import argparse
import logging
import sys
import os

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # This is a bit of a hack to make imports work given the project structure.
    # It assumes the script is run from the project root.
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

    try:
        from run_web import app, db
        from cyberhunter_3d.web.models import Scan, Target, User
        from cyberhunter_3d.core.phase_manager import PhaseManager
    except ImportError as e:
        logger.error(f"Failed to import necessary modules: {e}")
        logger.error("Please ensure you are running this script from the root of the project directory.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="CyberHunter 3D - Command-Line Scanner")
    parser.add_argument("domain", help="The root domain to target for the scan.")
    parser.add_argument("--user-id", type=int, default=1, help="The user ID to associate the scan with. Defaults to 1.")
    args = parser.parse_args()

    with app.app_context():
        # A database and user must exist for a scan to be created.
        # We can check for the user and provide a helpful error message.
        user = User.query.get(args.user_id)
        if not user:
            logger.error(f"User with ID {args.user_id} not found in the database.")
            logger.error("Please create a user via the web interface before running a scan.")
            sys.exit(1)

        logger.info(f"Starting scan for domain: '{args.domain}' on behalf of user '{user.username}' (ID: {user.id})")

        # 1. Create Scan and Target objects in the DB, mirroring web submission
        new_scan = Scan(user_id=user.id, status='QUEUED')
        db.session.add(new_scan)
        db.session.flush()  # We need the new_scan.id for the target

        new_target = Target(value=args.domain, type='domain', scan_id=new_scan.id)
        db.session.add(new_target)
        db.session.commit()

        logger.info(f"Created Scan with ID: {new_scan.id} and Target: {args.domain}")

        # 2. Instantiate and run the PhaseManager
        try:
            phase_manager = PhaseManager(scan_id=new_scan.id, app=app)
            phase_manager.run_scan()
            logger.info(f"Scan {new_scan.id} process finished.")
            # Update scan status to COMPLETED if it's not FAILED
            final_scan = Scan.query.get(new_scan.id)
            if final_scan.status != 'FAILED':
                final_scan.status = 'COMPLETED'
                db.session.commit()

        except Exception as e:
            logger.exception(f"An error occurred during the scan execution for scan {new_scan.id}.")
            # Mark the scan as FAILED in the database
            scan_to_fail = Scan.query.get(new_scan.id)
            if scan_to_fail:
                scan_to_fail.status = 'FAILED'
                scan_to_fail.results = f"Scan failed due to an unexpected error: {e}"
                db.session.commit()


if __name__ == "__main__":
    main()
