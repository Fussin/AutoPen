import shutil
from typing import List, Dict
from ...common.exec import run_command
from ...common.schema import Finding
from ...common.exceptions import ToolExecutionError
from ...common.utils import load_config

config = load_config()

class AmassPlugin:
    def name(self) -> str: return "amass"
    def phase(self) -> str: return "recon"

    def check_dependencies(self) -> bool:
        return shutil.which(config['tools']['amass']) is not None

    def run(self, targets: List[str]) -> List[Dict]:
        if not self.check_dependencies():
            # In a real scenario, we might want to return a structured error
            # but for now, we'll follow the pattern of printing and returning empty.
            print("Amass is not installed or configured.")
            return []

        all_findings = []
        for target in targets:
            try:
                tool_path = config['tools']['amass']
                command = [tool_path, "enum", "-passive", "-d", target, "-nolocal", "-nocolor"]
                raw_output = run_command(command)
                if raw_output:
                    findings = self.parse(raw_output, target)
                    all_findings.extend(findings)
            except ToolExecutionError as e:
                print(f"Error running amass: {e}")
        return all_findings

    def parse(self, raw_output: str, target: str) -> List[Dict]:
        findings = []
        for subdomain in raw_output.strip().split('\n'):
            if subdomain:
                finding: Finding = {
                    "target": target,
                    "phase": self.phase(),
                    "tool": self.name(),
                    "evidence": {"poc": subdomain.strip()},
                }
                findings.append(finding)
        return findings
