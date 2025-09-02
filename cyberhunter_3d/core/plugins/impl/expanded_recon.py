import logging
import shodan
import os
from typing import List, Dict, Set
from ..base import Plugin
from ..context import ScanContext

log = logging.getLogger(__name__)

class ExpandedReconPlugin(Plugin):
    """
    A plugin that uses discovered artifacts to find new, related assets
    using external search engines like Shodan.
    """
    @property
    def name(self) -> str:
        return "Expanded Reconnaissance"

    @property
    def description(self) -> str:
        return "Uses artifacts (e.g., favicon hashes) to find related assets via Shodan."

    @property
    def requires(self) -> List[str]:
        return ["discovered_artifacts"]

    @property
    def provides(self) -> List[str]:
        return ["expanded_targets"]

    def __init__(self):
        self.shodan_api_key = os.getenv("SHODAN_API_KEY")
        self.shodan_client = None
        if self.shodan_api_key:
            try:
                self.shodan_client = shodan.Shodan(self.shodan_api_key)
                self.shodan_client.info()
                log.info("Shodan client initialized successfully.")
            except shodan.APIError as e:
                log.error(f"Shodan API key is invalid: {e}")
                self.shodan_client = None
        else:
            log.warning("SHODAN_API_KEY not set. Expanded Reconnaissance plugin will be disabled.")

    def run(self, context: ScanContext):
        if not self.shodan_client:
            log.info("Shodan client not available. Skipping expanded reconnaissance.")
            return

        artifacts = context.get("discovered_artifacts", {})
        if not artifacts:
            log.info("No discovered artifacts to use for expanded recon.")
            return

        new_domains: Set[str] = set()

        favicon_hashes = artifacts.get("favicon_hashes", [])
        for f_hash in favicon_hashes:
            log.info(f"Searching Shodan for favicon hash: {f_hash}")
            try:
                results = self.shodan_client.search(f"http.favicon.hash:{f_hash}")
                for result in results.get('matches', []):
                    for domain in result.get('hostnames', []):
                        if isinstance(domain, str):
                            new_domains.add(domain.strip().lower())
            except shodan.APIError as e:
                log.error(f"Shodan search failed for favicon hash {f_hash}: {e}")

        ga_ids = artifacts.get("google_analytics_ids", [])
        for ga_id in ga_ids:
            log.info(f"Searching Shodan for Google Analytics ID: {ga_id}")
            try:
                results = self.shodan_client.search(f'http.html:"{ga_id}"')
                for result in results.get('matches', []):
                    for domain in result.get('hostnames', []):
                         if isinstance(domain, str):
                            new_domains.add(domain.strip().lower())
            except shodan.APIError as e:
                log.error(f"Shodan search failed for GA ID {ga_id}: {e}")

        if new_domains:
            log.warning(f"Expanded Recon discovered {len(new_domains)} new potential domains: {new_domains}")
            existing_subdomains = context.get("subdomains", set())
            updated_subdomains = existing_subdomains.union(new_domains)
            context.set("subdomains", updated_subdomains)
            context.set("expanded_targets", list(new_domains))
        else:
            log.info("Expanded Recon did not find any new domains.")
            context.set("expanded_targets", [])
