import logging
from typing import Dict, Any, List
from ..scoring.risk_scorer import calculate_risk

log = logging.getLogger(__name__)


class ContextualRiskScorer:
    """
    Calculates a contextual risk score for findings.
    """

    def __init__(self, findings: List[Dict[str, Any]], exploit_chains: List[Dict[str, Any]]):
        """
        Initializes the ContextualRiskScorer.
        :param findings: A list of findings to be processed.
        :param exploit_chains: A list of identified exploit chains.
        """
        self.findings = findings
        self.exploit_chains = exploit_chains
        self.finding_map = {f.get('id'): f for f in findings if f.get('id')}

    def run(self):
        """
        Calculates and adds contextual risk scores to all findings.
        """
        log.info("Running contextual risk scorer...")

        for finding in self.findings:
            base_risk_info = calculate_risk(finding.get('cve_list', []))
            base_score = base_risk_info.get('cvss_score', 0.0)

            # Start with the base score
            contextual_score = base_score

            # Adjust score based on exploit chains
            if self._is_in_exploit_chain(finding):
                contextual_score = min(10.0, base_score * 1.5) # Increase score by 50% for being in a chain

            # Adjust score based on pattern analysis
            if finding.get('is_anomaly'):
                contextual_score *= 0.8 # Decrease score by 20% for being an anomaly

            # Adjust score based on validation
            if finding.get('validation_outcome') is False:
                contextual_score *= 0.5 # Halve the score if validation failed

            finding['contextual_risk_score'] = contextual_score
            finding['base_risk_level'] = base_risk_info.get('risk_level')

        log.info("Contextual risk scoring finished.")
        return self.findings

    def _is_in_exploit_chain(self, finding: Dict[str, Any]) -> bool:
        """
        Checks if a finding is part of any identified exploit chain.
        """
        finding_id = finding.get('id')
        if not finding_id:
            return False

        for chain in self.exploit_chains:
            for step in chain.get('steps', []):
                if step.get('id') == finding_id:
                    return True
        return False
