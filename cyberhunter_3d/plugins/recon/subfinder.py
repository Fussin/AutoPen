import shutil
import time
from typing import List, Dict
from ...common.exec import run_command
from ...common.schema import Finding
from ...common.exceptions import ToolExecutionError
from ...common.utils import load_config

config = load_config()

class SubfinderPlugin:
    def name(self) -> str: return "subfinder"
    def phase(self) -> str: return "recon"

    def check_dependencies(self) -> bool:
        return shutil.which(config['tools']['subfinder']) is not None

    def run(self, targets: List[str], retries: int = 1, timeout: int = 300) -> List[Dict]:
        if not self.check_dependencies():
            return [{
                "tool": self.name(), "phase": self.phase(), "target": t,
                "status": "failed", "evidence": None,
                "error": "Subfinder tool not found."
            } for t in targets]

        all_findings = []
        for target in targets:
            for attempt in range(retries):
                try:
                    tool_path = config['tools']['subfinder']
                    command = [tool_path, "-d", target, "-silent"]
                    raw_output = run_command(command, timeout=timeout)
                    if raw_output:
                        findings = self.parse(raw_output, target)
                        all_findings.extend(findings)
                    break  # Success, exit retry loop
                except ToolExecutionError as e:
                    if attempt < retries - 1:
                        time.sleep(2)  # Wait 2s before retrying
                        continue
                    else:
                        all_findings.append({
                            "tool": self.name(), "phase": self.phase(), "target": target,
                            "status": "failed", "evidence": None, "error": str(e)
                        })
        return all_findings

    def parse(self, raw_output: str, target: str) -> List[Dict]:
        findings = []
        for subdomain in raw_output.strip().split('\n'):
            if subdomain:
                finding: Finding = {
                    "target": target,
                    "phase": self.phase(),
                    "tool": self.name(),
                    "status": "success",
                    "evidence": {"poc": subdomain},
                    "error": None,
                }
                findings.append(finding)
        return findings
