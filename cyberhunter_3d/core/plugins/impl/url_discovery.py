import logging
import subprocess
import os
from typing import List, Set
from ..base import Plugin
from ..context import ScanContext
from ...reconnaissance.utils import load_config

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

        config = load_config()
        tool_commands = config.get("tool_commands", {})

        if subdomains:
            log.info(f"Starting URL discovery for {len(subdomains)} subdomains.")
            temp_subdomain_file = os.path.join(context.results_dir, "temp_subdomains.txt")
            with open(temp_subdomain_file, "w") as f:
                f.write("\n".join(subdomains))

            commands_to_run = {
                "gau_file": tool_commands.get("gau_file", "").format(input_file=temp_subdomain_file),
                "katana_list": tool_commands.get("katana_list", "").format(input_file=temp_subdomain_file),
            }
            for tool, command in commands_to_run.items():
                if command:
                    log.info(f"Running {tool} for all subdomains")
                    urls = self._run_tool(command)
                    log.info(f"Found {len(urls)} URLs with {tool}")
                    all_urls.update(urls)

            if os.path.exists(temp_subdomain_file):
                os.remove(temp_subdomain_file)
        else:
            log.info(f"Starting URL discovery for the root domain: {target_domain}")
            commands_to_run = {
                "gau": tool_commands.get("gau", "").format(target=target_domain),
                "waybackurls": tool_commands.get("waybackurls", "").format(target=target_domain),
                "katana": tool_commands.get("katana", "").format(target=target_domain),
                "hakrawler": tool_commands.get("hakrawler", "").format(target=target_domain),
            }
            for tool, command in commands_to_run.items():
                if command:
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
