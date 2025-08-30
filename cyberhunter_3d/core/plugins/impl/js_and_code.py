import logging
import re
from typing import List, Set
from ..base import Plugin
from ..context import ScanContext
from ....utils.file_utils import run_command
from ...reconnaissance.utils import load_config

log = logging.getLogger(__name__)

class JsAndCodePlugin(Plugin):
    """
    Plugin for JS and Code analysis.
    """
    def __init__(self):
        super().__init__()
        self.config = load_config()

    @property
    def name(self) -> str:
        return "js_and_code_analysis"

    @property
    def description(self) -> str:
        return "Crawls JS files and other sources to find subdomains and secrets."

    @property
    def requires(self) -> List[str]:
        return ["validated_subdomains"]

    @property
    def provides(self) -> List[str]:
        return ["js_subdomains", "secrets"]

    def run(self, context: ScanContext):
        log.info("Running JS and Code analysis plugin...")
        live_hosts = context.get("validated_subdomains")
        if not live_hosts:
            log.info("No live hosts to analyze. Skipping JS/Code analysis.")
            context.set("js_subdomains", set())
            context.set("secrets", [])
            return

        httpx_path = self.config['tools']['httpx']
        katana_path = self.config['tools']['katana']

        # Using httpx to gather URLs from live hosts
        httpx_cmd = [httpx_path, "-l", "\n".join(live_hosts), "-silent"]
        urls = run_command(httpx_cmd).strip().split('\n')

        # Using katana to crawl for JS files and endpoints
        katana_cmd = [katana_path, "-u", "\n".join(urls), "-silent", "-jc"] # jc for js crawling
        crawled_output = run_command(katana_cmd)

        # Extract subdomains
        js_subdomains = self._extract_subdomains_from_text(crawled_output, context.target_domain)
        log.info(f"Found {len(js_subdomains)} subdomains from JS files.")
        context.set("js_subdomains", js_subdomains)

        # Extract secrets (simplified example)
        secrets = self._extract_secrets(crawled_output)
        log.info(f"Found {len(secrets)} potential secrets.")
        context.set("secrets", secrets)

    def _extract_subdomains_from_text(self, text: str, domain: str) -> Set[str]:
        """Extracts subdomains from a given block of text."""
        pattern = re.compile(r'([a-zA-Z0-9][a-zA-Z0-9-]*\.' + re.escape(domain) + ')')
        found = pattern.findall(text)
        return set(s.lower() for s in found)

    def _extract_secrets(self, text: str) -> List[str]:
        """A very basic secret extractor."""
        patterns = {
            "api_key": r'["\'](sk|pk)_[a-zA-Z0-9]{20,50}["\']',
            "aws_key": r'AKIA[0-9A-Z]{16}',
        }
        secrets = []
        for secret_type, pattern in patterns.items():
            found = re.findall(pattern, text)
            for s in found:
                secrets.append(f"{secret_type}: {s}")
        return secrets
