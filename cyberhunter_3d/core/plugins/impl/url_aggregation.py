import logging
import subprocess
import os
from typing import List
from ..base import Plugin
from ..context import ScanContext
from ...reconnaissance.utils import load_config

log = logging.getLogger(__name__)

class URLAggregationPlugin(Plugin):
    """
    A plugin to aggregate, normalize, and deduplicate URLs.
    """
    @property
    def name(self) -> str:
        return "URL Aggregation"

    @property
    def description(self) -> str:
        return "Aggregates, normalizes, and deduplicates URLs from various sources."

    @property
    def requires(self) -> List[str]:
        return ["urls"]

    @property
    def provides(self) -> List[str]:
        return ["aggregated_urls"]

    def run(self, context: ScanContext):
        raw_urls = context.get("urls")
        if not raw_urls:
            log.warning("No raw URLs found in context to aggregate.")
            return

        log.info(f"Aggregating {len(raw_urls)} raw URLs.")

        # Write raw URLs to a temporary file
        temp_raw_urls_file = os.path.join(context.results_dir, f"raw_urls_{context.scan_id}.txt")
        with open(temp_raw_urls_file, "w") as f:
            f.write("\n".join(raw_urls))

        # Use shell commands for aggregation: cat *.txt | sort -u | unfurl format %s://%d%p
        # In this case, we use the file we just created

        config = load_config()
        tool_commands = config.get("tool_commands", {})
        unfurl_command = tool_commands.get("unfurl_normalize", "").format(input_file=temp_raw_urls_file)

        if not unfurl_command:
            log.error("Unfurl normalize command not configured. Skipping URL aggregation.")
            return

        try:
            # First, sort and unique the URLs
            sorted_unique_urls_file = os.path.join(context.results_dir, f"sorted_urls_{context.scan_id}.txt")
            sort_command = f"sort -u {temp_raw_urls_file} > {sorted_unique_urls_file}"
            subprocess.run(sort_command, shell=True, check=True)

            # Then, normalize the URLs with unfurl
            normalized_urls_file = os.path.join(context.results_dir, f"normalized_urls_{context.scan_id}.txt")
            unfurl_command = tool_commands.get("unfurl_normalize", "").format(input_file=sorted_unique_urls_file)

            with open(normalized_urls_file, "w") as f_out:
                process = subprocess.Popen(unfurl_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
                stdout, stderr = process.communicate()
                if process.returncode != 0:
                    log.error(f"Error running unfurl command: {stderr}")
                    return
                f_out.write(stdout)

            with open(normalized_urls_file, "r") as f:
                aggregated_urls = [line.strip() for line in f if line.strip()]

            log.info(f"Aggregated and normalized to {len(aggregated_urls)} unique URLs.")
            context.set("aggregated_urls", aggregated_urls)

            # Save the aggregated list for debugging and records
            final_url_list_path = os.path.join(context.results_dir, "all_urls.txt")
            with open(final_url_list_path, "w") as f:
                f.write("\n".join(aggregated_urls))
            log.info(f"Saved final aggregated URL list to {final_url_list_path}")

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            log.error(f"URL aggregation failed: {e}")
        finally:
            # Clean up temporary files
            if os.path.exists(temp_raw_urls_file):
                os.remove(temp_raw_urls_file)
            if os.path.exists(sorted_unique_urls_file):
                os.remove(sorted_unique_urls_file)
            if os.path.exists(normalized_urls_file):
                os.remove(normalized_urls_file)
