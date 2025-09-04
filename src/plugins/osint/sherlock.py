import shutil
import os
from typing import List, Dict
from src.common.base_plugin import Plugin
from src.common.exec import run_command
from src.common.schema import Finding
import datetime

class SherlockPlugin(Plugin):
    """
    Sherlock plugin for finding usernames across social networks.
    """

    def name(self) -> str:
        return "sherlock"

    def phase(self) -> str:
        return "osint"

    def check_dependencies(self) -> bool:
        """
        Checks if sherlock is installed.
        """
        return shutil.which("sherlock") is not None

    def run(self, targets: List[str]) -> List[Dict]:
        """
        Runs sherlock on a list of usernames.
        """
        if not self.check_dependencies():
            print("Sherlock is not installed. Please install it to use this plugin.")
            return []

        all_findings = []
        for target in targets: # target is a username
            print(f"Running sherlock on {target}...")

            output_dir = f"artifacts/osint/{self.name()}"
            os.makedirs(output_dir, exist_ok=True)
            output_filename = os.path.join(output_dir, f"{target}.txt")

            command = [
                "sherlock",
                target,
                "--output", output_dir
            ]

            # Sherlock prints to stdout and also saves to a file.
            raw_output = run_command(command)

            # The output file is named after the user, so we need to read that.
            if os.path.exists(output_filename):
                with open(output_filename, 'r') as f:
                    file_content = f.read()
                findings = self.parse(file_content, target)
                all_findings.extend(findings)

        return all_findings

    def parse(self, raw_output: str, target: str) -> List[Dict]:
        """
        Parses the text output of sherlock.
        """
        findings = []
        for line in raw_output.strip().split('\n'):
            if "http" in line:
                url = line.split(":")[-1].strip()
                finding: Finding = {
                    "target": target,
                    "phase": self.phase(),
                    "tool": self.name(),
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "evidence": {"poc": url},
                    "vuln": {
                        "name": "Social Media Account Found",
                        "severity": "info",
                    },
                    "tags": ["osint", "social"],
                    "fingerprints": {}
                }
                findings.append(finding)
        return findings
