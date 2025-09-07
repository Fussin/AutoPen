import logging
import shutil
import requests
from pathlib import Path
from .output_manager import OutputManager
from cyberhunter_3d.web.models import db, Scan, Target, User
from cyberhunter_3d.core.reporting.email_service import send_report_email

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def final_validation(scan_id, om: OutputManager):
    """Checks if the backup archive was created successfully."""
    logger.info(f"[{scan_id}] Performing final validation...")
    archive_path = Path("archive") / f"{om.base_dir.name}.zip"
    if archive_path.exists():
        logger.info(f"Validation successful: Archive found at {archive_path}")
    else:
        logger.error(f"Validation failed: Archive not found at {archive_path}")
    logger.info(f"[{scan_id}] Final validation complete.")

def notification_dispatch(scan_id, app, om: OutputManager):
    """Sends email notifications to stakeholders if enabled."""
    logger.info(f"[{scan_id}] Dispatching notifications...")

    scan = Scan.query.get(scan_id)
    if not scan:
        logger.error(f"[{scan_id}] Could not find scan for notification dispatch.")
        return

    user = scan.user
    if user and user.is_email_notifications_enabled and user.email:
        logger.info(f"[{scan_id}] Email notifications enabled for user {user.username}.")

        # Generate the PDF report
        summary = om.finalize(generate_pdf=True)
        pdf_report_path = summary.get("reports", [{}])[0].get("path")

        if pdf_report_path:
            with app.app_context():
                send_report_email(user.email, scan, pdf_report_path)
        else:
            logger.error(f"[{scan_id}] PDF report was not generated. Cannot send email.")
    else:
        logger.info(f"[{scan_id}] Email notifications are disabled for user {user.username}.")

    logger.info(f"[{scan_id}] Notification dispatch complete.")

def data_archival(scan_id, om: OutputManager):
    """Moves the backup archive to a long-term storage directory."""
    logger.info(f"[{scan_id}] Archiving data...")
    try:
        archive_dir = Path("archive")
        archive_dir.mkdir(exist_ok=True)

        archive_filename = f"{om.base_dir.name}.zip"
        source_path = om.base_dir.parent / archive_filename

        if not source_path.exists():
            logger.error(f"[{scan_id}] Backup archive not found at {source_path}. Skipping archival.")
            return

        destination_path = archive_dir / archive_filename
        shutil.move(str(source_path), str(destination_path))

        print(f"[{scan_id}] Data archived to: {destination_path}")
        logger.info(f"[{scan_id}] Data archival complete.")
    except Exception as e:
        logger.error(f"[{scan_id}] Data archival failed: {e}")

