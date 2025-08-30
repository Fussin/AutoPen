import logging
import json
from typing import List, Dict
from ..base import Plugin
from ..context import ScanContext
from ...reconnaissance.utils import load_config, run_command

log = logging.getLogger(__name__)

class TechFingerprintingPlugin(Plugin):
    """
    Plugin for technology fingerprinting and port scanning.
    """
    def __init__(self):
        super().__init__()
        self.config = load_config()

    @property
    def name(self) -> str:
        return "tech_fingerprinting"

    @property
    def description(self) -> str:
        return "Identifies technologies and open ports on live hosts."

    @property
    def requires(self) -> List[str]:
        return ["validated_subdomains"]

    @property
    def provides(self) -> List[str]:
        return ["tech_fingerprints", "open_ports"]

    def run(self, context: ScanContext):
        log.info("Running technology fingerprinting plugin...")
        live_hosts = context.get("validated_subdomains")
        if not live_hosts:
            log.info("No live hosts provided for technology fingerprinting.")
            context.set("tech_fingerprints", {})
            context.set("open_ports", {})
            return

        httpx_path = self.config['tools']['httpx']
        naabu_path = self.config['tools']['naabu']

        httpx_cmd = [httpx_path, "-l", "\n".join(live_hosts), "-json", "-silent"]
        httpx_output = run_command(httpx_cmd, context.target_domain, log)

        tech_fingerprints = self._parse_httpx_output(httpx_output)
        context.set("tech_fingerprints", tech_fingerprints)
        log.info(f"Fingerprinted technologies for {len(tech_fingerprints)} hosts.")

        naabu_cmd = [naabu_path, "-l", "\n".join(live_hosts), "-top-ports", "100", "-json", "-silent"]
        naabu_output = run_command(naabu_cmd, context.target_domain, log)

        open_ports = self._parse_naabu_output(naabu_output)
        context.set("open_ports", open_ports)
        log.info(f"Found open ports for {len(open_ports)} hosts.")

    def _parse_httpx_output(self, output: str) -> Dict[str, List[str]]:
        techs = {}
        for line in output.strip().split('\n'):
            if not line:
                continue
            try:
                data = json.loads(line)
                host = data.get("url")
                if host:
                    techs[host] = data.get("tech", [])
            except json.JSONDecodeError:
                log.warning(f"Could not decode JSON from httpx: {line}")
        return techs

    def _parse_naabu_output(self, output: str) -> Dict[str, List[int]]:
        ports = {}
        for line in output.strip().split('\n'):
            if not line:
                continue
            try:
                data = json.loads(line)
                host = data.get("host")
                if host:
                    if host not in ports:
                        ports[host] = []
                    ports[host].append(data.get("port"))
            except json.JSONDecodeError:
                log.warning(f"Could not decode JSON from naabu: {line}")
        return ports
