import os
import time
import requests
import logging
from typing import List, Dict
from ..base import Plugin
from ..context import ScanContext

log = logging.getLogger(__name__)

class CveMapperPlugin(Plugin):
    """
    Plugin for mapping technologies to CVEs using the NVD API.
    """
    @property
    def name(self) -> str:
        return "cve_mapper"

    @property
    def description(self) -> str:
        return "Maps technologies to CVEs."

    @property
    def requires(self) -> List[str]:
        return ["tech_fingerprints"]

    @property
    def provides(self) -> List[str]:
        return ["cve_results"]

    def run(self, context: ScanContext):
        log.info("Running CVE mapper plugin...")
        tech_fingerprints = context.get("tech_fingerprints")
        if not tech_fingerprints:
            log.info("No technology fingerprints found, skipping CVE mapping.")
            context.set("cve_results", {})
            return

        cve_results = {}
        for host, techs in tech_fingerprints.items():
            if techs:
                cve_results[host] = self._map_tech_to_cves(techs)

        context.set("cve_results", cve_results)
        log.info(f"Found CVEs for {len(cve_results)} hosts.")

    def _get_cpe_for_tech(self, technology: str) -> str:
        # This mapping is simplified and would be more extensive in a real app
        tech_to_cpe = {
            "nginx": "cpe:2.3:a:nginx:nginx",
            "apache": "cpe:2.3:a:apache:http_server",
            "jquery": "cpe:2.3:a:jquery:jquery",
        }
        return tech_to_cpe.get(technology.lower())

    def _query_nvd_for_cpe(self, cpe: str) -> List[Dict]:
        api_key = os.getenv("NVD_API_KEY")
        if not api_key:
            log.warning("NVD_API_KEY not set. Skipping CVE query.")
            return []

        base_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
        params = {"cpeName": cpe, "resultsPerPage": 5} # Limit results
        headers = {"apiKey": api_key}

        try:
            response = requests.get(base_url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            # Respect NVD API rate limits
            time.sleep(1)
            data = response.json()
            return data.get("vulnerabilities", [])
        except requests.RequestException as e:
            log.error(f"Error querying NVD API for CPE {cpe}: {e}")
            return []

    def _map_tech_to_cves(self, technologies: List[str]) -> Dict[str, List]:
        cve_results = {}
        for tech in technologies:
            cpe = self._get_cpe_for_tech(tech)
            if cpe:
                cves = self._query_nvd_for_cpe(cpe)
                if cves:
                    cve_results[tech] = cves
        return cve_results