def integration_updates(scan_id):
    """Simulates pushing updates to JIRA and Slack."""
    logger.info(f"[{scan_id}] Sending integration updates...")

    # In a real implementation, you would fetch these from a config file
    jira_webhook = "https://example.jira.com/hooks/..."
    slack_webhook = "https://hooks.slack.com/services/..."

    jira_payload = {"text": f"Scan {scan_id} completed. Results are ready for review."}
    try:
        # We don't expect this to succeed as the URL is fake, but it's a more realistic simulation.
        response = requests.post(jira_webhook, json=jira_payload, timeout=5)
        print(f"[{scan_id}] Pushed update to JIRA. Status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"[{scan_id}] Failed to push update to JIRA: {e}")

    slack_payload = {"text": f"Scan {scan_id} completed. Results available at <http://example.com/scans/{scan_id}>"}
    try:
        response = requests.post(slack_webhook, json=slack_payload, timeout=5)
        print(f"[{scan_id}] Pushed update to Slack. Status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"[{scan_id}] Failed to push update to Slack: {e}")

    logger.info(f"[{scan_id}] Integration updates complete.")

def cleanup_operations(scan_id, om: OutputManager):
    """Deletes the original scan results directory."""
    logger.info(f"[{scan_id}] Performing cleanup operations...")
    try:
        shutil.rmtree(om.base_dir)
        print(f"[{scan_id}] Cleanup successful: Deleted {om.base_dir}")
        logger.info(f"[{scan_id}] Cleanup operations complete.")
    except Exception as e:
        logger.error(f"[{scan_id}] Cleanup operations failed: {e}")

def session_termination(scan_id):
    """Simulates terminating the user session."""
    logger.info(f"[{scan_id}] Terminating session...")
    print(f"[{scan_id}] Simulating session termination: Invalidating user session token.")
    logger.info(f"[{scan_id}] Session termination complete.")

def backup_creation(scan_id, om: OutputManager):
    """Creates a zip archive of the scan results directory."""
    logger.info(f"[{scan_id}] Creating backup...")
    try:
        archive_path = shutil.make_archive(
            base_name=f"{om.base_dir.parent}/{om.base_dir.name}",
            format='zip',
            root_dir=om.base_dir
        )
        print(f"[{scan_id}] Backup created at: {archive_path}")
        logger.info(f"[{scan_id}] Backup creation complete.")
    except Exception as e:
        logger.error(f"[{scan_id}] Backup creation failed: {e}")

def analytics_update(scan_id, om: OutputManager):
    """Simulates sending analytics data to a dashboard."""
    logger.info(f"[{scan_id}] Updating analytics...")

    # In a real implementation, you would extract key metrics from the scan results
    # and send them to an analytics platform (e.g., Elastic, Splunk).
    # For now, we'll just simulate with dummy data.
    metrics = {
        "scan_id": scan_id,
        "total_assets": len(om.vulnerabilities) + 10, # dummy value
        "open_ports": len(om.vulnerabilities), # dummy value
        "vulnerabilities": len(om.vulnerabilities) # dummy value
    }
    print(f"[{scan_id}] Simulating sending analytics data: {metrics}")

    logger.info(f"[{scan_id}] Analytics update complete.")

def schedule_next_scan(scan_id):
    """Schedules a new scan with the same targets as the completed scan."""
    logger.info(f"[{scan_id}] Scheduling next scan...")

    current_scan = db.session.query(Scan).filter_by(id=scan_id).first()
    if not current_scan:
        logger.error(f"[{scan_id}] Could not find current scan to reschedule.")
        return

    # Create a new scan with the same targets
    new_scan = Scan(status='PENDING', user_id=current_scan.user_id)
    for target in current_scan.targets:
        new_scan.targets.append(Target(value=target.value, type=target.type))

    db.session.add(new_scan)
    db.session.commit()

    print(f"[{scan_id}] Simulating scheduling next scan. New scan ID: {new_scan.id}")
    logger.info(f"[{scan_id}] Next scan scheduled.")

def monitoring_activation(scan_id):
    """Simulates activating continuous monitoring for the target."""
    logger.info(f"[{scan_id}] Activating monitoring...")
    print(f"[{scan_id}] Simulating monitoring activation: Setting up continuous monitoring for the target.")
    logger.info(f"[{scan_id}] Monitoring activation complete.")

def platform_logout(scan_id):
    """Simulates logging out of the platform."""
    logger.info(f"[{scan_id}] Logging out of platform...")
    print(f"[{scan_id}] Simulating platform logout: Clearing session data.")
    logger.info(f"[{scan_id}] Platform logout complete.")

def session_closed(scan_id):
    """Simulates closing the user session and releasing resources."""
    logger.info(f"[{scan_id}] Closing session...")
    print(f"[{scan_id}] Simulating session closed: Releasing resources associated with the session.")
    logger.info(f"[{scan_id}] Session closed.")

def run_post_scan_operations(scan_id, app, om: OutputManager):
    """
    Main entry point to run all post-scan operations.
    """
    with app.app_context():
        logger.info(f"[{scan_id}] Starting post-scan operations...")

        notification_dispatch(scan_id, app, om)
        backup_creation(scan_id, om)
        final_validation(scan_id, om)
        data_archival(scan_id, om)
        integration_updates(scan_id)
        analytics_update(scan_id, om)
        schedule_next_scan(scan_id)
        monitoring_activation(scan_id)
        cleanup_operations(scan_id, om)
        session_termination(scan_id)
        platform_logout(scan_id)
        session_closed(scan_id)

        logger.info(f"[{scan_id}] All post-scan operations completed.")
