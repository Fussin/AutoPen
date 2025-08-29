import os
import time
import requests
from typing import List, Dict, Set

def _get_cpe_for_tech(technology: str) -> str:
    """
    Maps a technology name to its CPE string.
    This is a simple hardcoded mapping and is not exhaustive.
    It should be improved in the future with a more sophisticated mapping.
    """
    tech_to_cpe = {
        "nginx": "cpe:2.3:a:nginx:nginx:*:*:*:*:*:*:*:*",
        "apache": "cpe:2.3:a:apache:http_server:*:*:*:*:*:*:*:*",
        "jquery": "cpe:2.3:a:jquery:jquery:*:*:*:*:*:*:*:*",
        "react": "cpe:2.3:a:facebook:react:*:*:*:*:*:*:*:*",
        "php": "cpe:2.3:a:php:php:*:*:*:*:*:*:*:*",
        "python": "cpe:2.3:a:python:python:*:*:*:*:*:*:*:*",
        "wordpress": "cpe:2.3:a:wordpress:wordpress:*:*:*:*:*:*:*:*",
    }
    return tech_to_cpe.get(technology.lower())

def _query_nvd_for_cpe(cpe: str, logger) -> List[Dict]:
    """
    Queries the NVD API for CVEs associated with a given CPE.
    """
    api_key = os.getenv("NVD_API_KEY")
    if not api_key:
        logger.warning("NVD_API_KEY environment variable not set. Skipping CVE lookup.")
        return []

    base_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    params = {"cpeName": cpe}
    headers = {"apiKey": api_key}

    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()
        vulnerabilities = data.get("vulnerabilities", [])

        time.sleep(1) # Respect rate limits

        return vulnerabilities

    except requests.exceptions.RequestException as e:
        logger.error(f"Error querying NVD API for CPE {cpe}: {e}")
        return []

def map_tech_to_cves(technologies: List[str], logger) -> Dict[str, List]:
    """
    Maps a list of technologies to a list of associated CVEs.
    """
    cve_results = {}
    for tech in technologies:
        cpe = _get_cpe_for_tech(tech)
        if cpe:
            cves = _query_nvd_for_cpe(cpe, logger)
            if cves:
                cve_results[tech] = cves
    return cve_results
