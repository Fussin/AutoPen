import shutil
import os
from typing import List, Dict
from src.common.base_plugin import Plugin
from src.common.exec import run_command
from src.common.schema import Finding
import datetime

class DnsenumPlugin(Plugin):
    """
    DNSEnum plugin for DNS enumeration.
    """

    def name(self) -> str:
        return "dnsenum"

    def phase(self) -> str:
        return "recon"

    def check_dependencies(self) -> bool:
        """
        Checks if dnsenum is installed.
        """
        return shutil.which("dnsenum") is not None

    def run(self, targets: List[str]) -> List[Dict]:
        """
        Runs dnsenum on a list of domains.
        """
        if not self.check_dependencies():
            print("DNSEnum is not installed. Please install it to use this plugin.")
            return []

        all_findings = []
        for target in targets:
            print(f"Running dnsenum on {target}...")
            command = ["dnsenum", target]
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
        Parses the raw output of dnsenum.
        """
        findings = []
        # DNSEnum output is unstructured. This parser will look for host records.
        for line in raw_output.strip().split('\n'):
            if "A" in line and target in line:
                parts = line.split()
                if len(parts) > 0:
                    subdomain = parts[0]
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
