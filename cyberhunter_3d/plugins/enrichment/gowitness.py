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

class GowitnessPlugin:
    def name(self) -> str: return "gowitness"
    def phase(self) -> str: return "enrichment-screenshot"

    def check_dependencies(self) -> bool:
        return shutil.which(config['tools']['gowitness']) is not None

    def run(self, live_urls: List[str], retries: int = 1, timeout: int = 1200) -> List[Finding]:
        if not self.check_dependencies():
            return [{"tool": self.name(), "phase": self.phase(), "target": "multiple", "status": "failed", "evidence": None, "error": "gowitness tool not found."}]

        all_findings = []
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
            input_filename = tmp_file.name
            tmp_file.write('\n'.join(live_urls))

        output_dir = os.path.join(config['screenshot_dir'], 'gowitness')
        os.makedirs(output_dir, exist_ok=True)

        for attempt in range(retries):
            try:
                tool_path = config['tools']['gowitness']
                command = [tool_path, 'file', '-f', input_filename, '--screenshot-path', output_dir]
                run_command(command, timeout=timeout)
                all_findings.append({
                    "tool": self.name(), "phase": self.phase(), "target": "multiple",
                    "status": "success", "evidence": {"screenshot_dir": output_dir}, "error": None
                })
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
