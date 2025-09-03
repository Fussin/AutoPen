import logging
from typing import List, Dict, Any
from .ml.pattern_analysis import PatternAnalysis
from .vulnerability.exploit_chain import ExploitChainDetector
from .validation.contextual_validator import ContextualValidator
from .scoring.contextual_risk_scorer import ContextualRiskScorer

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
        log.info("Starting Intelligent Processing Engine pipeline...")

        self._run_pattern_analysis()
        self._run_exploit_chain_detection()
        self._run_false_positive_reduction()
        self._run_risk_scoring()
        self.findings = self._prioritize_vulnerabilities()

        log.info("Intelligent Processing Engine pipeline finished.")
        return self.findings

    def _run_pattern_analysis(self):
        """
        Runs the PatternAnalysis module to add anomaly and trend data.
        """
        log.info("Running Pattern Analysis module...")
        if not self.findings: return
        analyzer = PatternAnalysis(self.findings)
        self.findings = analyzer.run()

    def _run_exploit_chain_detection(self):
        """
        Runs the ExploitChainDetector to find multi-step attack paths.
        """
        log.info("Running Exploit Chain Detection module...")
        if not self.findings: return
        detector = ExploitChainDetector(self.findings)
        self.exploit_chains = detector.run()

    def _run_false_positive_reduction(self):
        """
        Runs the ContextualValidator to flag likely false positives.
        """
        log.info("Running False Positive Reduction module...")
        if not self.findings: return
        validator = ContextualValidator()
        for finding in self.findings:
            if not validator.validate(finding):
                finding['validation_outcome'] = False

    def _run_risk_scoring(self):
        """
        Runs the ContextualRiskScorer to calculate a nuanced risk score.
        """
        log.info("Running Risk Scoring module...")
        if not self.findings: return
        scorer = ContextualRiskScorer(self.findings, self.exploit_chains)
        self.findings = scorer.run()

    def _prioritize_vulnerabilities(self) -> List[Dict[str, Any]]:
        """
        Prioritizes vulnerabilities based on their contextual risk score.
        """
        log.info("Prioritizing vulnerabilities...")
        return sorted(self.findings, key=lambda x: x.get('contextual_risk_score', 0.0), reverse=True)
