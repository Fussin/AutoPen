import logging
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import LabelEncoder
from typing import List, Dict, Any

log = logging.getLogger(__name__)


class PatternAnalysis:
    """
    Analyzes findings for anomalies and trends using an Isolation Forest model.
    """

    def __init__(self, findings: List[Dict[str, Any]]):
        """
        Initializes the PatternAnalysis component.
        :param findings: A list of findings to be processed.
        """
        self.findings = findings
        if self.findings:
            self.findings_df = pd.DataFrame(findings)
        else:
            self.findings_df = pd.DataFrame()

    def run(self) -> List[Dict[str, Any]]:
        """
        Runs the full pattern analysis pipeline.
        """
        log.info("Running advanced pattern analysis...")

        if self.findings_df.empty:
            log.warning("No findings to analyze in PatternAnalysis.")
            return self.findings

        self._detect_anomalies()
        self._analyze_trends()

        log.info("Pattern analysis finished.")
        return self.findings_df.to_dict('records')

    def _detect_anomalies(self):
        """
        Detects anomalous findings using an Isolation Forest model.
        """
        log.info("Detecting anomalies with Isolation Forest...")

        features = self.findings_df.copy()

        # Feature Engineering
        features['port_count'] = features.get('open_ports', pd.Series([[] for _ in range(len(features))])).apply(lambda x: len(x) if isinstance(x, list) else 0)
        features['tech_count'] = features.get('technologies', pd.Series([[] for _ in range(len(features))])).apply(lambda x: len(x) if isinstance(x, list) else 0)

        if 'severity' in features.columns:
            le = LabelEncoder()
            features['severity_encoded'] = le.fit_transform(features['severity'].astype(str))
        else:
            features['severity_encoded'] = 0

        feature_columns = ['port_count', 'tech_count', 'severity_encoded']
        X = features[feature_columns]

        if X.empty:
            self.findings_df['is_anomaly'] = False
            return

        model = IsolationForest(contamination=0.1, random_state=42)
        model.fit(X)

        predictions = model.predict(X)
        self.findings_df['is_anomaly'] = [pred == -1 for pred in predictions]

        log.info(f"Flagged {self.findings_df['is_anomaly'].sum()} findings as anomalous.")

    def _analyze_trends(self):
        """
        Analyzes trends in the findings.
        """
        log.info("Analyzing trends...")
        if 'technologies' in self.findings_df.columns and not self.findings_df['technologies'].empty:
            all_techs = self.findings_df['technologies'].explode()
            if not all_techs.empty:
                tech_counts = all_techs.value_counts()
                top_technologies = tech_counts.nlargest(5).index.tolist()
                log.info(f"Top trending technologies: {top_technologies}")
                self.findings_df['trending_technologies'] = self.findings_df['technologies'].apply(
                    lambda x: [tech for tech in x if tech in top_technologies] if isinstance(x, list) else []
                )
            else:
                self.findings_df['trending_technologies'] = [[] for _ in range(len(self.findings_df))]
        else:
            self.findings_df['trending_technologies'] = [[] for _ in range(len(self.findings_df))]
