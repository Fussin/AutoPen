import requests
from typing import List, Dict, Optional

NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"

def get_cves_for_technology(technology: str, version: Optional[str] = None) -> List[Dict]:
    """
    Fetches CVEs for a given technology and optional version from the NVD API.

    :param technology: The technology to search for (e.g., "apache", "wordpress").
    :param version: The specific version of the technology.
    :return: A list of CVEs.
    """
    params = {
        "keywordSearch": technology,
        "resultsPerPage": 20  # Keep the number of results manageable
    }

    if version:
        params["keywordSearch"] += f" {version}"

    try:
        response = requests.get(NVD_API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("vulnerabilities", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching CVEs for {technology}: {e}")
        return []
