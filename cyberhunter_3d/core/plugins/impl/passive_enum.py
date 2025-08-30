import concurrent.futures
import logging
from typing import List
from ..base import Plugin
from ..context import ScanContext
from ....utils.file_utils import run_command
from ...reconnaissance.utils import load_config

log = logging.getLogger(__name__)

class PassiveEnumPlugin(Plugin):
    """
    Plugin for passive subdomain enumeration.
    """
    def __init__(self):
        super().__init__()
        self.config = load_config()

    @property
    def name(self) -> str:
        return "passive_enum"

    @property
    def description(self) -> str:
        return "Runs passive subdomain enumeration tools like subfinder and assetfinder."

    @property
    def provides(self) -> List[str]:
        return ["passive_subdomains"]

    def run(self, context: ScanContext):
        log.info("Running passive enumeration plugin...")
        target = context.target_domain

        subfinder_path = self.config['tools']['subfinder']
        assetfinder_path = self.config['tools']['assetfinder']

        commands = [
            [subfinder_path, "-d", target, "-silent"],
            [assetfinder_path, "--subs-only", target],
        ]

        all_subdomains = set()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_cmd = {executor.submit(run_command, cmd): cmd for cmd in commands}
            for future in concurrent.futures.as_completed(future_to_cmd):
                cmd = future_to_cmd[future]
                try:
                    output = future.result()
                    subdomains = set(output.strip().split('\n'))
                    all_subdomains.update(subdomains)
                    log.info(f"Found {len(subdomains)} subdomains with {' '.join(cmd)}")
                except Exception as exc:
                    log.error(f"{' '.join(cmd)} generated an exception: {exc}")

        # Add results to the context
        existing_subdomains = context.get("subdomains", set())
        combined_subdomains = existing_subdomains.union(all_subdomains)
        context.set("subdomains", combined_subdomains)
        context.set("passive_subdomains", all_subdomains)
        log.info(f"Found {len(all_subdomains)} new passive subdomains.")
