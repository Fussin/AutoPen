import shutil
import tempfile
import os
from typing import List, Dict
from ...common.exec import run_command
from ...common.schema import Finding
from ...common.exceptions import ToolExecutionError
from ...common.utils import load_config

config = load_config()

class GotatorPlugin:
    def name(self) -> str: return "gotator"
    def phase(self) -> str: return "recon-permutation"

    def check_dependencies(self) -> bool:
        return shutil.which(config['tools']['gotator']) is not None

    def run(self, subdomains: List[str], wordlist_path: str) -> List[Finding]:
        if not self.check_dependencies():
            return [{
                "tool": self.name(), "phase": self.phase(), "target": "multiple",
                "status": "failed", "evidence": None,
                "error": "gotator tool not found."
            }]

        all_findings = []
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
            subdomain_filename = tmp_file.name
            tmp_file.write('\n'.join(subdomains))

        try:
            tool_path = config['tools']['gotator']
            command = [
                tool_path, '-sub', subdomain_filename, '-perm', wordlist_path,
                '-depth', '2', '-mindup', '-silent'
            ]
            raw_output = run_command(command)
            if raw_output:
                findings = self.parse(raw_output, "multiple_targets")
                all_findings.extend(findings)
        except ToolExecutionError as e:
            all_findings.append({
                "tool": self.name(), "phase": self.phase(), "target": "multiple_targets",
                "status": "failed", "evidence": None, "error": str(e)
            })
        finally:
            os.remove(subdomain_filename)

        return all_findings

    def parse(self, raw_output: str, target: str) -> List[Finding]:
        findings = []
        for subdomain in raw_output.strip().split('\n'):
            if subdomain:
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
