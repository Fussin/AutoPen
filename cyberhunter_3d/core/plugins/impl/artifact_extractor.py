import logging
import requests
import re
import mmh3
import codecs
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Set
from ..base import Plugin
from ..context import ScanContext

log = logging.getLogger(__name__)

class ArtifactExtractorPlugin(Plugin):
    """
    A plugin to extract various artifacts from live web pages for the purpose of
    expanding reconnaissance (e.g., finding related domains).
    """
    @property
    def name(self) -> str:
        return "Artifact Extractor"

    @property
    def description(self) -> str:
        return "Extracts artifacts like Google Analytics IDs and favicon hashes from live websites."

    @property
    def requires(self) -> List[str]:
        return ["live_urls_2xx"]

    @property
    def provides(self) -> List[str]:
        return ["discovered_artifacts"]

    def run(self, context: ScanContext):
        live_urls = context.get("live_urls_2xx", [])
        if not live_urls:
            log.info("No live URLs to extract artifacts from.")
            return

        all_artifacts: Dict[str, Set[str]] = {
            "google_analytics_ids": set(),
            "favicon_hashes": set(),
        }

        for url in live_urls:
            try:
                log.info(f"Extracting artifacts from {url}")
                response = requests.get(url, timeout=10, verify=False)
                response.raise_for_status()
                content = response.text

                ga_ids = set(re.findall(r'UA-\d{4,9}-\d{1,4}', content))
                if ga_ids:
                    log.info(f"Found Google Analytics IDs: {ga_ids} on {url}")
                    all_artifacts["google_analytics_ids"].update(ga_ids)

                favicon_hash = self._get_favicon_hash(url, content)
                if favicon_hash:
                    log.info(f"Found favicon hash: {favicon_hash} on {url}")
                    all_artifacts["favicon_hashes"].add(str(favicon_hash))

            except requests.RequestException as e:
                log.warning(f"Could not fetch or process {url}: {e}")

        final_artifacts = {k: list(v) for k, v in all_artifacts.items()}
        context.set("discovered_artifacts", final_artifacts)
        log.info(f"Artifact extraction complete. Found: {final_artifacts}")

    def _get_favicon_hash(self, base_url: str, page_content: str) -> int:
        """Finds, fetches, and hashes the favicon for a given URL."""
        favicon_match = re.search(r'<link.*?rel=[\'"]icon[\'"].*?href=[\'"](.*?)[\'"]', page_content, re.I)

        favicon_url = None
        if favicon_match:
            favicon_url = urljoin(base_url, favicon_match.group(1))
        else:
            favicon_url = urljoin(base_url, "/favicon.ico")

        try:
            response = requests.get(favicon_url, timeout=5, verify=False)
            response.raise_for_status()

            favicon = codecs.encode(response.content, 'base64')
            return mmh3.hash(favicon)
        except requests.RequestException:
            log.debug(f"No favicon found for {base_url}")
            return None
