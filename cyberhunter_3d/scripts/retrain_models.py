import logging
import os
import sys
import pandas as pd

# Add the project root to the Python path to allow for module imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from run_web import create_app
from cyberhunter_3d.web.models import Finding
from cyberhunter_3d.core.ml.confidence_model import ConfidenceModel

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def retrain_confidence_model():
    """
    Retrains the ConfidenceModel based on user feedback stored in the database.
    """
    app = create_app()
    with app.app_context():
        log.info("--- Starting ConfidenceModel Retraining Pipeline ---")

        # 1. Load labeled data from the database
        log.info("Loading labeled findings from the database...")
        labeled_findings = Finding.query.filter(Finding.validation_outcome.isnot(None)).all()

        if len(labeled_findings) < 10:
            log.warning(f"Not enough labeled findings ({len(labeled_findings)}) to train a new model. Need at least 10. Exiting.")
            return

        log.info(f"Found {len(labeled_findings)} labeled findings for retraining.")

        # 2. Convert findings to the format expected by the model's train method
        training_data = []
        for f in labeled_findings:
            # Reconstruct the finding dictionary that the model expects
            finding_dict = {
                'finding_signature': f.finding_signature,
                'asset_context': f.asset_context or {},
                'validation_outcome': f.validation_outcome,
                'severity': f.severity,
            }
            # The model expects the source tool to be in the asset context
            if 'source_tool' not in finding_dict['asset_context']:
                # Attempt to infer from signature if not present
                if ':' in f.finding_signature:
                    finding_dict['asset_context']['source_tool'] = f.finding_signature.split(':')[0]
                else:
                    finding_dict['asset_context']['source_tool'] = 'unknown'

            training_data.append(finding_dict)

        # 3. Retrain the ConfidenceModel
        log.info("Retraining ConfidenceModel...")
        confidence_model = ConfidenceModel() # This will load the existing model path
        confidence_model.train(training_data)
        log.info("ConfidenceModel retraining complete. Model file has been updated.")

        log.info("--- Model Retraining Pipeline Finished Successfully ---")

def retrain_pattern_analysis_model():
    """
    Placeholder for retraining the PatternAnalysis model.
    Retraining an unsupervised model like IsolationForest is more complex.
    It might involve using the labels to tune hyperparameters (like the contamination factor)
    or to evaluate different anomaly detection strategies. This is a future enhancement.
    """
    log.info("--- Retraining for PatternAnalysis model is a future enhancement. Skipping. ---")
    pass

if __name__ == '__main__':
    retrain_confidence_model()
    retrain_pattern_analysis_model()
