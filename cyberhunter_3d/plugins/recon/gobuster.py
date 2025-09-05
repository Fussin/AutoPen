import shutil
import re
import time
from typing import List, Dict
from ...common.exec import run_command
from ...common.schema import Finding
from ...common.exceptions import ToolExecutionError
from ...common.utils import load_config

config = load_config()

class GobusterPlugin:
    def name(self) -> str: return "gobuster"
    def phase(self) -> str: return "recon-active"

    def check_dependencies(self) -> bool:
        return shutil.which(config['tools']['gobuster']) is not None

    def run(self, targets: List[str], wordlist: str, retries: int = 1, timeout: int = 600) -> List[Dict]:
        if not self.check_dependencies():
            return [{
                "tool": self.name(), "phase": self.phase(), "target": t,
                "status": "failed", "evidence": None,
                "error": "Gobuster tool not found."
            } for t in targets]

        all_findings = []
        for target in targets:
            for attempt in range(retries):
                try:
                    tool_path = config['tools']['gobuster']
                    command = [tool_path, 'dns', '-d', target, '-w', wordlist, '-q', '--no-color', '--no-error']
                    raw_output = run_command(command, timeout=timeout)
                    if raw_output:
                        findings = self.parse(raw_output, target)
                        all_findings.extend(findings)
                    break # Success
                except ToolExecutionError as e:
                    # Gobuster can exit with non-zero status if no domains are found. This is not a true failure.
                    if "found no valid domain" in e.stderr.lower():
                        break # Not an error, just no results. Exit retry loop.

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
        pattern = re.compile(r'Found:\s*(.*)', re.IGNORECASE)
        for line in raw_output.strip().split('\n'):
            match = pattern.match(line.strip())
            if match:
                subdomain = match.group(1).strip()
                if subdomain.endswith(target):
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
