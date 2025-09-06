import yaml
import os
import logging

# Set up a simple logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOG = logging.getLogger(__name__)


def load_config():
    """
    Loads the reconnaissance configuration from the YAML file.
    """
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'recon_config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)
