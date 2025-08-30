import logging
import subprocess
import os
from typing import List, Set
from ..base import Plugin
from ..context import ScanContext

log = logging.getLogger(__name__)

class URLDiscoveryPlugin(Plugin):
    """
    A plugin to discover URLs from various sources.
    """
    @property
    def name(self) -> str:
        return "URL Discovery"

    @property
    def description(self) -> str:
        return "Discovers URLs using various tools like GAU, Katana, Hakrawler, and Waybackurls."

    @property
    def requires(self) -> List[str]:
        return []

    @property
    def provides(self) -> List[str]:
        return ["urls"]

    def _run_tool(self, command: str) -> Set[str]:
        """Runs a command and returns a set of output lines."""
        urls = set()
        try:
            log.info(f"Running command: {command}")
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                log.error(f"Error running command: {command}\n{stderr}")
                return urls
            urls.update(stdout.strip().split('\n'))
        except FileNotFoundError:
            log.error(f"Tool for command not found: {command}. Is it installed and in PATH?")
        except Exception as e:
            log.error(f"An exception occurred while running {command}: {e}")
        return urls

    def run(self, context: ScanContext):
        target_domain = context.target_domain
        subdomains = context.get("subdomains")

        all_urls = set()

        if subdomains:
            log.info(f"Starting URL discovery for {len(subdomains)} subdomains.")
            # Create a temporary file with all subdomains
            temp_subdomain_file = os.path.join(context.results_dir, "temp_subdomains.txt")
            with open(temp_subdomain_file, "w") as f:
                f.write("\n".join(subdomains))

            commands = {
                "gau": f"gau --subs --file {temp_subdomain_file}",
                "katana": f"katana -list {temp_subdomain_file} -silent",
            }
            for tool, command in commands.items():
                log.info(f"Running {tool} for all subdomains")
                urls = self._run_tool(command)
                log.info(f"Found {len(urls)} URLs with {tool}")
                all_urls.update(urls)

            os.remove(temp_subdomain_file)
        else:
            log.info(f"Starting URL discovery for the root domain: {target_domain}")
            commands = {
                "gau": f"gau --subs {target_domain}",
                "waybackurls": f"waybackurls {target_domain}",
                "katana": f"katana -u {target_domain} -silent",
                "hakrawler": f"hakrawler -url {target_domain} -depth 2 -plain"
            }
            for tool, command in commands.items():
                log.info(f"Running {tool} for {target_domain}")
                urls = self._run_tool(command)
                log.info(f"Found {len(urls)} URLs with {tool}")
                all_urls.update(urls)

        # Deduplicate URLs
        unique_urls = sorted(list(all_urls))

        log.info(f"Found a total of {len(unique_urls)} unique URLs for {target_domain}")

        # Save master URL list
        master_url_file = os.path.join(context.results_dir, f"way_kat_{context.scan_id}.txt")
        with open(master_url_file, "w") as f:
            f.write("\n".join(unique_urls))
        log.info(f"Saved master URL list to {master_url_file}")

        context.set("urls", unique_urls)
