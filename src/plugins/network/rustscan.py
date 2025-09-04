import shutil
import os
import json
from typing import List, Dict
from src.common.base_plugin import Plugin
from src.common.exec import run_command
from src.common.schema import Finding
import datetime

class RustscanPlugin(Plugin):
    """
    Rustscan plugin for fast port scanning.
    """

    def name(self) -> str:
        return "rustscan"

    def phase(self) -> str:
        return "network"

    def check_dependencies(self) -> bool:
        """
        Checks if rustscan is installed.
        """
        return shutil.which("rustscan") is not None

    def run(self, targets: List[str]) -> List[Dict]:
        """
        Runs rustscan on a list of targets.
        """
        if not self.check_dependencies():
            print("Rustscan is not installed. Please install it to use this plugin.")
            return []

        all_findings = []

        output_dir = f"artifacts/network/{self.name()}"
        os.makedirs(output_dir, exist_ok=True)
        # Rustscan can't output to a file directly with JSON, so we redirect stdout.
        # It also scans one target at a time.
        for target in targets:
            print(f"Running rustscan on {target}...")

            safe_target_name = target.replace('/', '_').replace(':', '_')
            output_filename = os.path.join(output_dir, f"{safe_target_name}.json")

            command = [
                "rustscan",
                "-a", target,
                "--json"
            ]

            raw_output = run_command(command)
            if raw_output:
                with open(output_filename, "w") as f:
                    f.write(raw_output)

                findings = self.parse(raw_output, target)
                all_findings.extend(findings)

        return all_findings

    def parse(self, raw_output: str, target: str) -> List[Dict]:
        """
        Parses the JSON output of rustscan.
        """
        findings = []
        try:
            data = json.loads(raw_output)
            ports = data.get("ports", [])
            if ports:
                finding: Finding = {
                    "target": target,
                    "phase": self.phase(),
                    "tool": self.name(),
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "evidence": {},
                    "vuln": {
                        "name": "Open Ports Discovered",
                        "severity": "info",
                    },
                    "tags": ["network", "portscan"],
                    "fingerprints": {
                        "ports": ports
                    }
                }
                findings.append(finding)
        except json.JSONDecodeError:
            print(f"Error decoding Rustscan JSON output for {target}")
        return findings
