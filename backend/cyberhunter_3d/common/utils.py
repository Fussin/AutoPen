import yaml
import os
import shutil
from .exceptions import ToolNotFoundError

def load_config():
    """
    Loads the reconnaissance configuration from the YAML file.
    """
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'recon_config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def check_tool(tool_name: str, install_cmd: str = None) -> str:
    """
    Checks if a tool is in the system's PATH and returns the full path.
    If not found, raises a ToolNotFoundError.
    """
    path = shutil.which(tool_name)
    if path:
        return path
    else:
        raise ToolNotFoundError(tool_name, install_cmd)
