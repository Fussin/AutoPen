import shutil
import re
from typing import List, Dict
from ...common.exec import run_command
from ...common.schema import Finding
from ...common.exceptions import ToolExecutionError
from ...common.utils import load_config

config = load_config()

class NmapDnsPlugin:
    def name(self) -> str: return "nmap-dns-xfer"
    def phase(self) -> str: return "recon-active"

    def check_dependencies(self) -> bool:
        return shutil.which(config['tools']['nmap']) is not None

    def run(self, targets: List[str]) -> List[Dict]:
        if not self.check_dependencies():
            print("Nmap is not installed or configured.")
            return []

        all_findings = []
        for target in targets:
            try:
                tool_path = config['tools']['nmap']
                command = [tool_path, '--script', 'dns-zone-transfer', '-p', '53', target]
                raw_output = run_command(command)
                if raw_output and "dns-zone-transfer:" in raw_output:
                    findings = self.parse(raw_output, target)
                    all_findings.extend(findings)
            except ToolExecutionError as e:
                # Nmap can be noisy on stderr, only show error if zone transfer fails unexpectedly
                if "failed to get zone" not in e.stderr.lower():
                    print(f"Error running Nmap DNS Zone Transfer: {e}")
            except Exception as e:
                print(f"A general error occurred with Nmap DNS plugin: {e}")
        return all_findings

    def parse(self, raw_output: str, target: str) -> List[Dict]:
        findings = []
        # Regex to capture the hostname from a line like:
        # | an.example.com.              300 IN A     192.0.2.1
        pattern = re.compile(r'^\s*\|\s+([\w\-\.]+\.' + re.escape(target) + r')\.')

        for line in raw_output.strip().split('\n'):
            match = pattern.match(line)
            if match:
                subdomain = match.group(1).strip()
                finding: Finding = {
                    "target": target,
                    "phase": self.phase(),
                    "tool": self.name(),
                    "evidence": {"poc": subdomain},
                }
                findings.append(finding)
        return findings
