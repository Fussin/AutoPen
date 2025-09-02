"""
This module generates the compliance section of the report.
"""

class Compliance:
    """
    Generates the compliance report.
    """
    def __init__(self, data):
        self.data = data
        self.vulnerabilities = self.data.get("vulnerabilities", [])
        # In a real implementation, this mapping would be more sophisticated.
        self.cve_to_owasp = {
            "CVE-2023-1234": "A01:2021-Broken Access Control",
            "CVE-2023-5678": "A02:2021-Cryptographic Failures",
        }
        self.cve_to_cwe = {
            "CVE-2023-1234": "CWE-22: Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')",
            "CVE-2023-5678": "CWE-312: Cleartext Storage of Sensitive Information",
        }

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
