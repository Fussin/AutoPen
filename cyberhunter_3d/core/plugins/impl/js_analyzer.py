import logging
import subprocess
import os
import json
from typing import List, Dict
from ..base import Plugin
from ..context import ScanContext
from ...reconnaissance.utils import load_config

log = logging.getLogger(__name__)

class JavaScriptAnalyzerPlugin(Plugin):
    """
    A plugin to analyze JavaScript files for endpoints using LinkFinder.
    """
    @property
    def name(self) -> str:
        return "JavaScript Analyzer"

    @property
    def description(self) -> str:
        return "Analyzes JavaScript files for hidden endpoints and secrets using LinkFinder."

    @property
    def requires(self) -> List[str]:
        return ["live_urls"]

    @property
    def provides(self) -> List[str]:
        return ["js_endpoints"]

    def run(self, context: ScanContext):
        live_urls = context.get("live_urls", [])
        js_files = [url for url in live_urls if url.endswith(".js")]

        if not js_files:
            log.info("No JavaScript files to analyze.")
            return

        config = load_config()
        tool_commands = config.get("tool_commands", {})
        linkfinder_command_template = tool_commands.get("linkfinder")

        if not linkfinder_command_template:
            log.error("LinkFinder command not configured. Skipping JavaScript analysis.")
            return

        results_dir = context.results_dir
        scan_id = context.scan_id
        all_js_endpoints = {}

        for js_url in js_files:
            log.info(f"Analyzing JavaScript file: {js_url}")
            command = linkfinder_command_template.format(url=js_url)

            try:
                process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate()

                if process.returncode != 0:
                    log.error(f"LinkFinder scan failed for {js_url}: {stderr}")
                    continue

                endpoints = [line for line in stdout.split('\n') if line.strip() and not line.startswith('[')]
                if endpoints:
                    all_js_endpoints[js_url] = endpoints
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                log.error(f"LinkFinder scan failed for {js_url}: {e}")

        if all_js_endpoints:
            log.info(f"Found endpoints in {len(all_js_endpoints)} JavaScript files.")
            context.set("js_endpoints", all_js_endpoints)

            # Save results to a file for aggregation
            js_endpoints_filepath = os.path.join(results_dir, f"js_endpoints_{scan_id}.json")
            with open(js_endpoints_filepath, "w") as f:
                json.dump(all_js_endpoints, f, indent=4)
            log.info(f"JavaScript analysis results saved to {js_endpoints_filepath}")
