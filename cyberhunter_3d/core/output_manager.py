
import os
import json
from datetime import datetime

class OutputManager:
    def __init__(self, output_dir, target_name):
        self.base_dir = os.path.join(output_dir, self._sanitize_filename(target_name))
        self.recon_dir = os.path.join(self.base_dir, 'recon')
        self.scan_dir = os.path.join(self.base_dir, 'scans')
        self.report_dir = os.path.join(self.base_dir, 'reports')
        self._setup_directories()

    def _sanitize_filename(self, name):
        return "".join([c for c in name if c.isalpha() or c.isdigit() or c.isspace()]).rstrip()

    def _setup_directories(self):
        os.makedirs(self.recon_dir, exist_ok=True)
        os.makedirs(self.scan_dir, exist_ok=True)
        os.makedirs(self.report_dir, exist_ok=True)

    def save_json(self, data, filename, subdir='recon'):
        dir_map = {
            'recon': self.recon_dir,
            'scans': self.scan_dir,
            'reports': self.report_dir
        }
        if subdir not in dir_map:
            raise ValueError("Invalid subdirectory specified.")

        filepath = os.path.join(dir_map[subdir], filename)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
        return filepath

    def get_path(self, filename, subdir='recon'):
        dir_map = {
            'recon': self.recon_dir,
            'scans': self.scan_dir,
            'reports': self.report_dir
        }
        if subdir not in dir_map:
            raise ValueError("Invalid subdirectory specified.")

        return os.path.join(dir_map[subdir], filename)


import json
from pathlib import Path

class OutputManager:
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.recon_dir = self.base_dir / "recon"
        self.network_dir = self.base_dir / "network"
        self.discovery_dir = self.base_dir / "discovery"
        self.vulns_dir = self.base_dir / "vulnerabilities"
        self._create_dirs()

    def _create_dirs(self):
        self.recon_dir.mkdir(parents=True, exist_ok=True)
        self.network_dir.mkdir(parents=True, exist_ok=True)
        self.discovery_dir.mkdir(parents=True, exist_ok=True)
        self.vulns_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def create_for_timestamp(cls, base_path):
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = Path(base_path) / timestamp
        return cls(output_dir)

    def write_recon_file(self, filename, content):
        (self.recon_dir / filename).write_text(content)

    def write_network_json(self, filename, data):
        with open(self.network_dir / filename, 'w') as f:
            json.dump(data, f, indent=2)

    def write_discovery_file(self, filename, content):
        (self.discovery_dir / filename).write_text(content)

    def add_vulnerability(self, vuln_data, severity="info"):
        pass

    def produce_metadata(self):
        pass

    def finalize(self, generate_pdf=False, generate_docx=False):
        return {}

class OutputManager:
    """
    This is a placeholder class to fix the ImportError.
    """
    pass

