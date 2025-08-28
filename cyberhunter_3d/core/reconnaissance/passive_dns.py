import requests
from typing import List, Dict

from cyberhunter_3d.utils.logger import setup_logger
from .utils import load_config

config = load_config()
logger = setup_logger('PassiveDNS', 'passive_dns.log')

SECURITYTRAILS_API_KEY = config.get('api_keys', {}).get('securitytrails_api_key')

def get_passive_dns_for_domain(domain: str) -> Dict[str, any]:
    """
    Gets historical DNS data for a domain from SecurityTrails.
    """
    if not SECURITYTRAILS_API_KEY:
        logger.warning("SecurityTrails API key not configured. Skipping passive DNS correlation.")
        return {}

    headers = {
        "accept": "application/json",
        "APIKEY": SECURITYTRAILS_API_KEY
    }
    url = f"https://api.securitytrails.com/v1/domain/{domain}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"SecurityTrails API error for domain {domain}: {e}")
        return {}
