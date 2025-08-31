import logging
import time
import requests
import re
from urllib.parse import urlparse
from abc import ABC, abstractmethod

log = logging.getLogger(__name__)

class ValidationHandler(ABC):
    """Abstract base class for validation handlers."""
    @abstractmethod
    def validate(self, finding: dict) -> bool:
        raise NotImplementedError

class TimeBasedSQLiHandler(ValidationHandler):
    """
    Validates time-based SQL injection vulnerabilities.
    """
    def validate(self, finding: dict) -> bool:
        # This is a simplified example. A real implementation would need to
        # parse the finding details to get the vulnerable URL and parameter.
        target_url = finding.get("supporting_evidence", [{}])[0].get("host")
        if not target_url:
            return False

        delay = 5
        payload = f"' OR SLEEP({delay})--"

        try:
            start_time = time.time()
            requests.get(f"{target_url}?param={payload}", timeout=delay + 2)
            end_time = time.time()

            if (end_time - start_time) >= delay:
                log.info(f"Time-based SQLi confirmed for {target_url}")
                return True
        except requests.exceptions.RequestException:
            return False
        return False

class ApiKeyValidationHandler(ValidationHandler):
    """
    Validates a leaked API key by making a simple read-only request.
    """
    def validate(self, finding: dict) -> bool:
        evidence = finding.get("supporting_evidence", [{}])[0]
        leaked_key_finding = evidence.get("leaked_key_finding", {})
        raw_secret = leaked_key_finding.get("Raw")

        if not raw_secret:
            return False

        # Extract the key value. This is a simple regex, a real one would be more complex.
        match = re.search(r"['\"](.*?)['\"]", raw_secret)
        if not match:
            return False
        api_key = match.group(1)

        # Get the host from the original JS file URL
        js_url = leaked_key_finding.get("Source") # Assuming Source holds the URL
        if not js_url:
            return False
        host = urlparse(js_url).hostname

        # Try a common read-only endpoint
        test_endpoints = ["/api/v1/user", "/api/me", "/v1/users/me"]
        for endpoint in test_endpoints:
            url = f"https://{host}{endpoint}"
            headers = {"Authorization": f"Bearer {api_key}"}
            try:
                response = requests.get(url, headers=headers, timeout=5)
                # 200 OK or 403 Forbidden (if we hit a real but unauthorized endpoint) can indicate a valid key
                if response.status_code in [200, 403]:
                    log.info(f"API key validation successful for {host}")
                    return True
            except requests.exceptions.RequestException:
                continue
        return False

class ValidationEngine:
    """
    The Validation Engine is responsible for safely validating high-impact,
    high-confidence findings to confirm exploitability.
    """
    def __init__(self, findings: list):
        self.findings_to_validate = findings
        self.validated_findings = []
        self.handlers = {
            "SQL Injection": TimeBasedSQLiHandler(),
            "Leaked API Key": ApiKeyValidationHandler()
        }

    def run(self):
        """
        The main entry point for the validation process.
        """
        log.info(f"Starting validation process for {len(self.findings_to_validate)} findings...")

        for finding in self.findings_to_validate:
            handler = self._get_handler(finding)
            if handler:
                is_validated = handler.validate(finding)
                if is_validated:
                    finding['status'] = 'Validated'
                    self.validated_findings.append(finding)
                else:
                    finding['status'] = 'Validation Failed'
            else:
                finding['status'] = 'No Validator'

        log.info(f"Validation process finished. Confirmed {len(self.validated_findings)} findings.")
        return self.validated_findings

    def _get_handler(self, finding: dict) -> ValidationHandler:
        """
        Gets the appropriate validation handler for a given finding.
        """
        # A simple dispatch based on the finding title. A more robust
        # implementation would use finding types or tags.
        finding_title = finding.get("title", "")
        for key, handler in self.handlers.items():
            if key in finding_title:
                return handler
        return None
