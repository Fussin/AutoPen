import shutil
import re
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

    def run(self, targets: List[str], wordlist: str) -> List[Dict]:
        if not self.check_dependencies():
            print("Gobuster is not installed or configured.")
            return []

        all_findings = []
        for target in targets:
            try:
                tool_path = config['tools']['gobuster']
                # We remove the -o flag to capture stdout
                command = [tool_path, 'dns', '-d', target, '-w', wordlist, '-q', '--no-color', '--no-error']
                raw_output = run_command(command)
                if raw_output:
                    findings = self.parse(raw_output, target)
                    all_findings.extend(findings)
            except ToolExecutionError as e:
                # Gobuster exits with status 1 if no domains are found, which is not a true error.
                if "found no valid domain" not in e.stderr.lower():
                    print(f"Error running Gobuster: {e}")
            except Exception as e:
                print(f"A general error occurred with Gobuster plugin: {e}")
        return all_findings

    def parse(self, raw_output: str, target: str) -> List[Dict]:
        findings = []
        # Gobuster's output format is typically "Found: subdomain.domain.com"
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
                        "evidence": {"poc": subdomain},
                    }
                    findings.append(finding)
        return findings
