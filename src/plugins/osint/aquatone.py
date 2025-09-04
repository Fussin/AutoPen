import shutil
import os
import tempfile
from typing import List, Dict
from src.common.base_plugin import Plugin
from src.common.exec import run_command
from src.common.schema import Finding
import datetime

class AquatonePlugin(Plugin):
    """
    Aquatone plugin for taking screenshots of websites.
    """

    def name(self) -> str:
        return "aquatone"

    def phase(self) -> str:
        return "osint"

    def check_dependencies(self) -> bool:
        """
        Checks if aquatone is installed.
        """
        return shutil.which("aquatone") is not None

    def run(self, targets: List[str]) -> List[Dict]:
        """
        Runs aquatone on a list of URLs.
        """
        if not self.check_dependencies():
            print("Aquatone is not installed. Please install it to use this plugin.")
            return []

        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp_file:
            tmp_file.write('\n'.join(targets))
            input_filename = tmp_file.name

        output_dir = f"artifacts/osint/{self.name()}"
        os.makedirs(output_dir, exist_ok=True)

        print(f"Running aquatone on {len(targets)} URLs...")
        # Aquatone takes input from stdin
        command = [
            "sh", "-c",
            f"cat {input_filename} | aquatone -out {output_dir}"
        ]

        run_command(command)
        os.remove(input_filename)

        # Aquatone does not produce structured output, it produces a directory of files.
        # We will create a single finding that points to the output directory.
        finding: Finding = {
            "target": " ".join(targets),
            "phase": self.phase(),
            "tool": self.name(),
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "evidence": {"path": output_dir},
            "vuln": {
                "name": "Website Screenshots",
                "severity": "info",
            },
            "tags": ["osint", "screenshot"],
            "fingerprints": {}
        }

        return [finding]

    def parse(self, raw_output: str) -> List[Dict]:
        """
        Aquatone does not produce parsable stdout.
        The run method creates a single finding.
        """
        return []
