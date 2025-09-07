import logging
import shutil
import requests
from pathlib import Path
from .output_manager import OutputManager
from cyberhunter_3d.web.models import db, Scan, Target

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def final_validation(scan, om: OutputManager):
    """Checks if the backup archive was created successfully."""

    logger.info(f"[{scan.id}] Performing final validation...")
    archive_path = Path("archive") / f"{om.base_dir.name}.zip"

    logger.info(f"[{scan_id}] Performing final validation...")

    archive_path = Path("archive") / f"{om.base_dir.name}.zip"

    archive_path = om.base_dir.parent / f"{om.base_dir.name}.zip"


    if archive_path.exists():
        logger.info(f"Validation successful: Archive found at {archive_path}")
    else:
        logger.error(f"Validation failed: Archive not found at {archive_path}")
    logger.info(f"[{scan.id}] Final validation complete.")

def report_generation(scan, om: OutputManager):
    """Generates the final reports for the scan."""
    logger.info(f"[{scan.id}] Generating reports...")
    summary = om.finalize(scan, generate_pdf=True, generate_docx=True)
    print("Generated reports summary:", summary)

    logger.info(f"[{scan.id}] Report generation complete.")

def notification_dispatch(scan):
    """Simulates sending email notifications to stakeholders."""
    logger.info(f"[{scan.id}] Dispatching notifications...")

    logger.info(f"[{scan_id}] Report generation complete.")

def notification_dispatch(scan_id):
    """Simulates sending email notifications to stakeholders."""
    logger.info(f"[{scan_id}] Dispatching notifications...")


    # In a real implementation, you would fetch these from a database or config
    stakeholders = ["admin@example.com", "security-team@example.com"]

    for email in stakeholders:
        print(f"[{scan_id}] Simulating sending email to {email}...")
        # Here you would use a library like smtplib to send the actual email


    scan = Scan.query.get(scan_id)
    if not scan:
        logger.error(f"[{scan_id}] Could not find scan for notification dispatch.")
        return


    for email in stakeholders:
        print(f"[{scan.id}] Simulating sending email to {email}...")
        # Here you would use a library like smtplib to send the actual email

    user = scan.user
    if user and user.is_email_notifications_enabled and user.email:
        logger.info(f"[{scan_id}] Email notifications enabled for user {user.username}.")

        # Find the PDF report path from the generated reports
        pdf_report_path = None
        for report in reports:
            if report.get("type") == "pdf":
                pdf_report_path = report.get("path")
                break

        if pdf_report_path:
            with app.app_context():
                send_report_email(user.email, scan, pdf_report_path)
        else:
            logger.error(f"[{scan_id}] PDF report was not generated. Cannot send email.")
    else:
        logger.info(f"[{scan_id}] Email notifications are disabled for user {user.username}.")



    logger.info(f"[{scan.id}] Notification dispatch complete.")

def data_archival(scan, om: OutputManager):
    """Moves the backup archive to a long-term storage directory."""
    logger.info(f"[{scan.id}] Archiving data...")
    try:
        archive_dir = Path("archive")
        archive_dir.mkdir(exist_ok=True)

        archive_filename = f"{om.base_dir.name}.zip"
        source_path = om.base_dir.parent / archive_filename

        if not source_path.exists():
            logger.error(f"[{scan.id}] Backup archive not found at {source_path}. Skipping archival.")
            return

        destination_path = archive_dir / archive_filename
        shutil.move(str(source_path), str(destination_path))

        print(f"[{scan.id}] Data archived to: {destination_path}")
        logger.info(f"[{scan.id}] Data archival complete.")
    except Exception as e:
        logger.error(f"[{scan.id}] Data archival failed: {e}")

