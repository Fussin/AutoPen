import os
import time
import requests
from typing import List, Dict, Any
from cyberhunter_3d.core.plugins.base import Plugin
from cyberhunter_3d.utils.logger import setup_logger

class CveMapperPlugin(Plugin):
    """
    Plugin for mapping technologies to CVEs.
    """
    @property
    def name(self) -> str:
        return "CVE Mapper"

    @property
    def description(self) -> str:
        return "Maps technologies to CVEs using the NVD API."

    @property
    def requires(self) -> List[str]:
        return ["tech"]

    @property
    def provides(self) -> List[str]:
        return ["cve_results"]

    def run(self, context: 'ScanContext'):
        logger = setup_logger('CveMapperPlugin', 'cve_mapper_plugin.log')
        target = context.target

        tech_data = context.get("tech")
        if not tech_data:
            logger.info("No technology data provided. Skipping CVE mapping.")
            return

        cve_results = {}
        for host, data in tech_data.items():
            techs = [t['name'] for t in data.get('technologies', [])]
            if techs:
                cve_results[host] = self._map_tech_to_cves(techs, logger)

        context.set("cve_results", cve_results)

    def _get_cpe_for_tech(self, technology: str) -> str:
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

    def _query_nvd_for_cpe(self, cpe: str, logger) -> List[Dict]:
        api_key = os.getenv("NVD_API_KEY")
        if not api_key:
            return []

        base_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
        params = {"cpeName": cpe}
        headers = {"apiKey": api_key}

        try:
            response = requests.get(base_url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            time.sleep(1)
            return data.get("vulnerabilities", [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying NVD API for CPE {cpe}: {e}")
            return []

    def _map_tech_to_cves(self, technologies: List[str], logger) -> Dict[str, List]:
        cve_results = {}
        for tech in technologies:
            cpe = self._get_cpe_for_tech(tech)
            if cpe:
                cves = self._query_nvd_for_cpe(cpe, logger)
                if cves:
                    cve_results[tech] = cves
        return cve_results
