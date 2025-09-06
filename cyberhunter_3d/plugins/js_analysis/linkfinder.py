import shutil
import os
from typing import List, Dict
from ...common.exec import run_command
from ...common.schema import Finding
from ...common.exceptions import ToolExecutionError
from ...common.utils import load_config

config = load_config()

class LinkfinderPlugin:
    def name(self) -> str: return "linkfinder"
    def phase(self) -> str: return "js-analysis-endpoints"

    def check_dependencies(self) -> bool:
        return os.path.exists(config['tools']['linkfinder'])

    def run(self, targets: List[str]) -> List[Finding]:
        if not self.check_dependencies():
            return [{"tool": self.name(), "phase": self.phase(), "target": t, "status": "failed", "evidence": None, "error": "linkfinder.py script not found."} for t in targets]

        all_findings = []
        for target in targets:
            try:
                tool_path = config['tools']['linkfinder']
                command = ['python3', tool_path, '-i', target, '-o', 'cli']
                raw_output = run_command(command)
                if raw_output:
                    findings = self.parse(raw_output, target)
                    all_findings.extend(findings)
            except ToolExecutionError as e:
                all_findings.append({"tool": self.name(), "phase": self.phase(), "target": target, "status": "failed", "evidence": None, "error": str(e)})
        return all_findings

    def parse(self, raw_output: str, target: str) -> List[Finding]:
        findings = []
        for line in raw_output.strip().split('\n'):
            if line.startswith('/') and not line.startswith('//'):
                finding: Finding = {
                    "target": target, "phase": self.phase(), "tool": self.name(),
                    "status": "success", "evidence": {"endpoint": line.strip()}, "error": None,
                }
                findings.append(finding)
        return findings
