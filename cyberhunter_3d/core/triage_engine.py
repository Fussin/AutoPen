import logging
from urllib.parse import urlparse
from typing import List, Dict, Any
from .plugins.context import ScanContext
from .ml.confidence_model import ConfidenceModel

log = logging.getLogger(__name__)

class TriageEngine:
    """
    The Triage Engine is responsible for normalizing, correlating, and
    de-duplicating findings from various scanners to produce high-quality,
    actionable intelligence ready to be stored in the database.
    """
    def __init__(self, context: ScanContext):
        self.context = context
        self.normalized_findings: List[Dict[str, Any]] = []
        self.triaged_findings: Dict[str, Dict[str, Any]] = {}
        self.confidence_model = ConfidenceModel()

    def run(self) -> List[Dict]:
        """
        The main entry point for the triage process.
        """
        log.info("Starting Triage Engine...")
        # In a real run, this would be populated by the SpecializedScanManager
        raw_results = self.context.get("specialized_scan_results", {})

        self._normalize_results(raw_results)
        self._run_correlation_rules()
        self._deduplicate_and_finalize()
        self._perform_automated_triage()

        log.info(f"Triage complete. Generated {len(self.triaged_findings)} final findings.")
        return list(self.triaged_findings.values())

    def _perform_automated_triage(self):
        """
        Applies a set of rules to automatically triage findings based on
        their severity and confidence score.
        """
        log.info("Performing automated triage...")
        triaged_count = 0
        for key, finding in self.triaged_findings.items():
            is_critical_or_high = finding.get('severity') in ['Critical', 'High']
            is_high_confidence = finding.get('confidence', 0.0) > 0.8

            if is_critical_or_high and is_high_confidence:
                finding['status'] = 'Triaged'
                finding['disposition'] = 'Action Required'
                triaged_count += 1

        log.info(f"Automatically triaged {triaged_count} findings.")

    def _normalize_results(self, raw_results: Dict):
        """
        Converts raw tool outputs into a standardized "NormalizedFinding" format.
        """
        log.info("Normalizing raw results...")
        api_vulns = raw_results.get("api_vulnerabilities", {})
        for host, vulns in api_vulns.items():
            for vuln in vulns:
                template_id = vuln.get('template-id', 'unknown')
                self.normalized_findings.append({
                    "source_tool": "nuclei",
                    "host": host,
                    "finding_signature": f"nuclei:{template_id}",
                    "vulnerability_type": vuln.get('info', {}).get('classification', {}).get('cwe-id', 'unknown'),
                    "severity": vuln.get('info', {}).get('severity', 'Info').capitalize(),
                    "details": vuln,
                    "asset_context": {"target": host, "tech": ["api"]}
                })
        js_secrets = raw_results.get("js_secrets", {})
        for url, secrets in js_secrets.items():
            for secret in secrets:
                detector = secret.get("DetectorName", "generic")
                self.normalized_findings.append({
                    "source_tool": "trufflehog",
                    "host": urlparse(url).hostname,
                    "finding_signature": f"trufflehog:{detector}",
                    "vulnerability_type": "LeakedSecret",
                    "severity": "High",
                    "details": secret,
                    "asset_context": {"leaked_in_url": url, "tech": ["javascript"]}
                })
        log.info(f"Normalized {len(self.normalized_findings)} raw results.")

    def _run_correlation_rules(self):
        """
        Placeholder for future correlation logic.
        """
        pass

    def _deduplicate_and_finalize(self):
        """
        Creates final finding dictionaries for all normalized results,
        and performs deduplication based on the finding signature and host.
        """
        log.info("Deduplicating and finalizing findings...")
        for norm_finding in self.normalized_findings:
            host = norm_finding['host']
            signature = norm_finding['finding_signature']
            finding_key = f"{host}-{signature}"

            if finding_key in self.triaged_findings:
                self.triaged_findings[finding_key]["raw_evidence"].append(norm_finding["details"])
                continue

            if norm_finding["source_tool"] == "nuclei":
                vuln_info = norm_finding["details"].get("info", {})
                title = f"API Vulnerability: {vuln_info.get('name')} on {host}"
                description = vuln_info.get('description', 'No description available.')
            elif norm_finding["source_tool"] == "trufflehog":
                title = f"Potential Secret Leaked in JavaScript on {host}"
                description = f"A potential secret was found. Raw finding: {norm_finding['details'].get('Raw')}"
            else:
                title = f"Ungrouped finding on {host}"
                description = "An unclassified finding was reported."

            finding_dict = {
                "scan_id": self.context.get("scan_id"),
                "target_domain": self.context.get("target_domain"),
                "title": title,
                "severity": norm_finding['severity'],
                "status": "New",
                "description": description,
                "raw_evidence": [norm_finding["details"]],
                "finding_signature": signature,
                "asset_context": norm_finding["asset_context"],
                # These will be populated by later stages
                "confidence": self.confidence_model.predict(norm_finding),
                "validation_outcome": None,
                "disposition": None,
                # These fields are useful for the next stages but not part of the DB model
                "host": host,
                "vulnerability_type": norm_finding["vulnerability_type"],
                "tags": {norm_finding["source_tool"]}
            }
            self.triaged_findings[finding_key] = finding_dict
