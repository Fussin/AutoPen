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
