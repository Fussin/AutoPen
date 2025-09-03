import logging
import tempfile
import os
import json
from typing import List
from ..base import Plugin
from ..context import ScanContext
from ...reconnaissance.utils import load_config, run_command

log = logging.getLogger(__name__)

class TakeoverPlugin(Plugin):
    """
    Plugin for detecting subdomain takeover vulnerabilities using Nuclei.
    """
    def __init__(self):
        super().__init__()
        self.config = load_config()

    @property
    def name(self) -> str:
        return "subdomain_takeover"

    @property
    def description(self) -> str:
        return "Checks for subdomain takeover vulnerabilities."

    @property
    def requires(self) -> List[str]:
        return ["validated_subdomains"]

    @property
    def provides(self) -> List[str]:
        return ["takeover_vulnerabilities"]

    def run(self, context: ScanContext):
        log.info("Running subdomain takeover plugin...")
        live_hosts = context.get("validated_subdomains")
        if not live_hosts:
            log.info("No live hosts provided for takeover scan.")
            context.set("takeover_vulnerabilities", [])
            return

        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp_file:
            tmp_file.write('\n'.join(live_hosts))
            target_file = tmp_file.name

        vulnerabilities = []
        try:
            command_template = self.config['tool_commands']['nuclei_takeover_scan']
            command = command_template.format(input_file=target_file)
            result = run_command(command.split(), "", log)

            for line in result.strip().split('\n'):
                if line:
                    try:
                        vulnerabilities.append(json.loads(line))
                    except json.JSONDecodeError:
                        log.warning(f"Could not decode JSON from Nuclei: {line}")

            log.info(f"Found {len(vulnerabilities)} potential takeover vulnerabilities.")
        except Exception as e:
            log.error(f"An error occurred while running Nuclei for takeovers: {e}")
        finally:
            os.remove(target_file)

        context.set("takeover_vulnerabilities", vulnerabilities)
