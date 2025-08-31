import logging
from urllib.parse import urlparse
from typing import List, Dict, Set, Any
from .plugins.context import ScanContext

log = logging.getLogger(__name__)


class TriagedFinding:
    """
    A class to represent a triaged finding, which may be a correlation of
    multiple raw findings. It provides a standardized structure for findings
    that the Validation and Response engines will use.
    """

    def __init__(self, finding_id: str, title: str, severity: str, description: str,
                 confidence: str, host: str, vulnerability_type: str,
                 raw_evidence: List[Dict[str, Any]], tags: Set[str] = None):
        self.id = finding_id
        self.title = title
        self.severity = severity
        self.description = description
        self.confidence = confidence
        self.host = host  # The primary affected host/domain
        self.vulnerability_type = vulnerability_type # e.g., "SQLI", "LeakedKey", "RCE"
        self.raw_evidence = raw_evidence # List of raw tool outputs
        self.tags = tags or set()

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "severity": self.severity,
            "description": self.description,
            "confidence": self.confidence,
            "host": self.host,
            "vulnerability_type": self.vulnerability_type,
            "raw_evidence": self.raw_evidence,
            "tags": list(self.tags)
        }


class TriageEngine:
    """
    The Triage Engine is responsible for normalizing, correlating, and
    de-duplicating findings from various scanners to produce high-quality,
    actionable intelligence.
    """
    CONFIDENCE_MAP = {
        # High confidence sources
        "trufflehog": "High",
        "wpscan": "High",
        "retire.js": "High",
        "blobhunter": "High",
        "s3scanner": "High",
        # Medium confidence sources (template-based or require interpretation)
        "nuclei": "Medium",
        # Default for unknown sources
        "default": "Low"
    }

    def __init__(self, context: ScanContext):
        self.context = context
        self.normalized_findings = []
        self.triaged_findings: Dict[str, TriagedFinding] = {}

    def run(self) -> List[Dict]:
        """
        The main entry point for the triage process.
        """
        log.info("Starting automated triage process...")
        raw_results = self.context.get("specialized_scan_results", {})

        # 1. Normalize all raw results into a common format
        self._normalize_results(raw_results)

        # 2. Run correlation rules
        self._run_correlation_rules()

        # 3. Deduplicate and finalize
        self._deduplicate_and_finalize()

        log.info(f"Triage complete. Generated {len(self.triaged_findings)} final findings.")
        return [finding.to_dict() for finding in self.triaged_findings.values()]

    def _normalize_results(self, raw_results: Dict):
        """
        Converts raw tool outputs into a standardized "NormalizedFinding" format.
        This is a placeholder for what would be a series of parsers for each tool.
        For now, we'll do a simplified normalization.
        """
        log.info("Normalizing raw results...")
        # Example for Nuclei
        api_vulns = raw_results.get("api_vulnerabilities", {})
        for host, vulns in api_vulns.items():
            for vuln in vulns:
                self.normalized_findings.append({
                    "source": "nuclei",
                    "host": host,
                    "type": vuln.get('info', {}).get('classification', {}).get('cwe-id', 'unknown'),
                    "details": vuln,
                    "confidence": self.CONFIDENCE_MAP.get("nuclei")
                })
        # Example for Trufflehog
        js_secrets = raw_results.get("js_secrets", {})
        for url, secrets in js_secrets.items():
            for secret in secrets:
                self.normalized_findings.append({
                    "source": "trufflehog",
                    "host": urlparse(url).hostname,
                    "type": "LeakedSecret",
                    "details": secret,
                    "confidence": self.CONFIDENCE_MAP.get("trufflehog")
                })
        log.info(f"Normalized {len(self.normalized_findings)} raw results.")


    def _run_correlation_rules(self):
        """
        Iterates through correlation rules to create initial TriagedFindings.
        """
        log.info("Running correlation rules...")
        self._correlate_leaked_key_with_vulnerable_api()
        # Future correlation rules would be called here
        # self._correlate_vulnerable_software_with_exploit()

    def _correlate_leaked_key_with_vulnerable_api(self):
        """
        Correlation Rule: Finds leaked API keys that correspond to a host
        that also has API vulnerabilities.
        """
        leaked_secrets = [f for f in self.normalized_findings if f["source"] == "trufflehog"]
        api_vulns = [f for f in self.normalized_findings if f["source"] == "nuclei"]

        for secret_finding in leaked_secrets:
            secret_host = secret_finding["host"]
            # Simple heuristic to see if it's a key
            raw_secret = secret_finding["details"].get("Raw", "")
            if "key" not in raw_secret.lower() and "token" not in raw_secret.lower():
                continue

            # Check for any API vuln on the same host
            for vuln_finding in api_vulns:
                if vuln_finding["host"] == secret_host:
                    finding_id = f"correlated-leaked-key-{secret_host}"
                    title = f"Critical Risk: Leaked API Key for Vulnerable API on {secret_host}"
                    description = (
                        f"An API key was discovered in a JavaScript file on {secret_host}. "
                        f"This same host also has potential API vulnerabilities, such as "
                        f"'{vuln_finding['details'].get('info', {}).get('name')}'. "
                        "This combination could allow an attacker to perform authenticated, "
                        "malicious actions against the API."
                    )
                    finding = TriagedFinding(
                        finding_id=finding_id,
                        title=title,
                        severity="Critical",
                        description=description,
                        confidence="High",
                        host=secret_host,
                        vulnerability_type="LeakedKeyForVulnerableApi",
                        raw_evidence=[secret_finding["details"], vuln_finding["details"]],
                        tags={"LeakedKey", "VulnerableAPI", "Correlation"}
                    )
                    # If a finding with this ID already exists, append evidence
                    if finding_id in self.triaged_findings:
                        self.triaged_findings[finding_id].raw_evidence.extend(finding.raw_evidence)
                    else:
                        self.triaged_findings[finding_id] = finding
                    log.warning(f"CRITICAL FINDING: {title}")


    def _deduplicate_and_finalize(self):
        """
        Creates TriagedFindings for individual normalized results that were not
        part of a correlation, and performs deduplication.
        """
        log.info("Creating findings for non-correlated items and deduplicating...")
        for norm_finding in self.normalized_findings:
            # Simple check to see if the evidence is already in a correlated finding
            is_used = any(
                norm_finding["details"] in f.raw_evidence
                for f in self.triaged_findings.values()
            )
            if is_used:
                continue

            # Create a simple, unique-enough ID for deduplication
            host = norm_finding['host']
            vuln_type = norm_finding['type']
            finding_id = f"individual-{host}-{vuln_type}"

            # If we have a similar finding already, just add the evidence and continue
            if finding_id in self.triaged_findings:
                self.triaged_findings[finding_id].raw_evidence.append(norm_finding["details"])
                continue

            # Create a new individual finding
            if norm_finding["source"] == "nuclei":
                vuln_info = norm_finding["details"].get("info", {})
                title = f"API Vulnerability: {vuln_info.get('name')} on {host}"
                severity = vuln_info.get('severity', 'Info').capitalize()
                description = vuln_info.get('description', 'No description available.')
            elif norm_finding["source"] == "trufflehog":
                title = f"Potential Secret Leaked in JavaScript on {host}"
                severity = "High"
                description = f"A potential secret was found. Raw finding: {norm_finding['details'].get('Raw')}"
            else:
                title = f"Ungrouped finding on {host}"
                severity = "Medium"
                description = "An unclassified finding was reported."

            finding = TriagedFinding(
                finding_id=finding_id,
                title=title,
                severity=severity,
                description=description,
                confidence=norm_finding["confidence"],
                host=host,
                vulnerability_type=vuln_type,
                raw_evidence=[norm_finding["details"]],
                tags={norm_finding["source"]}
            )
            self.triaged_findings[finding_id] = finding
