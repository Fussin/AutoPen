import logging
from flask import Flask
from .feeds.hackerone_client import get_hackerone_scopes
from ..web.models import db, User, Scan, Target

log = logging.getLogger(__name__)

def sync_hackerone_programs(app: Flask):
    """
    Fetches HackerOne programs for all users with an API key and creates
    new scans for programs that haven't been scanned before.
    """
    with app.app_context():
        log.info("Scheduler: Starting HackerOne program sync job.")

        # Get all users who have a HackerOne API key configured
        users_with_h1_keys = User.query.filter(User.hackerone_api_key.isnot(None)).all()
        if not users_with_h1_keys:
            log.info("Scheduler: No users with HackerOne API keys found. Exiting job.")
            return

        total_new_scans = 0
        for user in users_with_h1_keys:
            log.info(f"Scheduler: Fetching programs for user '{user.username}'.")
            # The H1 API requires both a username and a key for its auth
            # Assuming the user's main username is their H1 username.
            # A more robust implementation might store the H1 user separately.
            try:
                programs = get_hackerone_scopes(user.username, user.hackerone_api_key)
            except Exception as e:
                log.error(f"Scheduler: Failed to fetch H1 scopes for user '{user.username}': {e}")
                continue

            for program in programs:
                program_name = program.get('name')
                if not program_name:
                    continue

                # Create a unique source identifier for this program and user
                scan_source_id = f"h1-{user.id}-{program_name}"

                # Check if a scan from this source already exists
                existing_scan = Scan.query.filter_by(source=scan_source_id, user_id=user.id).first()
                if existing_scan:
                    log.info(f"Scheduler: Scan for program '{program_name}' already exists for user '{user.username}'. Skipping.")
                    continue

                # If we are here, it's a new program, so create a scan
                log.info(f"Scheduler: Found new program '{program_name}' for user '{user.username}'. Creating scan.")

                # Create the new scan object
                new_scan = Scan(
                    user_id=user.id,
                    status='QUEUED',
                    scan_type='passive', # Automated scans default to passive
                    source=scan_source_id,
                    in_scope_rules=program.get('in_scope_rules', ''),
                    out_of_scope_rules=program.get('out_of_scope_rules', '')
                )
                db.session.add(new_scan)

                # We need to flush to get the new_scan.id
                db.session.flush()

                # Add all targets from the program to this scan
                for target_value in program.get('targets', []):
                    new_target = Target(value=target_value, scan_id=new_scan.id)
                    db.session.add(new_target)

                total_new_scans += 1

        # Commit all the new scans and targets for all users at once
        db.session.commit()
        log.info(f"Scheduler: HackerOne sync job finished. Created {total_new_scans} new scans.")
