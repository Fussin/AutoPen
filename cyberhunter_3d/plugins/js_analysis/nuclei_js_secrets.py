import shutil
import tempfile
import os
import json
from typing import List, Dict
from ...common.exec import run_command
from ...common.schema import Finding
from ...common.exceptions import ToolExecutionError
from ...common.utils import load_config

config = load_config()

class NucleiJsSecretsPlugin:
    def name(self) -> str: return "nuclei-js-secrets"
    def phase(self) -> str: return "js-analysis-secrets"

    def check_dependencies(self) -> bool:
        return shutil.which(config['tools']['nuclei']) is not None

    def run(self, live_hosts: List[str]) -> List[Finding]:
        if not self.check_dependencies():
            return [{"tool": self.name(), "phase": self.phase(), "target": "multiple", "status": "failed", "evidence": None, "error": "nuclei tool not found."}]

        all_findings = []
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as input_file, \
             tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".json") as output_file:
            input_filename = input_file.name
            output_filename = output_file.name
            input_file.write('\n'.join(live_hosts))

        try:
            tool_path = config['tools']['nuclei']
            command = [tool_path, '-l', input_filename, '-t', 'technologies/javascript/js-secrets.yaml', '-jsonl', '-o', output_filename, '-silent']
            run_command(command)
            with open(output_filename, 'r') as f:
                raw_output = f.read()
            if raw_output:
                findings = self.parse(raw_output)
                all_findings.extend(findings)
        except ToolExecutionError as e:
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
                    "status": "success", "evidence": {
                        "template": data.get('template-id'),
                        "finding_name": data.get('info', {}).get('name'),
                        "matched_at": data.get('matched-at'),
                    }, "error": None,
                }
                findings.append(finding)
            except (json.JSONDecodeError, KeyError):
                pass
        return findings
