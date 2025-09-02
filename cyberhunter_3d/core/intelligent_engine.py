import logging
from typing import List, Dict, Any

from cyberhunter_3d.core.ml.pattern_analysis import PatternAnalysis
from cyberhunter_3d.core.vulnerability.exploit_chain import ExploitChainDetector
from cyberhunter_3d.core.validation.contextual_validator import ContextualValidator
from cyberhunter_3d.core.scoring.contextual_risk_scorer import ContextualRiskScorer

log = logging.getLogger(__name__)


class IntelligentEngine:
    """
    The Intelligent Processing Engine for AI analysis and correlation.
    """

    def __init__(self, findings: List[Dict[str, Any]]):
        """
        Initializes the IntelligentEngine.
        :param findings: A list of findings to be processed.
        """
        self.findings = findings
        self.exploit_chains = []

    def run(self) -> List[Dict[str, Any]]:
        """
        Runs the full intelligent processing pipeline.
        """
        log.info("Starting Intelligent Processing Engine...")

        # 1. Pattern Analysis
        self._run_pattern_analysis()

        # 2. Exploit Chain Detection
        self._run_exploit_chain_detection()

        # 3. False Positive Reduction
        self._run_false_positive_reduction()

        # 4. Risk Scoring
        self._run_risk_scoring()

        # 5. Vulnerability Prioritization
        self.findings = self._prioritize_vulnerabilities()

        log.info("Intelligent Processing Engine finished.")
        return self.findings

    def _run_pattern_analysis(self):
        """
        Analyzes findings for anomalies and trends.
        """
        log.info("Running Pattern Analysis...")
        pattern_analyzer = PatternAnalysis(self.findings)
        self.findings = pattern_analyzer.run()

    def _run_exploit_chain_detection(self):
        """
        Identifies multi-vulnerability attack paths.
        """
        log.info("Running Exploit Chain Detection...")
        exploit_chain_detector = ExploitChainDetector(self.findings)
        self.exploit_chains = exploit_chain_detector.run()

    def _run_false_positive_reduction(self):
        """
        Reduces false positives using contextual validation.
        """
        log.info("Running False Positive Reduction...")
        contextual_validator = ContextualValidator()
        for finding in self.findings:
            # A more robust implementation would integrate this into the main ValidationEngine
            if not contextual_validator.validate(finding):
                finding['validation_outcome'] = False

    def _run_risk_scoring(self):
        """
        Calculates a contextual risk score for each finding.
        """
        log.info("Running Risk Scoring...")
        risk_scorer = ContextualRiskScorer(self.findings, self.exploit_chains)
        self.findings = risk_scorer.run()

    def _prioritize_vulnerabilities(self) -> List[Dict[str, Any]]:
        """
        Prioritizes vulnerabilities based on their contextual risk scores.
        """
        log.info("Prioritizing vulnerabilities...")
        # The contextual risk scorer has already added the 'contextual_risk_score' key to each finding.
        # Now, we just need to sort the findings based on this score.
        return sorted(self.findings, key=lambda x: x.get('contextual_risk_score', 0), reverse=True)
