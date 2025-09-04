import shutil
import os
import re
from typing import List, Dict
from src.common.base_plugin import Plugin
from src.common.exec import run_command
from src.common.schema import Finding
import datetime

class Enum4linuxPlugin(Plugin):
    """
    Enum4linux plugin for enumerating Windows/Samba systems.
    """

    def name(self) -> str:
        return "enum4linux"

    def phase(self) -> str:
        return "network"

    def check_dependencies(self) -> bool:
        """
        Checks if enum4linux is installed.
        """
        return shutil.which("enum4linux") is not None

    def run(self, targets: List[str]) -> List[Dict]:
        """
        Runs enum4linux on a list of targets.
        """
        if not self.check_dependencies():
            print("Enum4linux is not installed. Please install it to use this plugin.")
            return []

        all_findings = []
        for target in targets:
            print(f"Running enum4linux on {target}...")

            # -a runs all simple enumeration options
            command = ["enum4linux", "-a", target]

            raw_output = run_command(command)
            if raw_output:
                output_dir = f"artifacts/network/{self.name()}"
                os.makedirs(output_dir, exist_ok=True)
                safe_target_name = target.replace('/', '_').replace(':', '_')
                output_path = os.path.join(output_dir, f"{safe_target_name}.txt")
                with open(output_path, "w") as f:
                    f.write(raw_output)

                findings = self.parse(raw_output, target)
                all_findings.extend(findings)

        return all_findings

    def parse(self, raw_output: str, target: str) -> List[Dict]:
        """
        Parses the text output of enum4linux.
        """
        findings = []

        users = re.findall(r"user:\[(.*?)\]", raw_output)
        shares = re.findall(r"Sharename\s+Type\s+Comment\n\s*---\s*---\s*---\n(.*?)\n\n", raw_output, re.DOTALL)
        os_info = re.search(r"OS Info.*?\[(.*?)\]", raw_output)

        if users:
            finding: Finding = {
                "target": target,
                "phase": self.phase(),
                "tool": self.name(),
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "evidence": {"snippet": f"Users: {', '.join(users)}"},
                "vuln": { "name": "User Information Disclosed", "severity": "low" },
                "tags": ["smb", "enum"],
                "fingerprints": { "users": users }
            }
            findings.append(finding)

        if shares:
            share_list = [s.split()[0] for s in shares[0].strip().split('\n')]
            finding: Finding = {
                "target": target,
                "phase": self.phase(),
                "tool": self.name(),
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "evidence": {"snippet": f"Shares: {', '.join(share_list)}"},
                "vuln": { "name": "Network Shares Disclosed", "severity": "medium" },
                "tags": ["smb", "enum"],
                "fingerprints": { "shares": share_list }
            }
            findings.append(finding)

        if os_info:
            os = os_info.group(1)
            finding: Finding = {
                "target": target,
                "phase": self.phase(),
                "tool": self.name(),
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "evidence": {"snippet": f"OS: {os}"},
                "vuln": { "name": "OS Information Disclosed", "severity": "low" },
                "tags": ["smb", "fingerprint"],
                "fingerprints": { "os": os }
            }
            findings.append(finding)

        return findings
