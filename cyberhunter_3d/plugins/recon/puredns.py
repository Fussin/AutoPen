import shutil
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

    def run(self, targets: List[str], wordlist: str, resolvers: str) -> List[Dict]:
        if not self.check_dependencies():
            print("PureDNS is not installed or configured.")
            return []

        all_findings = []
        for target in targets:
            try:
                tool_path = config['tools']['puredns']
                # puredns bruteforce [wordlist] [target] -r [resolvers] --output stdout --quiet
                command = [
                    tool_path, 'bruteforce', wordlist, target,
                    '-r', resolvers, '--output', 'stdout', '--quiet'
                ]
                raw_output = run_command(command)
                if raw_output:
                    findings = self.parse(raw_output, target)
                    all_findings.extend(findings)
            except ToolExecutionError as e:
                print(f"Error running PureDNS: {e}")
        return all_findings

    def parse(self, raw_output: str, target: str) -> List[Finding]:
        findings = []
        for subdomain in raw_output.strip().split('\n'):
            if subdomain and target in subdomain:
                finding: Finding = {
                    "target": target,
                    "phase": self.phase(),
                    "tool": self.name(),
                    "evidence": {"poc": subdomain.strip()},
                }
                findings.append(finding)
        return findings
