import shutil
import os
import json
from typing import List, Dict
from src.common.base_plugin import Plugin
from src.common.exec import run_command
from src.common.schema import Finding
import datetime

class TrufflehogPlugin(Plugin):
    """
    TruffleHog plugin for secrets scanning in git repositories.
    """

    def name(self) -> str:
        return "trufflehog"

    def phase(self) -> str:
        return "vuln"

    def check_dependencies(self) -> bool:
        """
        Checks if trufflehog is installed.
        """
        return shutil.which("trufflehog") is not None

    def run(self, targets: List[str]) -> List[Dict]:
        """
        Runs trufflehog on a list of git repository URLs.
        """
        if not self.check_dependencies():
            print("TruffleHog is not installed. Please install it to use this plugin.")
            return []

        all_findings = []
        for target in targets:
            print(f"Running trufflehog on {target}...")

            # TruffleHog can be slow on large repositories.
            command = [
                "trufflehog",
                "git",
                target,
                "--json"
            ]

            raw_output = run_command(command)
            if raw_output:
                output_dir = f"artifacts/vuln/{self.name()}"
                os.makedirs(output_dir, exist_ok=True)
                safe_target_name = target.replace('/', '_').replace(':', '_')
                output_path = os.path.join(output_dir, f"{safe_target_name}.json")
                with open(output_path, "w") as f:
                    f.write(raw_output)

                findings = self.parse(raw_output, target)
                all_findings.extend(findings)

        return all_findings

    def parse(self, raw_output: str, target: str) -> List[Dict]:
        """
        Parses the JSON output of trufflehog.
        """
        findings = []
        for line in raw_output.strip().split('\n'):
            if line:
                try:
                    data = json.loads(line)
                    finding: Finding = {
                        "target": target,
                        "phase": self.phase(),
                        "tool": self.name(),
                        "timestamp": datetime.datetime.utcnow().isoformat(),
                        "evidence": {
                            "path": data.get("SourceMetadata", {}).get("Data", {}).get("Git", {}).get("file"),
                            "snippet": data.get("Raw"),
                            "poc": f"Secret found in commit {data.get('SourceMetadata', {}).get('Data', {}).get('Git', {}).get('commit')}"
                        },
                        "vuln": {
                            "id": data.get("DetectorName"),
                            "name": f"Secret Detected: {data.get('DetectorName')}",
                            "severity": "high", # Secrets are usually high or critical
                        },
                        "tags": ["secret", "vuln", "git"],
                        "fingerprints": {}
                    }
                    findings.append(finding)
                except json.JSONDecodeError:
                    print(f"Error decoding TruffleHog JSON line: {line}")
        return findings
