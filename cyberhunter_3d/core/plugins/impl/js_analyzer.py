import logging
import subprocess
import os
import json
from typing import List, Set
from ..base import Plugin
from ..context import ScanContext
from ...reconnaissance.utils import load_config

log = logging.getLogger(__name__)

class JavaScriptAnalyzerPlugin(Plugin):
    """
    A plugin to analyze JavaScript files for endpoints, secrets, and new URLs.
    """
    @property
    def name(self) -> str:
        return "JavaScript Analyzer"

    @property
    def description(self) -> str:
        return "Analyzes JavaScript files for secrets, endpoints, and new URLs using subjs, LinkFinder, and Trufflehog."

    @property
    def requires(self) -> List[str]:
        return ["js_files_urls"]

    @property
    def provides(self) -> List[str]:
        return ["api_endpoints", "js_secrets", "new_urls_from_js"]

    def _run_command(self, command: str) -> str:
        """Runs a command and returns its stdout."""
        try:
            log.info(f"Running command: {command}")
            env = os.environ.copy()
            go_path = subprocess.check_output("go env GOPATH", shell=True, text=True).strip()
            env['PATH'] = f"{os.path.join(go_path, 'bin')}:{env['PATH']}"
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True, env=env)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                log.error(f"Error running command: {command}\n{stderr}")
                return ""
            return stdout
        except FileNotFoundError:
            log.error(f"Tool for command not found: {command}. Is it installed and in PATH?")
        except Exception as e:
            log.error(f"An exception occurred while running {command}: {e}")
        return ""

    def run(self, context: ScanContext):
        js_files = context.get("js_files_urls", [])
        if not js_files:
            log.info("No JavaScript files to analyze.")
            return

        results_dir = context.results_dir
        js_files_list_path = os.path.join(results_dir, "js_files.txt")

        config = load_config()
        tool_commands = config.get("tool_commands", {})

        # --- 5. JavaScript Recursive Analysis (subjs) ---
        new_urls_from_js: Set[str] = set()
        subjs_command = tool_commands.get("subjs", "").format(input_file=js_files_list_path)
        if subjs_command:
            log.info("Running subjs to find new URLs in JavaScript files.")
            output = self._run_command(subjs_command)
            new_urls = {line.strip() for line in output.split('\n') if line.strip()}
            log.info(f"subjs found {len(new_urls)} new potential URLs.")
            new_urls_from_js.update(new_urls)

        # --- Additional JS Analysis: LinkFinder and Trufflehog ---
        all_js_endpoints = {}
        all_js_secrets = {}

        # LinkFinder for endpoints
        linkfinder_command_template = tool_commands.get("linkfinder_file")
        if linkfinder_command_template:
            log.info("Running LinkFinder on all JS files.")
            linkfinder_output_file = os.path.join(results_dir, "linkfinder_output.txt")
            command = linkfinder_command_template.format(input_file=js_files_list_path, output_file=linkfinder_output_file)
            self._run_command(command)
            # Process LinkFinder output - this is a simplified parser
            with open(linkfinder_output_file, "r") as f:
                endpoints = [line.strip() for line in f if line.strip() and not line.startswith('/')]
            all_js_endpoints["all_js_files"] = endpoints
            log.info(f"LinkFinder found {len(endpoints)} endpoints.")

        # Trufflehog for secrets
        trufflehog_command_template = tool_commands.get("trufflehog_file")
        if trufflehog_command_template:
            log.info("Running Trufflehog to find secrets in JavaScript files.")
            for js_url in js_files:
                command = trufflehog_command_template.format(url=js_url)
                output = self._run_command(command)
                secrets = [json.loads(line) for line in output.split('\n') if line.strip()]
                if secrets:
                    log.info(f"Trufflehog found {len(secrets)} potential secrets in {js_url}.")
                    all_js_secrets[js_url] = secrets

        # --- Set results in context ---
        context.set("api_endpoints", all_js_endpoints)
        context.set("js_secrets", all_js_secrets)
        context.set("new_urls_from_js", list(new_urls_from_js))

        # --- Save results to files ---
        js_endpoints_filepath = os.path.join(results_dir, f"js_endpoints_{context.scan_id}.json")
        with open(js_endpoints_filepath, "w") as f:
            json.dump(all_js_endpoints, f, indent=4)
        log.info(f"JavaScript endpoint analysis results saved to {js_endpoints_filepath}")

        js_secrets_filepath = os.path.join(results_dir, f"js_secrets_{context.scan_id}.json")
        with open(js_secrets_filepath, "w") as f:
            json.dump(all_js_secrets, f, indent=4)
        log.info(f"JavaScript secret analysis results saved to {js_secrets_filepath}")

        new_urls_from_js_filepath = os.path.join(results_dir, "new_from_js.txt")
        with open(new_urls_from_js_filepath, "w") as f:
            f.write("\n".join(sorted(list(new_urls_from_js))))
        log.info(f"New URLs from JS analysis saved to {new_urls_from_js_filepath}")
