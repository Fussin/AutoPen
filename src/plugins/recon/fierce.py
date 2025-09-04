import shutil
import os
from typing import List, Dict
from src.common.base_plugin import Plugin
from src.common.exec import run_command
from src.common.schema import Finding
import datetime

class FiercePlugin(Plugin):
    """
    Fierce plugin for DNS analysis and subdomain enumeration.
    """

    def name(self) -> str:
        return "fierce"

    def phase(self) -> str:
        return "recon"

    def check_dependencies(self) -> bool:
        """
        Checks if fierce is installed.
        """
        return shutil.which("fierce") is not None

    def run(self, targets: List[str]) -> List[Dict]:
        """
        Runs fierce on a list of domains.
        """
        if not self.check_dependencies():
            print("Fierce is not installed. Please install it to use this plugin.")
            return []

        all_findings = []
        for target in targets:
            print(f"Running fierce on {target}...")
            # Note: Fierce can be slow. Consider running with --threads option.
            command = ["fierce", "--domain", target]
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
        Parses the raw output of fierce.
        """
        findings = []
        # Fierce output is not structured, so we'll have to parse it with regex or line splitting.
        # This is a simple example that just looks for lines containing the target domain.
        for line in raw_output.strip().split('\n'):
            if target in line and "Found:" in line:
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
                    "tags": ["subdomain", "recon", "dns"],
                    "fingerprints": {}
                }
                findings.append(finding)
        return findings
