import logging
from cyberhunter_3d.web.models import db, Scan
from cyberhunter_3d.core.scan_manager import run_discovery_phase, run_execution_phase

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ScanLifecycleManager:
    """
    Orchestrates the full lifecycle of a scan, from input to continuous monitoring.
    """
    def __init__(self, scan_id, app):
        self.scan_id = scan_id
        self.app = app
        self.scan = None

    def run(self):
        """
        Executes the entire scan lifecycle.
        """
        with self.app.app_context():
            self.scan = Scan.query.get(self.scan_id)
            if not self.scan:
                logging.error(f"Scan {self.scan_id} not found.")
                return

            try:
                self._run_stage(self._input_stage)
                self._run_stage(self._validation_stage)
                self._run_stage(self._queue_stage)
                self._run_stage(self._processing_stage)
                self._run_stage(self._scanning_stage)
                self._run_stage(self._analysis_stage)
                self._run_stage(self._correlation_stage)
                self._run_stage(self._reporting_stage)
                self._run_stage(self._integration_stage)
                self._run_stage(self._archival_stage)
                self._run_stage(self._continuous_monitoring_stage)
                self._finalize_scan('COMPLETED')
            except Exception as e:
                logging.error(f"Fatal error in scan lifecycle for scan {self.scan_id}: {e}")
                self._finalize_scan('FAILED', str(e))

    def _run_stage(self, stage_method):
        """
        Helper to run a stage and handle errors.
        """
        stage_name = stage_method.__name__
        logging.info(f"[{self.scan.id}] Starting stage: {stage_name}")
        self.scan.status = f'RUNNING_{stage_name}'
        db.session.commit()

        stage_method()

        logging.info(f"[{self.scan.id}] Completed stage: {stage_name}")
        db.session.commit()

    def _input_stage(self):
        """
        Handles the initial input. In our case, the targets are already in the DB.
        """
        logging.info(f"[{self.scan.id}] Input stage: {len(self.scan.targets)} targets found.")

    def _validation_stage(self):
        """
        Validates the targets in the scan.
        This is currently handled within the discovery phase, but could be a separate step.
        """
        logging.info(f"[{self.scan.id}] Validation stage: Scope rules will be applied during processing.")

    def _queue_stage(self):
        """
        The scan is already 'queued' by being created. This stage marks the start of active processing.
        """
        logging.info(f"[{self.scan.id}] Queue stage: Scan picked up for processing.")
        self.scan.status = 'RUNNING'
        db.session.commit()

    def _processing_stage(self):
        """
        The main processing, which encompasses discovery and execution.
        """
        logging.info(f"[{self.scan.id}] Processing stage: Running discovery phase.")
        run_discovery_phase(self.scan.id, self.app)

        # In a real scenario, we would wait for user review here if the status is PENDING_REVIEW
        # For now, we'll assume auto-approval for the lifecycle
        if self.scan.status == 'PENDING_REVIEW':
            logging.info(f"[{self.scan.id}] Auto-approving assets for execution.")
            for asset in self.scan.assets:
                asset.is_approved_for_scan = True
            db.session.commit()

            logging.info(f"[{self.scan.id}] Processing stage: Running execution phase.")
            run_execution_phase(self.scan.id, self.app)

    def _scanning_stage(self):
        """
        Placeholder for any additional scanning logic.
        """
        logging.info(f"[{self.scan.id}] Scanning stage: Placeholder.")

    def _analysis_stage(self):
        """
        Placeholder for deeper analysis of scan findings.
        """
        logging.info(f"[{self.scan.id}] Analysis stage: Placeholder.")

    def _correlation_stage(self):
        """
        Placeholder for advanced correlation of findings.
        """
        logging.info(f"[{self.scan.id}] Correlation stage: Placeholder.")

    def _reporting_stage(self):
        """
        Generates reports from the scan data.
        """
        logging.info(f"[{self.scan.id}] Reporting stage: Placeholder for report generation.")

    def _integration_stage(self):
        """
        Integrates with external systems (e.g., Jira, Slack).
        """
        logging.info(f"[{self.scan.id}] Integration stage: Placeholder for external integrations.")

    def _archival_stage(self):
        """
        Archives the scan results for long-term storage.
        """
        logging.info(f"[{self.scan.id}] Archival stage: Placeholder for data archival.")

    def _continuous_monitoring_stage(self):
        """
        Sets up continuous monitoring for the targets.
        """
        logging.info(f"[{self.scan.id}] Continuous Monitoring stage: Placeholder.")

    def _finalize_scan(self, status, results=None):
        """
        Sets the final status of the scan.
        """
        logging.info(f"[{self.scan.id}] Finalizing scan with status: {status}")
        self.scan.status = status
        if results:
            self.scan.results = results
        db.session.commit()
