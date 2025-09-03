import logging
import time
import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, List

log = logging.getLogger(__name__)

class ValidationHandler(ABC):
    """Abstract base class for validation handlers."""
    @abstractmethod
    def validate(self, finding: Dict[str, Any]) -> bool:
        raise NotImplementedError

class TimeBasedSQLiHandler(ValidationHandler):
    """
    Validates time-based SQL injection vulnerabilities by re-testing with a
    safe, time-delay payload.
    """
    def validate(self, finding: Dict[str, Any]) -> bool:
        nuclei_evidence = next((ev for ev in finding.get("raw_evidence", []) if ev.get("template-id")), None)
        if not nuclei_evidence:
            return False
        target_url = nuclei_evidence.get("matched-at")
        if not target_url:
            return False
        delay = 5
        payload = f"' OR SLEEP({delay})--"
        if "?" in target_url:
            validated_url = f"{target_url}{payload}"
        else:
            return False
        try:
            start_time = time.time()
            requests.get(validated_url, timeout=delay + 3, verify=False)
            end_time = time.time()
            if (end_time - start_time) >= delay:
                return True
        except requests.exceptions.Timeout:
            return True
        except requests.exceptions.RequestException:
            return False
        return False

class ValidationEngine:
    """
    The Validation Engine is responsible for safely validating high-impact,
    high-confidence findings and updating them with the validation outcome.
    """
    def __init__(self, findings: List[Dict[str, Any]]):
        self.findings = findings
        self.handlers = {
            "CWE-89": TimeBasedSQLiHandler(),
        }
        self.confidence_threshold = 0.75

    def run(self) -> List[Dict[str, Any]]:
        """
        Iterates through findings, attempts to validate them, and updates
        their status and validation_outcome fields.
        """
        log.info(f"Starting validation process for {len(self.findings)} findings...")
        for finding in self.findings:
            if finding.get('confidence', 0.0) < self.confidence_threshold:
                finding['status'] = 'Validation Skipped (Low Confidence)'
                finding['validation_outcome'] = None
                continue
            handler = self.handlers.get(finding.get("vulnerability_type"))
            if handler:
                is_validated = handler.validate(finding)
                finding['status'] = 'Validated' if is_validated else 'Validation Failed'
                finding['validation_outcome'] = is_validated
            else:
                finding['status'] = 'No Validator'
                finding['validation_outcome'] = None
        log.info("Validation process finished.")
        return self.findings
