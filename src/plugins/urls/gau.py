import shutil
import os
from typing import List, Dict
from src.common.base_plugin import Plugin
from src.common.exec import run_command
from src.common.schema import Finding
import datetime

class GauPlugin(Plugin):
    """
    Gau plugin for URL discovery.
    Also can be used for finding domains with the same analytics ID.
    """

    def name(self) -> str:
        return "gau"

    def phase(self) -> str:
        return "urls"

    def check_dependencies(self) -> bool:
        """
        Checks if gau is installed.
        """
        return shutil.which("gau") is not None

    def run(self, targets: List[str]) -> List[Dict]:
        """
        Runs gau on a list of domains.
        """
        if not self.check_dependencies():
            print("Gau is not installed. Please install it to use this plugin.")
            return []

        all_findings = []
        for target in targets:
            print(f"Running gau on {target}...")
            command = ["gau", target]
            raw_output = run_command(command)
            if raw_output:
                # Save raw output
                output_dir = f"artifacts/urls/{self.name()}"
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"{target}.txt")
                with open(output_path, "w") as f:
                    f.write(raw_output)

                findings = self.parse(raw_output, target)
                all_findings.extend(findings)
        return all_findings

    def parse(self, raw_output: str, target: str) -> List[Dict]:
        """
        Parses the raw output of gau.
        """
        findings = []
        for url in raw_output.strip().split('\n'):
            if url:
                finding: Finding = {
                    "target": target,
                    "phase": self.phase(),
                    "tool": self.name(),
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "evidence": {"poc": url},
                    "vuln": {
                        "name": "URL Discovered",
                        "severity": "info",
                    },
                    "tags": ["url", "discovery"],
                    "fingerprints": {}
                }
                findings.append(finding)
        return findings
