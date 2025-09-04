import shutil
import os
import json
from typing import List, Dict
from src.common.base_plugin import Plugin
from src.common.exec import run_command
from src.common.schema import Finding
import datetime

class MasscanPlugin(Plugin):
    """
    Masscan plugin for fast port scanning.
    """

    def name(self) -> str:
        return "masscan"

    def phase(self) -> str:
        return "network"

    def check_dependencies(self) -> bool:
        """
        Checks if masscan is installed.
        """
        return shutil.which("masscan") is not None

    def run(self, targets: List[str], ports: str = "0-65535", rate: int = 1000) -> List[Dict]:
        """
        Runs masscan on a list of targets.
        """
        if not self.check_dependencies():
            print("Masscan is not installed. Please install it to use this plugin.")
            return []

        all_findings = []

        output_dir = f"artifacts/network/{self.name()}"
        os.makedirs(output_dir, exist_ok=True)
        output_filename = os.path.join(output_dir, "masscan_results.json")

        command = [
            "masscan",
            "-p", ports,
            "--rate", str(rate),
            "-oJ", output_filename, # JSON output
        ] + targets

        print(f"Running masscan on {len(targets)} targets...")
        run_command(command)

        if os.path.exists(output_filename):
            with open(output_filename, 'r') as f:
                raw_output = f.read()
            findings = self.parse(raw_output)
            all_findings.extend(findings)

        return all_findings

    def parse(self, raw_output: str) -> List[Dict]:
        """
        Parses the JSON output of masscan.
        """
        findings = []
        try:
            # Masscan produces a list of JSON objects, but not a valid JSON array.
            # We need to wrap it in brackets and separate with commas.
            data = json.loads(f"[{','.join(raw_output.strip().splitlines())}]")
            for item in data:
                ip = item["ip"]
                port_info = item["ports"][0]
                port = port_info["port"]

                finding: Finding = {
                    "target": ip,
                    "phase": self.phase(),
                    "tool": self.name(),
                    "timestamp": datetime.datetime.fromtimestamp(item["timestamp"]).isoformat(),
                    "evidence": {},
                    "vuln": {
                        "name": "Open Port Discovered",
                        "severity": "info",
                    },
                    "tags": ["network", "portscan"],
                    "fingerprints": {
                        "ports": [port]
                    }
                }
                findings.append(finding)
        except json.JSONDecodeError:
            print("Error decoding Masscan JSON output.")
        return findings
