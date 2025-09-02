import logging
from typing import Dict, Any, List

from ..scoring.risk_scorer import calculate_risk

log = logging.getLogger(__name__)


class ContextualRiskScorer:
    """
    Calculates a contextual risk score for findings using a more nuanced algorithm.
    """

    def __init__(self, findings: List[Dict[str, Any]], exploit_chains: List[Dict[str, Any]]):
        """
        Initializes the ContextualRiskScorer.
        :param findings: A list of findings to be processed.
        :param exploit_chains: A list of identified exploit chains.
        """
        self.findings = findings
        self.exploit_chains = exploit_chains

    def run(self) -> List[Dict[str, Any]]:
        """
        Calculates and adds contextual risk scores to all findings.
        """
        log.info("Running refined contextual risk scorer...")

        # First, calculate a chain score for each exploit chain
        chain_risk_map = self._calculate_chain_risks()

        for finding in self.findings:
            finding_id = finding.get('id')

            # Start with the base CVSS score
            base_risk_info = calculate_risk(finding.get('cve_list', []))
            contextual_score = base_risk_info.get('cvss_score', 0.0)

            # If the finding is part of a chain, its risk is elevated to the chain's risk
            if finding_id in chain_risk_map:
                contextual_score = chain_risk_map[finding_id]

            # Apply other contextual adjustments
            if finding.get('is_anomaly'):
                contextual_score *= 0.8  # Decrease score by 20% for being an anomaly

            if finding.get('validation_outcome') is False:
                contextual_score *= 0.5  # Halve the score if validation failed

            finding['contextual_risk_score'] = round(contextual_score, 1)
            finding['base_risk_level'] = base_risk_info.get('risk_level')

        log.info("Contextual risk scoring finished.")
        return self.findings

    def _calculate_chain_risks(self) -> Dict[str, float]:
        """
        Calculates a risk score for each identified exploit chain and returns a
        map of finding IDs in those chains to their new chain-based risk score.
        """
        finding_risk_map = {}
        for chain in self.exploit_chains:
            base_scores = []
            for step in chain.get('steps', []):
                risk_info = calculate_risk(step.get('cve_list', []))
                base_scores.append(risk_info.get('cvss_score', 0.0))

            if not base_scores:
                continue

            # Calculate chain score: max score in chain + bonus for each additional link
            max_score = max(base_scores)
            bonus = 1.0 * (len(base_scores) - 1)
            chain_score = min(10.0, max_score + bonus)

            # All findings in the chain now have this elevated risk score
            for step in chain.get('steps', []):
                step_id = step.get('id')
                if step_id:
                    finding_risk_map[step_id] = chain_score

        return finding_risk_map
