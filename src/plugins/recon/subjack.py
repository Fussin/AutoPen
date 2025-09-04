import shutil
import os
import tempfile
import json
from typing import List, Dict
from src.common.base_plugin import Plugin
from src.common.exec import run_command
from src.common.schema import Finding
import datetime

class SubjackPlugin(Plugin):
    """
    Subjack plugin for subdomain takeover vulnerability detection.
    """

    def name(self) -> str:
        return "subjack"

    def phase(self) -> str:
        return "recon"

    def check_dependencies(self) -> bool:
        """
        Checks if subjack is installed.
        """
        return shutil.which("subjack") is not None

    def run(self, targets: List[str]) -> List[Dict]:
        """
        Runs subjack on a list of subdomains.
        """
        if not self.check_dependencies():
            print("Subjack is not installed. Please install it to use this plugin.")
            return []

        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp_file:
            tmp_file.write('\n'.join(targets))
            input_filename = tmp_file.name

        output_dir = f"artifacts/recon/{self.name()}"
        os.makedirs(output_dir, exist_ok=True)
        output_filename = os.path.join(output_dir, "takeover_findings.json")

        print(f"Running subjack on {len(targets)} subdomains...")
        command = [
            "subjack",
            "-w", input_filename,
            "-o", output_filename,
            "-ssl", # Enable SSL to check https versions
            "-json" # Output in JSON format
        ]
        run_command(command)
        os.remove(input_filename)

        all_findings = []
        if os.path.exists(output_filename):
            with open(output_filename, 'r') as f:
                raw_output = f.read()
            findings = self.parse(raw_output)
            all_findings.extend(findings)

        return all_findings

    def parse(self, raw_output: str) -> List[Dict]:
        """
        Parses the JSON output of subjack.
        """
        findings = []
        try:
            data = json.loads(raw_output)
            for item in data:
                if item["vulnerable"]:
                    finding: Finding = {
                        "target": item["subdomain"],
                        "phase": self.phase(),
                        "tool": self.name(),
                        "timestamp": datetime.datetime.utcnow().isoformat(),
                        "evidence": {
                            "poc": f"Subdomain {item['subdomain']} is vulnerable to takeover via {item['service']}.",
                            "snippet": f"Service: {item['service']}, Fingerprint: {item['fingerprint']}"
                        },
                        "vuln": {
                            "id": "subdomain-takeover",
                            "name": "Subdomain Takeover",
                            "severity": "high",
                        },
                        "tags": ["takeover", "vuln"],
                        "fingerprints": {"services": [item['service']]}
                    }
                    findings.append(finding)
        except json.JSONDecodeError:
            print("Error decoding Subjack JSON output.")
        return findings
