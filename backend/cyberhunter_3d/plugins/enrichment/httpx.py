import shutil
import tempfile
import os
import time
from typing import List, Dict
from ...common.exec import run_command
from ...common.schema import Finding
from ...common.exceptions import ToolExecutionError
from ...common.utils import load_config

config = load_config()

class HttpxPlugin:
    def name(self) -> str: return "httpx"
    def phase(self) -> str: return "enrichment-live-hosts"

    def check_dependencies(self) -> bool:
        return shutil.which(config['tools']['httpx']) is not None

    def run(self, subdomains: List[str], retries: int = 1, timeout: int = 600) -> List[Finding]:
        if not self.check_dependencies():
            return [{"tool": self.name(), "phase": self.phase(), "target": "multiple", "status": "failed", "evidence": None, "error": "httpx tool not found."}]

        all_findings = []
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
            input_filename = tmp_file.name
            tmp_file.write('\n'.join(subdomains))

        for attempt in range(retries):
            try:
                tool_path = config['tools']['httpx']
                command = [tool_path, '-l', input_filename, '-p', '80,443,8080,8000', '-silent']
                raw_output = run_command(command, timeout=timeout)
                if raw_output:
                    findings = self.parse(raw_output)
                    all_findings.extend(findings)
                break
            except ToolExecutionError as e:
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
                else:
                    all_findings.append({"tool": self.name(), "phase": self.phase(), "target": "multiple", "status": "failed", "evidence": None, "error": str(e)})
            finally:
                os.remove(input_filename)
        return all_findings

    def parse(self, raw_output: str) -> List[Finding]:
        findings = []
        for live_host in raw_output.strip().split('\n'):
            if live_host:
                finding: Finding = {
                    "target": live_host.strip(), "phase": self.phase(), "tool": self.name(),
                    "status": "success", "evidence": {"live_url": live_host.strip()}, "error": None,
                }
                findings.append(finding)
        return findings
