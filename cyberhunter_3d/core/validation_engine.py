import logging
import time
import requests
import re
import boto3
from botocore.exceptions import ClientError
from urllib.parse import urlparse, urljoin
from abc import ABC, abstractmethod
from typing import Dict, Any

log = logging.getLogger(__name__)


class ValidationHandler(ABC):
    """Abstract base class for validation handlers."""

    @abstractmethod
    def validate(self, finding: Dict[str, Any]) -> bool:
        """
        Takes a TriagedFinding (as a dict) and returns True if it's validated,
        False otherwise.
        """
        raise NotImplementedError


class TimeBasedSQLiHandler(ValidationHandler):
    """
    Validates time-based SQL injection vulnerabilities by re-testing with a
    safe, time-delay payload.
    """
    def validate(self, finding: Dict[str, Any]) -> bool:
        # Extract the original request details from Nuclei's raw evidence
        nuclei_evidence = next((ev for ev in finding.get("raw_evidence", []) if ev.get("template-id")), None)
        if not nuclei_evidence:
            log.warning("Could not find Nuclei evidence in SQLi finding.")
            return False

        target_url = nuclei_evidence.get("matched-at")
        if not target_url:
            log.warning("Could not determine target URL from Nuclei evidence.")
            return False

        delay = 5
        # This payload is still generic. A more advanced system might try
        # different payloads based on the database type identified by Nuclei.
        payload = f"' OR SLEEP({delay})--"

        # Replace the original vulnerable parameter's value with the payload
        # This assumes a simple GET parameter. A full implementation would need
        # to handle POST requests, JSON bodies, etc.
        if "?" in target_url:
            base_url, query_string = target_url.split("?", 1)
            params = query_string.split("&")
            # For simplicity, we append. A real implementation would replace the
            # specific vulnerable parameter identified by Nuclei.
            validated_url = f"{target_url}{payload}"
        else:
            # This is a fallback and likely won't work if there's no query string.
            log.warning(f"Cannot inject payload into URL with no query string: {target_url}")
            return False

        log.info(f"Attempting to validate Time-based SQLi at {validated_url}")
        try:
            start_time = time.time()
            # We add a buffer to the timeout to avoid false negatives on slow networks
            requests.get(validated_url, timeout=delay + 3, verify=False)
            end_time = time.time()

            if (end_time - start_time) >= delay:
                log.warning(f"CONFIRMED: Time-based SQLi at {target_url}")
                return True
        except requests.exceptions.Timeout:
            # A timeout is also a strong indicator of success
            log.warning(f"CONFIRMED: Time-based SQLi at {target_url} (request timed out)")
            return True
        except requests.exceptions.RequestException as e:
            log.error(f"Validation request failed for {target_url}: {e}")
            return False
        return False


class AWSKeyValidationHandler(ValidationHandler):
    """
    Validates a leaked AWS key by making a safe 'GetCallerIdentity' call.
    """
    def validate(self, finding: Dict[str, Any]) -> bool:
        trufflehog_evidence = next((ev for ev in finding.get("raw_evidence", []) if ev.get("SourceMetadata")), None)
        if not trufflehog_evidence:
            return False

        # Trufflehog provides the raw secret directly
        api_key = trufflehog_evidence.get("Raw")
        if not api_key:
            return False

        # Basic check for AWS key format
        if not re.match(r"AKIA[0-9A-Z]{16}", api_key):
             return False

        # To validate, we need a secret key. A leaked access key alone is not
        # enough. This highlights a limitation of simple secret scanners.
        # A real implementation would need to find both parts of the key.
        # For this example, we'll assume the key is for a public service or
        # the secret key is found elsewhere. We cannot proceed safely without it.
        log.warning("Found an AWS Access Key, but cannot validate without the Secret Key.")
        return False
        # Example of what a real validation would look like if we had the secret:
        # try:
        #     client = boto3.client(
        #         'sts',
        #         aws_access_key_id=api_key,
        #         aws_secret_access_key=secret_key
        #     )
        #     response = client.get_caller_identity()
        #     if "Arn" in response:
        #         log.warning(f"CONFIRMED: Leaked AWS Key is active for ARN: {response['Arn']}")
        #         return True
        # except ClientError as e:
        #     log.info(f"AWS key validation failed: {e}")
        #     return False


class ValidationEngine:
    """
    The Validation Engine is responsible for safely validating high-impact,
    high-confidence findings to confirm exploitability.
    """
    def __init__(self, findings: list):
        self.findings_to_validate = findings
        self.validated_findings = []
        self.handlers = {
            "CWE-89": TimeBasedSQLiHandler(), # CWE-89 is SQL Injection
            "AWSKey": AWSKeyValidationHandler(),
            # "LeakedKeyForVulnerableApi": ApiKeyValidationHandler(), # Add this later
        }

    def run(self):
        """
        The main entry point for the validation process.
        """
        log.info(f"Starting validation process for {len(self.findings_to_validate)} findings...")

        for finding in self.findings_to_validate:
            # Only try to validate high-confidence findings
            if finding.get('confidence') != 'High':
                finding['status'] = 'Validation Skipped (Low Confidence)'
                continue

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
        return self.findings_to_validate # Return all findings with updated statuses

    def _get_handler(self, finding: dict) -> ValidationHandler:
        """
        Gets the appropriate validation handler for a given finding based on its type.
        """
        vuln_type = finding.get("vulnerability_type")
        return self.handlers.get(vuln_type)
