import logging
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import LabelEncoder
from typing import List, Dict, Any

log = logging.getLogger(__name__)


class PatternAnalysis:
    """
    Analyzes findings for anomalies and trends using more advanced techniques.
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
        log.info("Running enhanced pattern analysis...")

        if self.findings_df.empty:
            log.warning("No findings to analyze.")
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
        if self.findings_df.empty:
            self.findings_df['is_anomaly'] = False
            return

        # Feature Engineering
        features = self.findings_df.copy()

        # 1. Port count
        features['port_count'] = features['open_ports'].apply(lambda x: len(x) if isinstance(x, list) else 0)

        # 2. Technology count
        features['tech_count'] = features['technologies'].apply(lambda x: len(x) if isinstance(x, list) else 0)

        # 3. Categorical features (e.g., severity)
        # We can label encode severity to treat it as a numerical feature.
        if 'severity' in features.columns:
            le = LabelEncoder()
            features['severity_encoded'] = le.fit_transform(features['severity'].astype(str))
        else:
            features['severity_encoded'] = 0

        # Select features for the model
        feature_columns = ['port_count', 'tech_count', 'severity_encoded']
        X = features[feature_columns]

        # Fit the Isolation Forest model
        # The contamination parameter is an estimate of the proportion of outliers in the data.
        # This should be tuned based on domain knowledge.
        model = IsolationForest(contamination=0.1, random_state=42)
        model.fit(X)

        # Predict anomalies (-1 for anomalies, 1 for inliers)
        predictions = model.predict(X)
        self.findings_df['is_anomaly'] = [pred == -1 for pred in predictions]

        log.info(f"Flagged {self.findings_df['is_anomaly'].sum()} findings as anomalous.")


    def _analyze_trends(self):
        """
        Analyzes trends in the findings.
        (Keeping this simple as it requires historical data for a full implementation)
        """
        log.info("Analyzing trends...")
        if 'technologies' in self.findings_df.columns:
            # Get the top 5 most common technologies
            tech_counts = self.findings_df['technologies'].explode().value_counts()
            top_technologies = tech_counts.nlargest(5).index.tolist()
            log.info(f"Top trending technologies: {top_technologies}")
            self.findings_df['trending_technologies'] = self.findings_df['technologies'].apply(
                lambda x: [tech for tech in x if tech in top_technologies] if isinstance(x, list) else []
            )
        else:
            self.findings_df['trending_technologies'] = [[] for _ in range(len(self.findings_df))]
