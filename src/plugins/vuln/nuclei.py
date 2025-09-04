import shutil
import os
import json
from typing import List, Dict
from src.common.base_plugin import Plugin
from src.common.exec import run_command
from src.common.schema import Finding
import datetime

class NucleiPlugin(Plugin):
    """
    Nuclei plugin for vulnerability scanning.
    """

    def name(self) -> str:
        return "nuclei"

    def phase(self) -> str:
        return "vuln"

    def check_dependencies(self) -> bool:
        """
        Checks if nuclei is installed.
        """
        return shutil.which("nuclei") is not None

    def run(self, targets: List[str], templates: List[str] = None) -> List[Dict]:
        """
        Runs nuclei on a list of targets with a given set of templates.
        If no templates are provided, it uses the default community templates.
        """
        if not self.check_dependencies():
            print("Nuclei is not installed. Please install it to use this plugin.")
            return []

        all_findings = []

        output_dir = f"artifacts/vuln/{self.name()}"
        os.makedirs(output_dir, exist_ok=True)
        # Nuclei can take multiple targets, but let's run one by one for clarity
        for target in targets:
            print(f"Running nuclei on {target}...")

            # Sanitize target for use as a filename
            safe_target_name = target.replace('/', '_').replace(':', '_')
            output_filename = os.path.join(output_dir, f"{safe_target_name}.json")

            command = [
                "nuclei",
                "-u", target,
                "-json",
                "-o", output_filename,
                "-silent"
            ]
            if templates:
                command.extend(["-t", ",".join(templates)])

            run_command(command)

            if os.path.exists(output_filename):
                with open(output_filename, 'r') as f:
                    raw_output = f.read()
                findings = self.parse(raw_output)
                all_findings.extend(findings)

        return all_findings

    def parse(self, raw_output: str) -> List[Dict]:
        """
        Parses the JSONL output of nuclei.
        """
        findings = []
        for line in raw_output.strip().split('\n'):
            if line:
                try:
                    data = json.loads(line)
                    finding: Finding = {
                        "target": data.get("host", data.get("matched-at")),
                        "phase": self.phase(),
                        "tool": self.name(),
                        "timestamp": data.get("timestamp"),
                        "evidence": {
                            "poc": data.get("matched-at"),
                            "snippet": data.get("extracted-results") or data.get("curl-command")
                        },
                        "vuln": {
                            "id": data["template-id"],
                            "name": data["info"]["name"],
                            "severity": data["info"]["severity"],
                        },
                        "tags": list(data["info"].get("tags", [])),
                        "fingerprints": {}
                    }
                    findings.append(finding)
                except json.JSONDecodeError:
                    print(f"Error decoding Nuclei JSON line: {line}")
        return findings
