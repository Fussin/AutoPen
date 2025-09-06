import shutil
import os
import time
from typing import List, Dict
from ...common.exec import run_command
from ...common.schema import Finding
from ...common.exceptions import ToolExecutionError
from ...common.utils import load_config

config = load_config()

class AquatonePlugin:
    def name(self) -> str: return "aquatone"
    def phase(self) -> str: return "enrichment-screenshot"

    def check_dependencies(self) -> bool:
        return shutil.which(config['tools']['aquatone']) is not None

    def run(self, live_urls: List[str], retries: int = 1, timeout: int = 1200) -> List[Finding]:
        if not self.check_dependencies():
            return [{"tool": self.name(), "phase": self.phase(), "target": "multiple", "status": "failed", "evidence": None, "error": "aquatone tool not found."}]

        all_findings = []
        input_data = '\n'.join(live_urls)
        output_dir = os.path.join(config['screenshot_dir'], 'aquatone')

        for attempt in range(retries):
            try:
                tool_path = config['tools']['aquatone']
                command = [tool_path, '-out', output_dir]
                run_command(command, timeout=timeout, input_data=input_data)
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
        return all_findings
