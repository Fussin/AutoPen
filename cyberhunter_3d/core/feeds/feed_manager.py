from .hackerone_client import get_hackerone_scopes
from cyberhunter_3d.web.models import db, Scan, Target, User
from flask import Flask

def check_for_new_targets(app: Flask):
    """
    Checks for new targets from all integrated feeds (currently just HackerOne).
    This function is designed to be run in a background scheduler.
    """
    with app.app_context():
        print("Checking for new targets from feeds...")
        users_with_h1 = User.query.filter(
            User.is_autonomous_scanning_enabled == True,
            User.hackerone_username.isnot(None),
            User.hackerone_api_key.isnot(None)
        ).all()

        for user in users_with_h1:
            print(f"Checking HackerOne for user: {user.username}")
            h1_scopes = get_hackerone_scopes(user.hackerone_username, user.hackerone_api_key)

            for scope in h1_scopes:
                program_name = scope.get("name")
                if not program_name:
                    continue

                # Check if a scan for this program already exists for this user
                existing_scan = Scan.query.join(Target).filter(
                    Scan.user_id == user.id,
                    Target.value.like(f"%{program_name}%")
                ).first()

                if not existing_scan:
                    print(f"Found new program '{program_name}' for user '{user.username}'. Creating new scan.")

                    new_scan = Scan(user_id=user.id, status='QUEUED', name=f"H1 - {program_name}")
                    db.session.add(new_scan)
                    db.session.flush()  # To get the scan ID

                    for target_value in scope.get("targets", []):
                        new_target = Target(
                            value=target_value,
                            type='domain',  # Assuming targets are domains for now
                            scan_id=new_scan.id,
                            in_scope_rules="\n".join(scope.get("in_scope_rules", [])),
                            out_of_scope_rules="\n".join(scope.get("out_of_scope_rules", []))
                        )
                        db.session.add(new_target)

                    db.session.commit()
        print("Finished checking for new targets.")
