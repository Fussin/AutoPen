import logging
import subprocess
import json
from typing import List, Dict, Any
from ..base import Plugin
from ..context import ScanContext
from ...reconnaissance.utils import load_config
from cyberhunter_3d.utils.file_utils import get_results_dir
import os

log = logging.getLogger(__name__)

class URLProcessorPlugin(Plugin):
    """
    A plugin to process discovered URLs.
    """
    @property
    def name(self) -> str:
        return "URL Processor"

    @property
    def description(self) -> str:
        return "Processes URLs to check for live status and extracts parameters."

    @property
    def requires(self) -> List[str]:
        return ["urls"]

    @property
    def provides(self) -> List[str]:
        return ["live_urls", "dead_urls", "redirect_urls", "url_parameters"]

    def _save_urls_to_file(self, urls: List[str], filename: str, results_dir: str):
        """Saves a list of URLs to a file."""
        filepath = os.path.join(results_dir, filename)
        with open(filepath, 'w') as f:
            for url in urls:
                f.write(f"{url}\n")
        log.info(f"Saved {len(urls)} URLs to {filepath}")

    def run(self, context: ScanContext):
        urls = context.get("urls")
        if not urls:
            log.warning("No URLs found in context to process.")
            return

        target_domain = context.target_domain
        results_dir = context.results_dir
        scan_id = context.scan_id
        log.info(f"Processing {len(urls)} URLs for {target_domain}")

        temp_url_file = os.path.join(results_dir, f"temp_urls_{scan_id}.txt")
        httpx_output_file = os.path.join(results_dir, f"httpx_output_{scan_id}.json")
        unfurl_output_file = os.path.join(results_dir, f"unfurl_output_{scan_id}.json")

        try:
            # Write URLs to a temporary file for httpx
            with open(temp_url_file, "w") as f:
                f.write("\n".join(urls))

            config = load_config()
            tool_commands = config.get("tool_commands", {})

            # Run httpx to get status codes
            httpx_command = tool_commands.get("httpx_file", "").format(input_file=temp_url_file, output_file=httpx_output_file)
            if httpx_command:
                subprocess.run(httpx_command, shell=True, check=True, capture_output=True, text=True)

            # Process httpx output
            live_urls, dead_urls, redirect_urls = [], [], []
            with open(httpx_output_file, "r") as f:
                for line in f:
                    try:
                        result = json.loads(line)
                        status_code = result.get("status_code")
                        url = result.get("url")
                        if not url: continue
                        if 200 <= status_code < 300: live_urls.append(url)
                        elif 300 <= status_code < 400: redirect_urls.append(url)
                        else: dead_urls.append(url)
                    except json.JSONDecodeError: continue

            # Save categorized URLs to files
            self._save_urls_to_file(live_urls, f"alive_urls_{scan_id}.txt", results_dir)
            self._save_urls_to_file(dead_urls, f"dead_urls_{scan_id}.txt", results_dir)
            self._save_urls_to_file(redirect_urls, f"redirect_urls_{scan_id}.txt", results_dir)

            # Extract parameters using unfurl
            unfurl_command = tool_commands.get("unfurl_file", "").format(input_file=temp_url_file)
            if unfurl_command:
                # We need to redirect the output to the file
                with open(unfurl_output_file, "w") as f:
                    subprocess.run(unfurl_command, shell=True, check=True, stdout=f, text=True)

            url_parameters = []
            with open(unfurl_output_file, "r") as f:
                url_parameters = [line.strip() for line in f if line.strip()]
            self._save_urls_to_file(url_parameters, f"parameters_{scan_id}.txt", results_dir)

            # Set data in context
            context.set("live_urls", live_urls)
            context.set("dead_urls", dead_urls)
            context.set("redirect_urls", redirect_urls)
            context.set("url_parameters", url_parameters)

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            log.error(f"URL processing failed: {e}")
        finally:
            # Clean up temporary files
            for f in [temp_url_file, httpx_output_file, unfurl_output_file]:
                if os.path.exists(f):
                    os.remove(f)
