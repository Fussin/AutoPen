import os
from cyberhunter_3d.web.models import db, User, Scan, Target
from cyberhunter_3d.core.feeds.hackerone_client import get_hackerone_scopes
from cyberhunter_3d.core.scan_manager import run_discovery_phase
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=2)

def check_for_new_targets(app):
    """
    Checks for new programs from HackerOne and starts scans for them.
    This function is intended to be called by a scheduler.
    """
    with app.app_context():
        print("FEED: Checking for new targets from HackerOne...")

        # Get all users with a HackerOne API key
        users_with_keys = User.query.filter(User.hackerone_api_key.isnot(None)).all()
        if not users_with_keys:
            print("FEED: No users with HackerOne API keys configured.")
            return

        for user in users_with_keys:
            print(f"FEED: Checking for programs for user '{user.username}'...")
            if not user.hackerone_username:
                print(f"FEED: User '{user.username}' has an API key but no HackerOne username. Skipping.")
                continue

            programs = get_hackerone_scopes(user.hackerone_username, user.hackerone_api_key)

            for program in programs:
                handle = program.get('name')
                if not handle:
                    continue

                # Check if a scan for this program already exists for this user
                existing_scan = Scan.query.filter_by(
                    user_id=user.id,
                    hackerone_program_handle=handle
                ).first()

                if existing_scan:
                    print(f"FEED: Scan for program '{handle}' already exists for user '{user.username}'. Skipping.")
                    continue

                print(f"FEED: Found new program '{handle}' for user '{user.username}'. Creating new scan.")

                # Create a new scan
                new_scan = Scan(
                    user_id=user.id,
                    status='QUEUED',
                    in_scope_rules=program.get('in_scope_rules'),
                    out_of_scope_rules=program.get('out_of_scope_rules'),
                    hackerone_program_handle=handle
                )
                db.session.add(new_scan)
                db.session.flush()

                for target_value in program.get('targets', []):
                    # The target parser from the main app could be used here for more robustness
                    new_target = Target(value=target_value, type='unknown', scan_id=new_scan.id)
                    db.session.add(new_target)

                db.session.commit()
                print(f"FEED: Created new scan with ID {new_scan.id} for program '{handle}'.")

                # Start the discovery phase in the background
                executor.submit(run_discovery_phase, new_scan.id, app)

        print("FEED: Finished checking for new targets.")
