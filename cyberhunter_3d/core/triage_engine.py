import logging
from urllib.parse import urlparse
from .plugins.context import ScanContext

log = logging.getLogger(__name__)

class TriagedFinding:
    """
    A class to represent a triaged finding, which may be a correlation of
    multiple raw findings.
    """
    def __init__(self, title: str, severity: str, description: str, confidence: str, supporting_evidence: list):
        self.title = title
        self.severity = severity
        self.description = description
        self.confidence = confidence
        self.supporting_evidence = supporting_evidence

    def to_dict(self):
        return {
            "title": self.title,
            "severity": self.severity,
            "description": self.description,
            "confidence": self.confidence,
            "supporting_evidence": self.supporting_evidence
        }

class TriageEngine:
    """
    The Triage Engine is responsible for correlating findings, assessing risk,
    and reducing false positives.
    """
    CONFIDENCE_MAP = {
        "trufflehog": "High",   # Secret scanners are generally high confidence
        "nuclei": "Medium",     # Template-based, so medium confidence
        "wpscan": "High",       # Very specific and reliable
        "retire.js": "High",    # Version matching is reliable
        "blobhunter": "High",   # Finding a public blob is high confidence
        "s3scanner": "High",    # Finding a public bucket is high confidence
        "default": "Medium"
    }

    def __init__(self, context: ScanContext):
        self.context = context
        self.raw_results = {}
        self.triaged_findings = []
        self.used_raw_findings = set() # Keep track of raw findings used in correlations

    def run(self):
        """
        The main entry point for the triage process.
        """
        log.info("Starting automated triage process...")
        self._gather_raw_results()
        self._correlate_findings()
        self._triage_individual_findings()

        log.info(f"Triage complete. Generated {len(self.triaged_findings)} triaged findings.")
        return [finding.to_dict() for finding in self.triaged_findings]

    def _gather_raw_results(self):
        """
        Gathers all the raw results from the ScanContext into a single place.
        """
        self.raw_results = self.context.get("specialized_scan_results", {})

    def _correlate_findings(self):
        """
        Correlates findings from different scanners to identify high-impact risks.
        """
        log.info("Correlating findings...")
        js_secrets = self.raw_results.get("js_secrets", {})
        api_vulns = self.raw_results.get("api_vulnerabilities", {})

        if not js_secrets or not api_vulns:
            log.info("Not enough data to correlate JS secrets and API vulnerabilities.")
            return

        # Example Correlation: Leaked API Key for a Vulnerable API
        for url, secrets in js_secrets.items():
            host = urlparse(url).hostname
            if not host:
                continue

            for secret in secrets:
                # A simple heuristic to identify potential API keys
                if "key" in secret.get("Raw", "").lower() or "token" in secret.get("Raw", "").lower():
                    # Check if this host has any API vulnerabilities
                    if host in api_vulns and api_vulns[host]:
                        title = "Critical Risk: Leaked API Key for Vulnerable API"
                        description = (
                            f"An API key was discovered in a JavaScript file ({url}) hosted on {host}. "
                            f"This same host also has {len(api_vulns[host])} potential API vulnerabilities. "
                            "This combination could allow an attacker to perform authenticated, malicious actions against the API."
                        )
                        evidence = {
                            "leaked_key_finding": secret,
                            "api_vulnerability_findings": api_vulns[host]
                        }
                        finding = TriagedFinding(
                            title=title,
                            severity="Critical",
                            description=description,
                            confidence="High",
                            supporting_evidence=[evidence]
                        )
                        self.triaged_findings.append(finding)
                        # Mark the raw findings as used
                        self.used_raw_findings.add(f"secret_{secret.get('Raw')}")
                        for vuln in api_vulns[host]:
                            self.used_raw_findings.add(f"api_vuln_{vuln.get('template-id')}_{vuln.get('host')}")
                        log.warning(f"CRITICAL FINDING: {title} on host {host}")

    def _triage_individual_findings(self):
        """
        Creates triaged findings for individual raw results that were not part
        of a correlation.
        """
        log.info("Triaging individual findings...")
        for key, results in self.raw_results.items():
            if key == "js_secrets":
                for url, secrets in results.items():
                    for secret in secrets:
                        finding_id = f"secret_{secret.get('Raw')}"
                        if finding_id not in self.used_raw_findings:
                            finding = TriagedFinding(
                                title=f"Potential Secret Leaked in JavaScript on {urlparse(url).hostname}",
                                severity="High",
                                description=f"A potential secret was found in {url}. Raw finding: {secret.get('Raw')}",
                                confidence=self.CONFIDENCE_MAP.get("trufflehog", "Medium"),
                                supporting_evidence=[secret]
                            )
                            self.triaged_findings.append(finding)

            elif key == "api_vulnerabilities":
                for host, vulns in results.items():
                    for vuln in vulns:
                        finding_id = f"api_vuln_{vuln.get('template-id')}_{vuln.get('host')}"
                        if finding_id not in self.used_raw_findings:
                            finding = TriagedFinding(
                                title=f"API Vulnerability: {vuln.get('info', {}).get('name')} on {host}",
                                severity=vuln.get('info', {}).get('severity', 'Info').capitalize(),
                                description=vuln.get('info', {}).get('description', 'No description available.'),
                                confidence=self.CONFIDENCE_MAP.get("nuclei", "Medium"),
                                supporting_evidence=[vuln]
                            )
                            self.triaged_findings.append(finding)
