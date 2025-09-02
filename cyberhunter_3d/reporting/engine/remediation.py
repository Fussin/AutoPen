"""
This module generates the remediation guide section of the report.
"""
import json
import os
from datetime import datetime, timedelta

class RemediationGuide:
    """
    Generates the remediation guide.
    """
    def __init__(self, data):
        self.data = data
        self.vulnerabilities = self.data.get("vulnerabilities", [])
        self.mappings_dir = os.path.join(os.path.dirname(__file__), 'mappings')
        self.remediation_db = self._load_mapping('remediation.json')
        self.cve_to_owasp = self._load_mapping('cve_to_owasp.json')

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
        Generates the remediation guide content.
        """
        recommendations = self._generate_recommendations()
        roadmap, timelines = self._generate_roadmap_and_timelines()

        return {
            "title": "Remediation Guide",
            "recommendations": recommendations,
            "priority_roadmap": roadmap,
            "patch_timelines": timelines,
        }

    def _generate_recommendations(self):
        """
        Generates remediation recommendations for each vulnerability.
        """
        recs = {}
        for vuln in self.vulnerabilities:
            cve = vuln.get("cve")
            owasp_category = self.cve_to_owasp.get(cve)
            if owasp_category and owasp_category in self.remediation_db:
                recs[cve] = self.remediation_db[owasp_category]
            else:
                recs[cve] = self.remediation_db.get("default", "No recommendation available.")
        return recs

    def _generate_roadmap_and_timelines(self):
        """
        Generates a prioritized roadmap and suggested timelines based on severity.
        """
        severity_order = {"critical": 1, "high": 2, "medium": 3, "low": 4}
        timeline_map = {"critical": 7, "high": 30, "medium": 90, "low": 180} # days

        sorted_vulns = sorted(self.vulnerabilities, key=lambda v: severity_order.get(v.get("severity", "low").lower(), 5))

        roadmap = [f"Priority {i+1}: Address {v.get('cve')} ({v.get('severity')})" for i, v in enumerate(sorted_vulns)]

        today = datetime.now()
        timelines = {}
        for v in sorted_vulns:
            severity = v.get("severity", "low").lower()
            days = timeline_map.get(severity, 180)
            timelines[v.get('cve')] = f"Suggested completion by: {(today + timedelta(days=days)).strftime('%Y-%m-%d')}"

        return roadmap, timelines
