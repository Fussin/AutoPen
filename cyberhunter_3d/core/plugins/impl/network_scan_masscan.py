import logging
import subprocess
import json
import tempfile
import os
from typing import Dict, Any

from ..base import Plugin
from ..context import ScanContext

log = logging.getLogger(__name__)

class MasscanScanPlugin(Plugin):
    """
    Masscan Scan Plugin to discover open ports.
    """
    @property
    def name(self) -> str:
        return "Masscan Scan"

    @property
    def description(self) -> str:
        return "Performs a Masscan scan to discover open ports."

    @property
    def requires(self) -> list[str]:
        return ["validated_subdomains"]

    @property
    def provides(self) -> list[str]:
        return ["open_ports"]

    def run(self, context: ScanContext):
        subdomains = context.get("validated_subdomains")
        if not subdomains:
            log.info("No validated subdomains found, skipping Masscan scan.")
            return

        log.info(f"Running Masscan scan on {len(subdomains)} subdomains.")
        open_ports: Dict[str, Any] = context.get("open_ports", {})

        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
            for subdomain in subdomains:
                tmp_file.write(subdomain + '\n')
            target_file = tmp_file.name

        # Create a temporary file for the output
        output_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
        output_file.close()

        try:
            # -iL: Input from list of hosts/networks
            # -oJ: Output in JSON format
            # --rate: The rate in packets/second
            command = [
                "masscan",
                "-iL",
                target_file,
                "-oJ",
                output_file.name,
                "--rate",
                "1000" # Default rate
            ]
            subprocess.run(command, capture_output=True, text=True, check=True)

            with open(output_file.name, 'r') as f:
                # Masscan produces a stream of JSON objects, not a single valid JSON array.
                # We need to read each line and parse it as a separate JSON object.
                # The last line could be a "finished" message, so we skip it if it is not a valid json.
                for line in f:
                    if line.startswith('{'):
                        try:
                            data = json.loads(line.strip(','))
                            ip = data.get('ip')
                            port_info = data.get('ports')[0]
                            port = port_info.get('port')
                            if ip and port:
                                # masscan gives ip, not hostname. We need to resolve it.
                                # For now, we will store by IP. A separate plugin could do the resolution.
                                if ip not in open_ports:
                                    open_ports[ip] = []
                                if port not in open_ports[ip]:
                                    open_ports[ip].append(port)
                        except json.JSONDecodeError:
                            log.warning(f"Could not parse line from masscan output: {line}")

            log.info(f"Masscan scan completed. Found open ports on {len(open_ports)} hosts.")

        except FileNotFoundError:
            log.error("masscan not found. Please ensure it is installed and in your PATH.")
        except subprocess.CalledProcessError as e:
            log.error(f"Masscan scan failed: {e.stderr}")
        finally:
            os.remove(target_file)
            os.remove(output_file.name)
            context.set("open_ports", open_ports)
