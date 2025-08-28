import shodan
from censys_platform import SDK
from typing import List, Dict, Set

from cyberhunter_3d.utils.logger import setup_logger
from .utils import load_config

config = load_config()
logger = setup_logger('ThreatIntel', 'threat_intel.log')

SHODAN_API_KEY = config.get('api_keys', {}).get('shodan')
CENSYS_PERSONAL_ACCESS_TOKEN = config.get('api_keys', {}).get('censys_personal_access_token')

def enrich_ips_with_shodan(ips: Set[str]) -> List[Dict[str, any]]:
    """
    Enriches a list of IPs with data from Shodan.
    """
    if not SHODAN_API_KEY:
        logger.warning("Shodan API key not configured. Skipping Shodan enrichment.")
        return []

    api = shodan.Shodan(SHODAN_API_KEY)
    enriched_data = []

    for ip in ips:
        try:
            host_info = api.host(ip)
            enriched_data.append(host_info)
        except shodan.APIError as e:
            logger.error(f"Shodan API error for IP {ip}: {e}")

    return enriched_data

def enrich_ips_with_censys(ips: Set[str]) -> List[Dict[str, any]]:
    """
    Enriches a list of IPs with data from Censys.
    """
    if not CENSYS_PERSONAL_ACCESS_TOKEN:
        logger.warning("Censys personal access token not configured. Skipping Censys enrichment.")
        return []

    with SDK(personal_access_token=CENSYS_PERSONAL_ACCESS_TOKEN) as sdk:
        enriched_data = []
        for ip in ips:
            try:
                host_info = sdk.v2.hosts.view(ip)
                enriched_data.append(host_info)
            except Exception as e:
                logger.error(f"Censys API error for IP {ip}: {e}")

    return enriched_data
