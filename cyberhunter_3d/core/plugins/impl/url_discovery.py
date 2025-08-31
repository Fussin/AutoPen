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
            env = os.environ.copy()
            go_path = subprocess.check_output("go env GOPATH", shell=True, text=True).strip()
            env['PATH'] = f"{os.path.join(go_path, 'bin')}:{env['PATH']}"
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True, env=env)
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

        if not subdomains:
            log.warning("No subdomains found in context. URL Discovery might not find many URLs.")

        all_urls = set()

        config = load_config()
        tool_commands = config.get("tool_commands", {})

        if subdomains:
            log.info(f"Starting URL discovery for {len(subdomains)} subdomains.")
            # Create a temporary file with subdomains for tools that accept a list
            temp_subdomain_file = os.path.join(context.results_dir, "temp_subdomains_for_urls.txt")
            with open(temp_subdomain_file, "w") as f:
                f.write("\n".join(subdomains))

            # Tools that can take a list of subdomains
            commands_for_list = {
                "gau_file": tool_commands.get("gau_file", "").format(input_file=temp_subdomain_file),
                "katana_list": tool_commands.get("katana_list", "").format(input_file=temp_subdomain_file),
            }
            for tool, command in commands_for_list.items():
                if command:
                    log.info(f"Running {tool} for all subdomains from file.")
                    urls = self._run_tool(command)
                    log.info(f"Found {len(urls)} URLs with {tool}")
                    all_urls.update(urls)

            # Tools that need to be run per subdomain
            commands_per_domain = {
                "waybackurls": tool_commands.get("waybackurls", ""),
                "hakrawler": tool_commands.get("hakrawler", ""),
            }
            for subdomain in subdomains:
                for tool, command_template in commands_per_domain.items():
                    if command_template:
                        command = command_template.format(target=subdomain)
                        log.info(f"Running {tool} for {subdomain}")
                        urls = self._run_tool(command)
                        log.info(f"Found {len(urls)} URLs with {tool} for {subdomain}")
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

        raw_urls = list(all_urls)
        log.info(f"Discovered a total of {len(raw_urls)} raw URLs for {target_domain}")
        context.set("urls", raw_urls)
