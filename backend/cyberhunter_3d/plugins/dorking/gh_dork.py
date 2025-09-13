import shutil
import tempfile
import os
from typing import List, Dict
from ...common.exec import run_command
from ...common.schema import Finding
from ...common.exceptions import ToolExecutionError
from ...common.utils import load_config

config = load_config()

class GhDorkPlugin:
    def name(self) -> str: return "gh-dork"
    def phase(self) -> str: return "dorking-github"

    def check_dependencies(self) -> bool:
        return os.path.exists(config['tools']['gh_dork']) and os.path.exists(config['wordlists']['github_dorks'])

    def run(self, org_names: List[str]) -> List[Finding]:
        if not self.check_dependencies():
            return [{"tool": self.name(), "phase": self.phase(), "target": "multiple", "status": "failed", "evidence": None, "error": "gh-dork.py script or dorks file not found."}]

        all_findings = []
        output_dir = 'gh_dork_results'
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt") as tmp_file:
            orgs_filename = tmp_file.name
            tmp_file.write('\n'.join(org_names))

        try:
            tool_path = config['tools']['gh_dork']
            dorks_file = config['wordlists']['github_dorks']
            command = ['python3', tool_path, '-d', dorks_file, '-of', orgs_filename, '-o', output_dir]
            run_command(command)

            if os.path.exists(output_dir):
                findings = self.parse(output_dir)
                all_findings.extend(findings)
        except ToolExecutionError as e:
            all_findings.append({"tool": self.name(), "phase": self.phase(), "target": "multiple", "status": "failed", "evidence": None, "error": str(e)})
        finally:
            os.remove(orgs_filename)
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)

        return all_findings

    def parse(self, output_dir: str) -> List[Finding]:
        findings = []
        for filename in os.listdir(output_dir):
            with open(os.path.join(output_dir, filename), 'r') as f:
                for line in f:
                    finding: Finding = {
                        "target": "github", "phase": self.phase(), "tool": self.name(),
                        "status": "success", "evidence": {"dork_result": line.strip()}, "error": None,
                    }
                    findings.append(finding)
        return findings
