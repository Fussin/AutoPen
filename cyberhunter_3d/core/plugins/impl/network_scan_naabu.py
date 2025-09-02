import logging
import subprocess
import json
import tempfile
import os
from typing import Dict, Any

from ..base import Plugin
from ..context import ScanContext

log = logging.getLogger(__name__)

class NaabuScanPlugin(Plugin):
    """
    Naabu Scan Plugin to discover open ports.
    """
    @property
    def name(self) -> str:
        return "Naabu Scan"

    @property
    def description(self) -> str:
        return "Performs a Naabu scan to discover open ports."

    @property
    def requires(self) -> list[str]:
        return ["validated_subdomains"]

    @property
    def provides(self) -> list[str]:
        return ["open_ports"]

    def run(self, context: ScanContext):
        subdomains = context.get("validated_subdomains")
        if not subdomains:
            log.info("No validated subdomains found, skipping Naabu scan.")
            return

        log.info(f"Running Naabu scan on {len(subdomains)} subdomains.")
        open_ports: Dict[str, Any] = context.get("open_ports", {})

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
            for subdomain in subdomains:
                tmp_file.write(subdomain + '\n')
            target_file = tmp_file.name

        try:
            # -iL: Input from list of hosts/networks
            # -json: Output in json format
            command = [
                "naabu",
                "-iL",
                target_file,
                "-json"
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=True)

            for line in result.stdout.strip().split('\n'):
                try:
                    data = json.loads(line)
                    host = data.get('host')
                    port = data.get('port')
                    if host and port:
                        if host not in open_ports:
                            open_ports[host] = []
                        if port not in open_ports[host]:
                            open_ports[host].append(port)
                except json.JSONDecodeError:
                    log.warning(f"Could not parse line from naabu output: {line}")

            log.info(f"Naabu scan completed. Found open ports on {len(open_ports)} hosts.")

        except FileNotFoundError:
            log.error("naabu not found. Please ensure it is installed and in your PATH.")
        except subprocess.CalledProcessError as e:
            log.error(f"Naabu scan failed: {e.stderr}")
        finally:
            os.remove(target_file)
            context.set("open_ports", open_ports)
