import logging
from typing import Dict, Any, List
from .vulnerability.validation import XSSValidator, SQLiValidator

log = logging.getLogger(__name__)


import time

class ValidationEngine:
    """
    The Validation Engine is responsible for safely validating high-impact,
    high-confidence findings and updating them with the validation outcome.
    """
    def __init__(self, findings: List[Dict[str, Any]], clock=None):
        self.findings = findings
        self.clock = clock or time.time
        self.validators = {
            "CWE-79": XSSValidator,
            "CWE-89": SQLiValidator,
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

            validator_class = self.validators.get(finding.get("vulnerability_type"))
            if validator_class:
                validator = validator_class(finding, clock=self.clock)
                is_validated = validator.validate()
                finding['status'] = 'Validated' if is_validated else 'Validation Failed'
                finding['validation_outcome'] = is_validated
            else:
                finding['status'] = 'No Validator'
                finding['validation_outcome'] = None
        log.info("Validation process finished.")
        return self.findings
