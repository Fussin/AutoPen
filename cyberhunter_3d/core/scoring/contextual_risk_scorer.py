import logging
from typing import Dict, Any, List
from ..scoring.risk_scorer import calculate_risk

log = logging.getLogger(__name__)


class ContextualRiskScorer:
    """
    Calculates a contextual risk score for findings using a nuanced algorithm.
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
        log.info("Running nuanced contextual risk scorer...")

        chain_risk_map = self._calculate_chain_risks()

        for finding in self.findings:
            finding_id = finding.get('id')

            base_risk_info = calculate_risk(finding.get('cve_list', []))
            contextual_score = base_risk_info.get('cvss_score', 0.0)

            if finding_id in chain_risk_map:
                contextual_score = chain_risk_map[finding_id]

            if finding.get('is_anomaly'):
                contextual_score *= 0.8

            if finding.get('validation_outcome') is False:
                contextual_score *= 0.5

            finding['contextual_risk_score'] = round(contextual_score, 1)
            finding['base_risk_level'] = base_risk_info.get('risk_level')

        log.info("Contextual risk scoring finished.")
        return self.findings

    def _calculate_chain_risks(self) -> Dict[str, float]:
        """
        Calculates a risk score for each exploit chain.
        The score is the max CVSS in the chain plus a bonus for each additional link.
        Returns a map of finding IDs in chains to their new chain-based risk score.
        """
        finding_risk_map = {}
        for chain in self.exploit_chains:
            if not chain.get('steps'):
                continue

            base_scores = [calculate_risk(step.get('cve_list', [])).get('cvss_score', 0.0) for step in chain['steps']]

            if not any(base_scores):
                # If no steps have a CVSS score, assign a moderate base risk for being in a chain
                max_score = 4.0
            else:
                max_score = max(base_scores)

            bonus = 1.0 * (len(base_scores) - 1)
            chain_score = min(10.0, max_score + bonus)

            for step in chain['steps']:
                step_id = step.get('id')
                if step_id:
                    finding_risk_map[step_id] = chain_score

        return finding_risk_map
