import logging
import subprocess
import os
import json
import tempfile
from typing import List
from urllib.parse import urljoin
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
        return ["api_endpoints", "spec_endpoints"]

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
        js_endpoints = context.get("api_endpoints", {})
        spec_endpoints = context.get("spec_endpoints", {})

        # Merge endpoints from both sources
        all_endpoints = set()
        for host, endpoints in js_endpoints.items():
             # js_analyzer now returns a dict of { "all_js_files": ["/endpoint1", "/endpoint2"] }
             # We need to construct the full URL
            base_url = host if host.startswith('http') else f"http://{host}"
            if isinstance(endpoints, dict): # Handle the nested structure
                for endpoint_list in endpoints.values():
                    for endpoint in endpoint_list:
                         all_endpoints.add(urljoin(base_url, endpoint))
            elif isinstance(endpoints, list): # Handle a flat list
                 for endpoint in endpoints:
                    all_endpoints.add(urljoin(base_url, endpoint))

        for host, endpoints in spec_endpoints.items():
            base_url = host if host.startswith('http') else f"http://{host}"
            for endpoint in endpoints:
                all_endpoints.add(urljoin(base_url, endpoint))

        if not all_endpoints:
            log.info("No API endpoints found, skipping scan.")
            context.set("api_vulnerabilities", {})
            return

        # Separate GraphQL endpoints
        graphql_endpoints = {e for e in all_endpoints if "graphql" in e.lower()}
        rest_endpoints = all_endpoints - graphql_endpoints

        config = load_config()
        nuclei_rest_command = config.get("tool_commands", {}).get("nuclei_api_scan")
        nuclei_gql_command = config.get("tool_commands", {}).get("nuclei_graphql_scan")
        dalfox_command = config.get("tool_commands", {}).get("dalfox_api_scan")

        all_vulnerabilities = {}
        results_dir = context.results_dir

        self._run_scans(rest_endpoints, "rest", nuclei_rest_command, dalfox_command, results_dir, context.scan_id, all_vulnerabilities)
        self._run_scans(graphql_endpoints, "graphql", nuclei_gql_command, None, results_dir, context.scan_id, all_vulnerabilities) # No dalfox for GQL

        context.set("api_vulnerabilities", all_vulnerabilities)

        # Save aggregated results
        api_vulns_filepath = os.path.join(results_dir, f"api_vulnerabilities_{context.scan_id}.json")
        with open(api_vulns_filepath, "w") as f:
            json.dump(all_vulnerabilities, f, indent=4)
        log.info(f"API security scan results saved to {api_vulns_filepath}")

    def _run_scans(self, endpoints: set, scan_type: str, nuclei_command_template: str, dalfox_command_template: str, results_dir: str, scan_id: str, all_vulnerabilities: dict):
        if not endpoints:
            return

        log.info(f"Running {scan_type} API scans on {len(endpoints)} endpoints...")

        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
            tmp_file.write('\n'.join(endpoints))
            endpoints_filepath = tmp_file.name

        try:
            # Run Nuclei
            if nuclei_command_template:
                log.info(f"Running Nuclei for {scan_type} API vulnerabilities...")
                nuclei_output_filepath = os.path.join(results_dir, f"nuclei_{scan_type}_results_{scan_id}.json")
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
                log.info(f"Nuclei {scan_type} API scan complete.")

            # Run Dalfox for XSS
            if dalfox_command_template:
                log.info(f"Running Dalfox for XSS in {scan_type} APIs...")
                dalfox_output_filepath = os.path.join(results_dir, f"dalfox_{scan_type}_results_{scan_id}.json")
                command = dalfox_command_template.format(input_file=endpoints_filepath, output_file=dalfox_output_filepath)
                self._run_command(command)

                if os.path.exists(dalfox_output_filepath):
                     with open(dalfox_output_filepath, "r") as f:
                        try:
                            dalfox_results = json.load(f)
                            results_list = dalfox_results.get("results", []) if isinstance(dalfox_results, dict) else dalfox_results
                            for result in results_list:
                                host = result.get("url", "unknown")
                                if host not in all_vulnerabilities:
                                    all_vulnerabilities[host] = []
                                all_vulnerabilities[host].append(result)
                        except json.JSONDecodeError:
                            log.warning("Could not decode Dalfox JSON output.")
                log.info(f"Dalfox {scan_type} API scan complete.")
        finally:
            os.remove(endpoints_filepath)
