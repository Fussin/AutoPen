import shutil
import os
from typing import List, Dict
from src.common.base_plugin import Plugin
from src.common.exec import run_command
from src.common.schema import Finding
import datetime

class AmassPlugin(Plugin):
    """
    Amass plugin for subdomain enumeration.
    """

    def name(self) -> str:
        return "amass"

    def phase(self) -> str:
        return "recon"

    def check_dependencies(self) -> bool:
        """
        Checks if amass is installed.
        """
        return shutil.which("amass") is not None

    def run(self, targets: List[str]) -> List[Dict]:
        """
        Runs amass on a list of domains.
        """
        if not self.check_dependencies():
            print("Amass is not installed. Please install it to use this plugin.")
            return []

        all_findings = []
        for target in targets:
            print(f"Running amass on {target}...")
            command = ["amass", "enum", "-passive", "-d", target]
            raw_output = run_command(command)
            if raw_output:
                # Save raw output
                output_dir = f"artifacts/recon/{self.name()}"
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"{target}.txt")
                with open(output_path, "w") as f:
                    f.write(raw_output)

                findings = self.parse(raw_output, target)
                all_findings.extend(findings)
        return all_findings

    def parse(self, raw_output: str, target: str) -> List[Dict]:
        """
        Parses the raw output of amass.
        """
        findings = []
        for line in raw_output.strip().split('\n'):
            # Amass output can be noisy, so we look for lines that look like subdomains
            # This is a simple parser, a more robust one would use the JSON output of amass
            if target in line:
                subdomain = line.split()[-1]
                finding: Finding = {
                    "target": target,
                    "phase": self.phase(),
                    "tool": self.name(),
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "evidence": {"poc": subdomain},
                    "vuln": {
                        "name": "Subdomain Discovered",
                        "severity": "info",
                    },
                    "tags": ["subdomain", "recon"],
                    "fingerprints": {}
                }
                findings.append(finding)
        return findings
