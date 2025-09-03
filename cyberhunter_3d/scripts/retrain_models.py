import logging
import os
import sys
import pandas as pd

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

        log.info("Loading labeled findings from the database...")
        labeled_findings = Finding.query.filter(Finding.validation_outcome.isnot(None)).all()

        if len(labeled_findings) < 10:
            log.warning(f"Not enough labeled findings ({len(labeled_findings)}) to train a new model. Need at least 10. Exiting.")
            return

        log.info(f"Found {len(labeled_findings)} labeled findings for retraining.")

        training_data = []
        for f in labeled_findings:
            finding_dict = {
                'finding_signature': f.finding_signature,
                'asset_context': f.asset_context or {},
                'validation_outcome': f.validation_outcome,
                'severity': f.severity,
            }
            if 'source_tool' not in finding_dict['asset_context']:
                if ':' in f.finding_signature:
                    finding_dict['asset_context']['source_tool'] = f.finding_signature.split(':')[0]
                else:
                    finding_dict['asset_context']['source_tool'] = 'unknown'

            training_data.append(finding_dict)

        log.info("Retraining ConfidenceModel...")
        confidence_model = ConfidenceModel()
        confidence_model.train(training_data)
        log.info("ConfidenceModel retraining complete. Model file has been updated.")

        log.info("--- Model Retraining Pipeline Finished Successfully ---")

if __name__ == '__main__':
    retrain_confidence_model()
