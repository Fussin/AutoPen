import shutil
import tempfile
import os
import time
import json
from typing import List, Dict
from ...common.exec import run_command
from ...common.schema import Finding
from ...common.exceptions import ToolExecutionError
from ...common.utils import load_config

config = load_config()

class NaabuPlugin:
    def name(self) -> str: return "naabu"
    def phase(self) -> str: return "enrichment-portscan"

    def check_dependencies(self) -> bool:
        return shutil.which(config['tools']['naabu']) is not None

    def run(self, live_hosts: List[str], retries: int = 1, timeout: int = 1200) -> List[Finding]:
        if not self.check_dependencies():
            return [{"tool": self.name(), "phase": self.phase(), "target": "multiple", "status": "failed", "evidence": None, "error": "naabu tool not found."}]

        all_findings = []
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as input_file, \
             tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".json") as output_file:
            input_filename = input_file.name
            output_filename = output_file.name
            input_file.write('\n'.join(live_hosts))

        for attempt in range(retries):
            try:
                tool_path = config['tools']['naabu']
                command = [tool_path, '-list', input_filename, '-top-ports', '1000', '-jsonl', '-o', output_filename]
                run_command(command, timeout=timeout)
                with open(output_filename, 'r') as f:
                    raw_output = f.read()
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
                os.remove(output_filename)
        return all_findings

    def parse(self, raw_output: str) -> List[Finding]:
        findings = []
        for line in raw_output.strip().split('\n'):
            if not line: continue
            try:
                data = json.loads(line)
                finding: Finding = {
                    "target": data.get('host'), "phase": self.phase(), "tool": self.name(),
                    "status": "success", "evidence": {"port": str(data.get('port')), "ip": data.get('ip')}, "error": None,
                }
                findings.append(finding)
            except (json.JSONDecodeError, KeyError):
                pass
        return findings
