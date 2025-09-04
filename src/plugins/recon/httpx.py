import shutil
import os
import tempfile
import json
from typing import List, Dict
from src.common.base_plugin import Plugin
from src.common.exec import run_command
from src.common.schema import Finding
import datetime

class HttpxPlugin(Plugin):
    """
    HTTPx plugin for probing and technology detection.
    """

    def name(self) -> str:
        return "httpx"

    def phase(self) -> str:
        return "recon"

    def check_dependencies(self) -> bool:
        """
        Checks if httpx is installed.
        """
        return shutil.which("httpx") is not None

    def run(self, targets: List[str]) -> List[Dict]:
        """
        Runs httpx on a list of subdomains.
        """
        if not self.check_dependencies():
            print("HTTPx is not installed. Please install it to use this plugin.")
            return []

        all_findings = []
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp_file:
            tmp_file.write('\n'.join(targets))
            input_filename = tmp_file.name

        print(f"Running httpx on {len(targets)} targets...")
        command = [
            "httpx",
            "-l", input_filename,
            "-silent",
            "-json",
            "-status-code",
            "-title",
            "-tls-grab",
            "-tech-detect"
        ]
        raw_output = run_command(command)
        os.remove(input_filename)

        if raw_output:
            # Save raw output
            output_dir = f"artifacts/recon/{self.name()}"
            os.makedirs(output_dir, exist_ok=True)
            # Use a single file for all targets since httpx combines them
            output_path = os.path.join(output_dir, "httpx_results.json")
            with open(output_path, "w") as f:
                f.write(raw_output)

            findings = self.parse(raw_output)
            all_findings.extend(findings)

        return all_findings

    def parse(self, raw_output: str) -> List[Dict]:
        """
        Parses the JSON output of httpx.
        """
        findings = []
        for line in raw_output.strip().split('\n'):
            if line:
                try:
                    data = json.loads(line)
                    finding: Finding = {
                        "target": data.get("url", data.get("input")),
                        "phase": self.phase(),
                        "tool": self.name(),
                        "timestamp": datetime.datetime.utcnow().isoformat(),
                        "evidence": {
                            "poc": data.get("url"),
                            "snippet": f"Status: {data.get('status_code')}, Title: {data.get('title')}"
                        },
                        "vuln": {
                            "name": "Live Host Detected",
                            "severity": "info",
                        },
                        "tags": ["live", "http"],
                        "fingerprints": {
                            "tech": data.get("tech", []),
                            "ports": [data.get("port")],
                            "tls": data.get("tls", {})
                        }
                    }
                    findings.append(finding)
                except json.JSONDecodeError:
                    print(f"Error decoding JSON line: {line}")
        return findings
