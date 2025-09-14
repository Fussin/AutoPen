import shutil
import tempfile
import os
from typing import List, Dict
from ...common.exec import run_command
from ...common.schema import Finding
from ...common.exceptions import ToolExecutionError
from ...common.utils import load_config

config = load_config()

class GoblobPlugin:
    def name(self) -> str: return "goblob"
    def phase(self) -> str: return "cloud-asset-enum-azure"

    def check_dependencies(self) -> bool:
        return shutil.which(config['tools']['goblob']) is not None

    def run(self, potential_names: List[str]) -> List[Finding]:
        if not self.check_dependencies():
            return [{"tool": self.name(), "phase": self.phase(), "target": "multiple", "status": "failed", "evidence": None, "error": "goblob tool not found."}]

        all_findings = []
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
            input_filename = tmp_file.name
            tmp_file.write('\n'.join(potential_names))

        try:
            tool_path = config['tools']['goblob']
            command = [tool_path, '-accounts', input_filename, '-silent']
            raw_output = run_command(command)
            if raw_output:
                findings = self.parse(raw_output)
                all_findings.extend(findings)
        except ToolExecutionError as e:
            all_findings.append({"tool": self.name(), "phase": self.phase(), "target": "multiple", "status": "failed", "evidence": None, "error": str(e)})
        finally:
            os.remove(input_filename)

        return all_findings

    def parse(self, raw_output: str) -> List[Finding]:
        findings = []
        for line in raw_output.strip().split('\n'):
            if line:
                finding: Finding = {
                    "target": line.strip(), "phase": self.phase(), "tool": self.name(),
                    "status": "success", "evidence": {"azure_blob": line.strip()}, "error": None,
                }
                findings.append(finding)
        return findings
