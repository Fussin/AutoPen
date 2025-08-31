import logging
import subprocess
import os
import json
import tempfile
from typing import List
from ..base import Plugin
from ..context import ScanContext
from ...reconnaissance.utils import load_config

log = logging.getLogger(__name__)

class ApiSecurityScannerPlugin(Plugin):
    """
    A plugin to scan for common API security vulnerabilities.
    """
    @property
    def name(self) -> str:
        return "API Security Scanner"

    @property
    def description(self) -> str:
        return "Scans for common API security vulnerabilities using Nuclei and Dalfox."

    @property
    def requires(self) -> List[str]:
        return ["api_endpoints"]

    @property
    def provides(self) -> List[str]:
        return ["api_vulnerabilities"]

    def _run_command(self, command: str) -> str:
        """Runs a command and returns its stdout."""
        try:
            log.info(f"Running command: {command}")
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
            stdout, stderr = process.communicate()
            if process.returncode != 0 and stderr:
                # Log stderr but don't immediately return empty, as some tools write info to stderr
                log.warning(f"Command '{command}' exited with non-zero status. Stderr: {stderr}")
            return stdout
        except FileNotFoundError:
            log.error(f"Tool for command not found: {command}. Is it installed and in PATH?")
            return ""
        except Exception as e:
            log.error(f"An exception occurred while running {command}: {e}")
            return ""

    def run(self, context: ScanContext):
        log.info("Running API security scanner plugin...")
        api_endpoints = context.get("api_endpoints", [])

        if not api_endpoints:
            log.info("No API endpoints found, skipping scan.")
            context.set("api_vulnerabilities", {})
            return

        config = load_config()
        nuclei_command_template = config.get("tool_commands", {}).get("nuclei_api_scan")
        dalfox_command_template = config.get("tool_commands", {}).get("dalfox_api_scan")

        all_vulnerabilities = {}
        results_dir = context.results_dir

        # Create a temporary file to store the API endpoints
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
            tmp_file.write('\n'.join(api_endpoints))
            endpoints_filepath = tmp_file.name

        try:
            # Run Nuclei for general API vulnerabilities
            if nuclei_command_template:
                log.info("Running Nuclei for API vulnerabilities...")
                nuclei_output_filepath = os.path.join(results_dir, f"nuclei_api_results_{context.scan_id}.json")
                command = nuclei_command_template.format(input_file=endpoints_filepath, output_file=nuclei_output_filepath)
                self._run_command(command)

                if os.path.exists(nuclei_output_filepath):
                    with open(nuclei_output_filepath, "r") as f:
                        for line in f:
                            try:
                                vuln = json.loads(line)
                                host = vuln.get("host", "unknown")
                                if host not in all_vulnerabilities:
                                    all_vulnerabilities[host] = []
                                all_vulnerabilities[host].append(vuln)
                            except json.JSONDecodeError:
                                log.warning(f"Could not decode Nuclei output line: {line.strip()}")
                log.info("Nuclei API scan complete.")

            # Run Dalfox for XSS in APIs
            if dalfox_command_template:
                log.info("Running Dalfox for XSS in APIs...")
                dalfox_output_filepath = os.path.join(results_dir, f"dalfox_api_results_{context.scan_id}.json")
                command = dalfox_command_template.format(input_file=endpoints_filepath, output_file=dalfox_output_filepath)
                self._run_command(command)

                if os.path.exists(dalfox_output_filepath):
                     with open(dalfox_output_filepath, "r") as f:
                        try:
                            # Dalfox may output a single JSON array or object
                            dalfox_results = json.load(f)
                            results_list = dalfox_results.get("results", []) if isinstance(dalfox_results, dict) else dalfox_results
                            for result in results_list:
                                host = result.get("url", "unknown")
                                if host not in all_vulnerabilities:
                                    all_vulnerabilities[host] = []
                                all_vulnerabilities[host].append(result)
                        except json.JSONDecodeError:
                            log.warning("Could not decode Dalfox JSON output.")
                log.info("Dalfox API scan complete.")

        finally:
            # Clean up the temporary file
            os.remove(endpoints_filepath)

        context.set("api_vulnerabilities", all_vulnerabilities)

        # Save aggregated results
        api_vulns_filepath = os.path.join(results_dir, f"api_vulnerabilities_{context.scan_id}.json")
        with open(api_vulns_filepath, "w") as f:
            json.dump(all_vulnerabilities, f, indent=4)
        log.info(f"API security scan results saved to {api_vulns_filepath}")
