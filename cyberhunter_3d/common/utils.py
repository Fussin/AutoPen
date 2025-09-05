import yaml
import os

def load_config():
    """
    Loads the reconnaissance configuration from the YAML file.
    """
    # The path is calculated relative to this file's location
    # common/utils.py -> common/ -> cyberhunter_3d/ -> config/recon_config.yaml
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'recon_config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)
