import logging
import subprocess
import os
from typing import List
from ..base import Plugin
from ..context import ScanContext
from ...reconnaissance.utils import load_config

log = logging.getLogger(__name__)

class VisualReconPlugin(Plugin):
    """
    A plugin to perform visual reconnaissance using gowitness.
    """
    @property
    def name(self) -> str:
        return "Visual Recon"

    @property
    def description(self) -> str:
        return "Takes screenshots of live URLs using gowitness."

    @property
    def requires(self) -> List[str]:
        return ["live_urls_2xx"]

    @property
    def provides(self) -> List[str]:
        return ["screenshots"]

    def run(self, context: ScanContext):
        live_urls = context.get("live_urls_2xx")
        if not live_urls:
            log.info("No live URLs to screenshot.")
            return

        results_dir = context.results_dir
        screenshots_dir = os.path.join(results_dir, "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)

        log.info(f"Starting visual reconnaissance on {len(live_urls)} live URLs.")

        temp_urls_file = os.path.join(results_dir, "gowitness_targets.txt")
        with open(temp_urls_file, "w") as f:
            f.write("\n".join(live_urls))

        config = load_config()
        tool_commands = config.get("tool_commands", {})
        gowitness_command = tool_commands.get("gowitness_file", "").format(
            input_file=temp_urls_file,
            output_dir=screenshots_dir
        )

        if not gowitness_command:
            log.error("Gowitness command not configured. Skipping visual recon.")
            if os.path.exists(temp_urls_file):
                os.remove(temp_urls_file)
            return

        try:
            log.info(f"Running gowitness command: {gowitness_command}")
            subprocess.run(gowitness_command, shell=True, check=True, capture_output=True, text=True)
            log.info(f"Screenshots saved to {screenshots_dir}")
            context.set("screenshots_dir", screenshots_dir)

            # We can also list the screenshots taken and add them to the context if needed
            screenshots = [os.path.join(screenshots_dir, f) for f in os.listdir(screenshots_dir) if f.endswith('.png')]
            context.set("screenshots", screenshots)
            log.info(f"Took {len(screenshots)} screenshots.")

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            log.error(f"Gowitness scan failed: {e}")
        finally:
            if os.path.exists(temp_urls_file):
                os.remove(temp_urls_file)
