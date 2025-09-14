import shutil
import time
from typing import List, Dict
from ...common.exec import run_command
from ...common.schema import Finding
from ...common.exceptions import ToolExecutionError
from ...common.utils import load_config

config = load_config()

class NmapScanPlugin:
    def name(self) -> str: return "nmap-service-scan"
    def phase(self) -> str: return "enrichment-service-scan"

    def check_dependencies(self) -> bool:
        return shutil.which(config['tools']['nmap']) is not None

    def run(self, targets: List[Dict], retries: int = 1, timeout: int = 600) -> List[Finding]:
        if not self.check_dependencies():
            return [{"tool": self.name(), "phase": self.phase(), "target": "multiple", "status": "failed", "evidence": None, "error": "nmap tool not found."}]

        all_findings = []
        for target_info in targets:
            host = target_info.get('host')
            port = target_info.get('port')
            if not host or not port: continue

            for attempt in range(retries):
                try:
                    tool_path = config['tools']['nmap']
                    command = [tool_path, '-sV', '-p', str(port), host]
                    raw_output = run_command(command, timeout=timeout)
                    finding: Finding = {
                        "target": host, "phase": self.phase(), "tool": self.name(),
                        "status": "success", "evidence": {"port": str(port), "service_info": raw_output}, "error": None,
                    }
                    all_findings.append(finding)
                    break
                except ToolExecutionError as e:
                    if attempt < retries - 1:
                        time.sleep(2)
                        continue
                    else:
                        all_findings.append({"tool": self.name(), "phase": self.phase(), "target": host, "status": "failed", "evidence": {"port": str(port)}, "error": str(e)})
        return all_findings
