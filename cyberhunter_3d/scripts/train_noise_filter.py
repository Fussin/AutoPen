import os
import sys
import logging

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from cyberhunter_3d.web.models import db, Asset
from cyberhunter_3d.core.reconnaissance.ai.noise_filter import NoiseFilter
from run_web import app

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def train_model():
    """
    Fetches labeled data from the database and trains the noise filter model.
    """
    with app.app_context():
        log.info("Fetching labeled assets from the database...")

        # Fetch assets that have been explicitly labeled by a user.
        labeled_assets = Asset.query.filter(Asset.is_false_positive.isnot(None)).all()

        if not labeled_assets:
            log.warning("No labeled assets found in the database. Cannot train model.")
            return

        # Format data for the training function
        training_data = [(asset.value, asset.is_false_positive) for asset in labeled_assets]

        log.info(f"Found {len(training_data)} labeled assets for training.")

        noise_filter = NoiseFilter()
        noise_filter.train(training_data)

        log.info("Model training process finished.")

if __name__ == '__main__':
    train_model()
