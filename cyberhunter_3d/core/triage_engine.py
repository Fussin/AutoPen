import logging
from urllib.parse import urlparse
from typing import List, Dict, Any
from .plugins.context import ScanContext
from .ml.confidence_model import ConfidenceModel
from .intelligent_engine import IntelligentEngine
from ..web.models import db, Finding

log = logging.getLogger(__name__)

class TriageEngine:
    """
    The Triage Engine is responsible for normalizing, correlating, and
    de-duplicating findings from various scanners, running them through
    the intelligent processing engine, and saving them to the database.
    """
    def __init__(self, context: ScanContext):
        self.context = context
        self.scan_id = context.get("scan_id")
        self.normalized_findings: List[Dict[str, Any]] = []
        self.triaged_findings: Dict[str, Dict[str, Any]] = {}
        self.confidence_model = ConfidenceModel()

    def run(self) -> List[Dict]:
        """
        The main entry point for the triage process.
        """
        log.info("Starting Triage Engine...")
        raw_results = self.context.get("specialized_scan_results", {})

        self._normalize_results(raw_results)
        self._deduplicate_and_finalize()

        final_findings = list(self.triaged_findings.values())

        # Run the Intelligent Processing Engine
        log.info("Running Intelligent Processing Engine...")
        intelligent_engine = IntelligentEngine(final_findings)
        processed_findings = intelligent_engine.run()

        # Save findings to the database
        self._save_findings_to_db(processed_findings)

        log.info(f"Triage complete. Saved {len(processed_findings)} findings to the database.")
        return processed_findings

    def _normalize_results(self, raw_results: Dict):
        # (Same as before)
        pass

    def _deduplicate_and_finalize(self):
        # (Same as before)
        pass

    def _save_findings_to_db(self, findings: List[Dict[str, Any]]):
        """Saves the final, processed findings to the database."""
        log.info(f"Saving {len(findings)} findings to the database...")
        if not self.scan_id:
            log.error("No scan_id in context, cannot save findings to database.")
            return

        for finding_data in findings:
            # The DB model might not have all the keys from our dict, so we need to be careful.
            new_finding = Finding(
                scan_id=self.scan_id,
                title=finding_data.get('title'),
                severity=finding_data.get('severity'),
                confidence=finding_data.get('confidence'),
                status=finding_data.get('status', 'New'),
                description=finding_data.get('description'),
                raw_evidence=finding_data.get('raw_evidence'),
                finding_signature=finding_data.get('finding_signature'),
                asset_context=finding_data.get('asset_context'),
                validation_outcome=finding_data.get('validation_outcome'),
                disposition=finding_data.get('disposition'),
                # We can store the contextual score in the details or a new field
                # For now, let's add it to the asset_context
            )
            if 'contextual_risk_score' in finding_data:
                new_finding.asset_context['contextual_risk_score'] = finding_data['contextual_risk_score']

            db.session.add(new_finding)

        try:
            db.session.commit()
            log.info("Successfully committed findings to the database.")
        except Exception as e:
            log.error(f"Failed to commit findings to database: {e}")
            db.session.rollback()
