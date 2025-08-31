import logging
import subprocess
import os
import json
from typing import List, Dict
from ..base import Plugin
from ..context import ScanContext
from ...reconnaissance.utils import load_config

log = logging.getLogger(__name__)

class ContentDiscoveryPlugin(Plugin):
    """
    A plugin to discover content on live URLs using gobuster.
    """
    @property
    def name(self) -> str:
        return "Content Discovery"

    @property
    def description(self) -> str:
        return "Discovers directories and files on live web servers using gobuster."

    @property
    def requires(self) -> List[str]:
        return ["live_urls_2xx"]

    @property
    def provides(self) -> List[str]:
        return ["discovered_paths"]

    def run(self, context: ScanContext):
        live_urls = context.get("live_urls_2xx")
        if not live_urls:
            log.info("No live URLs to scan for content.")
            return

        config = load_config()
        tool_commands = config.get("tool_commands", {})
        wordlists = config.get("wordlists", {})
        gobuster_command_template = tool_commands.get("gobuster")
        wordlist_path = wordlists.get("dir_bruteforce")

        if not gobuster_command_template or not wordlist_path:
            log.error("Gobuster command or wordlist not configured. Skipping content discovery.")
            return

        results_dir = context.results_dir
        scan_id = context.scan_id
        all_discovered_paths = {}

        for url in live_urls:
            log.info(f"Running content discovery on {url}")
            # Sanitize URL to use as a filename
            sanitized_url = url.replace("http://", "").replace("https://", "").replace("/", "_")
            output_file = os.path.join(results_dir, f"gobuster_{sanitized_url}_{scan_id}.txt")

            command = gobuster_command_template.format(url=url, wordlist=wordlist_path, output_file=output_file)

            try:
                subprocess.run(command, shell=True, check=True, capture_output=True, text=True)

                if os.path.exists(output_file):
                    with open(output_file, "r") as f:
                        paths = [line.strip().split(" ")[0] for line in f if line.strip()]
                        if paths:
                            all_discovered_paths[url] = paths
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                log.error(f"Gobuster scan failed for {url}: {e}")
            finally:
                # Clean up the gobuster output file as we will store the results in the main report
                if os.path.exists(output_file):
                    os.remove(output_file)

        if all_discovered_paths:
            log.info(f"Found {len(all_discovered_paths)} hosts with discovered paths.")
            context.set("discovered_paths", all_discovered_paths)

            # Save results to a file for aggregation
            discovered_paths_filepath = os.path.join(results_dir, f"discovered_paths_{scan_id}.json")
            with open(discovered_paths_filepath, "w") as f:
                json.dump(all_discovered_paths, f, indent=4)
            log.info(f"Discovered paths results saved to {discovered_paths_filepath}")
