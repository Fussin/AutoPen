import shutil
from typing import List, Dict
from ...common.base_plugin import Plugin
from ...common.exec import run_command
from ...common.schema import Finding
from ...common.exceptions import ToolExecutionError
import datetime
import os

class SubfinderPlugin(Plugin):
    """
    Subfinder plugin for subdomain enumeration.
    """

    def name(self) -> str:
        return "subfinder"

    def phase(self) -> str:
        return "recon"

    def check_dependencies(self) -> bool:
        return shutil.which("subfinder") is not None

    def run(self, targets: List[str]) -> List[Dict]:
        if not self.check_dependencies():
            print("Subfinder is not installed. Please install it to use this plugin.")
            return []

        all_findings = []
        for target in targets:
            print(f"Running subfinder on {target}...")
            command = ["subfinder", "-d", target, "-silent"]

            try:
                raw_output = run_command(command)
                if raw_output:
                    findings = self.parse(raw_output, target)
                    all_findings.extend(findings)
            except ToolExecutionError as e:
                print(f"Error running subfinder on {target}: {e}")

        return all_findings

    def parse(self, raw_output: str, target: str) -> List[Dict]:
        findings = []
        for subdomain in raw_output.strip().split('\n'):
            if subdomain:
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
                    "fingerprints": {},
                    "risk_score": 0.0
                }
                findings.append(finding)
        return findings

    def accepted_target_types(self) -> List[str]:
        return ["domain"]
