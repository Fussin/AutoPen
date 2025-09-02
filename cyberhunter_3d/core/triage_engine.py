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
                "title": title,
                "severity": norm_finding['severity'],
                "status": "New",
                "description": description,
                "raw_evidence": [norm_finding["details"]],
                "finding_signature": signature,
                "asset_context": norm_finding["asset_context"],
                "confidence": self.confidence_model.predict(norm_finding),
                "validation_outcome": None,
                "disposition": None,
                "host": host,
                "vulnerability_type": norm_finding["vulnerability_type"],
                "tags": {norm_finding["source_tool"]}
            }
            self.triaged_findings[finding_key] = finding_dict

    def _save_findings_to_db(self, findings: List[Dict[str, Any]]):
        """Saves the final, processed findings to the database."""
        log.info(f"Saving {len(findings)} findings to the database...")
        if not self.scan_id:
            log.error("No scan_id in context, cannot save findings to database.")
            return

        for finding_data in findings:
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
            )
            if 'contextual_risk_score' in finding_data:
                if new_finding.asset_context is None:
                    new_finding.asset_context = {}
                new_finding.asset_context['contextual_risk_score'] = finding_data['contextual_risk_score']

            db.session.add(new_finding)

        try:
            db.session.commit()
            log.info("Successfully committed findings to the database.")
        except Exception as e:
            log.error(f"Failed to commit findings to database: {e}")
            db.session.rollback()
