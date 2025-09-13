import shutil
from typing import List, Dict
from ...common.base_plugin import Plugin
from ...common.exec import run_command
from ...common.exceptions import ToolExecutionError
import datetime

class SubfinderPlugin(Plugin):
    def name(self) -> str: return "subfinder"
    def phase(self) -> str: return "recon"
    def check_dependencies(self) -> bool: return shutil.which("subfinder") is not None

    def run(self, targets: List[str]) -> List[Dict]:
        if not self.check_dependencies():
            print("Subfinder is not installed.")
            return []

        all_findings = []
        for target in targets:
            try:
                command = ["subfinder", "-d", target, "-silent"]
                raw_output = run_command(command)
                if raw_output:
                    findings = self.parse(raw_output, target)
                    all_findings.extend(findings)
            except ToolExecutionError as e:
                print(f"Error running subfinder: {e}")
        return all_findings

    def parse(self, raw_output: str, target: str) -> List[Dict]:
        findings = []
        for subdomain in raw_output.strip().split('\n'):
            if subdomain:
                finding = {
                    "tool": self.name(),
                    "type": "subdomain",
                    "severity": "Info",
                    "evidence": {"subdomain": subdomain, "source_target": target},
                }
                findings.append(finding)
        return findings
