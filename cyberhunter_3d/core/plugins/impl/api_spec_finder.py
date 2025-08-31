import logging
import requests
import json
from typing import List
from urllib.parse import urljoin
from ..base import Plugin
from ..context import ScanContext

log = logging.getLogger(__name__)

class ApiSpecFinderPlugin(Plugin):
    """
    A plugin to find and parse API specification files (Swagger, OpenAPI).
    """
    @property
    def name(self) -> str:
        return "API Spec Finder"

    @property
    def description(self) -> str:
        return "Finds and parses API specification files to discover endpoints."

    @property
    def requires(self) -> List[str]:
        return ["live_hosts"]

    @property
    def provides(self) -> List[str]:
        return ["spec_endpoints"]

    def run(self, context: ScanContext):
        log.info("Running API Spec Finder plugin...")
        live_hosts = context.get("live_hosts", [])

        spec_files = [
            "swagger.json",
            "openapi.json",
            "api/swagger.json",
            "api/openapi.json",
            "v1/swagger.json",
            "v1/openapi.json",
            "v2/swagger.json",
            "v2/openapi.json",
            "api-docs",
            "api/api-docs",
            "v1/api-docs",
            "v2/api-docs",
        ]

        all_spec_endpoints = {}

        for host in live_hosts:
            for spec_file in spec_files:
                url = urljoin(host, spec_file)
                try:
                    response = requests.get(url, timeout=5, verify=False)
                    if response.status_code == 200:
                        spec_content = response.json()
                        log.info(f"Found API spec file at: {url}")

                        endpoints = self._parse_spec(spec_content)
                        if endpoints:
                            log.info(f"Found {len(endpoints)} endpoints in {url}")
                            if host not in all_spec_endpoints:
                                all_spec_endpoints[host] = []
                            all_spec_endpoints[host].extend(endpoints)

                except requests.exceptions.RequestException:
                    continue # Ignore connection errors, timeouts, etc.
                except json.JSONDecodeError:
                    log.warning(f"Could not decode JSON from spec file: {url}")
                    continue

        context.set("spec_endpoints", all_spec_endpoints)
        log.info(f"API Spec Finder finished. Found endpoints for {len(all_spec_endpoints)} hosts.")

    def _parse_spec(self, spec_content: dict) -> List[str]:
        """
        Parses a Swagger/OpenAPI spec and returns a list of paths.
        """
        endpoints = []
        if "paths" in spec_content and isinstance(spec_content["paths"], dict):
            for path in spec_content["paths"].keys():
                endpoints.append(path)
        return endpoints
