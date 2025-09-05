import shutil
import time
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
        # Linkfinder is a python script, so we just check for its path in the config
        return os.path.exists(config['tools']['linkfinder'])

    def run(self, targets: List[str], retries: int = 1, timeout: int = 600) -> List[Finding]:
        """
        Takes a list of targets (live hosts/URLs).
        """
        if not self.check_dependencies():
            return [{
                "tool": self.name(), "phase": self.phase(), "target": t,
                "status": "failed", "evidence": None,
                "error": "linkfinder.py script not found."
            } for t in targets]

        all_findings = []
        for target in targets:
            for attempt in range(retries):
                try:
                    tool_path = config['tools']['linkfinder']
                    command = ['python3', tool_path, '-i', target, '-o', 'cli']
                    raw_output = run_command(command, timeout=timeout)
                    if raw_output:
                        findings = self.parse(raw_output, target)
                        all_findings.extend(findings)
                    break
                except ToolExecutionError as e:
                    if attempt < retries - 1:
                        time.sleep(2)
                        continue
                    else:
                        all_findings.append({
                            "tool": self.name(), "phase": self.phase(), "target": target,
                            "status": "failed", "evidence": None, "error": str(e)
                        })
        return all_findings

    def parse(self, raw_output: str, target: str) -> List[Finding]:
        findings = []
        # Linkfinder output can be noisy, we're interested in the endpoints
        for line in raw_output.strip().split('\n'):
            if line.startswith('/'): # A simple heuristic for endpoints
                finding: Finding = {
                    "target": target,
                    "phase": self.phase(),
                    "tool": self.name(),
                    "status": "success",
                    "evidence": {"endpoint": line.strip()},
                    "error": None,
                }
                findings.append(finding)
        return findings
