"""
This module generates the compliance section of the report.
"""
import json
import os

class Compliance:
    """
    Generates the compliance report.
    """
    def __init__(self, data):
        self.data = data
        self.vulnerabilities = self.data.get("vulnerabilities", [])
        self.mappings_dir = os.path.join(os.path.dirname(__file__), 'mappings')
        self.cve_to_owasp = self._load_mapping('cve_to_owasp.json')
        self.cve_to_cwe = self._load_mapping('cve_to_cwe.json')

    def _load_mapping(self, filename):
        """
        Loads a mapping from a JSON file.
        """
        try:
            with open(os.path.join(self.mappings_dir, filename), 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def generate(self):
        """
        Generates the compliance content.
        """
        owasp_mapping = self._map_to_owasp()
        cwe_mapping = self._map_to_cwe()

        return {
            "title": "Compliance Report",
            "owasp_top_10": owasp_mapping,
            "cwe_classification": cwe_mapping,
        }

    def _map_to_owasp(self):
        """
        Maps vulnerabilities to the OWASP Top 10.
        """
        mapping = {}
        for vuln in self.vulnerabilities:
            cve = vuln.get("cve")
            if cve in self.cve_to_owasp:
                mapping[cve] = self.cve_to_owasp[cve]
        return mapping

    def _map_to_cwe(self):
        """
        Maps vulnerabilities to CWE classifications.
        """
        mapping = {}
        for vuln in self.vulnerabilities:
            cve = vuln.get("cve")
            if cve in self.cve_to_cwe:
                mapping[cve] = self.cve_to_cwe[cve]
        return mapping
