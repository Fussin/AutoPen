import shutil
import os
import re
from typing import List, Dict
from src.common.base_plugin import Plugin
from src.common.exec import run_command
from src.common.schema import Finding
import datetime

class SqlmapPlugin(Plugin):
    """
    SQLMap plugin for SQL injection testing.
    """

    def name(self) -> str:
        return "sqlmap"

    def phase(self) -> str:
        return "vuln"

    def check_dependencies(self) -> bool:
        """
        Checks if sqlmap is installed.
        """
        return shutil.which("sqlmap") is not None

    def run(self, targets: List[str]) -> List[Dict]:
        """
        Runs sqlmap on a list of URLs.
        """
        if not self.check_dependencies():
            print("SQLMap is not installed. Please install it to use this plugin.")
            return []

        all_findings = []
        for target in targets:
            print(f"Running sqlmap on {target}...")

            output_dir = f"artifacts/vuln/{self.name()}"
            os.makedirs(output_dir, exist_ok=True)
            safe_target_name = target.replace('/', '_').replace(':', '_')
            output_path = os.path.join(output_dir, f"{safe_target_name}.txt")

            # Using --batch to avoid interactive prompts.
            # --crawl=1 to stay on the provided URL.
            # --output-dir to store session files, but we parse the stdout.
            command = [
                "sqlmap",
                "-u", target,
                "--batch",
                "--crawl=1",
                "--output-dir", output_dir
            ]

            # We don't need the return value of run_command directly,
            # as we will parse the log file that sqlmap creates.
            # However, running it to capture stdout can still be useful for debugging.
            raw_output = run_command(command)

            # For sqlmap, it's better to parse the session files than stdout.
            # A simple approach is to look for a log file.
            # A more robust approach would be to use the --save option and parse the saved request.
            # For now, we will parse the stdout.
            if raw_output:
                with open(output_path, "w") as f:
                    f.write(raw_output)
                findings = self.parse(raw_output, target)
                all_findings.extend(findings)

        return all_findings

    def parse(self, raw_output: str, target: str) -> List[Dict]:
        """
        Parses the text output of sqlmap.
        This is a simplified parser.
        """
        findings = []
        # Look for indicators of a vulnerability
        if "the back-end DBMS is" in raw_output and "is vulnerable" in raw_output:
            # Find the injectable parameter
            param_match = re.search(r"Parameter: #1\* \((GET|POST)\)", raw_output)
            param = param_match.group(1) if param_match else "N/A"

            finding: Finding = {
                "target": target,
                "phase": self.phase(),
                "tool": self.name(),
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "evidence": {
                    "poc": f"SQL injection found in parameter: {param}",
                    "snippet": raw_output # The raw output is the evidence
                },
                "vuln": {
                    "id": "CWE-89",
                    "name": "SQL Injection",
                    "severity": "high",
                },
                "tags": ["sqli", "vuln"],
                "fingerprints": {}
            }
            findings.append(finding)
        return findings
