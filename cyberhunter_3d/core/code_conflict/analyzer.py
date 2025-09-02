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
    requirements.txt files against a database of known vulnerabilities.
    """
    def __init__(self, codebase_path):
        self.codebase_path = codebase_path
        self.vulnerable_packages = self._load_vulnerabilities()

    def _load_vulnerabilities(self):
        """
        Loads the vulnerability database from the JSON files in the vuln_db directory.
        """
        vuln_db = {}
        db_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'vuln_db')
        if not os.path.isdir(db_dir):
            print(f"Warning: Vulnerability database directory not found at {db_dir}")
            return vuln_db

        for filename in os.listdir(db_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(db_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        vuln_data = json.load(f)
                        if 'affected' in vuln_data and len(vuln_data['affected']) > 0:
                            package_name = vuln_data['affected'][0]['package']['name']
                            if package_name not in vuln_db:
                                vuln_db[package_name] = []
                            vuln_db[package_name].append(vuln_data)
                except (json.JSONDecodeError, KeyError):
                    print(f"Warning: Could not parse vulnerability file: {filename}")
        return vuln_db

    def _find_requirements_files(self):
        """
        Finds all requirements.txt files in the codebase path.
        """
        found_files = []
        for root, _, files in os.walk(self.codebase_path):
            if "requirements.txt" in files:
                found_files.append(os.path.join(root, "requirements.txt"))
        return found_files

    def analyze(self):
        """
        Performs the analysis and returns a list of conflicts.
        """
        conflicts = []
        requirements_files = self._find_requirements_files()
        if not requirements_files:
            print(f"Warning: No requirements.txt files found in {self.codebase_path}")
            return conflicts

        req_pattern = re.compile(r'([a-zA-Z0-9_-]+)(?:([<>=!~]{1,2})([0-9a-zA-Z.-]+))?')

        for req_path in requirements_files:
            with open(req_path, 'r') as f:
                lines = f.readlines()

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
                        # No version specified, can't check, so we could either assume
                        # vulnerable or ignore. For now, let's ignore.
                        continue

                    detected_version = version.parse(detected_version_str)

                    for vuln_data in self.vulnerable_packages[package_name]:
                        for affected in vuln_data.get('affected', []):
                            for version_range in affected.get('ranges', []):
                                if version_range['type'] == 'ECOSYSTEM':
                                    introduced = version.parse(version_range['events'][0].get('introduced', '0'))
                                    fixed = version.parse(version_range['events'][1].get('fixed', '9999'))

                                    if introduced <= detected_version < fixed:
                                        conflicts.append({
                                            "type": "Vulnerable Dependency",
                                            "file": os.path.relpath(req_path, self.codebase_path),
                                            "dependency": package_name,
                                            "detected_version": detected_version_str,
                                            "affected_versions": f">= {introduced}, < {fixed}",
                                            "severity": vuln_data.get('database_specific', {}).get('severity', 'UNKNOWN'),
                                            "description": vuln_data.get('summary', 'No summary available.')
                                        })

        return conflicts
