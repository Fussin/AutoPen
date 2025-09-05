import shutil
import time
from typing import List, Dict
from ...common.exec import run_command
from ...common.schema import Finding
from ...common.exceptions import ToolExecutionError
from ...common.utils import load_config

config = load_config()

class PureDNSPlugin:
    def name(self) -> str: return "puredns"
    def phase(self) -> str: return "recon-active"

    def check_dependencies(self) -> bool:
        return shutil.which(config['tools']['puredns']) is not None

    def run(self, targets: List[str], wordlist: str, resolvers: str, retries: int = 1, timeout: int = 600) -> List[Dict]:
        if not self.check_dependencies():
            return [{
                "tool": self.name(), "phase": self.phase(), "target": t,
                "status": "failed", "evidence": None,
                "error": "PureDNS tool not found."
            } for t in targets]

        all_findings = []
        for target in targets:
            for attempt in range(retries):
                try:
                    tool_path = config['tools']['puredns']
                    command = [
                        tool_path, 'bruteforce', wordlist, target,
                        '-r', resolvers, '--output', 'stdout', '--quiet'
                    ]
                    raw_output = run_command(command, timeout=timeout)
                    if raw_output:
                        findings = self.parse(raw_output, target)
                        all_findings.extend(findings)
                    break  # Success
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

    def parse(self, raw_output: str, target: str) -> List[Dict]:
        findings = []
        for subdomain in raw_output.strip().split('\n'):
            if subdomain and subdomain.endswith(target):
                finding: Finding = {
                    "target": target,
                    "phase": self.phase(),
                    "tool": self.name(),
                    "status": "success",
                    "evidence": {"poc": subdomain.strip()},
                    "error": None,
                }
                findings.append(finding)
        return findings
