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

import re
import socket
from ..common.log import get_rich_logger

logger = get_rich_logger(__name__)

def is_valid_domain(domain: str) -> bool:
    """
    Validates if the given string is a valid domain name.
    """
    if not domain or not isinstance(domain, str):
        return False
    # Basic regex for domain validation
    pattern = re.compile(
        r'^(?:[a-zA-Z0-9]'  # First character of the domain
        r'(?:[a-zA-Z0-9-_]{0,61}[a-zA-Z0-9])?\.)'  # Subdomains
        r'+[a-zA-Z]{2,6}$'  # Top-level domain
    )
    return re.match(pattern, domain) is not None

def resolve_domain(domain: str) -> str | None:
    """
    Resolves a domain to its IP address (A record).
    Returns the IP address as a string or None if resolution fails.
    """
    try:
        ip_address = socket.gethostbyname(domain)
        logger.info(f"Resolved {domain} to {ip_address}")
        return ip_address
    except socket.gaierror:
        logger.warning(f"Could not resolve domain: {domain}")
        return None
