import logging
import subprocess
import os
import json
from typing import List
from ..base import Plugin
from ..context import ScanContext
from ...reconnaissance.utils import load_config

log = logging.getLogger(__name__)

class WordPressScannerPlugin(Plugin):
    """
    A plugin to scan WordPress sites using WPScan.
    """
    @property
    def name(self) -> str:
        return "WordPress Scanner"

    @property
    def description(self) -> str:
        return "Scans WordPress sites for vulnerabilities using WPScan."

    @property
    def requires(self) -> List[str]:
        return ["wordpress_urls"]

    @property
    def provides(self) -> List[str]:
        return ["wordpress_vulnerabilities"]

    def _run_command(self, command: str) -> str:
        """Runs a command and returns its stdout."""
        try:
            log.info(f"Running command: {command}")
            # Ensure the command is run in a shell if it contains pipes, etc.
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                # WPScan exits with non-zero code for vulnerabilities found, but we still want the JSON output
                if "vulnerabilities identified" in stderr.lower():
                    log.warning(f"WPScan found vulnerabilities for command: {command}")
                elif stderr:
                    log.error(f"Error running command: {command}\n{stderr}")
                    return ""
            return stdout
        except FileNotFoundError:
            log.error(f"Tool for command not found: {command}. Is wpscan installed and in PATH?")
            return ""
        except Exception as e:
            log.error(f"An exception occurred while running {command}: {e}")
            return ""

    def run(self, context: ScanContext):
        log.info("Running WordPress scanner plugin...")
        # This should be a list of URLs identified as WordPress sites
        wordpress_urls = context.get("wordpress_urls", [])

        if not wordpress_urls:
            log.info("No WordPress URLs found, skipping scan.")
            context.set("wordpress_vulnerabilities", {})
            return

        config = load_config()
        wpscan_command_template = config.get("tool_commands", {}).get("wpscan_scan")

        if not wpscan_command_template:
            log.error("WPScan command template not found in config. Skipping scan.")
            return

        all_vulnerabilities = {}
        results_dir = context.results_dir

        for url in wordpress_urls:
            log.info(f"Scanning WordPress site: {url}")

            # WPScan requires an API token for vulnerability data
            wpscan_api_token = os.getenv("WPSCAN_API_TOKEN", "")
            if not wpscan_api_token:
                log.warning("WPSCAN_API_TOKEN environment variable not set. Vulnerability data will be limited.")

            command = wpscan_command_template.format(target_url=url, api_token=wpscan_api_token)

            output = self._run_command(command)

            if output:
                try:
                    # WPScan output can sometimes contain non-JSON text at the beginning.
                    # We need to find where the JSON object starts.
                    json_start_index = output.find('{')
                    if json_start_index != -1:
                        json_output = output[json_start_index:]
                        scan_results = json.loads(json_output)
                        all_vulnerabilities[url] = scan_results
                        log.info(f"Successfully parsed WPScan results for {url}")
                    else:
                        log.error(f"No JSON object found in WPScan output for {url}")
                except json.JSONDecodeError as e:
                    log.error(f"Failed to decode WPScan JSON output for {url}: {e}")
                    log.debug(f"WPScan raw output for {url}:\n{output}")

        context.set("wordpress_vulnerabilities", all_vulnerabilities)

        # Save results to a file for persistence
        wpscan_results_filepath = os.path.join(results_dir, f"wpscan_results_{context.scan_id}.json")
        with open(wpscan_results_filepath, "w") as f:
            json.dump(all_vulnerabilities, f, indent=4)
        log.info(f"WordPress scan results saved to {wpscan_results_filepath}")
