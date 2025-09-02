"""
This module contains the Code Conflict Analyzer.
"""
import os
import re
from packaging import version

class Analyzer:
    """
    Analyzes a codebase for potential security conflicts by checking
    a requirements.txt file for known vulnerable packages.
    """
    def __init__(self, codebase_path):
        self.codebase_path = codebase_path
        # In a real implementation, this would come from a database or a more robust source.
        self.vulnerable_packages = {
            "django": {
                "affected_versions": "<2.2.17",
                "severity": "High",
                "description": "Django versions before 2.2.17 are vulnerable to SQL injection."
            },
            "requests": {
                "affected_versions": "<2.25.0",
                "severity": "Medium",
                "description": "Requests versions before 2.25.0 are vulnerable to a CRLF injection."
            }
        }

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
        # Handles lines like: requests==2.24.0, django>=2.0, flask
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
                # We found a potentially vulnerable package, now check the version
                detected_version_str = match.group(3)
                if not detected_version_str:
                    # No version specified, so we can't check. Assume vulnerable.
                    is_vulnerable = True
                else:
                    detected_version = version.parse(detected_version_str)

                    # For simplicity, we only handle the '<' specifier from our DB
                    vuln_details = self.vulnerable_packages[package_name]
                    affected_spec = vuln_details["affected_versions"]
                    if affected_spec.startswith('<'):
                        vulnerable_version = version.parse(affected_spec[1:])
                        if detected_version < vulnerable_version:
                            is_vulnerable = True
                        else:
                            is_vulnerable = False
                    else:
                        # Other specifiers not handled in this mock
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
