"""
This module contains the Code Conflict Analyzer.
"""
import os
import re
import json
from packaging import version

class Analyzer:
    """
    Analyzes a codebase for potential security conflicts by checking
    a requirements.txt file for known vulnerable packages.
    """
    def __init__(self, codebase_path):
        self.codebase_path = codebase_path
        self.vulnerable_packages = self._load_vulnerabilities()

    def _load_vulnerabilities(self):
        """
        Loads the vulnerability database from the JSON file.
        """
        db_path = os.path.join(os.path.dirname(__file__), 'vulnerable_packages.json')
        try:
            with open(db_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print(f"Warning: Vulnerability database not found or corrupted at {db_path}")
            return {}

    def analyze(self):
        """
        Performs the analysis and returns a list of conflicts.
        """
        conflicts = []
        requirements_path = os.path.join(self.codebase_path, "requirements.txt")

        if not os.path.exists(requirements_path):
            print(f"Warning: requirements.txt not found at {requirements_path}")
            return conflicts

        with open(requirements_path, 'r') as f:
            lines = f.readlines()

        # Regex to capture package name and version
        req_pattern = re.compile(r'([a-zA-Z0-9_-]+)(?:([<>=!~]{1,2})([0-9a-zA-Z.-]+))?')

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            match = req_pattern.match(line)
            if not match:
                continue

            package_name = match.group(1).lower()

            if package_name in self.vulnerable_packages:
                detected_version_str = match.group(3)
                if not detected_version_str:
                    is_vulnerable = True
                else:
                    detected_version = version.parse(detected_version_str)
                    vuln_details = self.vulnerable_packages[package_name]
                    affected_spec = vuln_details["affected_versions"]
                    if affected_spec.startswith('<'):
                        vulnerable_version = version.parse(affected_spec[1:])
                        if detected_version < vulnerable_version:
                            is_vulnerable = True
                        else:
                            is_vulnerable = False
                    else:
                        is_vulnerable = False

                if is_vulnerable:
                    vuln_details = self.vulnerable_packages[package_name]
                    conflicts.append({
                        "type": "Vulnerable Dependency",
                        "file": "requirements.txt",
                        "dependency": package_name,
                        "detected_version": detected_version_str or "Not specified",
                        "affected_versions": vuln_details["affected_versions"],
                        "severity": vuln_details["severity"],
                        "description": vuln_details["description"]
                    })

        return conflicts
