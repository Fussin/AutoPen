import logging
import subprocess
import json
import os
import warnings
from typing import List
from ..base import Plugin
from ..context import ScanContext
from ...reconnaissance.utils import load_config

log = logging.getLogger(__name__)

class URLProcessorPlugin(Plugin):
    """
    A plugin to process aggregated URLs, check for liveness, and perform triage.
    """
    @property
    def name(self) -> str:
        return "URL Processor"

    @property
    def description(self) -> str:
        return "Processes URLs for liveness, enrichment, and triage."

    @property
    def requires(self) -> List[str]:
        return ["aggregated_urls"]

    @property
    def provides(self) -> List[str]:
        return ["live_urls_2xx", "parameterized_urls", "js_files_urls", "live_urls"]

    def _run_command(self, command: str):
        """Runs a shell command."""
        try:
            log.info(f"Running command: {command}")
            env = os.environ.copy()
            go_path = subprocess.check_output("go env GOPATH", shell=True, text=True).strip()
            env['PATH'] = f"{os.path.join(go_path, 'bin')}:{env['PATH']}"
            subprocess.run(command, shell=True, check=True, capture_output=True, text=True, env=env)
        except subprocess.CalledProcessError as e:
            log.error(f"Command '{command}' failed with error: {e.stderr}")
            raise
        except FileNotFoundError:
            log.error(f"Command not found: {command}. Make sure the tool is installed and in PATH.")
            raise

    def run(self, context: ScanContext):
        urls = context.get("aggregated_urls")
        if not urls:
            log.warning("No aggregated URLs found in context to process.")
            return

        results_dir = context.results_dir
        log.info(f"Processing {len(urls)} aggregated URLs.")

        # Define file paths
        all_urls_file = os.path.join(results_dir, "all_urls.txt")
        httpx_results_file = os.path.join(results_dir, "results.json")
        live_urls_2xx_file = os.path.join(results_dir, "2xx.txt")
        parameterized_urls_file = os.path.join(results_dir, "p.txt")
        js_files_urls_file = os.path.join(results_dir, "js_files.txt")

        # Write aggregated URLs to all_urls.txt
        with open(all_urls_file, "w") as f:
            f.write("\n".join(urls))

        config = load_config()
        tool_commands = config.get("tool_commands", {})

        try:
            # 3. Liveness & Enrichment Probe (HTTPX)
            httpx_command = tool_commands.get("httpx_enrich", "").format(
                input_file=all_urls_file,
                output_file=httpx_results_file
            )
            if httpx_command:
                self._run_command(httpx_command)
            else:
                log.error("HTTPX enrich command not configured.")
                return

            # 4A. Data Triage & Analysis
            # Filter for 2xx status codes
            jq_2xx_command = tool_commands.get("jq_2xx", "").format(
                input_file=httpx_results_file,
                output_file=live_urls_2xx_file
            )
            if jq_2xx_command:
                self._run_command(jq_2xx_command)

            # Filter for URLs with parameters
            jq_params_command = tool_commands.get("jq_params", "").format(
                input_file=httpx_results_file,
                output_file=parameterized_urls_file
            )
            if jq_params_command:
                self._run_command(jq_params_command)

            # Filter for JavaScript files
            jq_js_command = tool_commands.get("jq_js", "").format(
                input_file=httpx_results_file,
                output_file=js_files_urls_file
            )
            if jq_js_command:
                self._run_command(jq_js_command)

            # Read results back and set them in the context
            with open(live_urls_2xx_file, "r") as f:
                live_urls_2xx = [line.strip() for line in f if line.strip()]
            with open(parameterized_urls_file, "r") as f:
                parameterized_urls = [line.strip() for line in f if line.strip()]
            with open(js_files_urls_file, "r") as f:
                js_files_urls = [line.strip() for line in f if line.strip()]

            context.set("live_urls_2xx", live_urls_2xx)
            context.set("parameterized_urls", parameterized_urls)
            context.set("js_files_urls", js_files_urls)

            # Temporary alias for backward compatibility
            context.set("live_urls", live_urls_2xx)
            warnings.warn(
                "Deprecation: 'live_urls' has been replaced by 'live_urls_2xx'. "
                "Please update your plugins. 'live_urls' will be removed in the next release.",
                DeprecationWarning,
                stacklevel=2
            )

            log.info("URL processing and triage completed successfully.")
            log.info(f"Found {len(live_urls_2xx)} live 2xx URLs.")
            log.info(f"Found {len(parameterized_urls)} parameterized URLs.")
            log.info(f"Found {len(js_files_urls)} JavaScript files.")

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            log.error(f"URL processing and triage failed: {e}")
