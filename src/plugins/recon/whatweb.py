import shutil
import os
import json
from typing import List, Dict
from src.common.base_plugin import Plugin
from src.common.exec import run_command
from src.common.schema import Finding
import datetime

class WhatWebPlugin(Plugin):
    """
    WhatWeb plugin for technology identification.
    """

    def name(self) -> str:
        return "whatweb"

    def phase(self) -> str:
        return "recon"

    def check_dependencies(self) -> bool:
        """
        Checks if whatweb is installed.
        """
        return shutil.which("whatweb") is not None

    def run(self, targets: List[str]) -> List[Dict]:
        """
        Runs whatweb on a list of URLs.
        """
        if not self.check_dependencies():
            print("WhatWeb is not installed. Please install it to use this plugin.")
            return []

        all_findings = []
        for target in targets:
            print(f"Running whatweb on {target}...")

            output_dir = f"artifacts/recon/{self.name()}"
            os.makedirs(output_dir, exist_ok=True)
            # WhatWeb's --log-json doesn't append, it overwrites. So we need a unique file per target.
            output_filename = os.path.join(output_dir, f"{target.replace('/', '_')}.json")

            command = [
                "whatweb",
                target,
                f"--log-json={output_filename}"
            ]
            run_command(command)

            if os.path.exists(output_filename):
                with open(output_filename, 'r') as f:
                    raw_output = f.read()
                findings = self.parse(raw_output, target)
                all_findings.extend(findings)

        return all_findings

    def parse(self, raw_output: str, target: str) -> List[Dict]:
        """
        Parses the JSON output of whatweb.
        """
        findings = []
        try:
            # WhatWeb outputs a list of JSON objects
            data = json.loads(raw_output)
            for item in data:
                tech = []
                for plugin, result in item.get("plugins", {}).items():
                    tech.append(plugin)
                    if "version" in result:
                        tech.append(f"{plugin}/{result['version'][0]}")

                if tech:
                    finding: Finding = {
                        "target": target,
                        "phase": self.phase(),
                        "tool": self.name(),
                        "timestamp": datetime.datetime.utcnow().isoformat(),
                        "evidence": {},
                        "vuln": {
                            "name": "Technology Identified",
                            "severity": "info",
                        },
                        "tags": ["tech", "fingerprint"],
                        "fingerprints": {
                            "tech": tech
                        }
                    }
                    findings.append(finding)
        except json.JSONDecodeError:
            print(f"Error decoding WhatWeb JSON output for {target}")
        return findings
