"""
This module generates the executive dashboard section of the report.
"""

class ExecutiveDashboard:
    """
    Generates the executive dashboard.
    """
    def __init__(self, data):
        self.data = data
        self.vulnerabilities = self.data.get("vulnerabilities", [])

    def generate(self):
        """
        Generates the executive dashboard content.
        """
        severity_counts = self._calculate_severity_counts()
        return {
            "title": "Executive Dashboard",
            "summary": f"Security scan for {self.data.get('domain')} identified {len(self.vulnerabilities)} total vulnerabilities.",
            "kpi_metrics": {
                "total_vulnerabilities": len(self.vulnerabilities),
                "critical_vulnerabilities": severity_counts.get("critical", 0),
                "high_vulnerabilities": severity_counts.get("high", 0),
                "medium_vulnerabilities": severity_counts.get("medium", 0),
                "low_vulnerabilities": severity_counts.get("low", 0),
            },
            "risk_heat_map": self._generate_risk_heat_map(severity_counts),
        }

    def _calculate_severity_counts(self):
        """
        Calculates the number of vulnerabilities for each severity level.
        """
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for vuln in self.vulnerabilities:
            severity = vuln.get("severity", "low").lower()
            if severity in counts:
                counts[severity] += 1
        return counts

    def _generate_risk_heat_map(self, severity_counts):
        """
        Generates a textual representation of a risk heat map.
        """
        # This is a simplified textual heat map.
        # In a real 3D engine, this would be a graphical visualization.
        heat_map = []
        for severity, count in severity_counts.items():
            heat_map.append(f"{severity.capitalize()}: {'*' * count}")
        return "\n".join(heat_map)
