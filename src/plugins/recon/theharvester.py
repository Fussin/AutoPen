import shutil
import os
import json
from typing import List, Dict
from src.common.base_plugin import Plugin
from src.common.exec import run_command
from src.common.schema import Finding
import datetime

class TheHarvesterPlugin(Plugin):
    """
    TheHarvester plugin for gathering emails, subdomains, etc.
    """

    def name(self) -> str:
        return "theharvester"

    def phase(self) -> str:
        return "recon"

    def check_dependencies(self) -> bool:
        """
        Checks if TheHarvester is installed.
        """
        return shutil.which("theharvester") is not None

    def run(self, targets: List[str]) -> List[Dict]:
        """
        Runs TheHarvester on a list of domains.
        """
        if not self.check_dependencies():
            print("TheHarvester is not installed. Please install it to use this plugin.")
            return []

        all_findings = []
        for target in targets:
            print(f"Running TheHarvester on {target}...")
            # Using a few sources for demonstration. A real implementation would use more.
            # TheHarvester can be slow, so running on a few sources is better for testing.
            # The -f flag saves the output to a JSON file.
            output_dir = f"artifacts/recon/{self.name()}"
            os.makedirs(output_dir, exist_ok=True)
            output_filename = os.path.join(output_dir, f"{target}.json")

            command = [
                "theharvester",
                "-d", target,
                "-b", "google,bing", # Using a subset of sources
                "-f", output_filename
            ]
            run_command(command) # TheHarvester doesn't print to stdout when using -f

            if os.path.exists(output_filename):
                with open(output_filename, 'r') as f:
                    raw_output = f.read()
                findings = self.parse(raw_output, target)
                all_findings.extend(findings)
        return all_findings

    def parse(self, raw_output: str, target: str) -> List[Dict]:
        """
        Parses the JSON output of TheHarvester.
        """
        findings = []
        try:
            data = json.loads(raw_output)
            for host in data.get("hosts", []):
                finding: Finding = {
                    "target": target,
                    "phase": self.phase(),
                    "tool": self.name(),
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "evidence": {"poc": host},
                    "vuln": {
                        "name": "Host Discovered",
                        "severity": "info",
                    },
                    "tags": ["host", "recon"],
                    "fingerprints": {}
                }
                findings.append(finding)
            for email in data.get("emails", []):
                finding: Finding = {
                    "target": target,
                    "phase": self.phase(),
                    "tool": self.name(),
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "evidence": {"poc": email},
                    "vuln": {
                        "name": "Email Discovered",
                        "severity": "info",
                    },
                    "tags": ["email", "osint"],
                    "fingerprints": {}
                }
                findings.append(finding)
        except json.JSONDecodeError:
            print(f"Error decoding TheHarvester JSON output for {target}")
        return findings
