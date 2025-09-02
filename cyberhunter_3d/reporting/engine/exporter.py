"""
This module exports the report in various formats.
"""
import json

class Exporter:
    """
    Exports the report.
    """
    def __init__(self, report_data):
        self.report_data = report_data

    def to_json(self, path):
        """
        Exports the report to a JSON file.
        """
        with open(path, 'w') as f:
            json.dump(self.report_data, f, indent=4)

    def to_html(self, path):
        """
        Exports the report to an HTML file.
        """
        html = self._generate_html_header()
        html += self._generate_html_body()
        html += self._generate_html_footer()
        with open(path, 'w') as f:
            f.write(html)

    def to_pdf(self, path):
        """
        Exports the report to a PDF file.
        """
        with open(path, 'w') as f:
            f.write("PDF Export (Not Implemented)")

    def _generate_html_header(self):
        return """
        <html>
        <head>
            <title>3D Security Report</title>
            <style>
                body { font-family: sans-serif; margin: 2em; }
                h1, h2, h3 { color: #333; }
                table { border-collapse: collapse; width: 100%; margin-bottom: 1em; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                .card { border: 1px solid #ccc; border-radius: 5px; padding: 1em; margin-bottom: 1em; }
                .monospace { font-family: monospace; background-color: #eee; padding: 2px 4px; }
            </style>
        </head>
        <body>
            <h1>3D Security Report</h1>
        """

    def _generate_html_body(self):
        body = ""
        # Executive Dashboard
        dash = self.report_data.get('executive_dashboard', {})
        body += f"<h2>{dash.get('title')}</h2>"
        body += f"<div class='card'><p>{dash.get('summary')}</p>"
        body += "<h3>KPI Metrics</h3><ul>"
        for key, value in dash.get('kpi_metrics', {}).items():
            body += f"<li><strong>{key.replace('_', ' ').title()}:</strong> {value}</li>"
        body += "</ul>"
        body += "<h3>Risk Heat Map</h3>"
        body += f"<pre>{dash.get('risk_heat_map')}</pre></div>"

        # Technical Deep Dive
        tech = self.report_data.get('technical_deep_dive', {})
        body += f"<h2>{tech.get('title')}</h2>"
        for vuln in tech.get('vulnerabilities', []):
            body += "<div class='card'>"
            body += f"<h3>CVE: {vuln.get('cve')} ({vuln.get('severity')})</h3>"
            body += f"<p><strong>Description:</strong> {vuln.get('description')}</p>"
            body += "</div>"

        # Compliance
        comp = self.report_data.get('compliance', {})
        body += f"<h2>{comp.get('title')}</h2>"
        body += "<div class='card'>"
        body += "<h3>OWASP Top 10 Mapping</h3>"
        for cve, owasp in comp.get('owasp_top_10', {}).items():
            body += f"<p><span class='monospace'>{cve}</span>: {owasp}</p>"
        body += "</div>"

        # Remediation Guide
        remed = self.report_data.get('remediation_guide', {})
        body += f"<h2>{remed.get('title')}</h2>"
        body += "<div class='card'>"
        for cve, rec in remed.get('recommendations', {}).items():
            body += f"<h3>{cve}</h3><p>{rec}</p>"
        body += "</div>"

        return body

    def _generate_html_footer(self):
        return "</body></html>"
