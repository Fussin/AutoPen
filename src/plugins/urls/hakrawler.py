import shutil
import os
from typing import List, Dict
from src.common.base_plugin import Plugin
from src.common.exec import run_command
from src.common.schema import Finding
import datetime

class HakrawlerPlugin(Plugin):
    """
    Hakrawler plugin for web crawling and URL discovery.
    """

    def name(self) -> str:
        return "hakrawler"

    def phase(self) -> str:
        return "urls"

    def check_dependencies(self) -> bool:
        """
        Checks if hakrawler is installed.
        """
        return shutil.which("hakrawler") is not None

    def run(self, targets: List[str]) -> List[Dict]:
        """
        Runs hakrawler on a list of domains.
        """
        if not self.check_dependencies():
            print("Hakrawler is not installed. Please install it to use this plugin.")
            return []

        all_findings = []
        for target in targets:
            print(f"Running hakrawler on {target}...")
            command = ["hakrawler", "-url", f"https://{target}", "-depth", "2"]
            raw_output = run_command(command)
            if raw_output:
                # Save raw output
                output_dir = f"artifacts/urls/{self.name()}"
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"{target}.txt")
                with open(output_path, "w") as f:
                    f.write(raw_output)

                findings = self.parse(raw_output, target)
                all_findings.extend(findings)
        return all_findings

    def parse(self, raw_output: str, target: str) -> List[Dict]:
        """
        Parses the raw output of hakrawler.
        """
        findings = []
        # Hakrawler output is a list of URLs, sometimes with extra info.
        # e.g., [linkfinder] http://example.com/main.js
        for line in raw_output.strip().split('\n'):
            if line:
                url = line.split()[-1]
                finding: Finding = {
                    "target": target,
                    "phase": self.phase(),
                    "tool": self.name(),
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "evidence": {"poc": url},
                    "vuln": {
                        "name": "URL Discovered",
                        "severity": "info",
                    },
                    "tags": ["url", "discovery", "crawler"],
                    "fingerprints": {}
                }
                findings.append(finding)
        return findings
