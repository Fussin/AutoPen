import shutil
import tempfile
import os
from typing import List, Dict
from ...common.exec import run_command
from ...common.schema import Finding
from ...common.exceptions import ToolExecutionError
from ...common.utils import load_config

config = load_config()

class S3ScannerPlugin:
    def name(self) -> str: return "s3scanner"
    def phase(self) -> str: return "cloud-asset-enum-s3-gcp"

    def check_dependencies(self) -> bool:
        return shutil.which(config['tools']['s3scanner']) is not None

    def run(self, potential_names: List[str], provider: str) -> List[Finding]:
        if not self.check_dependencies():
            return [{"tool": self.name(), "phase": self.phase(), "target": f"multiple-{provider}", "status": "failed", "evidence": None, "error": "s3scanner tool not found."}]

        all_findings = []
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
            input_filename = tmp_file.name
            tmp_file.write('\n'.join(potential_names))

        try:
            tool_path = config['tools']['s3scanner']
            command = [tool_path, '-provider', provider, '-bucket-file', input_filename]
            raw_output = run_command(command)
            if raw_output:
                findings = self.parse(raw_output, provider)
                all_findings.extend(findings)
        except ToolExecutionError as e:
            all_findings.append({"tool": self.name(), "phase": self.phase(), "target": f"multiple-{provider}", "status": "failed", "evidence": None, "error": str(e)})
        finally:
            os.remove(input_filename)

        return all_findings

    def parse(self, raw_output: str, provider: str) -> List[Finding]:
        findings = []
        for line in raw_output.strip().split('\n'):
            if "is readable" in line or "exists" in line:
                bucket_name = line.split()[0]
                finding: Finding = {
                    "target": bucket_name, "phase": self.phase(), "tool": f"{self.name()}-{provider}",
                    "status": "success", "evidence": {f"{provider}_bucket": bucket_name, "details": line.strip()}, "error": None,
                }
                findings.append(finding)
        return findings
