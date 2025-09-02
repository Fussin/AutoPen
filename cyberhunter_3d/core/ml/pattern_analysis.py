import logging
import pandas as pd
from typing import List, Dict, Any

log = logging.getLogger(__name__)


class PatternAnalysis:
    """
    Analyzes findings for anomalies and trends.
    """

    def __init__(self, findings: List[Dict[str, Any]]):
        """
        Initializes the PatternAnalysis component.
        :param findings: A list of findings to be processed.
        """
        self.findings = findings
        self.findings_df = pd.DataFrame(findings)

    def run(self) -> List[Dict[str, Any]]:
        """
        Runs the full pattern analysis pipeline.
        """
        log.info("Running pattern analysis...")

        if self.findings_df.empty:
            log.warning("No findings to analyze.")
            return self.findings

        self._detect_anomalies()
        self._analyze_trends()

        log.info("Pattern analysis finished.")
        return self.findings_df.to_dict('records')

    def _detect_anomalies(self):
        """
        Detects anomalous findings based on statistical methods.
        For now, this is a simple placeholder. A real implementation
        would use more sophisticated models (e.g., Isolation Forest).
        """
        log.info("Detecting anomalies...")
        # Example: Flag findings with a very high number of open ports as anomalous
        if 'open_ports' in self.findings_df.columns:
            # Calculate the 95th percentile for the number of open ports
            port_counts = self.findings_df['open_ports'].apply(lambda x: len(x) if isinstance(x, list) else 0)
            anomaly_threshold = port_counts.quantile(0.95)
            # Flag findings above the threshold as anomalous
            self.findings_df['is_anomaly'] = port_counts > anomaly_threshold
        else:
            self.findings_df['is_anomaly'] = False


    def _analyze_trends(self):
        """
        Analyzes trends in the findings.
        This is a placeholder and would require historical data for a
        proper implementation.
        """
        log.info("Analyzing trends...")
        # Example: Identify technologies that are trending in the current scan
        if 'technologies' in self.findings_df.columns:
            # Get the top 5 most common technologies
            tech_counts = self.findings_df['technologies'].explode().value_counts()
            top_technologies = tech_counts.nlargest(5).index.tolist()
            log.info(f"Top trending technologies: {top_technologies}")
            # This information could be used to adjust risk scores or guide further investigation.
            self.findings_df['trending_technologies'] = self.findings_df['technologies'].apply(
                lambda x: [tech for tech in x if tech in top_technologies] if isinstance(x, list) else []
            )
        else:
            self.findings_df['trending_technologies'] = [[] for _ in range(len(self.findings_df))]
