import os
import shutil
import logging
from cyberhunter_3d.web.models import db, Scan
from cyberhunter_3d.reporting.r2_uploader import upload_to_r2
from cyberhunter_3d.reporting import aggregator
from cyberhunter_3d.utils.file_utils import get_results_dir

log = logging.getLogger(__name__)

class SessionCloser:
    def __init__(self, scan_id, app, domain, output_paths=None, should_upload_to_r2=False, keep_temp_files=False):
        self.scan_id = scan_id
        self.app = app
        self.domain = domain
        self.output_paths = output_paths if output_paths is not None else {}
        self.should_upload_to_r2 = should_upload_to_r2
        self.keep_temp_files = keep_temp_files
        self.results_dir = get_results_dir(self.domain, self.scan_id)

    def finalize_session(self):
        with self.app.app_context():
            scan = Scan.query.get(self.scan_id)
            if not scan:
                log.error(f"Scan {self.scan_id} not found for session closure.")
                return

            log.info(f"--- Starting Session Closure for Scan ID: {self.scan_id} ---")

            self.generate_scan_summary(scan)
            self.sync_with_cloud_backup()
            self.update_scan_history(scan, "COMPLETED")
            self.generate_audit_logs()
            self.send_completion_notifications()
            self.schedule_next_scan()

            if not self.keep_temp_files:
                self.clean_temporary_files()
            else:
                log.info("Skipping temporary file cleanup as requested.")

            log.info(f"--- Session Closure for Scan ID: {self.scan_id} Finished ---")

    def generate_scan_summary(self, scan):
        log.info("Generating scan summary...")
        try:
            aggregator.aggregate_results(self.output_paths, self.domain, log, self.results_dir, self.scan_id)
            scan.results = f"Scan summary generated. See aggregated results in {self.results_dir}."
            db.session.commit()
            log.info("Scan summary generated successfully.")
        except Exception as e:
            log.error(f"Error generating scan summary: {e}")

    def sync_with_cloud_backup(self):
        if not self.should_upload_to_r2:
            log.info("Skipping cloud backup (R2 upload) as it was not requested.")
            return
        log.info("Syncing with cloud backup...")
        try:
            # This assumes the final aggregated file is ready.
            from cyberhunter_3d.core.reconnaissance.utils import load_config
            config = load_config()
            final_file_path = os.path.join(config['recon_output_dir'], config['final_recon_file'])
            if os.path.exists(final_file_path):
                upload_to_r2(log, file_path=final_file_path)
                log.info("Cloud backup sync successful.")
            else:
                log.warning(f"Could not find final aggregated file at {final_file_path} for upload.")
        except Exception as e:
            log.error(f"Error syncing with cloud backup: {e}")

    def update_scan_history(self, scan, status):
        log.info(f"Updating scan history with status: {status}...")
        try:
            scan.status = status
            db.session.commit()
            log.info("Scan history updated successfully.")
        except Exception as e:
            log.error(f"Error updating scan history: {e}")

    def generate_audit_logs(self):
        log.info("Generating audit logs...")
        # In a real system, this would write to a dedicated audit log file or service.
        # For now, we'll just log to the main application log.
        log.info(f"[AUDIT] Session for scan {self.scan_id} for domain {self.domain} was closed successfully.")

    def send_completion_notifications(self):
        log.info("Sending completion notifications...")
        # Placeholder for sending notifications (e.g., email, Slack).
        log.info("Notification system not implemented. Skipping.")

    def schedule_next_scan(self):
        log.info("Checking for scheduled next scan...")
        # Placeholder for scheduling logic.
        log.info("Scan scheduling not implemented. Skipping.")

    def clean_temporary_files(self):
        log.info(f"Cleaning temporary files from {self.results_dir}...")
        try:
            shutil.rmtree(self.results_dir)
            log.info("Temporary files cleaned up successfully.")
        except Exception as e:
            log.error(f"Error cleaning up temporary files: {e}")