def integration_updates(scan):
    """Simulates pushing updates to JIRA and Slack."""
    logger.info(f"[{scan.id}] Sending integration updates...")

    # In a real implementation, you would fetch these from a config file
    jira_webhook = "https://example.jira.com/hooks/..."
    slack_webhook = "https://hooks.slack.com/services/..."

    jira_payload = {"text": f"Scan {scan.id} completed. Results are ready for review."}
    try:
        # We don't expect this to succeed as the URL is fake, but it's a more realistic simulation.
        response = requests.post(jira_webhook, json=jira_payload, timeout=5)
        print(f"[{scan.id}] Pushed update to JIRA. Status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"[{scan.id}] Failed to push update to JIRA: {e}")

    slack_payload = {"text": f"Scan {scan.id} completed. Results available at <http://example.com/scans/{scan.id}>"}
    try:
        response = requests.post(slack_webhook, json=slack_payload, timeout=5)
        print(f"[{scan.id}] Pushed update to Slack. Status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"[{scan.id}] Failed to push update to Slack: {e}")

    logger.info(f"[{scan.id}] Integration updates complete.")

def cleanup_operations(scan, om: OutputManager):
    """Deletes the original scan results directory."""
    logger.info(f"[{scan.id}] Performing cleanup operations...")
    try:
        shutil.rmtree(om.base_dir)
        print(f"[{scan.id}] Cleanup successful: Deleted {om.base_dir}")
        logger.info(f"[{scan.id}] Cleanup operations complete.")
    except Exception as e:
        logger.error(f"[{scan.id}] Cleanup operations failed: {e}")

def session_termination(scan):
    """Simulates terminating the user session."""
    logger.info(f"[{scan.id}] Terminating session...")
    print(f"[{scan.id}] Simulating session termination: Invalidating user session token.")
    logger.info(f"[{scan.id}] Session termination complete.")

def backup_creation(scan, om: OutputManager):
    """Creates a zip archive of the scan results directory."""
    logger.info(f"[{scan.id}] Creating backup...")
    try:
        archive_path = shutil.make_archive(
            base_name=f"{om.base_dir.parent}/{om.base_dir.name}",
            format='zip',
            root_dir=om.base_dir
        )
        print(f"[{scan.id}] Backup created at: {archive_path}")
        logger.info(f"[{scan.id}] Backup creation complete.")
    except Exception as e:
        logger.error(f"[{scan.id}] Backup creation failed: {e}")

def analytics_update(scan, om: OutputManager):
    """Simulates sending analytics data to a dashboard."""
    logger.info(f"[{scan.id}] Updating analytics...")

    # In a real implementation, you would extract key metrics from the scan results
    # and send them to an analytics platform (e.g., Elastic, Splunk).
    # For now, we'll just simulate with dummy data.
    metrics = {
        "scan_id": scan.id,
        "total_assets": len(om.vulnerabilities) + 10, # dummy value
        "open_ports": len(om.vulnerabilities), # dummy value
        "vulnerabilities": len(om.vulnerabilities) # dummy value
    }
    print(f"[{scan.id}] Simulating sending analytics data: {metrics}")

    logger.info(f"[{scan.id}] Analytics update complete.")

def schedule_next_scan(scan):
    """Schedules a new scan with the same targets as the completed scan."""
    logger.info(f"[{scan.id}] Scheduling next scan...")

    current_scan = db.session.query(Scan).filter_by(id=scan.id).first()
    if not current_scan:
        logger.error(f"[{scan.id}] Could not find current scan to reschedule.")
        return

    # Create a new scan with the same targets
    new_scan = Scan(status='PENDING', user_id=current_scan.user_id)
    for target in current_scan.targets:
        new_scan.targets.append(Target(value=target.value, type=target.type))

    db.session.add(new_scan)
    db.session.commit()

    print(f"[{scan.id}] Simulating scheduling next scan. New scan ID: {new_scan.id}")
    logger.info(f"[{scan.id}] Next scan scheduled.")

def monitoring_activation(scan):
    """Simulates activating continuous monitoring for the target."""
    logger.info(f"[{scan.id}] Activating monitoring...")
    print(f"[{scan.id}] Simulating monitoring activation: Setting up continuous monitoring for the target.")
    logger.info(f"[{scan.id}] Monitoring activation complete.")

def platform_logout(scan):
    """Simulates logging out of the platform."""
    logger.info(f"[{scan.id}] Logging out of platform...")
    print(f"[{scan.id}] Simulating platform logout: Clearing session data.")
    logger.info(f"[{scan.id}] Platform logout complete.")

def session_closed(scan):
    """Simulates closing the user session and releasing resources."""
    logger.info(f"[{scan.id}] Closing session...")
    print(f"[{scan.id}] Simulating session closed: Releasing resources associated with the session.")
    logger.info(f"[{scan.id}] Session closed.")

def run_post_scan_operations(scan, app, om: OutputManager):
    """
    Main entry point to run all post-scan operations.
    """
    with app.app_context():

        logger.info(f"[{scan.id}] Starting post-scan operations...")

        report_generation(scan, om)
        backup_creation(scan, om)
        final_validation(scan, om)
        data_archival(scan, om)
        notification_dispatch(scan)
        integration_updates(scan)
        analytics_update(scan, om)
        schedule_next_scan(scan)
        monitoring_activation(scan)
        cleanup_operations(scan, om)
        session_termination(scan)
        platform_logout(scan)
        session_closed(scan)

        logger.info(f"[{scan.id}] All post-scan operations completed.")

        logger.info(f"[{scan_id}] Starting post-scan operations...")

        report_generation(scan_id, om)
        backup_creation(scan_id, om)
        final_validation(scan_id, om)
        data_archival(scan_id, om)
        notification_dispatch(scan_id)
        integration_updates(scan_id)
        analytics_update(scan_id, om)
        schedule_next_scan(scan_id)
        monitoring_activation(scan_id)
        cleanup_operations(scan_id, om)
        session_termination(scan_id)
        platform_logout(scan_id)
        session_closed(scan_id)

        logger.info(f"[{scan_id}] All post-scan operations completed.")

